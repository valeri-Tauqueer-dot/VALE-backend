from future import annotations

from typing import Iterable, List, Optional

from HEROIC.constraints.constraint_state import (
ConstraintStatus,
HeroicConstraintState,
)

class HeroicConstraintEngine:
"""
Evaluates and manages HEROIC mission constraints.

The engine does not invent constraints. It evaluates constraints
explicitly supplied by the mission, objective, goal, task, or
surrounding cognitive state.
"""

def __init__(
    self,
    constraints: Optional[
        Iterable[HeroicConstraintState]
    ] = None,
) -> None:
    self._constraints = {}

    if constraints:
        for constraint in constraints:
            self.register(constraint)

def register(
    self,
    constraint: HeroicConstraintState,
    overwrite: bool = True,
) -> HeroicConstraintState:
    """Register a constraint."""
    if (
        constraint.constraint_id in self._constraints
        and not overwrite
    ):
        raise ValueError(
            f"Constraint already exists: "
            f"{constraint.constraint_id}"
        )

    self._constraints[
        constraint.constraint_id
    ] = constraint

    return constraint

def get(
    self,
    constraint_id: str,
) -> Optional[HeroicConstraintState]:
    """Return a constraint if registered."""
    return self._constraints.get(constraint_id)

def require(
    self,
    constraint_id: str,
) -> HeroicConstraintState:
    """Return a constraint or raise an explicit error."""
    constraint = self.get(constraint_id)

    if constraint is None:
        raise KeyError(
            f"Unknown HEROIC constraint: {constraint_id}"
        )

    return constraint

def unregister(
    self,
    constraint_id: str,
) -> bool:
    """Remove a constraint."""
    if constraint_id not in self._constraints:
        return False

    del self._constraints[constraint_id]
    return True

def evaluate(
    self,
    constraint: HeroicConstraintState,
) -> bool:
    """
    Evaluate the current blocking state of a constraint.

    A mandatory violated or blocked constraint prevents the
    constraint from being considered satisfied.
    """
    if constraint.status == ConstraintStatus.SATISFIED:
        return True

    if constraint.status in {
        ConstraintStatus.VIOLATED,
        ConstraintStatus.BLOCKED,
    }:
        return False

    if constraint.status in {
        ConstraintStatus.DISABLED,
        ConstraintStatus.UNKNOWN,
    }:
        return not constraint.mandatory

    return True

def evaluate_all(self) -> bool:
    """
    Evaluate all registered constraints.

    Returns True only when every mandatory constraint is
    currently satisfied or otherwise non-blocking.
    """
    for constraint in self._constraints.values():
        if not self.evaluate(constraint):
            return False

    return True

def active(
    self,
) -> List[HeroicConstraintState]:
    """Return currently active constraints."""
    return [
        constraint
        for constraint in self._constraints.values()
        if constraint.is_active()
    ]

def satisfied(
    self,
) -> List[HeroicConstraintState]:
    """Return satisfied constraints."""
    return [
        constraint
        for constraint in self._constraints.values()
        if constraint.is_satisfied()
    ]

def violated(
    self,
) -> List[HeroicConstraintState]:
    """Return violated constraints."""
    return [
        constraint
        for constraint in self._constraints.values()
        if constraint.is_violated()
    ]

def blocking(
    self,
) -> List[HeroicConstraintState]:
    """Return constraints currently blocking progress."""
    return [
        constraint
        for constraint in self._constraints.values()
        if constraint.is_blocking()
    ]

def applicable_to(
    self,
    target_id: str,
) -> List[HeroicConstraintState]:
    """Return constraints applying to a specific mission element."""
    if not target_id:
        return []

    return [
        constraint
        for constraint in self._constraints.values()
        if target_id in constraint.applies_to
    ]

def mark_satisfied(
    self,
    constraint_id: str,
) -> HeroicConstraintState:
    """Mark a registered constraint as satisfied."""
    constraint = self.require(constraint_id)
    constraint.mark_satisfied()
    return constraint

def mark_violated(
    self,
    constraint_id: str,
    reason: str = "",
) -> HeroicConstraintState:
    """Mark a registered constraint as violated."""
    constraint = self.require(constraint_id)
    constraint.mark_violated(reason)
    return constraint

def mark_blocked(
    self,
    constraint_id: str,
    reason: str = "",
) -> HeroicConstraintState:
    """Mark a registered constraint as blocked."""
    constraint = self.require(constraint_id)
    constraint.mark_blocked(reason)
    return constraint

def clear(self) -> None:
    """Remove all registered constraints."""
    self._constraints.clear()

def __len__(self) -> int:
    return len(self._constraints)

def __contains__(
    self,
    constraint_id: str,
) -> bool:
    return constraint_id in self._constraints

def to_dict(self):
    """Serialize all registered constraints."""
    return {
        constraint_id: constraint.to_dict()
        for constraint_id, constraint
        in self._constraints.items()
}
