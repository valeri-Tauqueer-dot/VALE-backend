from future import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

class ConstraintType(str, Enum):
"""
Defines the semantic category of a HEROIC constraint.
"""

USER = "user"
SYSTEM = "system"
SAFETY = "safety"
RESOURCE = "resource"
TIME = "time"
DATA = "data"
EVIDENCE = "evidence"
PERFORMANCE = "performance"
SCOPE = "scope"
DEPENDENCY = "dependency"
EXECUTION = "execution"
OTHER = "other"

class ConstraintStatus(str, Enum):
"""
Lifecycle state of a HEROIC constraint.
"""

ACTIVE = "active"
SATISFIED = "satisfied"
VIOLATED = "violated"
BLOCKED = "blocked"
DISABLED = "disabled"
UNKNOWN = "unknown"

@dataclass
class HeroicConstraintState:
"""
Represents a constraint that HEROIC must preserve while
understanding, planning, coordinating, or executing a mission.
"""

constraint_id: str
description: str

constraint_type: ConstraintType = ConstraintType.OTHER

status: ConstraintStatus = ConstraintStatus.ACTIVE

priority: float = 0.0

mandatory: bool = True

source: str = ""

applies_to: List[str] = field(default_factory=list)

conditions: List[str] = field(default_factory=list)

dependencies: List[str] = field(default_factory=list)

violations: List[str] = field(default_factory=list)

metadata: Dict[str, Any] = field(default_factory=dict)

def add_target(
    self,
    target_id: str,
) -> None:
    """Register a mission element affected by this constraint."""
    if target_id and target_id not in self.applies_to:
        self.applies_to.append(target_id)

def add_condition(
    self,
    condition: str,
) -> None:
    """Register a condition associated with the constraint."""
    if condition and condition not in self.conditions:
        self.conditions.append(condition)

def add_dependency(
    self,
    dependency_id: str,
) -> None:
    """Register another constraint or state dependency."""
    if (
        dependency_id
        and dependency_id != self.constraint_id
        and dependency_id not in self.dependencies
    ):
        self.dependencies.append(dependency_id)

def add_violation(
    self,
    violation: str,
) -> None:
    """Register a detected constraint violation."""
    if violation and violation not in self.violations:
        self.violations.append(violation)

    self.status = ConstraintStatus.VIOLATED

def mark_satisfied(self) -> None:
    """Mark the constraint as satisfied."""
    self.status = ConstraintStatus.SATISFIED

def mark_violated(
    self,
    reason: str = "",
) -> None:
    """Mark the constraint as violated."""
    self.status = ConstraintStatus.VIOLATED

    if reason:
        self.add_violation(reason)

def mark_blocked(
    self,
    reason: str = "",
) -> None:
    """Mark the constraint as blocked."""
    self.status = ConstraintStatus.BLOCKED

    if reason:
        self.metadata["blocked_reason"] = reason

def mark_disabled(self) -> None:
    """Disable the constraint."""
    self.status = ConstraintStatus.DISABLED

def mark_unknown(self) -> None:
    """Mark the constraint state as unknown."""
    self.status = ConstraintStatus.UNKNOWN

def is_active(self) -> bool:
    """Return whether the constraint is currently active."""
    return self.status == ConstraintStatus.ACTIVE

def is_satisfied(self) -> bool:
    """Return whether the constraint has been satisfied."""
    return self.status == ConstraintStatus.SATISFIED

def is_violated(self) -> bool:
    """Return whether the constraint has been violated."""
    return self.status == ConstraintStatus.VIOLATED

def is_blocking(self) -> bool:
    """
    Return whether this constraint should currently block
    mission progress.
    """
    return (
        self.mandatory
        and self.status
        in {
            ConstraintStatus.VIOLATED,
            ConstraintStatus.BLOCKED,
        }
    )

def to_dict(self) -> Dict[str, Any]:
    """Serialize the constraint state."""
    return {
        "constraint_id": self.constraint_id,
        "description": self.description,
        "constraint_type": self.constraint_type.value,
        "status": self.status.value,
        "priority": self.priority,
        "mandatory": self.mandatory,
        "source": self.source,
        "applies_to": list(self.applies_to),
        "conditions": list(self.conditions),
        "dependencies": list(self.dependencies),
        "violations": list(self.violations),
        "metadata": dict(self.metadata),
}
