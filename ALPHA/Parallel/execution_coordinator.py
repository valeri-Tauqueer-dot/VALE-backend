"""
VALE ALPHA - Execution Coordinator

File:
    ALPHA/execution/execution_coordinator.py

Purpose:
    Coordinate the first complete ALPHA execution lifecycle:

        Execution Request
              ↓
        Execution Plan
              ↓
        Dependency Graph
              ↓
        Scheduler
              ↓
        Dispatch Batch
              ↓
        Parallel Executor
              ↓
        Execution Results
              ↓
        Execution Context

Architectural boundary:

    HEROIC decides WHAT needs to happen.

    ALPHA decides HOW that work should be planned, scheduled,
    dispatched, and executed.

    Specialist brains/capabilities perform intelligence.

    MCVL verifies results where required.

    UNITY remains responsible for system-wide integration and
    final synthesis.

This coordinator is deliberately an ALPHA execution component.
It does not become a replacement for HEROIC, UNITY, MCVL, or Supervisor.

Important:
    This module does not fabricate task handlers.
    Tasks must be explicitly registered with the ParallelExecutor.
"""


from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

from ALPHA.core.execution_context import ExecutionContext
from ALPHA.core.execution_models import (
    ExecutionPlan,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)

from ALPHA.planning.execution_planner import (
    ExecutionPlanner,
    PlanningBlueprint,
    PlanningError,
)

from ALPHA.scheduling.scheduler_engine import (
    AlphaScheduler,
    SchedulerError,
)

from ALPHA.scheduling.scheduler_models import (
    SchedulerCapacity,
    SchedulerInput,
    SchedulerPolicy,
    SchedulerCycleResult,
)

from ALPHA.parallel.parallel_executor import (
    ParallelExecutionConfig,
    ParallelExecutionError,
    ParallelExecutionReport,
    ParallelExecutor,
    TaskHandler,
)


class ExecutionCoordinatorError(RuntimeError):
    """Base exception for ALPHA execution coordination failures."""


class ExecutionCoordinatorConfigurationError(
    ExecutionCoordinatorError
):
    """Raised when coordinator configuration is invalid."""


class ExecutionCycleError(ExecutionCoordinatorError):
    """Raised when an ALPHA execution cycle cannot continue safely."""


@dataclass(frozen=True)
class ExecutionCoordinatorConfig:
    """
    Configuration for the ALPHA execution coordinator.
    """

    scheduler_policy: SchedulerPolicy = field(
        default_factory=SchedulerPolicy
    )

    scheduler_capacity: SchedulerCapacity = field(
        default_factory=SchedulerCapacity
    )

    parallel_config: ParallelExecutionConfig = field(
        default_factory=ParallelExecutionConfig
    )

    max_scheduler_cycles_per_call: int = 1

    stop_on_all_tasks_terminal: bool = True

    require_registered_handlers: bool = True

    def __post_init__(self) -> None:
        if self.max_scheduler_cycles_per_call < 1:
            raise ExecutionCoordinatorConfigurationError(
                "max_scheduler_cycles_per_call must be at least 1."
            )


@dataclass
class ExecutionCycleReport:
    """
    Complete report for one coordinator execution cycle.
    """

    execution_id: str

    cycle_started_at: datetime

    cycle_completed_at: Optional[datetime] = None

    scheduler_cycle: Optional[SchedulerCycleResult] = None

    parallel_report: Optional[ParallelExecutionReport] = None

    execution_results: Dict[
        str,
        ExecutionResult,
    ] = field(default_factory=dict)

    status: ExecutionStatus = ExecutionStatus.CREATED

    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """
        True when the cycle completed without execution failures.
        """

        if self.error is not None:
            return False

        if self.parallel_report is None:
            return True

        return self.parallel_report.success

    @property
    def completed_task_count(self) -> int:
        return len(
            self.parallel_report.completed_task_ids
            if self.parallel_report
            else []
        )

    @property
    def failed_task_count(self) -> int:
        return len(
            self.parallel_report.failed_task_ids
            if self.parallel_report
            else []
        )


