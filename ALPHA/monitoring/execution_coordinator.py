"""
VALE ALPHA - Execution Coordinator

File:
    ALPHA/execution/execution_coordinator.py

Purpose:
    Runs ONE ALPHA mission end-to-end:

        plan  ->  schedule  ->  execute (streaming, parallel)
              ->  record results  ->  recover from failures  ->  report

Architectural boundary:
    HEROIC decides WHAT must be accomplished.
    ALPHA (this coordinator) decides HOW it is executed and reports exactly
    what happened. Brains/tools do the real work through registered handlers.
    MCVL verifies. Supervisor owns operational incidents.

The coordinator never invents results:
    * a task with no handler FAILS ("not executed");
    * a result that does not belong to the dispatched task is rejected;
    * a failed prerequisite makes its hard dependents UNREACHABLE (skipped),
      never "completed";
    * planned work is never reported as done.

Execution model
---------------
``run()`` is **streaming**: the moment a task finishes, newly-ready
dependents start, without waiting for slower siblings (no wave barrier).
``run_cycle()`` is the single-step, wave-synchronous variant used when a
caller wants to drive execution manually.

Failure handling (driven by ALPHA's RecoveryManager)
----------------------------------------------------
    RETRY / RETRY_WITH_BACKOFF  bounded retry; the scheduler *holds* the task
                                for its backoff while other work keeps flowing
    REPLAN                      reroute to an alternative capability if the
                                injected ``fallback_resolver`` finds one,
                                otherwise the task fails permanently
    SKIP                        optional task skipped, work continues
    ESCALATE                    permanent failure + recorded escalation
                                (Supervisor / HEROIC decide what happens next)
    FAIL / CANCEL / DEGRADE     permanent failure

Final outcome vocabulary (honest, distinguishable):
    COMPLETED  every task completed (optional tasks may have been skipped)
    PARTIAL    some completed, some failed / unreachable / blocked
    FAILED     nothing completed
    BLOCKED    nothing failed but remaining work cannot proceed
    CANCELLED  stopped on request
    TIMED_OUT  the execution deadline expired
"""

from __future__ import annotations

import dataclasses
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import monotonic
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set

from ALPHA.Core.execution_context import ExecutionContext
from ALPHA.Core.execution_models import (
    ExecutionFailure,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionSummary,
    ExecutionTask,
    FailureType,
    TaskStatus,
)
from ALPHA.monitoring.execution_monitor import ExecutionMonitor
from ALPHA.Parallel.parallel_executor import (
    ParallelExecutionConfig,
    ParallelExecutionReport,
    ParallelExecutor,
    TaskHandler,
)
from ALPHA.Planning.execution_planner import ExecutionPlanner, PlanningBlueprint
from ALPHA.Recovery.recovery_manager import (
    RecoveryAction,
    RecoveryManager,
    RecoveryManagerConfig,
)
from ALPHA.Scheduling.scheduler_engine import AlphaScheduler
from ALPHA.Scheduling.scheduler_models import (
    SchedulerCapacity,
    SchedulerCycleResult,
    SchedulerPolicy,
    SchedulingDecisionType,
)


# ============================================================================
# EXCEPTIONS
# ============================================================================


class ExecutionCoordinatorError(RuntimeError):
    """Base exception for execution coordination failures."""


class ExecutionCoordinatorConfigurationError(ExecutionCoordinatorError):
    """Raised when coordinator configuration is invalid."""


class ExecutionCycleError(ExecutionCoordinatorError):
    """Raised when an execution cycle cannot be performed safely."""


# ============================================================================
# CONFIGURATION / REPORTS
# ============================================================================

OUTCOME_COMPLETED = "COMPLETED"
OUTCOME_PARTIAL = "PARTIAL"
OUTCOME_FAILED = "FAILED"
OUTCOME_BLOCKED = "BLOCKED"
OUTCOME_CANCELLED = "CANCELLED"
OUTCOME_TIMED_OUT = "TIMED_OUT"

_OUTCOME_TO_STATUS = {
    OUTCOME_COMPLETED: ExecutionStatus.COMPLETED,
    OUTCOME_PARTIAL: ExecutionStatus.PARTIAL,
    OUTCOME_FAILED: ExecutionStatus.FAILED,
    OUTCOME_BLOCKED: ExecutionStatus.WAITING,  # resumable: waiting on something
    OUTCOME_CANCELLED: ExecutionStatus.CANCELLED,
    OUTCOME_TIMED_OUT: ExecutionStatus.TIMED_OUT,
}


@dataclass(frozen=True)
class ExecutionCoordinatorConfig:
    scheduler_policy: SchedulerPolicy = field(default_factory=SchedulerPolicy)
    scheduler_capacity: SchedulerCapacity = field(default_factory=SchedulerCapacity)
    parallel_config: ParallelExecutionConfig = field(default_factory=ParallelExecutionConfig)

    # Safety valve against scheduler loops (counts schedule() calls per run()).
    max_scheduler_cycles_per_call: int = 500
    stop_on_all_tasks_terminal: bool = True

    # True  -> only registered handlers may run tasks.
    # False -> the default handler (e.g. ALPHA's dispatcher) may be used.
    require_registered_handlers: bool = True

    # Every task gets a bounded timeout. Tasks that declare none receive this.
    default_task_timeout_seconds: float = 30.0

    # Wall-clock bound for one run(). None disables it.
    execution_timeout_seconds: Optional[float] = 120.0

    enable_recovery: bool = True
    recovery_config: RecoveryManagerConfig = field(default_factory=RecoveryManagerConfig)

    enable_monitoring: bool = True

    # How many finished executions are kept for inspection.
    retain_executions: int = 64

    def __post_init__(self) -> None:
        if self.max_scheduler_cycles_per_call < 1:
            raise ExecutionCoordinatorConfigurationError(
                "max_scheduler_cycles_per_call must be at least 1."
            )
        if self.default_task_timeout_seconds <= 0:
            raise ExecutionCoordinatorConfigurationError(
                "default_task_timeout_seconds must be positive."
            )
        if self.execution_timeout_seconds is not None and self.execution_timeout_seconds <= 0:
            raise ExecutionCoordinatorConfigurationError(
                "execution_timeout_seconds must be positive or None."
            )
        if self.retain_executions < 1:
            raise ExecutionCoordinatorConfigurationError("retain_executions must be at least 1.")


