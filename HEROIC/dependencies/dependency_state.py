from future import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

class DependencyType(str, Enum):
"""
Defines what kind of dependency exists between HEROIC
mission components.
"""

TASK = "task"
GOAL = "goal"
OBJECTIVE = "objective"
CAPABILITY = "capability"
BRAIN = "brain"
INFORMATION = "information"
CONSTRAINT = "constraint"
EVIDENCE = "evidence"
RESOURCE = "resource"
SYSTEM = "system"
OTHER = "other"

class DependencyStatus(str, Enum):
"""
Lifecycle state of a dependency.
"""

UNKNOWN = "unknown"
IDENTIFIED = "identified"
SATISFIED = "satisfied"
UNSATISFIED = "unsatisfied"
BLOCKED = "blocked"
FAILED = "failed"

@dataclass
class HeroicDependencyState:
"""
Represents a directed dependency between two HEROIC entities.

`source_id` depends on `target_id`.
Therefore, the target must be available or satisfied before
the source can safely proceed.
"""

dependency_id: str

source_id: str

target_id: str

dependency_type: DependencyType = DependencyType.OTHER

status: DependencyStatus = DependencyStatus.IDENTIFIED

mandatory: bool = True

priority: float = 0.0

reason: str = ""

blockers: List[str] = field(default_factory=list)

metadata: Dict[str, Any] = field(default_factory=dict)

def add_blocker(
    self,
    blocker: str,
) -> None:
    """Register a blocker affecting this dependency."""
    if blocker and blocker not in self.blockers:
        self.blockers.append(blocker)

def mark_satisfied(self) -> None:
    """Mark the dependency as satisfied."""
    self.status = DependencyStatus.SATISFIED

def mark_unsatisfied(
    self,
    reason: str = "",
) -> None:
    """Mark the dependency as unsatisfied."""
    self.status = DependencyStatus.UNSATISFIED

    if reason:
        self.reason = reason

def mark_blocked(
    self,
    blocker: str = "",
) -> None:
    """Mark the dependency as blocked."""
    self.status = DependencyStatus.BLOCKED

    if blocker:
        self.add_blocker(blocker)

def mark_failed(
    self,
    reason: str = "",
) -> None:
    """Mark the dependency as failed."""
    self.status = DependencyStatus.FAILED

    if reason:
        self.reason = reason

def is_satisfied(self) -> bool:
    """Return whether the dependency is satisfied."""
    return self.status == DependencyStatus.SATISFIED

def is_blocking(self) -> bool:
    """
    Return whether this dependency currently prevents the
    source entity from safely proceeding.
    """
    if not self.mandatory:
        return False

    return self.status in {
        DependencyStatus.UNSATISFIED,
        DependencyStatus.BLOCKED,
        DependencyStatus.FAILED,
    }

def is_resolved(self) -> bool:
    """
    Return whether the dependency has reached a definitive
    non-active state.
    """
    return self.status in {
        DependencyStatus.SATISFIED,
        DependencyStatus.FAILED,
    }

def to_dict(self) -> Dict[str, Any]:
    """Serialize the dependency state."""
    return {
        "dependency_id": self.dependency_id,
        "source_id": self.source_id,
        "target_id": self.target_id,
        "dependency_type": self.dependency_type.value,
        "status": self.status.value,
        "mandatory": self.mandatory,
        "priority": self.priority,
        "reason": self.reason,
        "blockers": list(self.blockers),
        "metadata": dict(self.metadata),
    }