class AlphaExecutionCoordinator:
    """
    Coordinates ALPHA's planning, scheduling and execution layers.

    This class intentionally does not contain the implementation of:

        - planning intelligence
        - dependency graph algorithms
        - scheduling algorithms
        - parallel worker execution
        - retry policy
        - timeout enforcement
        - resource prediction
        - MCVL verification

    Those responsibilities remain in their dedicated modules.

    This component is the connective runtime between them.
    """

    def __init__(
        self,
        *,
        config: Optional[
            ExecutionCoordinatorConfig
        ] = None,
    ) -> None:
        self.config = (
            config
            or ExecutionCoordinatorConfig()
        )

        self.planner = ExecutionPlanner()

        self.scheduler = AlphaScheduler(
            policy=self.config.scheduler_policy,
            capacity=self.config.scheduler_capacity,
        )

        self.executor = ParallelExecutor(
            config=self.config.parallel_config
        )

        self._contexts: Dict[
            str,
            ExecutionContext,
        ] = {}

    # ------------------------------------------------------------------
    # HANDLER REGISTRATION
    # ------------------------------------------------------------------

    def register_handler(
        self,
        task_id: str,
        handler: TaskHandler,
    ) -> None:
        """
        Register the real implementation responsible for executing
        one ALPHA task.
        """

        self.executor.register_handler(
            task_id,
            handler,
        )

    def register_handlers(
        self,
        handlers: Mapping[
            str,
            TaskHandler,
        ],
    ) -> None:
        """
        Register multiple task handlers.
        """

        self.executor.register_handlers(
            handlers
        )

    def unregister_handler(
        self,
        task_id: str,
    ) -> None:
        self.executor.unregister_handler(
            task_id
        )

    # ------------------------------------------------------------------
    # EXECUTION ENTRY POINT
    # ------------------------------------------------------------------

    def execute(
        self,
        *,
        request: ExecutionRequest,
        blueprint: Optional[
            PlanningBlueprint
        ] = None,
    ) -> ExecutionCycleReport:
        """
        Execute an ALPHA request through the complete current pipeline.

        Current pipeline:

            Request
              ↓
            Planner
              ↓
            Context
              ↓
            Scheduler
              ↓
            Parallel Executor
              ↓
            Results

        The method intentionally executes only tasks that the scheduler
        dispatches.
        """

        if request is None:
            raise ValueError(
                "Execution request cannot be None."
            )

        cycle_started_at = self._utc_now()

        context = self._create_context(
            request
        )

        report = ExecutionCycleReport(
            execution_id=context.execution_id,
            cycle_started_at=cycle_started_at,
            status=ExecutionStatus.CREATED,
        )

        self._contexts[
            context.execution_id
        ] = context

        try:
            context.start()

            plan = self._build_plan(
                request=request,
                blueprint=blueprint,
            )

            context.attach_plan(
                plan
            )

            self.scheduler.load_plan(
                plan
            )

            report.status = (
                ExecutionStatus.PLANNED
            )

            scheduler_cycle = (
                self.scheduler.schedule(
                    SchedulerInput()
                )
            )

            report.scheduler_cycle = (
                scheduler_cycle
            )

            dispatch_batch = (
                scheduler_cycle.dispatch_batch
            )

            if not dispatch_batch.task_ids:
                self._finalize_without_dispatch(
                    context=context,
                    report=report,
                )

                return report

            parallel_report = (
                self.executor.execute(
                    dispatch_batch=dispatch_batch,
                    context=context,
                )
            )

            report.parallel_report = (
                parallel_report
            )

            report.execution_results = dict(
                parallel_report.results
            )

            self._synchronize_scheduler(
                parallel_report
            )

            self._finalize_context(
                context=context,
                report=report,
            )

            return report

        except (
            PlanningError,
            SchedulerError,
            ParallelExecutionError,
        ) as exc:
            return self._handle_cycle_error(
                context=context,
                report=report,
                error=exc,
            )

        except Exception as exc:
            return self._handle_cycle_error(
                context=context,
                report=report,
                error=exc,
            )

    # ------------------------------------------------------------------
    # PLAN CREATION
    # ------------------------------------------------------------------

    def _build_plan(
        self,
        *,
        request: ExecutionRequest,
        blueprint: Optional[
            PlanningBlueprint
        ],
    ) -> ExecutionPlan:
        """
        Ask the dedicated planner to construct the execution plan.

        The coordinator does not independently invent tasks.
        """

        return self.planner.create_plan(
            request,
            blueprint=blueprint,
        )

    # ------------------------------------------------------------------
    # CONTEXT
    # ------------------------------------------------------------------

    def _create_context(
        self,
        request: ExecutionRequest,
    ) -> ExecutionContext:
        """
        Create one execution-scoped context.

        Execution state is isolated from other requests.
        """

        return ExecutionContext(
            request=request
        )

    def get_context(
        self,
        execution_id: str,
    ) -> Optional[
        ExecutionContext
    ]:
        """
        Retrieve an execution context by execution ID.
        """

        return self._contexts.get(
            execution_id
        )

    # ------------------------------------------------------------------
    # SCHEDULER SYNCHRONIZATION
    # ------------------------------------------------------------------

    def _synchronize_scheduler(
        self,
        report: ParallelExecutionReport,
    ) -> None:
        """
        Send actual execution observations back to the scheduler.

        This is important:

            Executor observes execution.
            Scheduler updates scheduling state.

        The scheduler is never told that a task completed unless the
        executor actually reports it.
        """

        for task_id in report.completed_task_ids:
            self.scheduler.mark_completed(
                task_id
            )

        for task_id in report.failed_task_ids:
            self.scheduler.mark_failed(
                task_id
            )

    # ------------------------------------------------------------------
    # FINALIZATION
    # ------------------------------------------------------------------

    def _finalize_context(
        self,
        *,
        context: ExecutionContext,
        report: ExecutionCycleReport,
    ) -> None:
        """
        Determine the execution lifecycle state after the current cycle.
        """

        if report.error is not None:
            context.set_status(
                ExecutionStatus.FAILED
            )

            report.status = (
                ExecutionStatus.FAILED
            )

            report.cycle_completed_at = (
                self._utc_now()
            )

            return

        if (
            report.parallel_report
            and report.parallel_report.failed_task_ids
        ):
            context.set_status(
                ExecutionStatus.FAILED
            )

            report.status = (
                ExecutionStatus.FAILED
            )

        elif self._context_all_tasks_terminal(
            context
        ):
            context.complete()

            report.status = (
                ExecutionStatus.COMPLETED
            )

        else:
            context.set_status(
                ExecutionStatus.WAITING
            )

            report.status = (
                ExecutionStatus.WAITING
            )

        report.cycle_completed_at = (
            self._utc_now()
        )

    def _finalize_without_dispatch(
        self,
        *,
        context: ExecutionContext,
        report: ExecutionCycleReport,
    ) -> None:
        """
        Handle a scheduling cycle that produced no dispatchable work.
        """

        if self._context_all_tasks_terminal(
            context
        ):
            context.complete()

            report.status = (
                ExecutionStatus.COMPLETED
            )
        else:
            context.set_status(
                ExecutionStatus.WAITING
            )

            report.status = (
                ExecutionStatus.WAITING
            )

        report.cycle_completed_at = (
            self._utc_now()
        )

    def _context_all_tasks_terminal(
        self,
        context: ExecutionContext,
    ) -> bool:
        """
        Determine whether every planned task has reached a terminal state.
        """

        if context.plan is None:
            return False

        terminal_ids = (
            set(context.completed_task_ids)
            | set(context.failed_task_ids)
            | set(context.cancelled_task_ids)
            | set(context.timed_out_task_ids)
        )

        return all(
            task.task_id in terminal_ids
            for task in context.plan.tasks
        )

    # ------------------------------------------------------------------
    # ERROR HANDLING
    # ------------------------------------------------------------------

    def _handle_cycle_error(
        self,
        *,
        context: ExecutionContext,
        report: ExecutionCycleReport,
        error: Exception,
    ) -> ExecutionCycleReport:
        """
        Record an execution failure without hiding it.

        Recovery/retry intelligence will be added in the dedicated
        recovery layer rather than being embedded here.
        """

        message = str(error)

        context.runtime_metadata[
            "execution_coordinator_error"
        ] = message

        context.runtime_metadata[
            "execution_coordinator_error_type"
        ] = type(error).__name__

        context.set_status(
            ExecutionStatus.FAILED
        )

        report.status = (
            ExecutionStatus.FAILED
        )

        report.error = message

        report.cycle_completed_at = (
            self._utc_now()
        )

        return report

    # ------------------------------------------------------------------
    # RUNTIME CONTROL
    # ------------------------------------------------------------------

    def update_capacity(
        self,
        capacity: SchedulerCapacity,
    ) -> None:
        """
        Update scheduler execution capacity.

        Capacity must come from real runtime/resource information.
        """

        self.scheduler.update_capacity(
            capacity
        )

    def clear_execution(
        self,
        execution_id: str,
    ) -> bool:
        """
        Remove an execution context from the coordinator.

        This does not erase historical external telemetry or learning
        records. It only releases the coordinator's in-memory reference.
        """

        return (
            self._contexts.pop(
                execution_id,
                None,
            )
            is not None
        )

    def active_execution_ids(self) -> list[str]:
        """
        Return execution IDs currently retained by this coordinator.
        """

        return list(
            self._contexts.keys()
        )

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(
            timezone.utc
        )


__all__ = [
    "ExecutionCoordinatorError",
    "ExecutionCoordinatorConfigurationError",
    "ExecutionCycleError",
    "ExecutionCoordinatorConfig",
    "ExecutionCycleReport",
    "AlphaExecutionCoordinator",
]