@dataclass
class ExecutionCycleReport:
    """One manual scheduler/execution step (see ``run_cycle``)."""

    execution_id: str
    cycle_started_at: datetime
    cycle_completed_at: Optional[datetime] = None
    scheduler_cycle: Optional[SchedulerCycleResult] = None
    parallel_report: Optional[ParallelExecutionReport] = None
    execution_results: Dict[str, ExecutionResult] = field(default_factory=dict)
    status: ExecutionStatus = ExecutionStatus.CREATED
    error: Optional[str] = None
    dispatched_task_ids: List[str] = field(default_factory=list)
    recovery_actions: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: Optional[float] = None


@dataclass
class ExecutionRunReport:
    """The final, honest account of one execution."""

    execution_id: str
    plan_id: str
    request_id: str
    status: ExecutionStatus
    outcome: str
    reason: str

    task_outcomes: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    completed_task_ids: List[str] = field(default_factory=list)
    failed_task_ids: List[str] = field(default_factory=list)
    timed_out_task_ids: List[str] = field(default_factory=list)
    skipped_task_ids: List[str] = field(default_factory=list)      # optional, skipped after failure
    unreachable_task_ids: List[str] = field(default_factory=list)  # never ran: required prerequisite failed
    cancelled_task_ids: List[str] = field(default_factory=list)
    blocked_task_ids: List[str] = field(default_factory=list)      # never ran: could not proceed

    recovery_log: List[Dict[str, Any]] = field(default_factory=list)
    escalations: List[Dict[str, Any]] = field(default_factory=list)
    scheduling_cycles: int = 0

    timing_ms: Dict[str, Any] = field(default_factory=dict)
    summary: Optional[ExecutionSummary] = None
    error: Optional[str] = None

    @property
    def successful(self) -> bool:
        return self.outcome == OUTCOME_COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "request_id": self.request_id,
            "status": self.status.value,
            "outcome": self.outcome,
            "reason": self.reason,
            "successful": self.successful,
            "tasks": self.task_outcomes,
            "completed": list(self.completed_task_ids),
            "failed": list(self.failed_task_ids),
            "timed_out": list(self.timed_out_task_ids),
            "skipped_optional": list(self.skipped_task_ids),
            "unreachable": list(self.unreachable_task_ids),
            "cancelled": list(self.cancelled_task_ids),
            "blocked": list(self.blocked_task_ids),
            "recovery_log": list(self.recovery_log),
            "escalations": list(self.escalations),
            "scheduling_cycles": self.scheduling_cycles,
            "timing_ms": dict(self.timing_ms),
            "error": self.error,
        }


# ============================================================================
# INTERNAL RUN STATE
# ============================================================================


@dataclass
class _Run:
    context: ExecutionContext
    scheduler: AlphaScheduler
    executor: ParallelExecutor
    recovery: Optional[RecoveryManager]

    created_mono: float = field(default_factory=monotonic)
    planning_ms: float = 0.0

    started_mono: Optional[float] = None
    deadline_mono: Optional[float] = None
    finished: bool = False
    final: Optional[ExecutionRunReport] = None

    cancel_reason: Optional[str] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    deadline_hit: bool = False
    cycle_limit_hit: bool = False

    scheduling_cycles: int = 0
    scheduling_ms: float = 0.0
    recovery_ms: float = 0.0
    execution_ms: float = 0.0

    attempts: Dict[str, int] = field(default_factory=dict)
    attempt_durations: Dict[str, List[float]] = field(default_factory=dict)
    skipped_ids: Set[str] = field(default_factory=set)
    unreachable_ids: Set[str] = field(default_factory=set)
    recovery_log: List[Dict[str, Any]] = field(default_factory=list)
    escalations: List[Dict[str, Any]] = field(default_factory=list)
    reroutes: Dict[str, List[str]] = field(default_factory=dict)
    cycle_reports: List[ExecutionCycleReport] = field(default_factory=list)
    monitor_errors: List[str] = field(default_factory=list)

    run_lock: threading.RLock = field(default_factory=threading.RLock)


# ============================================================================
# COORDINATOR
# ============================================================================


FallbackResolver = Callable[[ExecutionTask, ExecutionFailure], Optional[str]]


