from __future__ import annotations

import logging
import threading
from datetime import datetime

from bson import ObjectId
from pymongo.collection import Collection

from .enums import DesiredState, ReconcileStatus
from .models import Job, DnsRecordSpec
from .providers import DnsProvider
from .queue import JobQueue

logger = logging.getLogger(__name__)


def reconcile_dns_record(
    coll: Collection,
    provider: DnsProvider,
    job: Job,
) -> None:
    """
    Reconcile a single dns_records document to its desired state.
    Uses resource doc as the source-of-truth.
    """
    doc = coll.find_one({"_id": ObjectId(job.dns_record_id)})
    if not doc:
        logger.info(
            "Record %s no longer exists; treating job as no-op",
            job.dns_record_id,
        )
        return

    spec = doc["spec"]
    status = doc["status"]

    current_version = spec["version"]
    desired_state = DesiredState(spec["desiredState"])

    # Job is stale if spec moved on since it was queued
    if current_version != job.target_version:
        logger.info(
            "Stale job for record %s (job gen=%s, current gen=%s); no-op",
            job.dns_record_id,
            job.target_version,
            current_version,
        )
        return

    # Optional: mark APPLYING
    # TODO: Consider not having intermediate states?
    coll.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "status.reconcileStatus": ReconcileStatus.APPLYING.value,
            }
        },
    )

    now = datetime.utcnow()

    try:
        if desired_state == DesiredState.PRESENT:
            record_spec = DnsRecordSpec(
                zone_id=spec["zoneId"],
                name=spec["name"],
                type=spec["type"],
                ttl=spec["ttl"],
                values=list(spec["values"]),
                desired_state=desired_state,
                version=current_version,
            )
            provider.upsert_record(record_spec)
        elif desired_state == DesiredState.ABSENT:
            # Later: provider.delete_record(...)
            logger.info(
                "Desired state ABSENT for %s; delete not implemented in MVP, no-op",
                job.dns_record_id,
            )

        coll.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "status.reconcileStatus": ReconcileStatus.IN_SYNC.value,
                    "status.observedVersion": current_version,
                    "status.lastError": None,
                    "status.lastReconciledAt": now,
                    "updatedAt": now,
                }
            },
        )
        logger.info(
            "Successfully reconciled record %s to version %s",
            job.dns_record_id,
            current_version,
        )

    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Failed to reconcile record %s",
            job.dns_record_id,
        )
        coll.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "status.reconcileStatus": ReconcileStatus.ERROR.value,
                    "status.lastError": str(exc),
                    "status.lastReconciledAt": now,
                    "updatedAt": now,
                }
            },
        )


def dispatcher_loop(
    name: str,
    coll: Collection,
    provider: DnsProvider,
    queue: JobQueue,
) -> None:
    """
    Dispatcher:
    - pulls jobs from the in-memory queue
    - reconciles the corresponding dns_records document
    """
    logger.info("Dispatcher %s starting", name)
    while True:
        job = queue.dequeue(timeout=2.0)
        if job is None:
            continue  # idle; in a real system, add shutdown semantics

        logger.info(
            "Dispatcher %s picked up job for record %s (target_version=%s)",
            name,
            job.dns_record_id,
            job.target_version,
        )

        reconcile_dns_record(coll, provider, job)
        queue.task_done() # Q: Wouldn't this be incorrect for multiple workers?


def start_dispatchers(
    coll: Collection,
    provider: DnsProvider,
    queue: JobQueue,
    workers: int = 1,
) -> None:
    for i in range(workers):
        t = threading.Thread(
            target=dispatcher_loop,
            args=(f"dispatcher-{i+1}", coll, provider, queue),
            daemon=True,
        )
        t.start()
