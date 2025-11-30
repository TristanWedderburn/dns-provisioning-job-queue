from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from bson import ObjectId  # provided by pymongo

from .enums import DesiredState, ReconcileStatus


@dataclass
class DnsRecordSpec:
    """
    Desired configuration of a DNS record.
    `version` increments whenever spec or desired_state changes.
    """
    zone_id: str
    name: str
    type: str  # "A", "CNAME", "TXT", etc.
    ttl: int
    values: List[str]
    desired_state: DesiredState
    version: int


@dataclass
class DnsRecordStatus:
    """
    Observed (reconciled) state of the record.
    `observed_version` is the last spec.version we successfully reconciled.
    """
    reconcile_status: ReconcileStatus
    observed_version: int
    last_error: Optional[str]
    last_reconciled_at: Optional[datetime]


@dataclass
class DnsRecord:
    """
    Aggregate root for a DNS record.
    Represents one document in the Mongo 'dns_records' collection.
    """
    id: ObjectId
    spec: DnsRecordSpec
    status: DnsRecordStatus
    created_at: datetime
    updated_at: datetime


@dataclass
class Job:
    """
    Transient job message for the in-memory queue.
    Pattern A: not persisted, just carries IDs/versions.
    """
    dns_record_id: str
    target_version: int