class AlphaExecutionCoordinator:
    """
    Orchestrates the execution of ALPHA missions.

    The coordinator is thread-compatible: independent executions may be run
    from different threads; a single execution is serialised by its own lock.
    """

    VERSION = "1.0.0"
    _MAX_LOG = 500

    def __init__(
        self,
        *,
        config: Optional[ExecutionCoordinatorConfig] = None,
        planner: Optional[ExecutionPlanner] = None,
        monitor: Optional[ExecutionMonitor] = None,
        fallback_resolver: Optional[FallbackResolver] = None,
    ) -> None:
        self.config = config or ExecutionCoordinatorConfig()
        self.planner = planner or ExecutionPlanner()
        self.monitor = monitor if monitor is not None else (
            ExecutionMonitor() if self.config.enable_monitoring else None
        )
        self.fallback_resolver = fallback_resolver

        self._handlers: Dict[str, TaskHandler] = {}
        self._default_handler: Optional[TaskHandler] = None
        self._runs: "OrderedDict[str, _Run]" = OrderedDict()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # HANDLER REGISTRY (copied into each execution's executor)
    # ------------------------------------------------------------------

    def register_handler(self, key: str, handler: TaskHandler) -> None:
        if not key or not str(key).strip():
            raise ValueError("handler key cannot be empty.")
        if not callable(handler):
            raise TypeError("handler must be callable.")
        with self._lock:
            self._handlers[str(key)] = handler

    def register_handlers(self, handlers: Mapping[str, TaskHandler]) -> None:
        for key, handler in handlers.items():
            self.register_handler(key, handler)

    def set_default_handler(self, handler: Optional[TaskHandler]) -> None:
        if handler is not None and not callable(handler):
            raise TypeError("default handler must be callable.")
        with self._lock:
            self._default_handler = handler

    def clear_handlers(self) -> None:
        with self._lock:
            self._handlers.clear()
            self._default_handler = None

    def has_handler_for(self, task: ExecutionTask) -> bool:
        """True if SOME handler (specific or default, per config) could run this task."""

        with self._lock:
            for key in (task.task_id, task.name, task.target, task.capability):
                if key and key in self._handlers:
                    return True
            return (not self.config.require_registered_handlers) and self._default_handler is not None

    # ------------------------------------------------------------------
    # PREPARE
    # ------------------------------------------------------------------

    def prepare(
        self,
        request: ExecutionRequest,
        blueprint: Optional[PlanningBlueprint] = None,
    ) -> str:
        """
        Plan a mission and load it into a fresh scheduler. Executes nothing.

        Returns the execution id.
        """

        if request is None:
            raise ExecutionCoordinatorError("Execution request cannot be None.")

        t0 = monotonic()

        try:
            plan = self.planner.create_plan(request, blueprint=blueprint)
        except Exception as exc:
            raise ExecutionCoordinatorError(f"Planning failed: {exc}") from exc

        default_ms = max(1, int(self.config.default_task_timeout_seconds * 1000))
        for task in plan.tasks.values():
            if task.constraints.timeout_ms is None:
                task.constraints = dataclasses.replace(task.constraints, timeout_ms=default_ms)

        context = ExecutionContext(request=request)
        context.attach_plan(plan)

        scheduler = AlphaScheduler(
            policy=self.config.scheduler_policy,
            capacity=self.config.scheduler_capacity,
        )
        try:
            scheduler.load_plan(plan, execution_id=context.execution_id)
        except Exception as exc:
            raise ExecutionCoordinatorError(f"Scheduling setup failed: {exc}") from exc

        parallel_config = dataclasses.replace(
            self.config.parallel_config,
            default_task_timeout_seconds=self.config.default_task_timeout_seconds,
            require_explicit_handlers=self.config.require_registered_handlers,
        )
        executor = ParallelExecutor(config=parallel_config)
        with self._lock:
            executor.register_handlers(dict(self._handlers))
            executor.set_default_handler(self._default_handler)

        recovery: Optional[RecoveryManager] = None
        if self.config.enable_recovery:
            recovery = RecoveryManager(config=self.config.recovery_config)
            for task in plan.tasks.values():
                recovery.register_task(task, context)

        run = _Run(context=context, scheduler=scheduler, executor=executor, recovery=recovery)
        run.planning_ms = (monotonic() - t0) * 1000.0

        self._safe(run, "created", lambda: self.monitor.observe_execution_created(context))
        self._safe(run, "planned", lambda: self.monitor.observe_execution_planned(context))
        context.add_trace(
            event_type="EXECUTION_PLANNED",
            component="ALPHA.coordinator",
            details={"plan_id": plan.plan_id, "tasks": plan.task_count(), "planning_ms": round(run.planning_ms, 3)},
        )

        with self._lock:
            self._runs[context.execution_id] = run
            self._evict_finished()

        return context.execution_id

    # ------------------------------------------------------------------
    # RUN (streaming)
    # ------------------------------------------------------------------

    def execute(
        self,
        request: ExecutionRequest,
        blueprint: Optional[PlanningBlueprint] = None,
    ) -> ExecutionRunReport:
        """Plan and run a mission to completion (or to an honest stop)."""

        return self.run(self.prepare(request, blueprint))

    def run(self, execution_id: str) -> ExecutionRunReport:
        """
        Run a prepared execution until it completes, fails, is blocked,
        is cancelled or its deadline expires. Returns the final report.

        Calling ``run`` again on a finished execution returns the same report.
        """

        run = self._get(execution_id)

        with run.run_lock:
            if run.final is not None:
                return run.final

            ctx = run.context
            self._begin(run)

            error: Optional[str] = None
            try:
                while True:
                    if run.cancel_event.is_set():
                        break
                    if self._deadline_passed(run):
                        break

                    ids = self._next_dispatch(run)

                    if ids:
                        t0 = monotonic()
                        try:
                            batch = run.executor.execute_tasks(
                                task_ids=ids,
                                context=ctx,
                                on_task_finished=lambda task_id, result: self._on_task_finished(run, task_id, result),
                            )
                        finally:
                            run.execution_ms += (monotonic() - t0) * 1000.0
                        self._note_executor_errors(run, batch)
                        continue

                    if run.scheduler.is_finished():
                        break

                    expiry = run.scheduler.next_hold_expiry()
                    if expiry is not None:
                        wait = max(0.0, expiry - monotonic())
                        if run.deadline_mono is not None:
                            wait = min(wait, max(0.0, run.deadline_mono - monotonic()))
                        run.cancel_event.wait(timeout=min(wait + 0.001, 5.0))
                        continue

                    break  # nothing runnable, nothing running, nothing held: blocked

            except Exception as exc:  # a coordinator fault must end as an honest FAILED report
                error = f"{type(exc).__name__}: {exc}"
                ctx.add_trace(event_type="COORDINATOR_ERROR", component="ALPHA.coordinator", details={"error": error})

            run.final = self._finalize(run, error=error)
            return run.final

    # ------------------------------------------------------------------
    # RUN (single step)
    # ------------------------------------------------------------------

    def run_cycle(self, execution_id: str) -> ExecutionCycleReport:
        """
        Perform ONE wave-synchronous step: schedule, execute the dispatched
        batch to completion, then apply results and recovery.

        When the execution is finished the final report is available through
        ``get_report``.
        """

        run = self._get(execution_id)

        with run.run_lock:
            started = datetime.now(timezone.utc)
            t0 = monotonic()
            report = ExecutionCycleReport(execution_id=execution_id, cycle_started_at=started)

            if run.final is not None:
                report.status = run.final.status
                report.cycle_completed_at = datetime.now(timezone.utc)
                return report

            self._begin(run)

            try:
                ids = self._next_dispatch(run, record_into=report)
                report.dispatched_task_ids = list(ids)

                if ids:
                    t1 = monotonic()
                    parallel = run.executor.execute_tasks(task_ids=ids, context=run.context)
                    run.execution_ms += (monotonic() - t1) * 1000.0
                    report.parallel_report = parallel
                    report.execution_results = dict(parallel.results)
                    self._note_executor_errors(run, parallel)

                    for task_id in parallel.task_ids:
                        if task_id in parallel.results:
                            report.recovery_actions.extend(self._process_outcome(run, task_id, parallel.results[task_id]))
                        elif task_id in parallel.cancelled_task_ids:
                            run.scheduler.mark_cancelled(task_id, "cancelled before start")

                stuck = (
                    not ids
                    and run.scheduler.next_hold_expiry() is None
                    and not run.scheduler.is_finished()
                )
                if (
                    run.cancel_event.is_set()
                    or self._deadline_passed(run)
                    or run.scheduler.is_finished()
                    or stuck
                ):
                    run.final = self._finalize(run)
                    report.status = run.final.status
                else:
                    report.status = run.context.status

            except Exception as exc:
                report.error = f"{type(exc).__name__}: {exc}"
                run.final = self._finalize(run, error=report.error)
                report.status = run.final.status

            report.cycle_completed_at = datetime.now(timezone.utc)
            report.duration_ms = (monotonic() - t0) * 1000.0
            run.cycle_reports.append(report)
            return report

    # ------------------------------------------------------------------
    # CANCEL / INSPECT / LIFECYCLE
    # ------------------------------------------------------------------

    def cancel(self, execution_id: str, reason: str = "cancelled") -> bool:
        """Request cancellation. Running tasks are signalled cooperatively."""

        run = self._get(execution_id)
        if run.final is not None:
            return False
        run.cancel_reason = reason or "cancelled"
        run.cancel_event.set()
        run.executor.cancel_running(reason)
        run.context.add_trace(
            event_type="CANCELLATION_REQUESTED",
            component="ALPHA.coordinator",
            details={"reason": run.cancel_reason},
        )
        return True

    def get_context(self, execution_id: str) -> ExecutionContext:
        return self._get(execution_id).context

    def get_report(self, execution_id: str) -> Optional[ExecutionRunReport]:
        return self._get(execution_id).final

    def snapshot(self, execution_id: str) -> Dict[str, Any]:
        run = self._get(execution_id)
        return {
            "execution_id": execution_id,
            "status": run.context.status.value,
            "finished": run.final is not None,
            "scheduler": run.scheduler.snapshot(),
            "monitor": (self.monitor.snapshot(execution_id) if self.monitor is not None else None),
            "attempts": dict(run.attempts),
            "escalations": list(run.escalations),
            "monitor_errors": list(run.monitor_errors),
        }

    def execution_ids(self) -> List[str]:
        with self._lock:
            return list(self._runs.keys())

    def forget(self, execution_id: str) -> None:
        with self._lock:
            self._runs.pop(execution_id, None)

    # ==================================================================
    # INTERNALS - dispatch & outcome handling
    # ==================================================================

    def _get(self, execution_id: str) -> _Run:
        with self._lock:
            run = self._runs.get(execution_id)
        if run is None:
            raise ExecutionCycleError(f"Unknown execution: {execution_id}")
        return run

    def _evict_finished(self) -> None:
        while len(self._runs) > self.config.retain_executions:
            for key, run in self._runs.items():
                if run.final is not None:
                    del self._runs[key]
                    break
            else:
                return

    def _begin(self, run: _Run) -> None:
        if run.started_mono is not None:
            return
        run.started_mono = monotonic()
        if self.config.execution_timeout_seconds is not None:
            run.deadline_mono = run.started_mono + self.config.execution_timeout_seconds
        run.context.start()
        self._safe(run, "started", lambda: self.monitor.observe_execution_started(run.context))

    def _deadline_passed(self, run: _Run) -> bool:
        if run.deadline_mono is not None and monotonic() >= run.deadline_mono:
            run.deadline_hit = True
            return True
        return False

    def _next_dispatch(self, run: _Run, record_into: Optional[ExecutionCycleReport] = None) -> List[str]:
        """Ask the scheduler what may run now and prepare those tasks."""

        if run.scheduling_cycles >= self.config.max_scheduler_cycles_per_call:
            if not run.cycle_limit_hit:
                run.cycle_limit_hit = True
                run.context.add_trace(
                    event_type="SCHEDULER_CYCLE_LIMIT",
                    component="ALPHA.coordinator",
                    details={"limit": self.config.max_scheduler_cycles_per_call},
                )
            return []

        t0 = monotonic()
        cycle = run.scheduler.schedule()
        run.scheduling_ms += (monotonic() - t0) * 1000.0
        run.scheduling_cycles += 1
        if record_into is not None:
            record_into.scheduler_cycle = cycle

        self._absorb_cycle(run, cycle)

        ids = list(cycle.dispatch_task_ids)
        plan = run.context.plan
        assert plan is not None

        remaining = None
        if run.deadline_mono is not None:
            remaining = max(0.0, run.deadline_mono - monotonic())

        for task_id in ids:
            task = plan.tasks[task_id]
            run.attempts[task_id] = run.attempts.get(task_id, 0) + 1
            if task.status != TaskStatus.READY:
                task.status = TaskStatus.READY

            # The execution deadline caps every task's own timeout.
            if remaining is not None and task.constraints.timeout_ms is not None:
                cap_ms = max(1, int(remaining * 1000))
                if cap_ms < task.constraints.timeout_ms:
                    task.constraints = dataclasses.replace(task.constraints, timeout_ms=cap_ms)

            run.context.add_trace(
                event_type="TASK_DISPATCHED",
                task_id=task_id,
                component="ALPHA.scheduler",
                details={"name": task.name, "target": task.target, "attempt": run.attempts[task_id]},
            )
            self._safe(run, "dispatched", lambda tid=task_id: self.monitor.observe_task_dispatched(run.context, tid))

        return ids

    def _absorb_cycle(self, run: _Run, cycle: SchedulerCycleResult) -> None:
        """Mirror the scheduler's decisions into the context and escalation log."""

        for decision in cycle.decisions:
            if decision.decision == SchedulingDecisionType.CANCEL and decision.metadata.get("unreachable"):
                self._mark_unreachable(run, decision.task_id, decision.metadata.get("explanation") or "prerequisite failed")

            if decision.requires_escalation:
                self._escalate(
                    run,
                    task_id=decision.task_id,
                    reason=(
                        "task is past its deadline"
                        if decision.metadata.get("overdue")
                        else f"scheduler could not admit the task ({decision.reason})"
                    ),
                    source="scheduler",
                    dedupe=True,
                )

            if decision.requires_replanning:
                run.context.runtime_metadata.setdefault("replanning_requested", [])
                reasons = run.context.runtime_metadata["replanning_requested"]
                if len(reasons) < 50:
                    reasons.append({"task_id": decision.task_id, "reason": decision.metadata.get("explanation")})

    def _on_task_finished(self, run: _Run, task_id: str, result: ExecutionResult) -> Sequence[str]:
        """Streaming hook: record the outcome, then immediately schedule successors."""

        self._process_outcome(run, task_id, result)

        if run.cancel_event.is_set() or self._deadline_passed(run):
            return []

        return self._next_dispatch(run)

    def _process_outcome(self, run: _Run, task_id: str, result: ExecutionResult) -> List[Dict[str, Any]]:
        """Apply one finished task to scheduler / recovery / monitor. Returns recovery actions."""

        ctx = run.context
        assert ctx.plan is not None
        task = ctx.plan.tasks[task_id]
        actions: List[Dict[str, Any]] = []

        if result.duration_ms is not None:
            durations = run.attempt_durations.setdefault(task_id, [])
            if len(durations) < 20:
                durations.append(result.duration_ms)

        if result.success:
            run.scheduler.mark_completed(task_id)
            self._safe(run, "completed", lambda: self.monitor.observe_task_completed(ctx, result))
            if run.recovery is not None and run.attempts.get(task_id, 1) > 1:
                self._safe_call(run, lambda: run.recovery.mark_recovered(task_id))
                self._log(run, {"task_id": task_id, "task": task.name, "action": "recovered", "attempt": run.attempts[task_id]})
            return actions

        failure = self._latest_failure(ctx, task_id) or ExecutionFailure(
            task_id=task_id,
            failure_type=result.failure_type or FailureType.EXECUTION,
            message=result.error or "Task failed.",
        )

        timed_out = result.status == TaskStatus.TIMED_OUT
        self._safe(
            run, "failed",
            lambda: (
                self.monitor.observe_task_timed_out(ctx, task_id) if timed_out
                else self.monitor.observe_task_failed(ctx, result)
            ),
        )

        t0 = monotonic()
        action = self._recover(run, task, result, failure, timed_out)
        run.recovery_ms += (monotonic() - t0) * 1000.0
        actions.append(action)
        return actions

    # ------------------------------------------------------------------
    # RECOVERY
    # ------------------------------------------------------------------

    def _recover(
        self,
        run: _Run,
        task: ExecutionTask,
        result: ExecutionResult,
        failure: ExecutionFailure,
        timed_out: bool,
    ) -> Dict[str, Any]:
        task_id = task.task_id

        if run.cancel_event.is_set() or self._deadline_passed(run):
            return self._fail_permanently(run, task, timed_out, "execution was cancelled or its deadline expired; no recovery attempted")

        if run.recovery is None:
            return self._fail_permanently(run, task, timed_out, "recovery is disabled")

        try:
            classification = run.recovery.classify_failure(failure=failure)
            run.recovery.register_failure(task_id, failure, classification)
            decision = run.recovery.decide(task_id)
        except Exception as exc:
            return self._fail_permanently(run, task, timed_out, f"recovery could not decide ({type(exc).__name__}: {exc})")

        action = decision.action

        if action in (RecoveryAction.RETRY, RecoveryAction.RETRY_WITH_BACKOFF):
            return self._retry(run, task, failure, decision.backoff_seconds, decision.reason, str(action.value))

        if action == RecoveryAction.REPLAN:
            alternative = self._find_alternative(task, failure)
            if alternative is not None:
                return self._reroute(run, task, failure, alternative, decision.reason)
            return self._fail_permanently(
                run, task, timed_out,
                "no alternative capability available to replan this task",
                action_name="replan_unavailable",
            )

        if action == RecoveryAction.SKIP:
            return self._skip(run, task, decision.reason)

        if action == RecoveryAction.ESCALATE:
            self._escalate(run, task_id=task_id, reason=decision.reason, source="recovery")
            return self._fail_permanently(run, task, timed_out, decision.reason, action_name="escalate")

        return self._fail_permanently(run, task, timed_out, decision.reason, action_name=str(action.value))

    def _find_alternative(self, task: ExecutionTask, failure: ExecutionFailure) -> Optional[str]:
        if self.fallback_resolver is None:
            return None
        try:
            alternative = self.fallback_resolver(task, failure)
        except Exception:
            return None
        if not alternative or alternative == task.target:
            return None
        tried = {task.target}
        tried.update(self._reroutes_for(task))
        return None if alternative in tried else alternative

    @staticmethod
    def _reroutes_for(task: ExecutionTask) -> List[str]:
        history = task.metadata.get("reroute_history")
        return list(history) if isinstance(history, list) else []

    def _reset_for_retry(self, run: _Run, task: ExecutionTask, failure: ExecutionFailure) -> None:
        ctx = run.context
        ctx.failed_task_ids.discard(task.task_id)
        ctx.timed_out_task_ids.discard(task.task_id)
        ctx.active_task_ids.discard(task.task_id)

        history = ctx.runtime_metadata.setdefault("attempt_history", {}).setdefault(task.task_id, [])
        if len(history) < 10:
            history.append({
                "attempt": run.attempts.get(task.task_id, 1),
                "failure_type": failure.failure_type.value,
                "error": failure.message,
                "target": task.target,
            })

        task.retry_count += 1
        task.status = TaskStatus.READY

    def _retry(
        self,
        run: _Run,
        task: ExecutionTask,
        failure: ExecutionFailure,
        backoff_seconds: float,
        reason: str,
        action_name: str,
    ) -> Dict[str, Any]:
        self._reset_for_retry(run, task, failure)
        run.scheduler.mark_retry(task.task_id)
        if backoff_seconds and backoff_seconds > 0:
            run.scheduler.hold_until(task.task_id, monotonic() + backoff_seconds)

        entry = {
            "task_id": task.task_id, "task": task.name, "action": action_name,
            "attempt_failed": run.attempts.get(task.task_id, 1),
            "backoff_seconds": round(float(backoff_seconds or 0.0), 3),
            "failure_type": failure.failure_type.value, "reason": reason,
        }
        self._log(run, entry)
        run.context.add_trace(event_type="TASK_RETRY_SCHEDULED", task_id=task.task_id, component="ALPHA.recovery", details=entry)
        return entry

    def _reroute(
        self,
        run: _Run,
        task: ExecutionTask,
        failure: ExecutionFailure,
        alternative: str,
        reason: str,
    ) -> Dict[str, Any]:
        previous = task.target
        history = self._reroutes_for(task)
        history.append(previous)
        task.metadata["reroute_history"] = history
        task.metadata["rerouted_from"] = previous
        task.target = alternative

        self._reset_for_retry(run, task, failure)
        run.scheduler.mark_retry(task.task_id)

        entry = {
            "task_id": task.task_id, "task": task.name, "action": "reroute",
            "from": previous, "to": alternative,
            "failure_type": failure.failure_type.value, "reason": reason,
        }
        self._log(run, entry)
        run.context.add_trace(event_type="TASK_REROUTED", task_id=task.task_id, component="ALPHA.recovery", details=entry)
        return entry

    def _skip(self, run: _Run, task: ExecutionTask, reason: str) -> Dict[str, Any]:
        ctx = run.context
        ctx.failed_task_ids.discard(task.task_id)
        ctx.timed_out_task_ids.discard(task.task_id)
        ctx.active_task_ids.discard(task.task_id)
        ctx.cancelled_task_ids.add(task.task_id)
        task.status = TaskStatus.SKIPPED
        run.skipped_ids.add(task.task_id)
        run.scheduler.mark_cancelled(task.task_id, f"optional task skipped: {reason}")

        entry = {"task_id": task.task_id, "task": task.name, "action": "skip_optional", "reason": reason}
        self._log(run, entry)
        ctx.add_trace(event_type="TASK_SKIPPED", task_id=task.task_id, component="ALPHA.recovery", details=entry)
        return entry

    def _fail_permanently(
        self,
        run: _Run,
        task: ExecutionTask,
        timed_out: bool,
        reason: str,
        *,
        action_name: str = "fail",
    ) -> Dict[str, Any]:
        if timed_out:
            run.scheduler.mark_timed_out(task.task_id)
        else:
            run.scheduler.mark_failed(task.task_id)

        entry = {"task_id": task.task_id, "task": task.name, "action": action_name, "reason": reason, "permanent": True}
        self._log(run, entry)
        run.context.add_trace(event_type="TASK_FAILED_PERMANENTLY", task_id=task.task_id, component="ALPHA.recovery", details=entry)
        return entry

    def _mark_unreachable(self, run: _Run, task_id: str, reason: str) -> None:
        ctx = run.context
        task = ctx.plan.tasks[task_id]  # type: ignore[union-attr]
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMED_OUT, TaskStatus.SKIPPED, TaskStatus.CANCELLED):
            return
        ctx.cancelled_task_ids.add(task_id)
        task.status = TaskStatus.SKIPPED
        run.unreachable_ids.add(task_id)
        ctx.add_trace(
            event_type="TASK_UNREACHABLE",
            task_id=task_id,
            component="ALPHA.scheduler",
            details={"name": task.name, "reason": reason},
        )
        self._safe(run, "unreachable", lambda: self.monitor.observe_task_cancelled(ctx, task_id))

    def _escalate(self, run: _Run, *, task_id: str, reason: str, source: str, dedupe: bool = False) -> None:
        if dedupe and any(e["task_id"] == task_id and e["source"] == source for e in run.escalations):
            return
        if len(run.escalations) >= self._MAX_LOG:
            return
        task = run.context.plan.tasks.get(task_id) if run.context.plan else None
        run.escalations.append({
            "task_id": task_id,
            "task": task.name if task else None,
            "target": task.target if task else None,
            "reason": reason,
            "source": source,
            "owner": "SUPERVISOR",  # operational incidents belong to Supervisor
        })

    # ==================================================================
    # INTERNALS - finalisation
    # ==================================================================

    def _finalize(self, run: _Run, *, error: Optional[str] = None) -> ExecutionRunReport:
        ctx = run.context
        plan = ctx.plan
        assert plan is not None
        finished_mono = monotonic()
        self._deadline_passed(run)  # settles run.deadline_hit if the deadline has passed

        # Never leave a task "running": anything still active is reported honestly.
        for task in plan.tasks.values():
            if task.status == TaskStatus.RUNNING and task.task_id not in ctx.results:
                ctx.active_task_ids.discard(task.task_id)

        cancelled_by_request = run.cancel_event.is_set()
        remaining: List[ExecutionTask] = []

        for task in plan.tasks.values():
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMED_OUT, TaskStatus.SKIPPED, TaskStatus.CANCELLED):
                continue
            remaining.append(task)

        reason_detail = ""
        if cancelled_by_request:
            reason_detail = f"cancelled: {run.cancel_reason or 'requested'}"
            for task in remaining:
                ctx.mark_task_cancelled(task.task_id, reason_detail)
        elif run.deadline_hit:
            reason_detail = f"execution deadline of {self.config.execution_timeout_seconds}s expired"
            for task in remaining:
                ctx.mark_task_cancelled(task.task_id, reason_detail)
        else:
            for task in remaining:
                task.status = TaskStatus.BLOCKED

        completed = [t for t in plan.tasks.values() if t.status == TaskStatus.COMPLETED]
        failed = [t for t in plan.tasks.values() if t.status == TaskStatus.FAILED]
        timed_out = [t for t in plan.tasks.values() if t.status == TaskStatus.TIMED_OUT]
        skipped = [t for t in plan.tasks.values() if t.task_id in run.skipped_ids]
        unreachable = [t for t in plan.tasks.values() if t.task_id in run.unreachable_ids]
        cancelled = [
            t for t in plan.tasks.values()
            if t.status == TaskStatus.CANCELLED
        ]
        blocked = [t for t in plan.tasks.values() if t.status == TaskStatus.BLOCKED]

        if error is not None:
            outcome, reason = (OUTCOME_PARTIAL if completed else OUTCOME_FAILED), f"coordinator error: {error}"
        elif cancelled_by_request:
            outcome, reason = OUTCOME_CANCELLED, reason_detail
        elif run.deadline_hit:
            outcome, reason = OUTCOME_TIMED_OUT, reason_detail
        elif not (failed or timed_out or unreachable or cancelled or blocked):
            outcome = OUTCOME_COMPLETED
            reason = (
                f"all tasks completed; {len(skipped)} optional task(s) skipped after failure"
                if skipped else "all tasks completed"
            )
        elif completed:
            outcome = OUTCOME_PARTIAL
            reason = self._describe_gaps(failed, timed_out, unreachable, blocked, run)
        elif blocked and not (failed or timed_out):
            outcome = OUTCOME_BLOCKED
            reason = self._describe_gaps(failed, timed_out, unreachable, blocked, run)
        else:
            outcome = OUTCOME_FAILED
            reason = self._describe_gaps(failed, timed_out, unreachable, blocked, run)

        if run.cycle_limit_hit and outcome in (OUTCOME_PARTIAL, OUTCOME_BLOCKED, OUTCOME_FAILED):
            reason += f"; scheduler cycle limit ({self.config.max_scheduler_cycles_per_call}) reached"

        # --- context finalisation (what ExecutionContext.complete() does, but for ANY outcome)
        ctx.completed_at_monotonic = finished_mono
        if ctx.timing is None:
            ctx.start()
        if ctx.timing is not None:
            ctx.timing.completed_at_monotonic = finished_mono
            ctx.timing.finalize()
        ctx.set_status(_OUTCOME_TO_STATUS[outcome])
        ctx.add_trace(
            event_type="EXECUTION_FINISHED",
            component="ALPHA.coordinator",
            status=outcome,
            details={"reason": reason},
        )

        started = run.started_mono if run.started_mono is not None else finished_mono
        total_ms = (finished_mono - started) * 1000.0
        timing = self._timing(run, total_ms)
        ctx.runtime_metadata["alpha_timing_ms"] = timing
        ctx.runtime_metadata["alpha_outcome"] = outcome

        if outcome == OUTCOME_COMPLETED:
            self._safe(run, "done", lambda: self.monitor.observe_execution_completed(ctx))
        elif outcome == OUTCOME_BLOCKED:
            self._safe(run, "waiting", lambda: self.monitor.observe_execution_waiting(ctx))
        else:
            self._safe(run, "failed", lambda: self.monitor.observe_execution_failed(ctx, error=reason))

        report = ExecutionRunReport(
            execution_id=ctx.execution_id,
            plan_id=plan.plan_id,
            request_id=ctx.request.request_id,
            status=ctx.status,
            outcome=outcome,
            reason=reason,
            task_outcomes=self._task_outcomes(run),
            completed_task_ids=[t.task_id for t in completed],
            failed_task_ids=[t.task_id for t in failed],
            timed_out_task_ids=[t.task_id for t in timed_out],
            skipped_task_ids=[t.task_id for t in skipped],
            unreachable_task_ids=[t.task_id for t in unreachable],
            cancelled_task_ids=[t.task_id for t in cancelled if t.task_id not in run.skipped_ids and t.task_id not in run.unreachable_ids],
            blocked_task_ids=[t.task_id for t in blocked],
            recovery_log=list(run.recovery_log),
            escalations=list(run.escalations),
            scheduling_cycles=run.scheduling_cycles,
            timing_ms=timing,
            summary=ctx.build_summary(),
            error=error,
        )
        run.finished = True
        return report

    @staticmethod
    def _describe_gaps(failed, timed_out, unreachable, blocked, run: _Run) -> str:
        parts: List[str] = []
        if failed:
            parts.append(f"{len(failed)} task(s) failed: " + ", ".join(t.name for t in failed[:6]))
        if timed_out:
            parts.append(f"{len(timed_out)} task(s) timed out: " + ", ".join(t.name for t in timed_out[:6]))
        if unreachable:
            parts.append(f"{len(unreachable)} task(s) could not run because a required prerequisite failed")
        if blocked:
            parts.append(f"{len(blocked)} task(s) blocked and did not run")
        return "; ".join(parts) or "no task completed"

    def _timing(self, run: _Run, total_ms: float) -> Dict[str, Any]:
        """Measured (never estimated) timing, including the observed critical path."""

        ctx = run.context
        plan = ctx.plan
        assert plan is not None

        last_duration: Dict[str, float] = {}
        task_runtime_sum = 0.0
        for task_id, durations in run.attempt_durations.items():
            task_runtime_sum += sum(durations)
            if durations:
                last_duration[task_id] = durations[-1]

        graph = run.scheduler.current_graph()
        finish: Dict[str, float] = {}
        best_prev: Dict[str, Optional[str]] = {}
        if graph is not None:
            for task_id in graph.topological_order():
                if task_id not in ctx.completed_task_ids:
                    continue
                prerequisite_ids = [
                    p for p in graph.prerequisites(task_id)
                    if p in finish
                ]
                start = max((finish[p] for p in prerequisite_ids), default=0.0)
                best_prev[task_id] = max(prerequisite_ids, key=lambda p: finish[p]) if prerequisite_ids else None
                finish[task_id] = start + last_duration.get(task_id, 0.0)

        critical_ms = max(finish.values(), default=0.0)
        path: List[str] = []
        if finish:
            cursor: Optional[str] = max(finish, key=lambda k: finish[k])
            while cursor is not None:
                path.append(cursor)
                cursor = best_prev.get(cursor)
            path.reverse()

        alpha_overhead = run.planning_ms + run.scheduling_ms + run.recovery_ms
        wall_execution = run.execution_ms

        return {
            "planning_ms": round(run.planning_ms, 3),
            "scheduling_ms": round(run.scheduling_ms, 3),
            "recovery_decision_ms": round(run.recovery_ms, 3),
            "alpha_overhead_ms": round(alpha_overhead, 3),
            "execution_wall_ms": round(wall_execution, 3),
            "total_ms": round(total_ms, 3),
            "task_runtime_sum_ms": round(task_runtime_sum, 3),
            "observed_critical_path_ms": round(critical_ms, 3),
            "observed_critical_path": [plan.tasks[t].name for t in path],
            "parallel_speedup": (round(task_runtime_sum / wall_execution, 3) if wall_execution > 0 and task_runtime_sum > 0 else None),
            "scheduling_cycles": run.scheduling_cycles,
        }

    def _task_outcomes(self, run: _Run) -> Dict[str, Dict[str, Any]]:
        ctx = run.context
        plan = ctx.plan
        assert plan is not None
        outcomes: Dict[str, Dict[str, Any]] = {}

        for task in plan.tasks.values():
            result = ctx.results.get(task.task_id)
            entry: Dict[str, Any] = {
                "name": task.name,
                "target": task.target,
                "capability": task.capability,
                "status": task.status.value,
                "attempts": run.attempts.get(task.task_id, 0),
                "executed": run.attempts.get(task.task_id, 0) > 0
                and not (result is not None and result.metadata.get("unavailable")),
            }
            if result is not None:
                entry["duration_ms"] = None if result.duration_ms is None else round(result.duration_ms, 3)
                entry["success"] = result.success
                if result.error:
                    entry["error"] = result.error
                if result.failure_type is not None:
                    entry["failure_type"] = result.failure_type.value
                if result.worker_id:
                    entry["worker"] = result.worker_id
            if task.metadata.get("rerouted_from"):
                entry["rerouted_from"] = task.metadata["rerouted_from"]
            if task.task_id in run.unreachable_ids:
                entry["reason"] = run.scheduler.cancel_reason(task.task_id) or "required prerequisite did not complete"
            elif task.task_id in run.skipped_ids:
                entry["reason"] = "optional task skipped after failure"
            elif task.status == TaskStatus.BLOCKED:
                entry["reason"] = "could not proceed (blocked)"
            outcomes[task.task_id] = entry

        return outcomes

    # ------------------------------------------------------------------
    # SMALL HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _latest_failure(ctx: ExecutionContext, task_id: str) -> Optional[ExecutionFailure]:
        for failure in reversed(ctx.failures):
            if failure.task_id == task_id:
                return failure
        return None

    def _note_executor_errors(self, run: _Run, batch: ParallelExecutionReport) -> None:
        problem = batch.errors.get("__on_task_finished__")
        if problem:
            errors = run.context.runtime_metadata.setdefault("executor_errors", [])
            if len(errors) < 25:
                errors.append(problem)
            run.context.add_trace(
                event_type="EXECUTOR_ERROR",
                component="ALPHA.executor",
                details={"error": problem},
            )

    def _log(self, run: _Run, entry: Dict[str, Any]) -> None:
        if len(run.recovery_log) < self._MAX_LOG:
            run.recovery_log.append(entry)

    def _safe(self, run: _Run, label: str, fn: Callable[[], Any]) -> None:
        """Run a monitor hook; monitoring must never break execution."""

        if self.monitor is None:
            return
        self._safe_call(run, fn, label)

    def _safe_call(self, run: _Run, fn: Callable[[], Any], label: str = "hook") -> None:
        try:
            fn()
        except Exception as exc:
            if len(run.monitor_errors) < 25:
                run.monitor_errors.append(f"{label}: {type(exc).__name__}: {exc}")


__all__ = [
    "AlphaExecutionCoordinator",
    "ExecutionCoordinatorConfig",
    "ExecutionCoordinatorConfigurationError",
    "ExecutionCoordinatorError",
    "ExecutionCycleError",
    "ExecutionCycleReport",
    "ExecutionRunReport",
    "FallbackResolver",
    "OUTCOME_BLOCKED",
    "OUTCOME_CANCELLED",
    "OUTCOME_COMPLETED",
    "OUTCOME_FAILED",
    "OUTCOME_PARTIAL",
    "OUTCOME_TIMED_OUT",
]
