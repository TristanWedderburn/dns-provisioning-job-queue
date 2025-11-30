from __future__ import annotations

from datetime import datetime
from typing import List

import yaml
from bson import ObjectId
from pymongo.collection import Collection

from .enums import DesiredState, ReconcileStatus
from .models import Job
from .queue import JobQueue


def apply_config_file(
    coll: Collection,
    queue: JobQueue,
    config_path: str,
) -> None:
    """
    Acts as a tiny 'planner' for the MVP:
    - Reads the YAML config
    - For each record, upserts a dns_records document
      with spec + desired_state=PRESENT
    - Bumps version on change
    - Marks status.reconcileStatus = PENDING
    - Enqueues a reconcile job with (id, target_version)
    """
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    zone_id = data["zone_id"]
    records_data = data.get("records", [])
    now = datetime.utcnow()

    for item in records_data:
        name = item["name"]
        type_ = item["type"]
        ttl = int(item.get("ttl", 60))
        values = [str(v) for v in item.get("values", [])]

        # Try to find an existing record by identity (zone_id + name + type)
        existing = coll.find_one(
            {
                "spec.zoneId": zone_id,
                "spec.name": name,
                "spec.type": type_,
            }
        )

        if existing:
            # Bump version
            current_gen = existing["spec"].get("version", 0)
            new_gen = current_gen + 1

            coll.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "spec.zoneId": zone_id,
                        "spec.name": name,
                        "spec.type": type_,
                        "spec.ttl": ttl,
                        "spec.values": values,
                        "spec.desiredState": DesiredState.PRESENT.value,
                        "spec.version": new_gen,
                        "status.reconcileStatus": ReconcileStatus.PENDING.value,
                        "updatedAt": now,
                    }
                },
            )

            record_id = existing["_id"]
            target_version = new_gen

        else:
            # New record: version starts at 1
            record = {
                "spec": {
                    "zoneId": zone_id,
                    "name": name,
                    "type": type_,
                    "ttl": ttl,
                    "values": values,
                    "desiredState": DesiredState.PRESENT.value,
                    "version": 1,
                },
                "status": {
                    "reconcileStatus": ReconcileStatus.PENDING.value,
                    "observedVersion": 0,
                    "lastError": None,
                    "lastReconciledAt": None,
                },
                "createdAt": now,
                "updatedAt": now,
            }
            result = coll.insert_one(record)
            record_id = result.inserted_id
            target_version = 1

        job = Job(dns_record_id=str(record_id), target_version=target_version)
        queue.enqueue(job)
