"""
VALE ALPHA - Execution Monitor

File:
    ALPHA/monitoring/execution_monitor.py

Purpose:
    Observe and record ALPHA execution lifecycle events and real timing
    information.

Architectural boundary:

    ALPHA executes and optimizes work.
    ExecutionMonitor observes execution.
    Supervisor may later consume health signals.
    MCVL may later consume execution provenance/reliability signals.
    UNITY may later consume system-level execution state.

This module does NOT:
    - fabricate metrics
    - benchmark nonexistent work
    - determine truth
    - replace Supervisor
    - replace MCVL
    - change scheduling decisions by itself
    - execute tasks
    - silently hide failures

Only timestamps and events actually observed by this runtime are recorded.
"""


from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ALPHA.core.execution_context import ExecutionContext
from ALPHA.core.execution_models import (
    ExecutionResult,
    ExecutionStatus,
    ExecutionTask,
    ExecutionTiming,
    TaskStatus,
)

from ALPHA.parallel.parallel_executor import (
    ParallelExecutionReport,
)

from ALPHA.scheduling.scheduler_models import (
    SchedulerCycleResult,
)


class ExecutionMonitorError(RuntimeError):
    """Base exception for execution-monitor failures."""


class MonitoringConfigurationError(
    ExecutionMonitorError
):
    """Raised when monitoring configuration is invalid."""


class MonitoringEventType:
    """
    String constants for execution-monitor events.

    These are intentionally simple immutable values so they can be
    serialized into logs, telemetry stores, or event buses later.
    """

    EXECUTION_CREATED = "execution.created"
    EXECUTION_STARTED = "execution.started"
    EXECUTION_PLANNED = "execution.planned"

    SCHEDULER_CYCLE_STARTED = "scheduler.cycle.started"
    SCHEDULER_CYCLE_COMPLETED = "scheduler.cycle.completed"

    TASK_READY = "task.ready"
    TASK_DISPATCHED = "task.dispatched"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_TIMED_OUT = "task.timed_out"

    EXECUTION_WAITING = "execution.waiting"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"

    MONITORING_ERROR = "monitoring.error"


@dataclass(frozen=True)
class MonitoringEvent:
    """
    Immutable observation of one execution lifecycle event.
    """

    event_id: str

    event_type: str

    timestamp: datetime

    execution_id: Optional[str] = None

    task_id: Optional[str] = None

    status: Optional[str] = None

    details: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class TaskTimingRecord:
    """
    Actual observed timing for one task.

    Values remain None until the corresponding event has actually
    occurred.
    """

    task_id: str

    ready_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    timed_out_at: Optional[datetime] = None

    @property
    def queue_wait_seconds(self) -> Optional[float]:
        if (
            self.ready_at is None
            or self.dispatched_at is None
        ):
            return None

        return max(
            0.0,
            (
                self.dispatched_at
                - self.ready_at
            ).total_seconds(),
        )

    @property
    def execution_seconds(self) -> Optional[float]:
        if (
            self.started_at is None
            or self.completed_at is None
        ):
            return None

        return max(
            0.0,
            (
                self.completed_at
                - self.started_at
            ).total_seconds(),
        )

    @property
    def failure_seconds(self) -> Optional[float]:
        if (
            self.started_at is None
            or self.failed_at is None
        ):
            return None

        return max(
            0.0,
            (
                self.failed_at
                - self.started_at
            ).total_seconds(),
        )

    def snapshot(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "ready_at": self._iso(self.ready_at),
            "dispatched_at": self._iso(
                self.dispatched_at
            ),
            "started_at": self._iso(
                self.started_at
            ),
            "completed_at": self._iso(
                self.completed_at
            ),
            "failed_at": self._iso(
                self.failed_at
            ),
            "cancelled_at": self._iso(
                self.cancelled_at
            ),
            "timed_out_at": self._iso(
                self.timed_out_at
            ),
            "queue_wait_seconds": (
                self.queue_wait_seconds
            ),
            "execution_seconds": (
                self.execution_seconds
            ),
            "failure_seconds": (
                self.failure_seconds
            ),
        }

    @staticmethod
    def _iso(
        value: Optional[datetime],
    ) -> Optional[str]:
        return (
            value.isoformat()
            if value is not None
            else None
        )


