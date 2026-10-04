from future import annotations

from collections import defaultdict, deque
from typing import Dict, Iterable, List, Sequence, Set

from HEROIC.Tasks.task_state import HeroicTaskState
from HEROIC.planning.plan_state import HeroicPlanState, PlanType

class HeroicDependencyPlanner:
"""
Resolves and validates task dependencies inside a HEROIC plan.

Responsibilities:
- Register task dependencies into the plan.
- Validate that dependency references point to known tasks.
- Detect circular dependencies.
- Produce a dependency-safe topological ordering.
- Identify tasks that can run in parallel.
- Classify the resulting plan as sequential, parallel, or hybrid.

This component does not execute tasks.
"""

def build_dependency_plan(
    self,
    plan: HeroicPlanState,
    tasks: Sequence[HeroicTaskState],
) -> HeroicPlanState:
    """
    Apply dependency analysis to an existing HEROIC plan.

    Raises:
        ValueError:
            If a task references a missing task or a dependency cycle
            is detected.
    """
    task_map = self._build_task_map(tasks)

    self._register_dependencies(plan, tasks)
    self._validate_dependency_references(tasks, task_map)

    ordered_task_ids = self._topological_order(tasks, task_map)

    plan.ordered_task_ids = ordered_task_ids

    self._build_parallel_groups(plan, tasks, task_map)
    self._classify_plan_type(plan)

    return plan

def validate(
    self,
    tasks: Sequence[HeroicTaskState],
) -> bool:
    """
    Validate task dependency integrity without modifying a plan.
    """
    task_map = self._build_task_map(tasks)
    self._validate_dependency_references(tasks, task_map)
    self._topological_order(tasks, task_map)

    return True

def _build_task_map(
    self,
    tasks: Sequence[HeroicTaskState],
) -> Dict[str, HeroicTaskState]:
    """
    Build a task lookup table.

    Duplicate task IDs are rejected because dependency resolution must
    operate on an unambiguous task graph.
    """
    task_map: Dict[str, HeroicTaskState] = {}

    for task in tasks:
        if task.task_id in task_map:
            raise ValueError(
                f"Duplicate task ID detected: {task.task_id}"
            )

        task_map[task.task_id] = task

    return task_map

def _register_dependencies(
    self,
    plan: HeroicPlanState,
    tasks: Sequence[HeroicTaskState],
) -> None:
    """
    Copy task-level dependency declarations into the plan dependency map.
    """
    for task in tasks:
        if not task.dependency_task_ids:
            plan.dependency_map.setdefault(task.task_id, [])
            continue

        for dependency_id in task.dependency_task_ids:
            plan.add_dependency(
                task.task_id,
                dependency_id,
            )

def _validate_dependency_references(
    self,
    tasks: Sequence[HeroicTaskState],
    task_map: Dict[str, HeroicTaskState],
) -> None:
    """
    Ensure every dependency points to an existing task.
    """
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

def _topological_order(
    self,
    tasks: Sequence[HeroicTaskState],
    task_map: Dict[str, HeroicTaskState],
) -> List[str]:
    """
    Produce a dependency-safe task ordering using Kahn's algorithm.

    A dependency A -> B means:
        B must complete before A can execute.
    """
    dependents: Dict[str, Set[str]] = defaultdict(set)
    indegree: Dict[str, int] = {
        task_id: 0 for task_id in task_map
    }

    for task in tasks:
        for dependency_id in task.dependency_task_ids:
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

def _build_parallel_groups(
    self,
    plan: HeroicPlanState,
    tasks: Sequence[HeroicTaskState],
    task_map: Dict[str, HeroicTaskState],
) -> None:
    """
    Build dependency levels.

    Tasks in the same level have no dependency relationship requiring
    one of them to execute before another within that level.

    Example:

        A
       / \
      B   C
       \ /
        D

    produces:

        Level 1: A
        Level 2: B, C
        Level 3: D
    """
    remaining_dependencies: Dict[str, Set[str]] = {
        task.task_id: set(task.dependency_task_ids)
        for task in tasks
    }

    completed: Set[str] = set()

    while len(completed) < len(task_map):
        ready = sorted(
            task_id
            for task_id, dependencies in remaining_dependencies.items()
            if task_id not in completed
            and dependencies.issubset(completed)
        )

        if not ready:
            # The graph should already have been validated by
            # _topological_order(). This is a defensive safeguard.
            unresolved = sorted(
                task_id
                for task_id in task_map
                if task_id not in completed
            )

            raise ValueError(
                "Unable to resolve dependency levels for: "
                + ", ".join(unresolved)
            )

        plan.add_parallel_group(ready)

        completed.update(ready)

def _classify_plan_type(
    self,
    plan: HeroicPlanState,
) -> None:
    """
    Classify the dependency structure.

    SINGLE_TASK:
        One task only.

    SEQUENTIAL:
        Multiple tasks but no meaningful parallel group.

    PARALLEL:
        Multiple independent tasks can execute together.

    HYBRID:
        The plan contains both dependency-ordered and parallel stages.
    """
    task_count = len(plan.task_ids)

    if task_count <= 1:
        plan.plan_type = PlanType.SINGLE_TASK
        return

    groups = [
        group
        for group in plan.parallel_task_groups
        if group
    ]

    has_parallel_stage = any(len(group) > 1 for group in groups)
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
