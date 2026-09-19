"""
VALE AI - ALPHA Brain
Timeout Manager

File:
    ALPHA/recovery/timeout_manager.py

Purpose:
    Enforce execution deadlines without mixing timeout policy into the
    scheduler or parallel executor.

Design principles:
    - Scheduler decides what should run.
    - Executor performs the work.
    - Monitor observes execution.
    - Timeout Manager enforces deadline policy.
    - Recovery handles what happens after a timeout.
    - No fabricated timing or fake completion.
    - Never claims that a Python worker thread was forcibly terminated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Event, Lock
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from ALPHA.core.execution_context import ExecutionContext
from ALPHA.core.execution_models import (
    ExecutionResult,
    ExecutionStatus,
    ExecutionTask,
    TaskStatus,
)


# ============================================================================
# ENUMS
# ============================================================================


class TimeoutManagerError(Exception):
    """Base exception for timeout-manager failures."""


class TimeoutConfigurationError(TimeoutManagerError):
    """Raised when timeout configuration is invalid."""


class TimeoutStateError(TimeoutManagerError):
    """Raised when an invalid timeout state transition is requested."""


class TimeoutAction(str, Enum):
    """
    Action selected when a timeout is detected.

    MARK_TIMEOUT:
        Mark the task as timed out in ALPHA state.

    REQUEST_CANCELLATION:
        Request cancellation if the underlying execution mechanism supports it.

    MARK_AND_CANCEL:
        Mark timeout and request cancellation.

    ESCALATE:
        Mark timeout and indicate that recovery/escalation is required.
    """

    MARK_TIMEOUT = "mark_timeout"
    REQUEST_CANCELLATION = "request_cancellation"
    MARK_AND_CANCEL = "mark_and_cancel"
    ESCALATE = "escalate"


class TimeoutState(str, Enum):
    """Lifecycle state of timeout tracking for a task."""

    NOT_TRACKED = "not_tracked"
    TRACKING = "tracking"
    WARNING = "warning"
    EXPIRED = "expired"
    CANCEL_REQUESTED = "cancel_requested"
    RESOLVED = "resolved"


# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass(frozen=True)
class TimeoutManagerConfig:
    """
    Configuration for timeout enforcement.

    default_timeout_seconds:
        Used when a task has no explicit timeout/deadline.

    warning_threshold_ratio:
        Fraction of the timeout at which a warning is generated.

        Example:
            0.80 means warning at 80% of the allowed duration.

    auto_mark_timeout:
        Whether expired tasks should automatically be marked timed out.

    request_cancellation:
        Whether the manager should request cancellation after expiry.

    escalation_enabled:
        Whether timeout events should request downstream recovery.

    minimum_timeout_seconds:
        Prevents accidental zero/near-zero timeout configuration.

    maximum_timeout_seconds:
        Optional safety ceiling. None means no ceiling.
    """

    default_timeout_seconds: float = 30.0
    warning_threshold_ratio: float = 0.80

    auto_mark_timeout: bool = True
    request_cancellation: bool = True
    escalation_enabled: bool = True

    minimum_timeout_seconds: float = 0.001
    maximum_timeout_seconds: Optional[float] = None

    def __post_init__(self) -> None:
        if self.default_timeout_seconds <= 0:
            raise TimeoutConfigurationError(
                "default_timeout_seconds must be greater than zero."
            )

        if not 0.0 < self.warning_threshold_ratio < 1.0:
            raise TimeoutConfigurationError(
                "warning_threshold_ratio must be between 0 and 1."
            )

        if self.minimum_timeout_seconds <= 0:
            raise TimeoutConfigurationError(
                "minimum_timeout_seconds must be greater than zero."
            )

        if (
            self.maximum_timeout_seconds is not None
            and self.maximum_timeout_seconds <= 0
        ):
            raise TimeoutConfigurationError(
                "maximum_timeout_seconds must be greater than zero when provided."
            )

        if (
            self.maximum_timeout_seconds is not None
            and self.maximum_timeout_seconds < self.minimum_timeout_seconds
        ):
            raise TimeoutConfigurationError(
                "maximum_timeout_seconds cannot be lower than "
                "minimum_timeout_seconds."
            )


# ============================================================================
# TIMEOUT RECORDS
# ============================================================================


@dataclass
class TimeoutRecord:
    """
    Runtime timeout state for one task.
    """

    task_id: str

    timeout_seconds: float

    started_at: Optional[datetime] = None
    deadline: Optional[datetime] = None

    state: TimeoutState = TimeoutState.NOT_TRACKED

    warning_emitted: bool = False
    timeout_detected_at: Optional[datetime] = None
    cancellation_requested_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    cancellation_supported: Optional[bool] = None
    cancellation_requested: bool = False

    escalation_required: bool = False

    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed_seconds(self) -> Optional[float]:
        if self.started_at is None:
            return None

        end_time = self.timeout_detected_at or datetime.now(timezone.utc)

        return max(
            0.0,
            (end_time - self.started_at).total_seconds(),
        )

    @property
    def remaining_seconds(self) -> Optional[float]:
        if self.deadline is None:
            return None

        return (self.deadline - datetime.now(timezone.utc)).total_seconds()

    @property
    def expired(self) -> bool:
        if self.deadline is None:
            return False

        return datetime.now(timezone.utc) >= self.deadline


@dataclass(frozen=True)
class TimeoutEvent:
    """
    Immutable event emitted by the timeout manager.
    """

    event_id: str
    task_id: str
    state: TimeoutState
    action: Optional[TimeoutAction]

    timestamp: datetime

    elapsed_seconds: Optional[float]
    remaining_seconds: Optional[float]

    escalation_required: bool

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeoutCheckResult:
    """
    Result of one timeout-check cycle.
    """

    checked_task_ids: List[str] = field(default_factory=list)

    warning_task_ids: List[str] = field(default_factory=list)
    timed_out_task_ids: List[str] = field(default_factory=list)
    cancellation_requested_task_ids: List[str] = field(default_factory=list)
    escalation_task_ids: List[str] = field(default_factory=list)

    events: List[TimeoutEvent] = field(default_factory=list)

    checked_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ============================================================================
# CANCELLATION INTERFACE
# ============================================================================


CancellationHandler = Callable[[str], bool]


# ============================================================================
# TIMEOUT MANAGER
# ============================================================================


class TimeoutManager:
    """
    ALPHA timeout enforcement engine.

    Responsibilities:
        - Track task deadlines.
        - Detect approaching deadlines.
        - Detect expired tasks.
        - Mark execution state as timed out.
        - Request cancellation when supported.
        - Produce timeout events.
        - Signal escalation to recovery.
        - Avoid unsafe claims about thread termination.

    Non-responsibilities:
        - Scheduling tasks.
        - Executing task logic.
        - Deciding task priority.
        - Recovering failed work.
        - Determining truth/correctness.
    """

    def __init__(
        self,
        config: Optional[TimeoutManagerConfig] = None,
    ) -> None:
        self.config = config or TimeoutManagerConfig()

        self._records: Dict[str, TimeoutRecord] = {}
        self._contexts: Dict[str, ExecutionContext] = {}
        self._cancellation_handlers: Dict[str, CancellationHandler] = {}

        self._events: List[TimeoutEvent] = []

        self._lock = Lock()
        self._wake_event = Event()

        self._event_counter = 0

    # ---------------------------------------------------------------------
    # INTERNAL UTILITIES
    # ---------------------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _next_event_id(self) -> str:
        with self._lock:
            self._event_counter += 1
            return f"timeout-event-{self._event_counter}"

    def _emit_event(
        self,
        record: TimeoutRecord,
        action: Optional[TimeoutAction] = None,
    ) -> TimeoutEvent:
        event = TimeoutEvent(
            event_id=self._next_event_id(),
            task_id=record.task_id,
            state=record.state,
            action=action,
            timestamp=self._now(),
            elapsed_seconds=record.elapsed_seconds,
            remaining_seconds=record.remaining_seconds,
            escalation_required=record.escalation_required,
            metadata=dict(record.metadata),
        )

        with self._lock:
            self._events.append(event)

        return event

    def _normalize_timeout(self, timeout_seconds: float) -> float:
        timeout = float(timeout_seconds)

        if timeout < self.config.minimum_timeout_seconds:
            raise TimeoutConfigurationError(
                f"Timeout {timeout} is below the configured minimum "
                f"{self.config.minimum_timeout_seconds}."
            )

        if (
            self.config.maximum_timeout_seconds is not None
            and timeout > self.config.maximum_timeout_seconds
        ):
            raise TimeoutConfigurationError(
                f"Timeout {timeout} exceeds configured maximum "
                f"{self.config.maximum_timeout_seconds}."
            )

        return timeout

    # ---------------------------------------------------------------------
    # TASK REGISTRATION
    # ---------------------------------------------------------------------

    def register_task(
        self,
        task: ExecutionTask,
        context: Optional[ExecutionContext] = None,
        timeout_seconds: Optional[float] = None,
        cancellation_handler: Optional[CancellationHandler] = None,
    ) -> TimeoutRecord:
        """
        Register a task for timeout tracking.

        The timeout is determined in this order:

            1. Explicit timeout_seconds argument.
            2. Task timeout/deadline metadata if available.
            3. Manager default.

        Registration alone does not mean execution has started.
        """

        task_id = str(task.task_id)

        timeout = timeout_seconds

        if timeout is None:
            timeout = self._extract_task_timeout(task)

        if timeout is None:
            timeout = self.config.default_timeout_seconds

        timeout = self._normalize_timeout(timeout)

        with self._lock:
            record = TimeoutRecord(
                task_id=task_id,
                timeout_seconds=timeout,
                state=TimeoutState.NOT_TRACKED,
            )

            self._records[task_id] = record

            if context is not None:
                self._contexts[task_id] = context

            if cancellation_handler is not None:
                self._cancellation_handlers[
                    task_id
                ] = cancellation_handler

        return record

    def register_tasks(
        self,
        tasks: Iterable[ExecutionTask],
        context: Optional[ExecutionContext] = None,
    ) -> List[TimeoutRecord]:
        """
        Register multiple tasks.
        """

        records: List[TimeoutRecord] = []

        for task in tasks:
            records.append(
                self.register_task(
                    task=task,
                    context=context,
                )
            )

        return records

    def _extract_task_timeout(
        self,
        task: ExecutionTask,
    ) -> Optional[float]:
        """
        Safely inspect optional timeout fields without assuming that every
        ExecutionTask implementation exposes them.
        """

        candidates = (
            "timeout_seconds",
            "timeout",
            "deadline_seconds",
        )

        for field_name in candidates:
            value = getattr(task, field_name, None)

            if value is None:
                continue

            try:
                value = float(value)
            except (TypeError, ValueError):
                continue

            if value > 0:
                return value

        return None

    # ---------------------------------------------------------------------
    # START / STOP TRACKING
    # ---------------------------------------------------------------------

    def start_tracking(
        self,
        task_id: str,
        started_at: Optional[datetime] = None,
    ) -> TimeoutRecord:
        """
        Start the timeout clock for a task.
        """

        task_id = str(task_id)

        with self._lock:
            record = self._records.get(task_id)

            if record is None:
                raise TimeoutStateError(
                    f"Task '{task_id}' is not registered."
                )

            if record.state in {
                TimeoutState.EXPIRED,
                TimeoutState.RESOLVED,
            }:
                raise TimeoutStateError(
                    f"Task '{task_id}' cannot restart from "
                    f"state '{record.state.value}'."
                )

            start = started_at or self._now()

            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)

            record.started_at = start
            record.deadline = start.replace(
                microsecond=start.microsecond
            )

            from datetime import timedelta

            record.deadline = start + timedelta(
                seconds=record.timeout_seconds
            )

            record.state = TimeoutState.TRACKING

        self._wake_event.set()

        self._emit_event(record)

        return record

    def stop_tracking(
        self,
        task_id: str,
        resolved: bool = True,
    ) -> Optional[TimeoutRecord]:
        """
        Stop timeout tracking.

        resolved=True means execution ended before timeout.
        """

        task_id = str(task_id)

        with self._lock:
            record = self._records.get(task_id)

            if record is None:
                return None

            if resolved:
                record.state = TimeoutState.RESOLVED
                record.resolved_at = self._now()

        if resolved:
            self._emit_event(record)

        return record

    # ---------------------------------------------------------------------
    # CHECKING
    # ---------------------------------------------------------------------

    def check(
        self,
        task_ids: Optional[Iterable[str]] = None,
    ) -> TimeoutCheckResult:
        """
        Perform one real-time timeout check.

        This method does not sleep and does not fabricate elapsed time.
        """

        if task_ids is None:
            with self._lock:
                ids = list(self._records.keys())
        else:
            ids = [str(task_id) for task_id in task_ids]

        result = TimeoutCheckResult(
            checked_task_ids=ids,
        )

        for task_id in ids:
            record = self.get_record(task_id)

            if record is None:
                continue

            if record.state not in {
                TimeoutState.TRACKING,
                TimeoutState.WARNING,
                TimeoutState.CANCEL_REQUESTED,
            }:
                continue

            result.checked_task_ids.append(task_id)

            event = self._evaluate_record(record)

            if event is not None:
                result.events.append(event)

                if event.state == TimeoutState.WARNING:
                    result.warning_task_ids.append(task_id)

                if event.state == TimeoutState.EXPIRED:
                    result.timed_out_task_ids.append(task_id)

                if event.state == TimeoutState.CANCEL_REQUESTED:
                    result.cancellation_requested_task_ids.append(
                        task_id
                    )

                if event.escalation_required:
                    result.escalation_task_ids.append(task_id)

        return result

    def _evaluate_record(
        self,
        record: TimeoutRecord,
    ) -> Optional[TimeoutEvent]:
        """
        Evaluate one tracked task.
        """

        if record.deadline is None:
            return None

        now = self._now()

        elapsed = (
            (now - record.started_at).total_seconds()
            if record.started_at is not None
            else 0.0
        )

        ratio = elapsed / record.timeout_seconds

        # -------------------------------------------------------------
        # WARNING
        # -------------------------------------------------------------

        if (
            ratio >= self.config.warning_threshold_ratio
            and ratio < 1.0
            and not record.warning_emitted
        ):
            with self._lock:
                record.warning_emitted = True
                record.state = TimeoutState.WARNING

            return self._emit_event(record)

        # -------------------------------------------------------------
        # EXPIRY
        # -------------------------------------------------------------

        if now >= record.deadline:
            return self._handle_expiry(record)

        return None

    # ---------------------------------------------------------------------
    # EXPIRY
    # ---------------------------------------------------------------------

    def _handle_expiry(
        self,
        record: TimeoutRecord,
    ) -> TimeoutEvent:
        """
        Handle a task that has exceeded its deadline.
        """

        with self._lock:
            if record.timeout_detected_at is None:
                record.timeout_detected_at = self._now()

            record.state = TimeoutState.EXPIRED

            record.escalation_required = (
                self.config.escalation_enabled
            )

        context = self._contexts.get(record.task_id)

        if self.config.auto_mark_timeout and context is not None:
            self._mark_context_timeout(
                context=context,
                task_id=record.task_id,
            )

        cancellation_requested = False

        if self.config.request_cancellation:
            cancellation_requested = self._request_cancellation(
                record.task_id
            )

        if cancellation_requested:
            with self._lock:
                record.cancellation_requested = True
                record.cancellation_requested_at = self._now()
                record.cancellation_supported = True
                record.state = TimeoutState.CANCEL_REQUESTED

            return self._emit_event(
                record,
                action=TimeoutAction.MARK_AND_CANCEL,
            )

        with self._lock:
            record.cancellation_supported = False

        action = (
            TimeoutAction.ESCALATE
            if record.escalation_required
            else TimeoutAction.MARK_TIMEOUT
        )

        return self._emit_event(
            record,
            action=action,
        )

    def _mark_context_timeout(
        self,
        context: ExecutionContext,
        task_id: str,
    ) -> None:
        """
        Update the ExecutionContext when a timeout is detected.

        ExecutionContext is authoritative for execution state; this manager
        does not replace it.
        """

        try:
            context.mark_task_timed_out(task_id)
        except Exception:
            # Timeout enforcement should not crash the entire manager merely
            # because a context implementation rejects a transition.
            #
            # The failure remains observable through manager state/events.
            return

    # ---------------------------------------------------------------------
    # CANCELLATION
    # ---------------------------------------------------------------------

    def register_cancellation_handler(
        self,
        task_id: str,
        handler: CancellationHandler,
    ) -> None:
        """
        Register a cancellation callback for a task.

        The callback must return True only when cancellation was actually
        accepted/successfully requested by the underlying execution layer.
        """

        task_id = str(task_id)

        if not callable(handler):
            raise TimeoutConfigurationError(
                "Cancellation handler must be callable."
            )

        with self._lock:
            self._cancellation_handlers[task_id] = handler

    def _request_cancellation(
        self,
        task_id: str,
    ) -> bool:
        handler = self._cancellation_handlers.get(task_id)

        if handler is None:
            return False

        try:
            return bool(handler(task_id))
        except Exception:
            return False

    # ---------------------------------------------------------------------
    # RESULT RECONCILIATION
    # ---------------------------------------------------------------------

    def reconcile_result(
        self,
        result: ExecutionResult,
    ) -> TimeoutRecord:
        """
        Reconcile an actual execution result with timeout state.

        This is important because a task may finish around the same time
        that the timeout manager detects expiry.

        The actual result is never overwritten here.
        """

        task_id = str(result.task_id)

        record = self.get_record(task_id)

        if record is None:
            raise TimeoutStateError(
                f"Task '{task_id}' is not registered."
            )

        success = bool(getattr(result, "success", False))

        with self._lock:
            if success:
                if record.state not in {
                    TimeoutState.EXPIRED,
                    TimeoutState.CANCEL_REQUESTED,
                }:
                    record.state = TimeoutState.RESOLVED
                    record.resolved_at = self._now()
            else:
                if record.state not in {
                    TimeoutState.EXPIRED,
                    TimeoutState.CANCEL_REQUESTED,
                }:
                    record.state = TimeoutState.RESOLVED
                    record.resolved_at = self._now()

        self._emit_event(record)

        return record

    # ---------------------------------------------------------------------
    # QUERY API
    # ---------------------------------------------------------------------

    def get_record(
        self,
        task_id: str,
    ) -> Optional[TimeoutRecord]:
        with self._lock:
            return self._records.get(str(task_id))

    def is_timed_out(
        self,
        task_id: str,
    ) -> bool:
        record = self.get_record(task_id)

        if record is None:
            return False

        return record.state in {
            TimeoutState.EXPIRED,
            TimeoutState.CANCEL_REQUESTED,
        }

    def remaining_seconds(
        self,
        task_id: str,
    ) -> Optional[float]:
        record = self.get_record(task_id)

        if record is None:
            return None

        return record.remaining_seconds

    def elapsed_seconds(
        self,
        task_id: str,
    ) -> Optional[float]:
        record = self.get_record(task_id)

        if record is None:
            return None

        return record.elapsed_seconds

    def active_task_ids(self) -> List[str]:
        with self._lock:
            return [
                task_id
                for task_id, record in self._records.items()
                if record.state
                in {
                    TimeoutState.TRACKING,
                    TimeoutState.WARNING,
                    TimeoutState.CANCEL_REQUESTED,
                }
            ]

    def timed_out_task_ids(self) -> List[str]:
        with self._lock:
            return [
                task_id
                for task_id, record in self._records.items()
                if record.state
                in {
                    TimeoutState.EXPIRED,
                    TimeoutState.CANCEL_REQUESTED,
                }
            ]

    def escalation_task_ids(self) -> List[str]:
        with self._lock:
            return [
                task_id
                for task_id, record in self._records.items()
                if record.escalation_required
                and record.state
                in {
                    TimeoutState.EXPIRED,
                    TimeoutState.CANCEL_REQUESTED,
                }
            ]

    # ---------------------------------------------------------------------
    # EVENTS
    # ---------------------------------------------------------------------

    def events(
        self,
        task_id: Optional[str] = None,
    ) -> List[TimeoutEvent]:
        with self._lock:
            events = list(self._events)

        if task_id is None:
            return events

        normalized_id = str(task_id)

        return [
            event
            for event in events
            if event.task_id == normalized_id
        ]

    def clear_events(self) -> None:
        with self._lock:
            self._events.clear()

    # ---------------------------------------------------------------------
    # CLEANUP
    # ---------------------------------------------------------------------

    def unregister_task(
        self,
        task_id: str,
    ) -> Optional[TimeoutRecord]:
        """
        Remove timeout state for a task that no longer needs tracking.
        """

        task_id = str(task_id)

        with self._lock:
            record = self._records.pop(task_id, None)

            self._contexts.pop(task_id, None)
            self._cancellation_handlers.pop(task_id, None)

        return record

    def reset(self) -> None:
        """
        Clear all active timeout state.

        Intended for a fresh ALPHA runtime/session, not normal per-task use.
        """

        with self._lock:
            self._records.clear()
            self._contexts.clear()
            self._cancellation_handlers.clear()
            self._events.clear()

        self._wake_event.clear()

    # ---------------------------------------------------------------------
    # SNAPSHOT
    # ---------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """
        Return an operational snapshot without inventing metrics.
        """

        with self._lock:
            records = list(self._records.values())

        return {
            "tracked_tasks": len(records),
            "active_tasks": len(
                [
                    record
                    for record in records
                    if record.state
                    in {
                        TimeoutState.TRACKING,
                        TimeoutState.WARNING,
                        TimeoutState.CANCEL_REQUESTED,
                    }
                ]
            ),
            "timed_out_tasks": len(
                [
                    record
                    for record in records
                    if record.state
                    in {
                        TimeoutState.EXPIRED,
                        TimeoutState.CANCEL_REQUESTED,
                    }
                ]
            ),
            "escalation_tasks": len(
                [
                    record
                    for record in records
                    if record.escalation_required
                ]
            ),
            "events": len(self.events()),
            "configuration": {
                "default_timeout_seconds": (
                    self.config.default_timeout_seconds
                ),
                "warning_threshold_ratio": (
                    self.config.warning_threshold_ratio
                ),
                "auto_mark_timeout": (
                    self.config.auto_mark_timeout
                ),
                "request_cancellation": (
                    self.config.request_cancellation
                ),
                "escalation_enabled": (
                    self.config.escalation_enabled
                ),
            },
        }


__all__ = [
    "TimeoutManagerError",
    "TimeoutConfigurationError",
    "TimeoutStateError",
    "TimeoutAction",
    "TimeoutState",
    "TimeoutManagerConfig",
    "TimeoutRecord",
    "TimeoutEvent",
    "TimeoutCheckResult",
    "TimeoutManager",
      ]
