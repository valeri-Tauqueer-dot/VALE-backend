from __future__ import annotations

from typing import Iterable, List, Optional

from HEROIC.Tasks.task_state import (
    HeroicTaskState,
    TaskStatus,
)


class HeroicPriorityEngine:
    """
    Evaluates and ranks HEROIC tasks by priority.

    Higher priority scores are ranked first. Task status
    contributes to ordering without changing the task's
    original priority value.
    """

    def rank(
        self,
        tasks: Iterable[HeroicTaskState],
    ) -> List[HeroicTaskState]:
        return sorted(
            list(tasks),
            key=self._ranking_key,
            reverse=True,
        )

    def select_next(
        self,
        tasks: Iterable[HeroicTaskState],
    ) -> Optional[HeroicTaskState]:
        candidates = [
            task
            for task in tasks
            if self._is_pending(task)
        ]

        ranked = self.rank(candidates)

        return ranked[0] if ranked else None

    def filter_ready(
        self,
        tasks: Iterable[HeroicTaskState],
    ) -> List[HeroicTaskState]:
        return [
            task
            for task in tasks
            if self._is_pending(task)
            and self._dependencies_satisfied(task)
        ]

    def _ranking_key(
        self,
        task: HeroicTaskState,
    ) -> tuple:
        priority = getattr(task, "priority", 0.0)

        try:
            priority_score = float(priority)
        except (TypeError, ValueError):
            priority_score = 0.0

        status = getattr(task, "status", None)
        status_value = getattr(status, "value", status)

        status_bonus = (
            1 if status_value == "in_progress" else 0
        )

        return priority_score, status_bonus

    def _is_pending(
        self,
        task: HeroicTaskState,
    ) -> bool:
        status = getattr(task, "status", None)

        if status == TaskStatus.PENDING:
            return True

        status_value = getattr(status, "value", status)

        return status_value == "pending"

    def _dependencies_satisfied(
        self,
        task: HeroicTaskState,
    ) -> bool:
        """
        Checks dependency completion when dependency status
        information is available on the task.

        Dependency identifiers alone cannot prove that
        their corresponding tasks have completed.
        """
        dependency_statuses = getattr(
            task,
            "dependency_statuses",
            None,
        )

        if dependency_statuses is None:
            return not bool(
                getattr(task, "dependency_task_ids", [])
            )

        if isinstance(dependency_statuses, dict):
            statuses = dependency_statuses.values()
        else:
            statuses = dependency_statuses

        for status in statuses:
            status_value = getattr(status, "value", status)

            if status_value not in {
                "completed",
                "satisfied",
                "success",
            }:
                return False

        return True
