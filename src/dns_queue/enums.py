from __future__ import annotations

from enum import Enum


class DesiredState(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


class ReconcileStatus(str, Enum):
    PENDING = "PENDING"
    APPLYING = "APPLYING"
    IN_SYNC = "IN_SYNC"
    ERROR = "ERROR"
