from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class GoalStatus(str, Enum):
    UNKNOWN = "unknown"
    PENDING = "pending"
    ACTIVE = "active"
    ACHIEVED = "achieved"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class HeroicGoalState:
    """
    Represents a goal that HEROIC is responsible for pursuing.

    A goal is not considered achieved merely because a plan
    exists. Achievement must be recorded explicitly.
    """

    goal_id: str
    name: str
    description: str = ""

    status: GoalStatus = GoalStatus.PENDING
    priority: float = 0.0

    success_criteria: List[str] = field(
        default_factory=list
    )
    objective_ids: List[str] = field(
        default_factory=list
    )
    parent_goal_id: str = ""

    progress: float = 0.0
    blockers: List[str] = field(
        default_factory=list
    )
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def add_success_criterion(
        self,
        criterion: str,
    ) -> None:
        if criterion and criterion not in self.success_criteria:
            self.success_criteria.append(criterion)

    def add_objective(
        self,
        objective_id: str,
    ) -> None:
        if objective_id and objective_id not in self.objective_ids:
            self.objective_ids.append(objective_id)

    def add_blocker(
        self,
        blocker: str,
    ) -> None:
        if blocker and blocker not in self.blockers:
            self.blockers.append(blocker)

        if self.status != GoalStatus.CANCELLED:
            self.status = GoalStatus.BLOCKED

    def remove_blocker(
        self,
        blocker: str,
    ) -> bool:
        if blocker not in self.blockers:
            return False

        self.blockers.remove(blocker)

        if (
            not self.blockers
            and self.status == GoalStatus.BLOCKED
        ):
            self.status = GoalStatus.PENDING

        return True

    def activate(self) -> None:
        if self.status in {
            GoalStatus.ACHIEVED,
            GoalStatus.FAILED,
            GoalStatus.CANCELLED,
        }:
            return

        if self.blockers:
            self.status = GoalStatus.BLOCKED
        else:
            self.status = GoalStatus.ACTIVE

    def update_progress(
        self,
        progress: float,
    ) -> None:
        self.progress = max(
            0.0,
            min(100.0, float(progress)),
        )

    def mark_achieved(self) -> None:
        self.status = GoalStatus.ACHIEVED
        self.progress = 100.0
        self.blockers.clear()

    def mark_failed(self) -> None:
        self.status = GoalStatus.FAILED

    def cancel(self) -> None:
        self.status = GoalStatus.CANCELLED

    def is_terminal(self) -> bool:
        return self.status in {
            GoalStatus.ACHIEVED,
            GoalStatus.FAILED,
            GoalStatus.CANCELLED,
        }

    def is_active(self) -> bool:
        return self.status == GoalStatus.ACTIVE

    def is_achieved(self) -> bool:
        return self.status == GoalStatus.ACHIEVED

    def is_blocked(self) -> bool:
        return (
            self.status == GoalStatus.BLOCKED
            or bool(self.blockers)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "success_criteria": list(self.success_criteria),
            "objective_ids": list(self.objective_ids),
            "parent_goal_id": self.parent_goal_id,
            "progress": self.progress,
            "blockers": list(self.blockers),
            "metadata": dict(self.metadata),
    }
