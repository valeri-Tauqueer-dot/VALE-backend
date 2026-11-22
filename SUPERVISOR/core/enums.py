"""SUPERVISOR enumerations. String enums, so they serialise straight to JSON."""
from __future__ import annotations

from enum import Enum


class _S(str, Enum):
    def __str__(self) -> str:
        return self.value


class Mode(_S):
    ADVISORY = "ADVISORY"        # observe, classify, record, escalate. Changes nothing in the system.
    ENFORCE = "ENFORCE"          # also allowed to run the approved recovery actions


class ComponentState(_S):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"          # no evidence. Never treated as healthy.
    ISOLATED = "ISOLATED"
    RECOVERING = "RECOVERING"


class Breaker(_S):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class IncidentType(_S):
    HEALTH = "HEALTH"
    TIMEOUT = "TIMEOUT"
    STATE_CONFLICT = "STATE_CONFLICT"
    DATA_INTEGRITY = "DATA_INTEGRITY"
    COMMUNICATION = "COMMUNICATION"
    RESOURCE = "RESOURCE"
    SECURITY = "SECURITY"
    OTHER = "OTHER"


class IncidentStatus(_S):
    DETECTED = "DETECTED"
    INVESTIGATING = "INVESTIGATING"
    CONTAINED = "CONTAINED"
    RECOVERING = "RECOVERING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    UNRESOLVED = "UNRESOLVED"


class ActionKind(_S):
    NOTIFY = "NOTIFY"
    ESCALATE = "ESCALATE"
    HOLD = "HOLD"
    RELEASE_HOLD = "RELEASE_HOLD"
    RESET_BRAIN = "RESET_BRAIN"
    ISOLATE_BRAIN = "ISOLATE_BRAIN"
    RESTORE_BRAIN = "RESTORE_BRAIN"
    PRUNE_TASKS = "PRUNE_TASKS"
    GC_COLLECT = "GC_COLLECT"
    ROLLBACK = "ROLLBACK"
    RETRY = "RETRY"


SEVERITIES = ("INFORMATIONAL", "WARNING", "HIGH", "CRITICAL")


def sev_rank(severity: str) -> int:
    try:
        return SEVERITIES.index(severity)
    except ValueError:
        return 0


def sev_max(a: str, b: str) -> str:
    return a if sev_rank(a) >= sev_rank(b) else b


def sev_up(severity: str, steps: int = 1) -> str:
    return SEVERITIES[min(sev_rank(severity) + steps, len(SEVERITIES) - 1)]


ACTIVE_STATUSES = frozenset({IncidentStatus.DETECTED, IncidentStatus.INVESTIGATING, IncidentStatus.CONTAINED,
                             IncidentStatus.RECOVERING, IncidentStatus.VERIFYING, IncidentStatus.ESCALATED,
                             IncidentStatus.UNRESOLVED})

MUTATING = frozenset({ActionKind.RESET_BRAIN, ActionKind.ISOLATE_BRAIN, ActionKind.RESTORE_BRAIN,
                      ActionKind.PRUNE_TASKS, ActionKind.GC_COLLECT})

CORE_BRAINS = frozenset({"UNITY", "HEROIC", "ALPHA"})
