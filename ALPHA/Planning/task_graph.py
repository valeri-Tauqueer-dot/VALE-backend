"""
VALE ALPHA - Task Dependency Graph

Provides the dependency graph used by ALPHA to understand execution order.

The graph answers structural questions such as:

    - Which tasks depend on this task?
    - Which tasks are prerequisites?
    - Which tasks are currently ready?
    - Which tasks are blocked?
    - Which tasks can potentially execute in parallel?
    - Does the plan contain a dependency cycle?
    - What becomes available after a task completes?

This module does NOT execute tasks.

It does NOT decide:
    - which brain is intellectually correct
    - what the final answer should be
    - whether a result is trustworthy
    - how workers are implemented
    - how many threads/processes are used
    - how resources are physically allocated

It provides the structural execution graph that those later systems consume.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple

from ..core.execution_models import (
    DependencyType,
    ExecutionPlan,
    ExecutionTask,
    TaskDependency,
    TaskStatus,
)


# ============================================================================
# GRAPH ERROR
# ============================================================================


class TaskGraphError(Exception):
    """
    Base exception for invalid ALPHA task graphs.
    """


class TaskNotFoundError(TaskGraphError):
    """
    Raised when a referenced task does not exist.
    """


class DependencyCycleError(TaskGraphError):
    """
    Raised when the execution graph contains a dependency cycle.
    """


# ============================================================================
# GRAPH NODE
# ============================================================================


@dataclass(frozen=True)
class TaskGraphNode:
    """
    Lightweight structural representation of a task in the graph.

    The actual ExecutionTask remains the source of task metadata/state.
    """

    task_id: str

    name: str

    task_kind: str

    target: str | None = None


# ============================================================================
# TASK GRAPH
# ============================================================================


class TaskDependencyGraph:
    """
    Directed dependency graph for an ALPHA ExecutionPlan.

    Edge direction:

        prerequisite → dependent

    Example:

        Market Data
             ↓
        Market Analysis
             ↓
        Risk Analysis

    Market Data must complete before Market Analysis can become ready.

    Independent branches can coexist:

        Market Data ─────→ Market Analysis ──→ Risk
              │
              └──────────→ Historical Analysis

    Market Analysis and Historical Analysis may potentially execute in
    parallel, depending on their other constraints.
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, ExecutionTask] = {}

        # prerequisite -> dependent tasks
        self._dependents: Dict[str, Set[str]] = defaultdict(set)

        # dependent -> prerequisite tasks
        self._prerequisites: Dict[str, Set[str]] = defaultdict(set)

        # Preserve the actual dependency definitions.
        self._dependency_metadata: Dict[
            Tuple[str, str],
            TaskDependency,
        ] = {}

    # ========================================================================
    # CONSTRUCTION
    # ========================================================================

    @classmethod
    def from_plan(
        cls,
        plan: ExecutionPlan,
    ) -> "TaskDependencyGraph":
        """
        Construct a graph from an ExecutionPlan.

        The plan is validated before the graph is returned.
        """

        graph = cls()

        for task in plan.tasks.values():
            graph.add_task(task)

        for dependency in plan.dependencies:
            graph.add_dependency(dependency)

        graph.validate()

        return graph

    # ========================================================================
    # TASKS
    # ========================================================================

    def add_task(
        self,
        task: ExecutionTask,
    ) -> None:
        """
        Add a task to the graph.
        """

        if task.task_id in self._tasks:
            raise TaskGraphError(
                f"Task already exists in graph: {task.task_id}"
            )

        self._tasks[task.task_id] = task

        # Ensure adjacency sets exist.
        self._dependents.setdefault(task.task_id, set())
        self._prerequisites.setdefault(task.task_id, set())

    def has_task(
        self,
        task_id: str,
    ) -> bool:
        """
        Determine whether a task exists.
        """

        return task_id in self._tasks

    def get_task(
        self,
        task_id: str,
    ) -> ExecutionTask:
        """
        Retrieve a task.
        """

        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise TaskNotFoundError(
                f"Unknown task_id: {task_id}"
            ) from exc

    def task_ids(self) -> Set[str]:
        """
        Return all task IDs.
        """

        return set(self._tasks.keys())

    def tasks(self) -> List[ExecutionTask]:
        """
        Return all tasks.
        """

        return list(self._tasks.values())

    def task_count(self) -> int:
        """
        Return number of tasks.
        """

        return len(self._tasks)

    # ========================================================================
    # DEPENDENCIES
    # ========================================================================

    def add_dependency(
        self,
        dependency: TaskDependency,
    ) -> None:
        """
        Add a directed dependency:

            prerequisite -> dependent
        """

        prerequisite = dependency.prerequisite_task_id
        dependent = dependency.dependent_task_id

        if prerequisite not in self._tasks:
            raise TaskNotFoundError(
                "Prerequisite task does not exist: "
                f"{prerequisite}"
            )

        if dependent not in self._tasks:
            raise TaskNotFoundError(
                "Dependent task does not exist: "
                f"{dependent}"
            )

        edge = (prerequisite, dependent)

        if edge in self._dependency_metadata:
            raise TaskGraphError(
                "Duplicate dependency: "
                f"{prerequisite} -> {dependent}"
            )

        self._dependents[prerequisite].add(dependent)
        self._prerequisites[dependent].add(prerequisite)

        self._dependency_metadata[edge] = dependency

    def prerequisites(
        self,
        task_id: str,
    ) -> Set[str]:
        """
        Return direct prerequisites of a task.
        """

        self._require_task(task_id)

        return set(self._prerequisites[task_id])

    def dependents(
        self,
        task_id: str,
    ) -> Set[str]:
        """
        Return tasks directly dependent on a task.
        """

        self._require_task(task_id)

        return set(self._dependents[task_id])

    def dependencies(
        self,
    ) -> List[TaskDependency]:
        """
        Return all dependency definitions.
        """

        return list(self._dependency_metadata.values())

    # ========================================================================
    # READINESS
    # ========================================================================

    def is_ready(
        self,
        task_id: str,
        completed_task_ids: Iterable[str],
    ) -> bool:
        """
        Determine whether a task's prerequisites have completed.

        This is a structural readiness check.

        It does NOT determine whether:
            - resources are available
            - the task should receive priority
            - verification permits execution
            - the task should be cancelled
        """

        self._require_task(task_id)

        completed = set(completed_task_ids)

        prerequisites = self._prerequisites[task_id]

        return prerequisites.issubset(completed)

    def ready_tasks(
        self,
        completed_task_ids: Iterable[str],
        active_task_ids: Iterable[str] = (),
    ) -> List[ExecutionTask]:
        """
        Return tasks whose dependencies are satisfied and which are not
        already completed or active.

        Tasks marked terminal are excluded.
        """

        completed = set(completed_task_ids)
        active = set(active_task_ids)

        ready: List[ExecutionTask] = []

        terminal_states = {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMED_OUT,
            TaskStatus.SKIPPED,
        }

        for task in self._tasks.values():
            if task.task_id in completed:
                continue

            if task.task_id in active:
                continue

            if task.status in terminal_states:
                continue

            if self.is_ready(task.task_id, completed):
                ready.append(task)

        return ready

    def blocked_tasks(
        self,
        completed_task_ids: Iterable[str],
        active_task_ids: Iterable[str] = (),
    ) -> List[ExecutionTask]:
        """
        Return tasks that cannot currently run because one or more
        prerequisites remain incomplete.
        """

        completed = set(completed_task_ids)
        active = set(active_task_ids)

        blocked: List[ExecutionTask] = []

        for task in self._tasks.values():
            if task.task_id in completed:
                continue

            if task.task_id in active:
                continue

            if task.status in {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
                TaskStatus.TIMED_OUT,
                TaskStatus.SKIPPED,
            }:
                continue

            if not self.is_ready(task.task_id, completed):
                blocked.append(task)

        return blocked

    # ========================================================================
    # PARALLELISM
    # ========================================================================

    def independent_ready_groups(
        self,
        completed_task_ids: Iterable[str],
        active_task_ids: Iterable[str] = (),
    ) -> List[List[ExecutionTask]]:
        """
        Group currently ready tasks into structurally independent groups.

        IMPORTANT:

        This does NOT guarantee that tasks are safe to execute concurrently.

        Resource conflicts, exclusive requirements, shared mutable state,
        brain capabilities, safety requirements, and other execution rules
        must be evaluated by later ALPHA components.

        This method only reasons about explicit task dependencies.
        """

        ready = self.ready_tasks(
            completed_task_ids=completed_task_ids,
            active_task_ids=active_task_ids,
        )

        if not ready:
            return []

        groups: List[List[ExecutionTask]] = []

        # A dependency-free set can be considered structurally independent
        # when no task in the group depends directly on another task in the
        # same group.
        current_group: List[ExecutionTask] = []

        for task in ready:
            task_prerequisites = self._prerequisites[task.task_id]

            conflicts_with_group = any(
                other.task_id in task_prerequisites
                or task.task_id in self._prerequisites[other.task_id]
                for other in current_group
            )

            if conflicts_with_group:
                groups.append(current_group)
                current_group = [task]
            else:
                current_group.append(task)

        if current_group:
            groups.append(current_group)

        return groups

    # ========================================================================
    # GRAPH ANALYSIS
    # ========================================================================

    def topological_order(self) -> List[str]:
        """
        Return a valid topological ordering of the graph.

        If a cycle exists, DependencyCycleError is raised.
        """

        indegree: Dict[str, int] = {
            task_id: len(prerequisites)
            for task_id, prerequisites in self._prerequisites.items()
        }

        queue = deque(
            task_id
            for task_id, degree in indegree.items()
            if degree == 0
        )

        order: List[str] = []

        while queue:
            current = queue.popleft()

            order.append(current)

            for dependent in self._dependents[current]:
                indegree[dependent] -= 1

                if indegree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(self._tasks):
            raise DependencyCycleError(
                "Execution graph contains a dependency cycle"
            )

        return order

    def contains_cycle(self) -> bool:
        """
        Return True when the graph contains a dependency cycle.
        """

        try:
            self.topological_order()
        except DependencyCycleError:
            return True

        return False

    def validate(self) -> None:
        """
        Validate graph structure.
        """

        self.topological_order()

    # ========================================================================
    # GRAPH INFORMATION
    # ========================================================================

    def root_tasks(self) -> List[ExecutionTask]:
        """
        Return tasks with no prerequisites.

        These are the initial candidates for execution.
        """

        return [
            task
            for task in self._tasks.values()
            if not self._prerequisites[task.task_id]
        ]

    def leaf_tasks(self) -> List[ExecutionTask]:
        """
        Return tasks with no dependents.

        These are terminal tasks in the dependency graph.
        """

        return [
            task
            for task in self._tasks.values()
            if not self._dependents[task.task_id]
        ]

    def dependency_depth(
        self,
        task_id: str,
    ) -> int:
        """
        Return the longest prerequisite depth for a task.

        Example:

            A
            ↓
            B
            ↓
            C

        depth(A) = 0
        depth(B) = 1
        depth(C) = 2
        """

        self._require_task(task_id)

        memo: Dict[str, int] = {}

        def calculate(current: str) -> int:
            if current in memo:
                return memo[current]

            prerequisites = self._prerequisites[current]

            if not prerequisites:
                memo[current] = 0
                return 0

            depth = 1 + max(
                calculate(parent)
                for parent in prerequisites
            )

            memo[current] = depth

            return depth

        return calculate(task_id)

    def critical_path_length(self) -> int:
        """
        Return the number of dependency edges on the longest path.

        This is a structural metric only.

        It does not estimate real milliseconds or actual runtime cost.
        """

        if not self._tasks:
            return 0

        return max(
            self.dependency_depth(task_id)
            for task_id in self._tasks
        )

    # ========================================================================
    # SERIALIZATION / DEBUGGING
    # ========================================================================

    def adjacency_map(self) -> Dict[str, Set[str]]:
        """
        Return prerequisite -> dependent adjacency information.
        """

        return {
            task_id: set(dependents)
            for task_id, dependents in self._dependents.items()
        }

    def prerequisite_map(self) -> Dict[str, Set[str]]:
        """
        Return dependent -> prerequisite adjacency information.
        """

        return {
            task_id: set(prerequisites)
            for task_id, prerequisites in self._prerequisites.items()
        }

    def describe(self) -> Dict[str, object]:
        """
        Produce a machine-readable structural description of the graph.
        """

        return {
            "task_count": self.task_count(),
            "dependency_count": len(
                self._dependency_metadata
            ),
            "root_tasks": [
                task.task_id
                for task in self.root_tasks()
            ],
            "leaf_tasks": [
                task.task_id
                for task in self.leaf_tasks()
            ],
            "critical_path_length": self.critical_path_length()
            if self._tasks
            else 0,
            "contains_cycle": self.contains_cycle(),
            "adjacency": {
                key: sorted(value)
                for key, value in self.adjacency_map().items()
            },
        }

    # ========================================================================
    # INTERNAL
    # ========================================================================

    def _require_task(
        self,
        task_id: str,
    ) -> None:
        """
        Ensure a task exists.
        """

        if task_id not in self._tasks:
            raise TaskNotFoundError(
                f"Unknown task_id: {task_id}"
            )


# ============================================================================
# PUBLIC EXPORTS
# ============================================================================


__all__ = [
    "TaskDependencyGraph",
    "TaskGraphNode",
    "TaskGraphError",
    "TaskNotFoundError",
    "DependencyCycleError",
  ]
