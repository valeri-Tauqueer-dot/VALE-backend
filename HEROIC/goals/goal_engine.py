from __future__ import annotations

from typing import Iterable, List, Optional

from .goal_state import (
    GoalStatus,
    HeroicGoalState,
)


class HeroicGoalEngine:
    """Manages HEROIC goals and their lifecycle."""

    def __init__(
        self,
        goals: Optional[Iterable[HeroicGoalState]] = None,
    ) -> None:
        self._goals: List[HeroicGoalState] = []

        if goals:
            for goal in goals:
                self.add_goal(goal)

    def add_goal(
        self,
        goal: HeroicGoalState,
    ) -> HeroicGoalState:
        if not isinstance(goal, HeroicGoalState):
            raise TypeError(
                "goal must be a HeroicGoalState instance."
            )

        existing = self.get_goal(goal.goal_id)

        if existing is not None:
            index = self._goals.index(existing)
            self._goals[index] = goal
        else:
            self._goals.append(goal)

        return goal

    def get_goal(
        self,
        goal_id: str,
    ) -> Optional[HeroicGoalState]:
        for goal in self._goals:
            if goal.goal_id == goal_id:
                return goal

        return None

    def require_goal(
        self,
        goal_id: str,
    ) -> HeroicGoalState:
        goal = self.get_goal(goal_id)

        if goal is None:
            raise KeyError(
                f"Unknown HEROIC goal: {goal_id}"
            )

        return goal

    def remove_goal(
        self,
        goal_id: str,
    ) -> Optional[HeroicGoalState]:
        goal = self.get_goal(goal_id)

        if goal is not None:
            self._goals.remove(goal)

        return goal

    def list_all(self) -> List[HeroicGoalState]:
        return list(self._goals)

    def active(self) -> List[HeroicGoalState]:
        return [
            goal
            for goal in self._goals
            if goal.status == GoalStatus.ACTIVE
        ]

    def pending(self) -> List[HeroicGoalState]:
        return [
            goal
            for goal in self._goals
            if goal.status == GoalStatus.PENDING
        ]

    def blocked(self) -> List[HeroicGoalState]:
        return [
            goal
            for goal in self._goals
            if goal.is_blocked()
        ]

    def achieved(self) -> List[HeroicGoalState]:
        return [
            goal
            for goal in self._goals
            if goal.status == GoalStatus.ACHIEVED
        ]

    def failed(self) -> List[HeroicGoalState]:
        return [
            goal
            for goal in self._goals
            if goal.status == GoalStatus.FAILED
        ]

    def activate(
        self,
        goal_id: str,
    ) -> HeroicGoalState:
        goal = self.require_goal(goal_id)
        goal.activate()
        return goal

    def mark_achieved(
        self,
        goal_id: str,
    ) -> HeroicGoalState:
        goal = self.require_goal(goal_id)
        goal.mark_achieved()
        return goal

    def mark_failed(
        self,
        goal_id: str,
    ) -> HeroicGoalState:
        goal = self.require_goal(goal_id)
        goal.mark_failed()
        return goal

    def add_blocker(
        self,
        goal_id: str,
        blocker: str,
    ) -> HeroicGoalState:
        goal = self.require_goal(goal_id)
        goal.add_blocker(blocker)
        return goal

    def remove_blocker(
        self,
        goal_id: str,
        blocker: str,
    ) -> HeroicGoalState:
        goal = self.require_goal(goal_id)
        goal.remove_blocker(blocker)
        return goal

    def all_achieved(self) -> bool:
        return bool(self._goals) and all(
            goal.status == GoalStatus.ACHIEVED
            for goal in self._goals
        )

    def clear(self) -> None:
        self._goals.clear()

    def to_dict(self) -> List[dict]:
        return [
            goal.to_dict()
            for goal in self._goals
        ]
