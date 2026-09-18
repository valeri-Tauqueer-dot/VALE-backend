"""
VALE ALPHA - Scheduler Engine

File:
    ALPHA/scheduling/scheduler_engine.py

Purpose:
    Provides ALPHA's execution scheduling intelligence.

Architectural boundary:
    HEROIC decides WHAT VALE needs to accomplish.
    ALPHA decides HOW that work should be scheduled and executed efficiently.

This module is responsible for:
    - maintaining scheduler state
    - discovering dependency-ready tasks
    - applying scheduling priorities
    - respecting deadlines
    - respecting declared resource requirements
    - respecting concurrency capacity
    - selecting dispatch candidates
    - producing explicit scheduling decisions
    - preventing unsafe dispatch caused by unresolved dependencies
    - preserving verification requirements

This module does NOT:
    - execute task handlers
    - decide whether a result is true
    - replace MCVL
    - replace HEROIC
    - perform final system synthesis
    - invent resource telemetry
    - silently remove verification requirements
    - assume structural independence means operational safety

Actual execution belongs to the future ALPHA execution layer.
"""


from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from ALPHA.core.execution_models import (
    ExecutionPlan,
    ExecutionTask,
    ResourceClass,
    TaskPriority,
    TaskStatus,
)
from ALPHA.planning.task_graph import TaskDependencyGraph

from .scheduler_models import (
    DispatchBatch,
    DispatchCandidate,
    QueueState,
    SchedulerCapacity,
    SchedulerCycleResult,
    SchedulerInput,
    SchedulerPolicy,
    SchedulerQueueEntry,
    SchedulerState,
    SchedulingDeadline,
    SchedulingDecision,
    SchedulingDecisionType,
    SchedulingPriority,
    SchedulingReason,
    SchedulingResourceProfile,
)


class SchedulerError(RuntimeError):
    """Base exception for scheduler failures."""


class SchedulerStateError(SchedulerError):
    """Raised when scheduler state is internally inconsistent."""


class SchedulerPlanError(SchedulerError):
    """Raised when the execution plan cannot be scheduled safely."""


@dataclass(frozen=True)
class SchedulerOrderingKey:
    """
    Internal deterministic ordering key.

    Lower tuple values are dispatched first.
    """

    blocked: int
    priority: int
    deadline_missing: int
    deadline_timestamp: float
    critical_path: int
    dependency_depth: int
    estimated_cost: float
    task_id: str