@dataclass
class ExecutionObservation:
    """
    Complete monitoring state for one execution.
    """

    execution_id: str

    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None

    current_status: ExecutionStatus = (
        ExecutionStatus.CREATED
    )

    task_timings: Dict[
        str,
        TaskTimingRecord,
    ] = field(default_factory=dict)

    events: List[MonitoringEvent] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def total_execution_seconds(
        self,
    ) -> Optional[float]:
        if (
            self.started_at is None
            or self.completed_at is None
        ):
            return None

        return max(
            0.0,
            (
                self.completed_at
                - self.started_at
            ).total_seconds(),
        )

    @property
    def completed_task_count(self) -> int:
        return sum(
            1
            for timing in self.task_timings.values()
            if timing.completed_at is not None
        )

    @property
    def failed_task_count(self) -> int:
        return sum(
            1
            for timing in self.task_timings.values()
            if timing.failed_at is not None
        )

    @property
    def observed_task_count(self) -> int:
        return len(self.task_timings)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "created_at": self._iso(
                self.created_at
            ),
            "started_at": self._iso(
                self.started_at
            ),
            "completed_at": self._iso(
                self.completed_at
            ),
            "failed_at": self._iso(
                self.failed_at
            ),
            "current_status": (
                self.current_status.value
                if hasattr(
                    self.current_status,
                    "value",
                )
                else str(
                    self.current_status
                )
            ),
            "total_execution_seconds": (
                self.total_execution_seconds
            ),
            "completed_task_count": (
                self.completed_task_count
            ),
            "failed_task_count": (
                self.failed_task_count
            ),
            "observed_task_count": (
                self.observed_task_count
            ),
            "task_timings": {
                task_id: timing.snapshot()
                for task_id, timing
                in self.task_timings.items()
            },
            "metadata": dict(
                self.metadata
            ),
        }

    @staticmethod
    def _iso(
        value: Optional[datetime],
    ) -> Optional[str]:
        return (
            value.isoformat()
            if value is not None
            else None
        )


@dataclass(frozen=True)
class ExecutionMonitorConfig:
    """
    Monitoring configuration.

    max_events_per_execution prevents unbounded in-memory growth.

    The monitor stores lifecycle observations only. It does not create
    synthetic performance measurements.
    """

    max_events_per_execution: int = 10_000

    retain_completed_observations: bool = True

    def __post_init__(self) -> None:
        if self.max_events_per_execution < 1:
            raise MonitoringConfigurationError(
                "max_events_per_execution must be at least 1."
            )


