"""
HEROIC DEPENDENCY PLANNER

Resolves and validates dependencies in a HEROIC plan.
Does not execute tasks or authorize runtime parallel execution.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Sequence, Set

from HEROIC.Tasks.task_state import HeroicTaskState
from HEROIC.planning.plan_state import HeroicPlanState, PlanType


class HeroicDependencyPlanner:
    """Resolve and validate a HEROIC plan's dependency graph."""

    VERSION = "0.3.0"

    def __init__(self) -> None:
        self.planner_name = "HEROIC_DEPENDENCY_PLANNER"
        self.version = self.VERSION

    def build_dependency_plan(
        self,
        plan: HeroicPlanState,
        tasks: Sequence[HeroicTaskState],
    ) -> HeroicPlanState:
        """Build dependency metadata and a valid topological order."""

        if plan is None:
            raise ValueError("plan must not be None.")

        task_list = list(tasks)

        if any(task is None for task in task_list):
            raise ValueError("tasks must not contain None.")

        task_map = self._build_task_map(task_list)
        self._validate_dependency_references(task_list, task_map)

        ordered_task_ids = self._topological_order(task_list, task_map)
        parallel_groups = self._get_dependency_levels(
            task_list,
            task_map,
        )

        # Update derived state only after validation succeeds.
        for task in task_list:
            plan.add_task(task.task_id)

        plan.dependency_map.clear()
        plan.parallel_task_groups.clear()

        self._register_dependencies(plan, task_list)

        plan.ordered_task_ids = ordered_task_ids

        for group in parallel_groups:
            if len(group) > 1:
                plan.add_parallel_group(group)

        self._classify_plan_type(plan)
        return plan

    def validate(
        self,
        tasks: Sequence[HeroicTaskState],
    ) -> bool:
        """Validate task IDs, references, and cycles without modifying a plan."""

        task_list = list(tasks)

        if any(task is None for task in task_list):
            raise ValueError("tasks must not contain None.")

        task_map = self._build_task_map(task_list)
        self._validate_dependency_references(task_list, task_map)
        self._topological_order(task_list, task_map)
        return True

    def _build_task_map(
        self,
        tasks: Sequence[HeroicTaskState],
    ) -> Dict[str, HeroicTaskState]:
        task_map: Dict[str, HeroicTaskState] = {}

        for task in tasks:
            task_id = task.task_id

            if not isinstance(task_id, str) or not task_id.strip():
                raise ValueError(
                    "Every task must have a non-empty task ID."
                )

            if task_id in task_map:
                raise ValueError(
                    f"Duplicate task ID detected: {task_id}"
                )

            task_map[task_id] = task

        return task_map

    def _validate_dependency_references(
        self,
        tasks: Sequence[HeroicTaskState],
        task_map: Dict[str, HeroicTaskState],
    ) -> None:
        for task in tasks:
            for dependency_id in task.dependency_task_ids:
                if dependency_id not in task_map:
                    raise ValueError(
                        f"Task '{task.task_id}' depends on unknown "
                        f"task '{dependency_id}'."
                    )

                if dependency_id == task.task_id:
                    raise ValueError(
                        f"Task '{task.task_id}' cannot depend on itself."
                    )

    def _register_dependencies(
        self,
        plan: HeroicPlanState,
        tasks: Sequence[HeroicTaskState],
    ) -> None:
        for task in tasks:
            plan.dependency_map.setdefault(task.task_id, [])

            for dependency_id in dict.fromkeys(task.dependency_task_ids):
                plan.add_dependency(task.task_id, dependency_id)

    def _topological_order(
        self,
        tasks: Sequence[HeroicTaskState],
        task_map: Dict[str, HeroicTaskState],
    ) -> List[str]:
        """Order every dependency before the task that requires it."""

        dependents: Dict[str, Set[str]] = defaultdict(set)
        indegree: Dict[str, int] = {
            task_id: 0 for task_id in task_map
        }

        for task in tasks:
            for dependency_id in set(task.dependency_task_ids):
                dependents[dependency_id].add(task.task_id)
                indegree[task.task_id] += 1

        queue = deque(
            sorted(
                task_id
                for task_id, degree in indegree.items()
                if degree == 0
            )
        )

        ordered: List[str] = []

        while queue:
            task_id = queue.popleft()
            ordered.append(task_id)

            for dependent_id in sorted(dependents[task_id]):
                indegree[dependent_id] -= 1

                if indegree[dependent_id] == 0:
                    queue.append(dependent_id)

        if len(ordered) != len(task_map):
            cycle_nodes = sorted(
                task_id
                for task_id, degree in indegree.items()
                if degree > 0
            )
            raise ValueError(
                "Circular task dependency detected involving: "
                + ", ".join(cycle_nodes)
            )

        return ordered

    def _get_dependency_levels(
        self,
        tasks: Sequence[HeroicTaskState],
        task_map: Dict[str, HeroicTaskState],
    ) -> List[List[str]]:
        """Return structural dependency levels, not execution permissions."""

        remaining: Dict[str, Set[str]] = {
            task.task_id: set(task.dependency_task_ids)
            for task in tasks
        }

        completed: Set[str] = set()
        levels: List[List[str]] = []

        while len(completed) < len(task_map):
            ready = sorted(
                task_id
                for task_id, dependencies in remaining.items()
                if task_id not in completed
                and dependencies.issubset(completed)
            )

            if not ready:
                unresolved = sorted(
                    task_id
                    for task_id in task_map
                    if task_id not in completed
                )
                raise ValueError(
                    "Unable to resolve dependency levels for: "
                    + ", ".join(unresolved)
                )

            levels.append(ready)
            completed.update(ready)

        return levels

    def _classify_plan_type(self, plan: HeroicPlanState) -> None:
        task_count = len(plan.task_ids)

        if task_count <= 1:
            plan.plan_type = PlanType.SINGLE_TASK
            return

        has_parallel_stage = any(
            len(group) > 1
            for group in plan.parallel_task_groups
        )

        has_dependency_edges = any(
            bool(dependencies)
            for dependencies in plan.dependency_map.values()
        )

        if has_parallel_stage and has_dependency_edges:
            plan.plan_type = PlanType.HYBRID
        elif has_parallel_stage:
            plan.plan_type = PlanType.PARALLEL
        else:
            plan.plan_type = PlanType.SEQUENTIAL


__all__ = ["HeroicDependencyPlanner"]