class AlphaScheduler:
    """
    Deterministic, dependency-aware ALPHA scheduler.

    The scheduler operates in cycles:

        scheduler input
              ↓
        synchronize state
              ↓
        inspect dependency graph
              ↓
        identify ready tasks
              ↓
        filter capacity/resource constraints
              ↓
        rank candidates
              ↓
        build dispatch batch
              ↓
        emit scheduling decisions
              ↓
        return cycle result

    It intentionally stops before actual task execution.
    """

    def __init__(
        self,
        *,
        policy: Optional[SchedulerPolicy] = None,
        capacity: Optional[SchedulerCapacity] = None,
    ) -> None:
        self.policy = policy or SchedulerPolicy()
        self.capacity = capacity or SchedulerCapacity()
        self.state = SchedulerState()

        self._plan: Optional[ExecutionPlan] = None
        self._graph: Optional[TaskDependencyGraph] = None

        self._queue: Dict[str, SchedulerQueueEntry] = {}

    # ------------------------------------------------------------------
    # PLAN LIFECYCLE
    # ------------------------------------------------------------------

    def load_plan(self, plan: ExecutionPlan) -> None:
        """
        Load a new execution plan into the scheduler.

        Existing queue state is discarded because a plan represents a new
        execution structure.
        """

        if plan is None:
            raise SchedulerPlanError("Execution plan cannot be None.")

        try:
            graph = TaskDependencyGraph.from_plan(plan)
            graph.validate()
        except Exception as exc:
            raise SchedulerPlanError(
                f"Execution plan failed dependency validation: {exc}"
            ) from exc

        self._plan = plan
        self._graph = graph
        self._queue.clear()

        self.state = SchedulerState(
            status=self.state.status,
            queue_state=QueueState.READY,
            cycle_count=0,
            queued_task_ids=[],
            active_task_ids=[],
            completed_task_ids=[],
            failed_task_ids=[],
            cancelled_task_ids=[],
            timed_out_task_ids=[],
            last_cycle_at=None,
            last_dispatch_at=None,
            total_dispatched=self.state.total_dispatched,
            total_completed=self.state.total_completed,
            total_failed=self.state.total_failed,
        )

        for task in plan.tasks:
            self._queue[task.task_id] = self._build_queue_entry(task)

    def clear(self) -> None:
        """Reset scheduler state and unload the current plan."""

        self._plan = None
        self._graph = None
        self._queue.clear()
        self.state = SchedulerState()

    # ------------------------------------------------------------------
    # PUBLIC SCHEDULING API
    # ------------------------------------------------------------------

    def schedule(
        self,
        scheduler_input: Optional[SchedulerInput] = None,
    ) -> SchedulerCycleResult:
        """
        Run one scheduling cycle.

        The scheduler does not execute anything. It produces a dispatch
        batch describing which tasks may be handed to the future execution
        layer.
        """

        if self._plan is None or self._graph is None:
            raise SchedulerStateError(
                "No execution plan is loaded into the scheduler."
            )

        scheduler_input = scheduler_input or SchedulerInput()

        cycle_started = self._utc_now()

        self._synchronize_external_state(scheduler_input)

        self.state.cycle_count += 1
        self.state.last_cycle_at = cycle_started

        decisions: List[SchedulingDecision] = []

        ready_tasks = self._graph.ready_tasks(
            completed=set(self.state.completed_task_ids)
        )

        candidate_tasks = self._build_candidates(
            ready_tasks=ready_tasks,
            now=cycle_started,
        )

        dispatch_candidates = self._rank_candidates(candidate_tasks)

        dispatch_batch = self._build_dispatch_batch(
            dispatch_candidates,
            now=cycle_started,
        )

        selected_ids = {
            candidate.task_id
            for candidate in dispatch_batch.candidates
        }

        decisions.extend(
            self._build_dispatch_decisions(
                dispatch_batch=dispatch_batch,
                all_candidates=dispatch_candidates,
            )
        )

        decisions.extend(
            self._build_wait_decisions(
                ready_tasks=ready_tasks,
                selected_ids=selected_ids,
                candidates=dispatch_candidates,
                now=cycle_started,
            )
        )

        decisions.extend(
            self._build_blocked_decisions(
                now=cycle_started,
            )
        )

        if dispatch_batch.task_ids:
            self.state.last_dispatch_at = cycle_started
            self.state.total_dispatched += len(dispatch_batch.task_ids)

        self._update_queue_states(dispatch_batch)

        return SchedulerCycleResult(
            cycle_id=self._build_cycle_id(cycle_started),
            generated_at=cycle_started,
            dispatch_batch=dispatch_batch,
            decisions=decisions,
            queue_snapshot=self._queue_snapshot(),
            scheduler_state=self.state,
        )

    # ------------------------------------------------------------------
    # TASK STATE UPDATES
    # ------------------------------------------------------------------

    def mark_active(self, task_id: str) -> None:
        """Mark a dispatched task as actively executing."""

        entry = self._require_queue_entry(task_id)

        entry.mark_active()

        self._remove_from_list(self.state.queued_task_ids, task_id)

        if task_id not in self.state.active_task_ids:
            self.state.active_task_ids.append(task_id)

        self.state.queue_state = QueueState.RUNNING

    def mark_completed(self, task_id: str) -> None:
        """Mark a task as successfully completed."""

        entry = self._require_queue_entry(task_id)

        entry.mark_completed()

        self._remove_from_list(self.state.queued_task_ids, task_id)
        self._remove_from_list(self.state.active_task_ids, task_id)

        if task_id not in self.state.completed_task_ids:
            self.state.completed_task_ids.append(task_id)

        self.state.total_completed += 1

        self._refresh_queue_state()

    def mark_failed(self, task_id: str) -> None:
        """Mark a task as failed."""

        entry = self._require_queue_entry(task_id)

        entry.mark_failed()

        self._remove_from_list(self.state.queued_task_ids, task_id)
        self._remove_from_list(self.state.active_task_ids, task_id)

        if task_id not in self.state.failed_task_ids:
            self.state.failed_task_ids.append(task_id)

        self.state.total_failed += 1

        self._refresh_queue_state()

    def mark_cancelled(self, task_id: str) -> None:
        """Mark a task as cancelled."""

        entry = self._require_queue_entry(task_id)

        entry.mark_cancelled()

        self._remove_from_list(self.state.queued_task_ids, task_id)
        self._remove_from_list(self.state.active_task_ids, task_id)

        if task_id not in self.state.cancelled_task_ids:
            self.state.cancelled_task_ids.append(task_id)

        self._refresh_queue_state()

    def mark_timed_out(self, task_id: str) -> None:
        """Mark a task as timed out."""

        entry = self._require_queue_entry(task_id)

        entry.mark_timed_out()

        self._remove_from_list(self.state.queued_task_ids, task_id)
        self._remove_from_list(self.state.active_task_ids, task_id)

        if task_id not in self.state.timed_out_task_ids:
            self.state.timed_out_task_ids.append(task_id)

        self._refresh_queue_state()

    # ------------------------------------------------------------------
    # CAPACITY
    # ------------------------------------------------------------------

    def update_capacity(self, capacity: SchedulerCapacity) -> None:
        """
        Replace scheduler capacity.

        Capacity is an explicit runtime contract. The scheduler does not
        fabricate CPU, memory, worker, or model availability.
        """

        if capacity is None:
            raise ValueError("Capacity cannot be None.")

        self.capacity = capacity

    def available_slots(self) -> int:
        """Return the currently available execution slots."""

        active_count = len(self.state.active_task_ids)

        return max(
            0,
            self.capacity.max_concurrent_tasks - active_count,
        )

    # ------------------------------------------------------------------
    # INSPECTION
    # ------------------------------------------------------------------

    def current_plan(self) -> Optional[ExecutionPlan]:
        """Return the currently loaded plan."""

        return self._plan

    def current_graph(self) -> Optional[TaskDependencyGraph]:
        """Return the currently loaded dependency graph."""

        return self._graph

    def queue_snapshot(self) -> Dict[str, SchedulerQueueEntry]:
        """Return a shallow copy of scheduler queue entries."""

        return dict(self._queue)

    # ------------------------------------------------------------------
    # CANDIDATE CREATION
    # ------------------------------------------------------------------

    def _build_candidates(
        self,
        *,
        ready_tasks: Sequence[ExecutionTask],
        now: datetime,
    ) -> List[DispatchCandidate]:
        candidates: List[DispatchCandidate] = []

        for task in ready_tasks:
            entry = self._require_queue_entry(task.task_id)

            if not self._is_task_dispatchable(task, entry):
                continue

            resource_profile = self._resource_profile_for(task)

            deadline = self._deadline_for(task)

            candidate = DispatchCandidate(
                task_id=task.task_id,
                priority=self._priority_for(task),
                deadline=deadline,
                resource_profile=resource_profile,
                estimated_cost=self._estimated_cost(task),
                critical_path_length=self._graph.critical_path_length(
                    task.task_id
                ),
                dependency_depth=self._graph.dependency_depth(
                    task.task_id
                ),
                ready_at=now,
            )

            candidates.append(candidate)

        return candidates

    def _rank_candidates(
        self,
        candidates: Sequence[DispatchCandidate],
    ) -> List[DispatchCandidate]:
        return sorted(
            candidates,
            key=self._ordering_key,
        )

    def _ordering_key(
        self,
        candidate: DispatchCandidate,
    ) -> SchedulerOrderingKey:
        deadline_timestamp = (
            candidate.deadline.timestamp
            if candidate.deadline is not None
            else float("inf")
        )

        return SchedulerOrderingKey(
            blocked=0,
            priority=-candidate.priority.level,
            deadline_missing=(
                1 if candidate.deadline is None else 0
            ),
            deadline_timestamp=deadline_timestamp,
            critical_path=-candidate.critical_path_length,
            dependency_depth=-candidate.dependency_depth,
            estimated_cost=candidate.estimated_cost,
            task_id=candidate.task_id,
        )

    # ------------------------------------------------------------------
    # DISPATCH
    # ------------------------------------------------------------------

    def _build_dispatch_batch(
        self,
        candidates: Sequence[DispatchCandidate],
        *,
        now: datetime,
    ) -> DispatchBatch:
        available_slots = self.available_slots()

        if available_slots <= 0:
            return DispatchBatch(
                created_at=now,
                candidates=[],
                capacity_limit=0,
                reason="No execution capacity available.",
            )

        selected: List[DispatchCandidate] = []

        used_resources = {
            ResourceClass.LIGHT: 0,
            ResourceClass.MEDIUM: 0,
            ResourceClass.HEAVY: 0,
        }

        for candidate in candidates:
            if len(selected) >= available_slots:
                break

            resource_class = candidate.resource_profile.resource_class

            if not self._resource_class_available(
                resource_class=resource_class,
                used_resources=used_resources,
            ):
                continue

            if not self._deadline_allowed(candidate, now):
                continue

            if not self._verification_requirement_allowed(candidate):
                continue

            selected.append(candidate)

            used_resources[resource_class] += 1

        return DispatchBatch(
            created_at=now,
            candidates=selected,
            capacity_limit=available_slots,
            reason=(
                "Selected dependency-ready tasks according to "
                "priority, deadline, resource, and capacity policy."
            ),
        )

    def _resource_class_available(
        self,
        *,
        resource_class: ResourceClass,
        used_resources: Dict[ResourceClass, int],
    ) -> bool:
        configured_limit = self._resource_limit(resource_class)

        if configured_limit is None:
            return True

        return used_resources[resource_class] < configured_limit

    def _resource_limit(
        self,
        resource_class: ResourceClass,
    ) -> Optional[int]:
        if resource_class == ResourceClass.LIGHT:
            return self.capacity.max_light_tasks

        if resource_class == ResourceClass.MEDIUM:
            return self.capacity.max_medium_tasks

        if resource_class == ResourceClass.HEAVY:
            return self.capacity.max_heavy_tasks

        return None

      # ------------------------------------------------------------------
    # DECISIONS
    # ------------------------------------------------------------------

    def _build_dispatch_decisions(
        self,
        *,
        dispatch_batch: DispatchBatch,
        all_candidates: Sequence[DispatchCandidate],
    ) -> List[SchedulingDecision]:
        selected_ids = {
            candidate.task_id
            for candidate in dispatch_batch.candidates
        }

        decisions: List[SchedulingDecision] = []

        for candidate in dispatch_batch.candidates:
            decisions.append(
                SchedulingDecision(
                    task_id=candidate.task_id,
                    decision_type=SchedulingDecisionType.DISPATCH,
                    reason=SchedulingReason.READY_AND_CAPACITY_AVAILABLE,
                    priority=candidate.priority,
                    created_at=dispatch_batch.created_at,
                    details={
                        "estimated_cost": candidate.estimated_cost,
                        "resource_class": candidate.resource_profile.resource_class.value,
                        "critical_path_length": candidate.critical_path_length,
                        "dependency_depth": candidate.dependency_depth,
                    },
                )
            )

        for candidate in all_candidates:
            if candidate.task_id in selected_ids:
                continue

            decisions.append(
                SchedulingDecision(
                    task_id=candidate.task_id,
                    decision_type=SchedulingDecisionType.WAIT,
                    reason=SchedulingReason.CAPACITY_LIMIT,
                    priority=candidate.priority,
                    created_at=dispatch_batch.created_at,
                    details={
                        "available_slots": dispatch_batch.capacity_limit,
                    },
                )
            )

        return decisions

    def _build_wait_decisions(
        self,
        *,
        ready_tasks: Sequence[ExecutionTask],
        selected_ids: Set[str],
        candidates: Sequence[DispatchCandidate],
        now: datetime,
    ) -> List[SchedulingDecision]:
        candidate_ids = {
            candidate.task_id
            for candidate in candidates
        }

        decisions: List[SchedulingDecision] = []

        for task in ready_tasks:
            if task.task_id in selected_ids:
                continue

            if task.task_id not in candidate_ids:
                decisions.append(
                    SchedulingDecision(
                        task_id=task.task_id,
                        decision_type=SchedulingDecisionType.WAIT,
                        reason=SchedulingReason.RESOURCE_UNAVAILABLE,
                        priority=self._priority_for(task),
                        created_at=now,
                        details={
                            "message": (
                                "Task is dependency-ready but could not "
                                "be dispatched under current resource policy."
                            )
                        },
                    )
                )

        return decisions

    def _build_blocked_decisions(
        self,
        *,
        now: datetime,
    ) -> List[SchedulingDecision]:
        if self._graph is None:
            return []

        decisions: List[SchedulingDecision] = []

        completed = set(self.state.completed_task_ids)
        terminal = (
            completed
            | set(self.state.failed_task_ids)
            | set(self.state.cancelled_task_ids)
            | set(self.state.timed_out_task_ids)
        )

        for task_id in self._graph.task_ids():
            if task_id in terminal:
                continue

            if task_id in self.state.active_task_ids:
                continue

            if task_id not in self._graph.ready_tasks(completed=completed):
                prerequisites = self._graph.prerequisites(task_id)

                unresolved = [
                    prerequisite
                    for prerequisite in prerequisites
                    if prerequisite not in completed
                ]

                if unresolved:
                    decisions.append(
                        SchedulingDecision(
                            task_id=task_id,
                            decision_type=SchedulingDecisionType.WAIT,
                            reason=SchedulingReason.DEPENDENCY_NOT_READY,
                            priority=self._priority_for(
                                self._graph.get_task(task_id)
                            ),
                            created_at=now,
                            details={
                                "unresolved_prerequisites": unresolved,
                            },
                        )
                    )

        return decisions

    # ------------------------------------------------------------------
    # TASK POLICY
    # ------------------------------------------------------------------

    def _is_task_dispatchable(
        self,
        task: ExecutionTask,
        entry: SchedulerQueueEntry,
    ) -> bool:
        if entry.state != QueueState.READY:
            return False

        if task.status not in (
            TaskStatus.PENDING,
            TaskStatus.READY,
        ):
            return False

        if task.task_id in self.state.active_task_ids:
            return False

        if task.task_id in self.state.completed_task_ids:
            return False

        if task.task_id in self.state.failed_task_ids:
            return False

        if task.task_id in self.state.cancelled_task_ids:
            return False

        if task.task_id in self.state.timed_out_task_ids:
            return False

        return True

    def _priority_for(
        self,
        task: ExecutionTask,
    ) -> SchedulingPriority:
        level = self._task_priority_level(task.priority)

        return SchedulingPriority(
            level=level,
            source="execution_task",
        )

    def _task_priority_level(
        self,
        priority: TaskPriority,
    ) -> int:
        mapping = {
            TaskPriority.CRITICAL: 100,
            TaskPriority.HIGH: 75,
            TaskPriority.NORMAL: 50,
            TaskPriority.LOW: 25,
            TaskPriority.BACKGROUND: 10,
        }

        return mapping.get(priority, 50)

    def _deadline_for(
        self,
        task: ExecutionTask,
    ) -> Optional[SchedulingDeadline]:
        deadline = getattr(task, "deadline", None)

        if deadline is None:
            return None

        if not isinstance(deadline, datetime):
            return None

        return SchedulingDeadline(
            timestamp=deadline,
            source="execution_task",
        )

    def _deadline_allowed(
        self,
        candidate: DispatchCandidate,
        now: datetime,
    ) -> bool:
        if candidate.deadline is None:
            return True

        if candidate.deadline.timestamp <= now:
            return self.policy.allow_overdue_tasks

        return True

    def _verification_requirement_allowed(
        self,
        candidate: DispatchCandidate,
    ) -> bool:
        """
        Verification is never removed by the scheduler.

        This method exists so future policy can distinguish dispatch
        treatment without weakening the requirement itself.
        """

        return True

    # ------------------------------------------------------------------
    # RESOURCE ESTIMATION
    # ------------------------------------------------------------------

    def _resource_profile_for(
        self,
        task: ExecutionTask,
    ) -> SchedulingResourceProfile:
        resource_requirement = getattr(
            task,
            "resource_requirement",
            None,
        )

        if resource_requirement is not None:
            resource_class = getattr(
                resource_requirement,
                "resource_class",
                ResourceClass.MEDIUM,
            )
        else:
            resource_class = self._infer_resource_class(task)

        return SchedulingResourceProfile(
            resource_class=resource_class,
            exclusive=bool(
                getattr(resource_requirement, "exclusive", False)
                if resource_requirement is not None
                else False
            ),
        )

    def _infer_resource_class(
        self,
        task: ExecutionTask,
    ) -> ResourceClass:
        """
        Conservative resource classification.

        This is a scheduling hint, not a measured performance claim.
        """

        task_kind = getattr(task, "task_kind", None)

        if task_kind is None:
            return ResourceClass.MEDIUM

        kind_value = getattr(task_kind, "value", str(task_kind))

        normalized = str(kind_value).lower()

        if any(
            token in normalized
            for token in (
                "verification",
                "mcvl",
                "validation",
            )
        ):
            return ResourceClass.MEDIUM

        if any(
            token in normalized
            for token in (
                "analysis",
                "reasoning",
                "simulation",
                "model",
            )
        ):
            return ResourceClass.HEAVY

        return ResourceClass.LIGHT

    def _estimated_cost(
        self,
        task: ExecutionTask,
    ) -> float:
        """
        Return an explicit task cost when available.

        If no cost is provided, return a neutral scheduling value rather
        than inventing a measured latency or compute cost.
        """

        explicit_cost = getattr(task, "estimated_cost", None)

        if explicit_cost is None:
            return 1.0

        try:
            value = float(explicit_cost)
        except (TypeError, ValueError):
            return 1.0

        if value < 0:
            return 1.0

        return value

    # ------------------------------------------------------------------
    # STATE SYNCHRONIZATION
    # ------------------------------------------------------------------

    def _synchronize_external_state(
        self,
        scheduler_input: SchedulerInput,
    ) -> None:
        """
        Synchronize externally observed terminal states.

        The scheduler accepts real execution observations from the
        execution layer instead of pretending to know that a task ran.
        """

        for task_id in scheduler_input.completed_task_ids:
            if task_id in self._queue:
                self.mark_completed(task_id)

        for task_id in scheduler_input.failed_task_ids:
            if task_id in self._queue:
                self.mark_failed(task_id)

        for task_id in scheduler_input.cancelled_task_ids:
            if task_id in self._queue:
                self.mark_cancelled(task_id)

        for task_id in scheduler_input.timed_out_task_ids:
            if task_id in self._queue:
                self.mark_timed_out(task_id)

    # ------------------------------------------------------------------
    # QUEUE MANAGEMENT
    # ------------------------------------------------------------------

    def _build_queue_entry(
        self,
        task: ExecutionTask,
    ) -> SchedulerQueueEntry:
        return SchedulerQueueEntry(
            task_id=task.task_id,
            state=QueueState.READY,
            priority=self._priority_for(task),
            enqueued_at=self._utc_now(),
        )

    def _update_queue_states(
        self,
        dispatch_batch: DispatchBatch,
    ) -> None:
        for candidate in dispatch_batch.candidates:
            entry = self._require_queue_entry(candidate.task_id)

            entry.mark_dispatched()

            if candidate.task_id not in self.state.queued_task_ids:
                self.state.queued_task_ids.append(
                    candidate.task_id
                )

        if dispatch_batch.task_ids:
            self.state.queue_state = QueueState.DISPATCHING
        else:
            self._refresh_queue_state()

    def _refresh_queue_state(self) -> None:
        if self.state.active_task_ids:
            self.state.queue_state = QueueState.RUNNING
            return

        if self.state.queued_task_ids:
            self.state.queue_state = QueueState.READY
            return

        if self._plan is None:
            self.state.queue_state = QueueState.EMPTY
            return

        if self._all_tasks_terminal():
            self.state.queue_state = QueueState.EMPTY
            return

        self.state.queue_state = QueueState.WAITING

    def _all_tasks_terminal(self) -> bool:
        if self._plan is None:
            return True

        terminal = (
            set(self.state.completed_task_ids)
            | set(self.state.failed_task_ids)
            | set(self.state.cancelled_task_ids)
            | set(self.state.timed_out_task_ids)
        )

        return all(
            task.task_id in terminal
            for task in self._plan.tasks
        )

    def _queue_snapshot(self) -> Dict[str, QueueState]:
        return {
            task_id: entry.state
            for task_id, entry in self._queue.items()
        }

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _require_queue_entry(
        self,
        task_id: str,
    ) -> SchedulerQueueEntry:
        try:
            return self._queue[task_id]
        except KeyError as exc:
            raise SchedulerStateError(
                f"Unknown scheduler task: {task_id}"
            ) from exc

    def _remove_from_list(
        self,
        values: List[str],
        value: str,
    ) -> None:
        while value in values:
            values.remove(value)

    def _build_cycle_id(
        self,
        timestamp: datetime,
    ) -> str:
        return (
            f"sched-{timestamp.strftime('%Y%m%dT%H%M%S%f')}"
        )

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)


__all__ = [
    "SchedulerError",
    "SchedulerStateError",
    "SchedulerPlanError",
    "SchedulerOrderingKey",
    "AlphaScheduler",
                  ]