class ExecutionMonitor:
    """
    ALPHA execution observation engine.

    Responsibilities:

        1. Record lifecycle events.
        2. Record real timestamps.
        3. Track task-level timing.
        4. Track execution-level timing.
        5. Provide immutable event snapshots.
        6. Provide observations to future optimization systems.

    It does not modify the execution itself.
    """

    def __init__(
        self,
        *,
        config: Optional[
            ExecutionMonitorConfig
        ] = None,
    ) -> None:
        self.config = (
            config
            or ExecutionMonitorConfig()
        )

        self._observations: Dict[
            str,
            ExecutionObservation,
        ] = {}

        self._event_counter = 0

        self._lock = Lock()

    # ------------------------------------------------------------------
    # EXECUTION LIFECYCLE
    # ------------------------------------------------------------------

    def observe_execution_created(
        self,
        context: ExecutionContext,
    ) -> MonitoringEvent:
        """
        Record creation of an execution context.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = self._utc_now()

        observation.created_at = timestamp
        observation.current_status = (
            ExecutionStatus.CREATED
        )

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.EXECUTION_CREATED
            ),
            timestamp=timestamp,
        )

    def observe_execution_started(
        self,
        context: ExecutionContext,
    ) -> MonitoringEvent:
        """
        Record actual execution start.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = self._utc_now()

        if observation.started_at is None:
            observation.started_at = timestamp

        observation.current_status = (
            ExecutionStatus.EXECUTING
        )

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.EXECUTION_STARTED
            ),
            timestamp=timestamp,
            status=(
                ExecutionStatus.EXECUTING.value
            ),
        )

    def observe_execution_planned(
        self,
        context: ExecutionContext,
    ) -> MonitoringEvent:
        """
        Record that an execution plan has been attached.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = self._utc_now()

        observation.current_status = (
            ExecutionStatus.PLANNED
        )

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.EXECUTION_PLANNED
            ),
            timestamp=timestamp,
            details={
                "task_count": (
                    len(context.plan.tasks)
                    if context.plan
                    else 0
                )
            },
        )

    def observe_execution_completed(
        self,
        context: ExecutionContext,
    ) -> MonitoringEvent:
        """
        Record actual execution completion.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = self._utc_now()

        observation.completed_at = timestamp
        observation.current_status = (
            ExecutionStatus.COMPLETED
        )

        event = self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.EXECUTION_COMPLETED
            ),
            timestamp=timestamp,
            status=(
                ExecutionStatus.COMPLETED.value
            ),
        )

        if not self.config.retain_completed_observations:
            self._remove_observation(
                context.execution_id
            )

        return event

    def observe_execution_failed(
        self,
        context: ExecutionContext,
        *,
        error: Optional[str] = None,
    ) -> MonitoringEvent:
        """
        Record actual execution failure.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = self._utc_now()

        observation.failed_at = timestamp
        observation.current_status = (
            ExecutionStatus.FAILED
        )

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.EXECUTION_FAILED
            ),
            timestamp=timestamp,
            status=(
                ExecutionStatus.FAILED.value
            ),
            details={
                "error": error,
            },
        )

    def observe_execution_waiting(
        self,
        context: ExecutionContext,
    ) -> MonitoringEvent:
        """
        Record that execution is waiting for additional work or capacity.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = self._utc_now()

        observation.current_status = (
            ExecutionStatus.WAITING
        )

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.EXECUTION_WAITING
            ),
            timestamp=timestamp,
            status=(
                ExecutionStatus.WAITING.value
            ),
        )

    # ------------------------------------------------------------------
    # SCHEDULER OBSERVATION
    # ------------------------------------------------------------------

    def observe_scheduler_cycle(
        self,
        context: ExecutionContext,
        cycle: SchedulerCycleResult,
    ) -> MonitoringEvent:
        """
        Record the outcome of a real scheduler cycle.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = self._utc_now()

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.SCHEDULER_CYCLE_COMPLETED
            ),
            timestamp=timestamp,
            details={
                "cycle_id": cycle.cycle_id,
                "dispatch_count": len(
                    cycle.dispatch_batch.task_ids
                ),
                "decision_count": len(
                    cycle.decisions
                ),
            },
        )

    # ------------------------------------------------------------------
    # TASK OBSERVATION
    # ------------------------------------------------------------------

    def observe_task_ready(
        self,
        context: ExecutionContext,
        task_id: str,
    ) -> MonitoringEvent:
        """
        Record when a task is observed as ready.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = self._utc_now()

        timing = self._get_task_timing(
            observation,
            task_id,
        )

        if timing.ready_at is None:
            timing.ready_at = timestamp

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.TASK_READY
            ),
            timestamp=timestamp,
            task_id=task_id,
        )

    def observe_task_dispatched(
        self,
        context: ExecutionContext,
        task_id: str,
    ) -> MonitoringEvent:
        """
        Record that the scheduler actually dispatched a task.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = self._utc_now()

        timing = self._get_task_timing(
            observation,
            task_id,
        )

        timing.dispatched_at = timestamp

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.TASK_DISPATCHED
            ),
            timestamp=timestamp,
            task_id=task_id,
        )

    def observe_task_started(
        self,
        context: ExecutionContext,
        task_id: str,
    ) -> MonitoringEvent:
        """
        Record actual handler execution start.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = self._utc_now()

        timing = self._get_task_timing(
            observation,
            task_id,
        )

        timing.started_at = timestamp

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.TASK_STARTED
            ),
            timestamp=timestamp,
            task_id=task_id,
        )

    def observe_task_completed(
        self,
        context: ExecutionContext,
        result: ExecutionResult,
    ) -> MonitoringEvent:
        """
        Record actual task completion.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = (
            result.completed_at
            or self._utc_now()
        )

        timing = self._get_task_timing(
            observation,
            result.task_id,
        )

        timing.completed_at = timestamp

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.TASK_COMPLETED
            ),
            timestamp=timestamp,
            task_id=result.task_id,
            details={
                "success": result.success,
                "error": result.error,
            },
        )

    def observe_task_failed(
        self,
        context: ExecutionContext,
        result: ExecutionResult,
    ) -> MonitoringEvent:
        """
        Record actual task failure.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = (
            result.completed_at
            or self._utc_now()
        )

        timing = self._get_task_timing(
            observation,
            result.task_id,
        )

        timing.failed_at = timestamp

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.TASK_FAILED
            ),
            timestamp=timestamp,
            task_id=result.task_id,
            details={
                "error": result.error,
                "failure_type": (
                    result.failure_type.value
                    if getattr(
                        result,
                        "failure_type",
                        None,
                    ) is not None
                    else None
                ),
            },
        )

    def observe_task_cancelled(
        self,
        context: ExecutionContext,
        task_id: str,
    ) -> MonitoringEvent:
        """
        Record actual cancellation.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = self._utc_now()

        timing = self._get_task_timing(
            observation,
            task_id,
        )

        timing.cancelled_at = timestamp

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.TASK_CANCELLED
            ),
            timestamp=timestamp,
            task_id=task_id,
        )

    def observe_task_timed_out(
        self,
        context: ExecutionContext,
        task_id: str,
    ) -> MonitoringEvent:
        """
        Record actual timeout observation.

        Timeout enforcement itself belongs to the timeout/recovery layer.
        """

        observation = self._get_or_create(
            context.execution_id
        )

        timestamp = self._utc_now()

        timing = self._get_task_timing(
            observation,
            task_id,
        )

        timing.timed_out_at = timestamp

        return self._record_event(
            observation=observation,
            event_type=(
                MonitoringEventType.TASK_TIMED_OUT
            ),
            timestamp=timestamp,
            task_id=task_id,
        )

    # ------------------------------------------------------------------
    # BATCH OBSERVATION
    # ------------------------------------------------------------------

    def observe_parallel_report(
        self,
        context: ExecutionContext,
        report: ParallelExecutionReport,
    ) -> None:
        """
        Record all real task results from a completed parallel batch.
        """

        for task_id in report.task_ids:
            result = report.results.get(
                task_id
            )

            if result is None:
                continue

            if result.success:
                self.observe_task_completed(
                    context,
                    result,
                )
            else:
                self.observe_task_failed(
                    context,
                    result,
                )

    # ------------------------------------------------------------------
    # READ API
    # ------------------------------------------------------------------

    def get_observation(
        self,
        execution_id: str,
    ) -> Optional[
        ExecutionObservation
    ]:
        """
        Return an execution observation.

        The returned object is the monitor's current observation object.
        Call snapshot() when an isolated serializable structure is needed.
        """

        with self._lock:
            return self._observations.get(
                execution_id
            )

    def snapshot(
        self,
        execution_id: str,
    ) -> Optional[
        Dict[str, Any]
    ]:
        """
        Return a serializable snapshot of an execution observation.
        """

        observation = self.get_observation(
            execution_id
        )

        if observation is None:
            return None

        return observation.snapshot()

    def events(
        self,
        execution_id: str,
    ) -> List[MonitoringEvent]:
        """
        Return a copy of observed lifecycle events.
        """

        observation = self.get_observation(
            execution_id
        )

        if observation is None:
            return []

        return list(
            observation.events
        )

    def task_timing(
        self,
        execution_id: str,
        task_id: str,
    ) -> Optional[
        TaskTimingRecord
    ]:
        """
        Return timing information for one task.
        """

        observation = self.get_observation(
            execution_id
        )

        if observation is None:
            return None

        return observation.task_timings.get(
            task_id
        )

    def active_execution_ids(self) -> List[str]:
        """
        Return executions retained by the monitor.
        """

        with self._lock:
            return list(
                self._observations.keys()
            )

    # ------------------------------------------------------------------
    # INTERNAL STATE
    # ------------------------------------------------------------------

    def _get_or_create(
        self,
        execution_id: str,
    ) -> ExecutionObservation:
        if not execution_id:
            raise ValueError(
                "execution_id cannot be empty."
            )

        with self._lock:
            observation = (
                self._observations.get(
                    execution_id
                )
            )

            if observation is None:
                observation = (
                    ExecutionObservation(
                        execution_id=execution_id
                    )
                )

                self._observations[
                    execution_id
                ] = observation

            return observation

    def _get_task_timing(
        self,
        observation: ExecutionObservation,
        task_id: str,
    ) -> TaskTimingRecord:
        timing = observation.task_timings.get(
            task_id
        )

        if timing is None:
            timing = TaskTimingRecord(
                task_id=task_id
            )

            observation.task_timings[
                task_id
            ] = timing

        return timing

    def _record_event(
        self,
        *,
        observation: ExecutionObservation,
        event_type: str,
        timestamp: datetime,
        task_id: Optional[str] = None,
        status: Optional[str] = None,
        details: Optional[
            Dict[str, Any]
        ] = None,
    ) -> MonitoringEvent:
        with self._lock:
            self._event_counter += 1

            event = MonitoringEvent(
                event_id=(
                    f"mon-{self._event_counter}"
                ),
                event_type=event_type,
                timestamp=timestamp,
                execution_id=(
                    observation.execution_id
                ),
                task_id=task_id,
                status=status,
                details=dict(
                    details or {}
                ),
            )

            observation.events.append(
                event
            )

            if (
                len(observation.events)
                > self.config.max_events_per_execution
            ):
                overflow = (
                    len(observation.events)
                    - self.config.max_events_per_execution
                )

                del observation.events[
                    :overflow
                ]

            return event

    def _remove_observation(
        self,
        execution_id: str,
    ) -> None:
        with self._lock:
            self._observations.pop(
                execution_id,
                None,
            )

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(
            timezone.utc
        )


__all__ = [
    "ExecutionMonitorError",
    "MonitoringConfigurationError",
    "MonitoringEventType",
    "MonitoringEvent",
    "TaskTimingRecord",
    "ExecutionObservation",
    "ExecutionMonitorConfig",
    "ExecutionMonitor",
      ]
