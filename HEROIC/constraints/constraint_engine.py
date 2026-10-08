from __future__ import annotations

from typing import Iterable, List, Optional

from .constraint_state import (
    ConstraintSeverity,
    HeroicConstraintState,
)


class HeroicConstraintEngine:
    """
    Evaluates and manages HEROIC constraints.

    The engine determines whether constraints are active,
    satisfied, violated, or blocking. It does not execute
    tasks or capabilities.
    """

    def __init__(
        self,
        constraints: Optional[
            Iterable[HeroicConstraintState]
        ] = None,
    ) -> None:
        self._constraints: List[
            HeroicConstraintState
        ] = []

        if constraints:
            for constraint in constraints:
                self.add_constraint(constraint)

    def add_constraint(
        self,
        constraint: HeroicConstraintState,
    ) -> HeroicConstraintState:
        if not isinstance(
            constraint,
            HeroicConstraintState,
        ):
            raise TypeError(
                "constraint must be a "
                "HeroicConstraintState instance."
            )

        existing = self.get_constraint(
            constraint.constraint_id
        )

        if existing is not None:
            self._constraints[
                self._constraints.index(existing)
            ] = constraint
        else:
            self._constraints.append(constraint)

        return constraint

    def remove_constraint(
        self,
        constraint_id: str,
    ) -> Optional[HeroicConstraintState]:
        constraint = self.get_constraint(
            constraint_id
        )

        if constraint is None:
            return None

        self._constraints.remove(constraint)

        return constraint

    def get_constraint(
        self,
        constraint_id: str,
    ) -> Optional[HeroicConstraintState]:
        for constraint in self._constraints:
            if constraint.constraint_id == constraint_id:
                return constraint

        return None

    def list_all(
        self,
    ) -> List[HeroicConstraintState]:
        return list(self._constraints)

    def active(
        self,
    ) -> List[HeroicConstraintState]:
        return [
            constraint
            for constraint in self._constraints
            if constraint.is_active()
        ]

    def violated(
        self,
    ) -> List[HeroicConstraintState]:
        return [
            constraint
            for constraint in self._constraints
            if constraint.is_active()
            and not constraint.is_satisfied()
        ]

    def blocking(
        self,
    ) -> List[HeroicConstraintState]:
        return [
            constraint
            for constraint in self._constraints
            if constraint.is_blocking()
        ]

    def critical_violations(
        self,
    ) -> List[HeroicConstraintState]:
        return [
            constraint
            for constraint in self.violated()
            if constraint.severity
            == ConstraintSeverity.CRITICAL
        ]

    def is_satisfied(self) -> bool:
        return not self.violated()

    def is_blocked(self) -> bool:
        return bool(self.blocking())

    def satisfy(
        self,
        constraint_id: str,
    ) -> HeroicConstraintState:
        constraint = self._require(
            constraint_id
        )

        constraint.satisfy()

        return constraint

    def violate(
        self,
        constraint_id: str,
        reason: str = "",
    ) -> HeroicConstraintState:
        constraint = self._require(
            constraint_id
        )

        constraint.violate(reason)

        return constraint

    def enable(
        self,
        constraint_id: str,
    ) -> HeroicConstraintState:
        constraint = self._require(
            constraint_id
        )

        constraint.activate()

        return constraint

    def disable(
        self,
        constraint_id: str,
    ) -> HeroicConstraintState:
        constraint = self._require(
            constraint_id
        )

        constraint.deactivate()

        return constraint

    def clear(self) -> None:
        self._constraints.clear()

    def _require(
        self,
        constraint_id: str,
    ) -> HeroicConstraintState:
        constraint = self.get_constraint(
            constraint_id
        )

        if constraint is None:
            raise KeyError(
                f"Unknown HEROIC constraint: "
                f"{constraint_id}"
            )

        return constraint

    def to_dict(self) -> List[dict]:
        return [
            constraint.to_dict()
            for constraint in self._constraints
    ]
