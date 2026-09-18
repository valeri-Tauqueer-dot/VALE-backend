"""
VALE ALPHA - Execution Context

The ExecutionContext is the live runtime container for one ALPHA execution.

It connects:

    ExecutionRequest
            ↓
    ExecutionPlan
            ↓
    Scheduler
            ↓
    Executor
            ↓
    Monitoring
            ↓
    Recovery / Replanning
            ↓
    Verification / UNITY

The context belongs to ONE execution instance.

It is intentionally separate from VALE's global/shared brain state.

Design principles:
    - one context per execution
    - explicit lifecycle
    - no hidden global execution state
    - results remain traceable to tasks
    - failures remain visible
    - real measurements only
    - cancellation is explicit
    - verification requirements remain attached to the execution
    - runtime components may update execution state
    - execution context does not make final cognitive decisions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from .execution_models import (
    ExecutionFailure,
    ExecutionPlan,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionSummary,
    ExecutionTask,
    ExecutionTiming,
    ExecutionTraceEvent,
    TaskStatus,
)


# ============================================================================
# EXECUTION CONTEXT
# ============================================================================


@dataclass
class ExecutionContext:
    """
    Runtime state for one ALPHA execution.

    This is the central execution object passed between ALPHA components.

    It does NOT decide:
        - what VALE ultimately believes
        - which political/financial/etc. decision is correct
        - whether a brain's conclusion is true
        - final system-level synthesis

    It tracks and coordinates execution state.
    """

    request: ExecutionRequest

    context_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    execution_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    status: ExecutionStatus = ExecutionStatus.CREATED

    plan: Optional[ExecutionPlan] = None

    results: Dict[str, ExecutionResult] = field(
        default_factory=dict
    )

    failures: List[ExecutionFailure] = field(
        default_factory=list
    )

    trace: List[ExecutionTraceEvent] = field(
        default_factory=list
    )

    timing: Optional[ExecutionTiming] = None

    shared_data: Dict[str, Any] = field(
        default_factory=dict
    )

    runtime_metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    active_task_ids: Set[str] = field(
        default_factory=set
    )

    completed_task_ids: Set[str] = field(
        default_factory=set
    )

    failed_task_ids: Set[str] = field(
        default_factory=set
    )

    cancelled_task_ids: Set[str] = field(
        default_factory=set
    )

    timed_out_task_ids: Set[str] = field(
        default_factory=set
    )

    started_at_monotonic: Optional[float] = field(
        default=None,
        repr=False,
    )

    completed_at_monotonic: Optional[float] = field(
        default=None,
        repr=False,
    )

    cancellation_requested: bool = False

    cancellation_reason: Optional[str] = None

    replanning_requested: bool = False

    replanning_reason: Optional[str] = None

    created_at_monotonic: float = field(
        default_factory=monotonic,
        repr=False,
    )

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    def set_status(self, status: ExecutionStatus) -> None:
        """
        Update execution lifecycle state.

        Every state change is recorded in the execution trace.
        """

        previous_status = self.status

        self.status = status

        self.add_trace(
            event_type="EXECUTION_STATUS_CHANGED",
            details={
                "previous_status": previous_status.value,
                "new_status": status.value,
            },
        )

    def start(self) -> None:
        """
        Mark execution as started.
        """

        if self.started_at_monotonic is not None:
            return

        self.started_at_monotonic = monotonic()

        self.timing = ExecutionTiming(
            execution_id=self.execution_id,
            started_at_monotonic=self.started_at_monotonic,
        )

        self.set_status(ExecutionStatus.RUNNING)

        self.add_trace(
            event_type="EXECUTION_STARTED"
        )

    def complete(self) -> None:
        """
        Mark execution as completed.

        Completion timing is measured from the monotonic clock.
        """

        self.completed_at_monotonic = monotonic()

        if self.timing is None:
            self.timing = ExecutionTiming(
                execution_id=self.execution_id,
                started_at_monotonic=self.started_at_monotonic,
            )

        self.timing.completed_at_monotonic = (
            self.completed_at_monotonic
        )

        self.timing.finalize()

        self.set_status(ExecutionStatus.COMPLETED)

        self.add_trace(
            event_type="EXECUTION_COMPLETED"
        )

    def cancel(self, reason: str) -> None:
        """
        Request cancellation of the execution.

        This method records the request.

        The executor is responsible for actually stopping work safely.
        """

        self.cancellation_requested = True
        self.cancellation_reason = reason

        self.set_status(ExecutionStatus.CANCELLED)

        self.add_trace(
            event_type="EXECUTION_CANCELLATION_REQUESTED",
            details={
                "reason": reason,
            },
        )

    def request_replanning(self, reason: str) -> None:
        """
        Request that ALPHA's planning layer reconsider the current plan.

        Replanning is a request, not an automatic decision to replace the plan.
        """

        self.replanning_requested = True
        self.replanning_reason = reason

        self.add_trace(
            event_type="REPLANNING_REQUESTED",
            details={
                "reason": reason,
            },
        )

    def clear_replanning_request(self) -> None:
        """
        Clear a previously satisfied replanning request.
        """

        self.replanning_requested = False
        self.replanning_reason = None

    # ========================================================================
    # PLAN
    # ========================================================================

    def attach_plan(self, plan: ExecutionPlan) -> None:
        """
        Attach an execution plan to this context.

        The plan must belong to this execution's request.
        """

        if plan.request_id != self.request.request_id:
            raise ValueError(
                "Execution plan request_id does not match "
                "the execution request"
            )

        if self.plan is not None:
            raise ValueError(
                "An execution plan is already attached. "
                "Use the planning/replanning layer to replace it explicitly."
            )

        self.plan = plan

        self.set_status(ExecutionStatus.READY)

        self.add_trace(
            event_type="EXECUTION_PLAN_ATTACHED",
            details={
                "plan_id": plan.plan_id,
                "task_count": plan.task_count(),
            },
        )

    # ========================================================================
    # TASK STATE
    # ========================================================================

    def get_task(self, task_id: str) -> ExecutionTask:
        """
        Retrieve a task from the current plan.
        """

        if self.plan is None:
            raise RuntimeError(
                "Cannot retrieve task before an execution plan exists"
            )

        try:
            return self.plan.tasks[task_id]
        except KeyError as exc:
            raise KeyError(
                f"Unknown task_id: {task_id}"
            ) from exc

    def mark_task_active(self, task_id: str) -> None:
        """
        Mark a task as actively executing.
        """

        task = self.get_task(task_id)

        task.status = TaskStatus.RUNNING

        self.active_task_ids.add(task_id)

        self.add_trace(
            event_type="TASK_STARTED",
            task_id=task_id,
        )

    def mark_task_completed(
        self,
        result: ExecutionResult,
    ) -> None:
        """
        Record a successful task result.
        """

        task = self.get_task(result.task_id)

        task.status = TaskStatus.COMPLETED

        self.results[result.task_id] = result

        self.active_task_ids.discard(result.task_id)
        self.completed_task_ids.add(result.task_id)

        self.failed_task_ids.discard(result.task_id)
        self.cancelled_task_ids.discard(result.task_id)
        self.timed_out_task_ids.discard(result.task_id)

        self.add_trace(
            event_type="TASK_COMPLETED",
            task_id=result.task_id,
            details={
                "success": result.success,
                "duration_ms": result.duration_ms,
            },
        )

    def mark_task_failed(
        self,
        result: ExecutionResult,
        failure: Optional[ExecutionFailure] = None,
    ) -> None:
        """
        Record a failed task.

        Failure is deliberately preserved.
        """

        task = self.get_task(result.task_id)

        task.status = TaskStatus.FAILED

        self.results[result.task_id] = result

        self.active_task_ids.discard(result.task_id)
        self.failed_task_ids.add(result.task_id)

        self.completed_task_ids.discard(result.task_id)
        self.cancelled_task_ids.discard(result.task_id)

        if failure is not None:
            self.failures.append(failure)

        self.add_trace(
            event_type="TASK_FAILED",
            task_id=result.task_id,
            details={
                "error": result.error,
                "failure_type": (
                    failure.failure_type.value
                    if failure is not None
                    else None
                ),
            },
        )

    def mark_task_cancelled(
        self,
        task_id: str,
        reason: Optional[str] = None,
    ) -> None:
        """
        Mark a task as cancelled.
        """

        task = self.get_task(task_id)

        task.status = TaskStatus.CANCELLED

        self.active_task_ids.discard(task_id)
        self.cancelled_task_ids.add(task_id)

        self.add_trace(
            event_type="TASK_CANCELLED",
            task_id=task_id,
            details={
                "reason": reason,
            },
        )

    def mark_task_timed_out(
        self,
        task_id: str,
        reason: Optional[str] = None,
    ) -> None:
        """
        Mark a task as timed out.
        """

        task = self.get_task(task_id)

        task.status = TaskStatus.TIMED_OUT

        self.active_task_ids.discard(task_id)
        self.timed_out_task_ids.add(task_id)

        self.add_trace(
            event_type="TASK_TIMED_OUT",
            task_id=task_id,
            details={
                "reason": reason,
            },
        )

    # ========================================================================
    # RESULTS
    # ========================================================================

    def get_result(
        self,
        task_id: str,
    ) -> Optional[ExecutionResult]:
        """
        Return a task result if one exists.
        """

        return self.results.get(task_id)

    def has_result(self, task_id: str) -> bool:
        """
        Determine whether a task has produced a result.
        """

        return task_id in self.results

    # ========================================================================
    # DEPENDENCY STATE
    # ========================================================================

    def prerequisites_completed(
        self,
        task_id: str,
    ) -> bool:
        """
        Determine whether all prerequisites for a task have completed.

        The scheduler will later use this to determine task readiness.

        This method does NOT decide whether a failed prerequisite should
        permit execution. That policy belongs to the dependency/scheduler
        layer.
        """

        if self.plan is None:
            raise RuntimeError(
                "Cannot evaluate dependencies before a plan exists"
            )

        prerequisites = self.plan.prerequisites_for(task_id)

        return prerequisites.issubset(
            self.completed_task_ids
        )

    def dependency_state(
        self,
        task_id: str,
    ) -> Dict[str, str]:
        """
        Return the current state of each prerequisite.
        """

        if self.plan is None:
            raise RuntimeError(
                "Cannot inspect dependencies before a plan exists"
            )

        dependencies = self.plan.prerequisites_for(task_id)

        return {
            dependency_id: self.get_task(dependency_id).status.value
            for dependency_id in dependencies
        }

    # ========================================================================
    # TRACE
    # ========================================================================

    def add_trace(
        self,
        event_type: str,
        task_id: Optional[str] = None,
        component: Optional[str] = None,
        status: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> ExecutionTraceEvent:
        """
        Add an execution trace event.

        Trace data should describe what actually happened.
        """

        event = ExecutionTraceEvent(
            execution_id=self.execution_id,
            event_type=event_type,
            task_id=task_id,
            component=component,
            status=status,
            details=details or {},
        )

        self.trace.append(event)

        return event

    # ========================================================================
    # DATA
    # ========================================================================

    def set_shared_data(
        self,
        key: str,
        value: Any,
    ) -> None:
        """
        Store execution-scoped data.

        This is NOT global VALE shared memory.

        It exists only for this execution context.
        """

        if not key.strip():
            raise ValueError(
                "Execution shared-data key cannot be empty"
            )

        self.shared_data[key] = value

    def get_shared_data(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Retrieve execution-scoped data.
        """

        return self.shared_data.get(key, default)

    # ========================================================================
    # SUMMARY
    # ========================================================================

    def build_summary(self) -> ExecutionSummary:
        """
        Build an aggregate execution summary from actual runtime state.
        """

        total_tasks = (
            self.plan.task_count()
            if self.plan is not None
            else 0
        )

        summary = ExecutionSummary(
            execution_id=self.execution_id,
            request_id=self.request.request_id,
            status=self.status,
            total_tasks=total_tasks,
            completed_tasks=len(self.completed_task_ids),
            failed_tasks=len(self.failed_task_ids),
            cancelled_tasks=len(self.cancelled_task_ids),
            timed_out_tasks=len(self.timed_out_task_ids),
            skipped_tasks=sum(
                1
                for task in (
                    self.plan.tasks.values()
                    if self.plan is not None
                    else []
                )
                if task.status == TaskStatus.SKIPPED
            ),
            results=dict(self.results),
            failures=list(self.failures),
            timing=self.timing,
            metadata={
                "context_id": self.context_id,
                **self.runtime_metadata,
            },
        )

        return summary


# ============================================================================
# PUBLIC EXPORTS
# ============================================================================


__all__ = [
    "ExecutionContext",
  ]
