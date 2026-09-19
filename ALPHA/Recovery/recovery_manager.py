"""
VALE AI - ALPHA Brain
Failure & Recovery Manager

File:
    ALPHA/recovery/recovery_manager.py

Purpose:
    Handle execution failures and controlled recovery without mixing
    recovery policy into the scheduler, executor, or monitoring systems.

Architecture boundary:

    HEROIC
        ↓
    ALPHA Planner
        ↓
    Scheduler
        ↓
    Parallel Executor
        ↓
    Monitor
        ↓
    Timeout Manager
        ↓
    Recovery Manager
        ↓
    Retry / Replan / Degrade / Escalate
        ↓
    ALPHA
        ↓
    UNITY

Design principles:
    - Recovery is evidence-driven.
    - Never retry blindly.
    - Never fabricate successful output.
    - Never convert failure into success.
    - Preserve failure provenance.
    - Respect retry limits.
    - Respect task idempotency.
    - Preserve verification requirements.
    - Recovery may request replanning but does not itself become HEROIC.
    - Recovery cannot override safety or correctness requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Set

from ALPHA.core.execution_context import ExecutionContext
from ALPHA.core.execution_models import (
    ExecutionFailure,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTask,
    FailureType,
    TaskStatus,
)


# ============================================================================
# EXCEPTIONS
# ============================================================================


class RecoveryManagerError(Exception):
    """Base exception for recovery-manager failures."""


class RecoveryConfigurationError(RecoveryManagerError):
    """Raised when recovery configuration is invalid."""


class RecoveryStateError(RecoveryManagerError):
    """Raised when an invalid recovery state transition occurs."""


class RecoveryPolicyError(RecoveryManagerError):
    """Raised when a recovery action violates policy."""


# ============================================================================
# ENUMS
# ============================================================================


class RecoveryAction(str, Enum):
    """
    Action selected by the recovery manager.

    RETRY:
        Attempt the same task again.

    RETRY_WITH_BACKOFF:
        Retry after a controlled delay.

    REPLAN:
        Request a new execution plan.

    DEGRADE:
        Continue with a reduced capability path when explicitly allowed.

    SKIP:
        Skip an optional task.

    CANCEL:
        Cancel the task/execution path.

    ESCALATE:
        Hand the problem to a higher-level recovery/coordination layer.

    FAIL:
        Declare the task unrecoverable.
    """

    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    REPLAN = "replan"
    DEGRADE = "degrade"
    SKIP = "skip"
    CANCEL = "cancel"
    ESCALATE = "escalate"
    FAIL = "fail"


class RecoveryState(str, Enum):
    """Lifecycle state of recovery processing."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    ANALYZING = "analyzing"
    RETRYING = "retrying"
    REPLANNING = "replanning"
    DEGRADING = "degrading"
    ESCALATING = "escalating"
    RECOVERED = "recovered"
    UNRECOVERABLE = "unrecoverable"


class FailureClass(str, Enum):
    """
    Higher-level classification of execution failures.
    """

    TRANSIENT = "transient"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    DEPENDENCY = "dependency"
    INPUT = "input"
    CONFIGURATION = "configuration"
    HANDLER = "handler"
    VALIDATION = "validation"
    CANCELLATION = "cancellation"
    UNKNOWN = "unknown"


class RetryDisposition(str, Enum):
    """Whether retry is appropriate."""

    ALLOWED = "allowed"
    DISCOURAGED = "discouraged"
    FORBIDDEN = "forbidden"


# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass(frozen=True)
class RecoveryManagerConfig:
    """
    Global recovery policy.

    max_retries:
        Maximum retry attempts for one logical task.

    retry_backoff_seconds:
        Base delay used by the caller/integration layer.

    backoff_multiplier:
        Exponential backoff multiplier.

    max_backoff_seconds:
        Maximum calculated retry delay.

    allow_replan:
        Whether recovery may request replanning.

    allow_degradation:
        Whether explicitly degradable tasks may use reduced execution paths.

    allow_optional_task_skip:
        Whether optional tasks may be skipped.

    escalate_after_retries:
        Whether repeated failures should be escalated.

    preserve_failure_history:
        Keep all recovery attempts in memory for traceability.
    """

    max_retries: int = 2

    retry_backoff_seconds: float = 0.25
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 10.0

    allow_replan: bool = True
    allow_degradation: bool = False
    allow_optional_task_skip: bool = True

    escalate_after_retries: bool = True

    preserve_failure_history: bool = True

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise RecoveryConfigurationError(
                "max_retries cannot be negative."
            )

        if self.retry_backoff_seconds < 0:
            raise RecoveryConfigurationError(
                "retry_backoff_seconds cannot be negative."
            )

        if self.backoff_multiplier < 1.0:
            raise RecoveryConfigurationError(
                "backoff_multiplier must be at least 1.0."
            )

        if self.max_backoff_seconds < 0:
            raise RecoveryConfigurationError(
                "max_backoff_seconds cannot be negative."
            )


# ============================================================================
# FAILURE CLASSIFICATION
# ============================================================================


@dataclass(frozen=True)
class FailureClassification:
    """
    Normalized representation of a failure.
    """

    failure_class: FailureClass
    retry_disposition: RetryDisposition

    reason: str

    transient: bool = False
    timeout: bool = False
    resource_related: bool = False
    dependency_related: bool = False
    input_related: bool = False

    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# RECOVERY RECORD
# ============================================================================


@dataclass
class RecoveryRecord:
    """
    Complete recovery state for one logical task.
    """

    task_id: str

    state: RecoveryState = RecoveryState.NOT_REQUIRED

    attempts: int = 0
    failures: int = 0

    last_failure: Optional[ExecutionFailure] = None
    last_classification: Optional[FailureClassification] = None

    selected_action: Optional[RecoveryAction] = None

    retry_count: int = 0
    replan_count: int = 0
    degradation_count: int = 0

    recovery_started_at: Optional[datetime] = None
    recovered_at: Optional[datetime] = None

    escalation_required: bool = False

    history: List[Dict[str, Any]] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# RECOVERY DECISION
# ============================================================================


@dataclass(frozen=True)
class RecoveryDecision:
    """
    Decision produced by the recovery manager.

    This is a recovery-policy decision, not a truth/correctness decision.
    """

    task_id: str

    action: RecoveryAction

    state: RecoveryState

    reason: str

    retry_attempt: int
    max_retries: int

    backoff_seconds: float

    requires_replan: bool
    requires_escalation: bool

    may_degrade: bool
    may_skip: bool

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryCycleResult:
    """
    Result of processing one or more failures.
    """

    decisions: List[RecoveryDecision] = field(default_factory=list)

    recovered_task_ids: List[str] = field(default_factory=list)
    retry_task_ids: List[str] = field(default_factory=list)
    replan_task_ids: List[str] = field(default_factory=list)
    degraded_task_ids: List[str] = field(default_factory=list)
    skipped_task_ids: List[str] = field(default_factory=list)
    escalated_task_ids: List[str] = field(default_factory=list)
    unrecoverable_task_ids: List[str] = field(default_factory=list)

    processed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ============================================================================
# RECOVERY MANAGER
# ============================================================================


class RecoveryManager:
    """
    ALPHA failure and recovery engine.

    Responsibilities:
        - Receive real execution failures.
        - Classify failures.
        - Track retry history.
        - Determine whether retry is allowed.
        - Calculate controlled backoff.
        - Request replanning when necessary.
        - Support controlled degradation.
        - Skip optional work when explicitly allowed.
        - Escalate repeated/unrecoverable failures.
        - Preserve recovery provenance.

    Non-responsibilities:
        - Executing tasks.
        - Scheduling tasks.
        - Determining truth.
        - Overriding MCVL.
        - Making final user-facing decisions.
        - Designing new task plans itself.
    """

    def __init__(
        self,
        config: Optional[RecoveryManagerConfig] = None,
    ) -> None:
        self.config = config or RecoveryManagerConfig()

        self._records: Dict[str, RecoveryRecord] = {}
        self._contexts: Dict[str, ExecutionContext] = {}
        self._tasks: Dict[str, ExecutionTask] = {}

        self._lock = Lock()

    # ---------------------------------------------------------------------
    # INTERNAL UTILITIES
    # ---------------------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    # ---------------------------------------------------------------------
    # TASK REGISTRATION
    # ---------------------------------------------------------------------

    def register_task(
        self,
        task: ExecutionTask,
        context: Optional[ExecutionContext] = None,
    ) -> RecoveryRecord:
        """
        Register a logical task for recovery tracking.
        """

        task_id = str(task.task_id)

        with self._lock:
            record = self._records.get(task_id)

            if record is None:
                record = RecoveryRecord(
                    task_id=task_id,
                )

                self._records[task_id] = record

            self._tasks[task_id] = task

            if context is not None:
                self._contexts[task_id] = context

        return record

    def register_tasks(
        self,
        tasks: Iterable[ExecutionTask],
        context: Optional[ExecutionContext] = None,
    ) -> List[RecoveryRecord]:
        return [
            self.register_task(
                task=task,
                context=context,
            )
            for task in tasks
        ]

    # ---------------------------------------------------------------------
    # FAILURE CLASSIFICATION
    # ---------------------------------------------------------------------

    def classify_failure(
        self,
        failure: Optional[ExecutionFailure] = None,
        result: Optional[ExecutionResult] = None,
        error: Optional[BaseException] = None,
    ) -> FailureClassification:
        """
        Classify a real failure without inventing its cause.
        """

        failure_type = None

        if failure is not None:
            failure_type = getattr(
                failure,
                "failure_type",
                None,
            )

        if failure_type is None and result is not None:
            failure_type = getattr(
                result,
                "failure_type",
                None,
            )

        normalized = str(failure_type).lower() if failure_type else ""

        # -------------------------------------------------------------
        # TIMEOUT
        # -------------------------------------------------------------

        if "timeout" in normalized:
            return FailureClassification(
                failure_class=FailureClass.TIMEOUT,
                retry_disposition=RetryDisposition.ALLOWED,
                reason="Execution exceeded its allowed deadline.",
                transient=True,
                timeout=True,
            )

        # -------------------------------------------------------------
        # RESOURCE
        # -------------------------------------------------------------

        resource_terms = (
            "resource",
            "capacity",
            "memory",
            "cpu",
            "quota",
        )

        if any(term in normalized for term in resource_terms):
            return FailureClassification(
                failure_class=FailureClass.RESOURCE,
                retry_disposition=RetryDisposition.DISCOURAGED,
                reason="Execution failed due to a resource-related condition.",
                transient=True,
                resource_related=True,
            )

        # -------------------------------------------------------------
        # DEPENDENCY
        # -------------------------------------------------------------

        if "depend" in normalized:
            return FailureClassification(
                failure_class=FailureClass.DEPENDENCY,
                retry_disposition=RetryDisposition.DISCOURAGED,
                reason="Execution depends on unavailable or failed work.",
                dependency_related=True,
            )

        # -------------------------------------------------------------
        # INPUT
        # -------------------------------------------------------------

        if "input" in normalized or "argument" in normalized:
            return FailureClassification(
                failure_class=FailureClass.INPUT,
                retry_disposition=RetryDisposition.FORBIDDEN,
                reason="The execution input appears invalid.",
                input_related=True,
            )

        # -------------------------------------------------------------
        # VALIDATION
        # -------------------------------------------------------------

        if "validation" in normalized:
            return FailureClassification(
                failure_class=FailureClass.VALIDATION,
                retry_disposition=RetryDisposition.FORBIDDEN,
                reason="Execution output or state failed validation.",
            )

        # -------------------------------------------------------------
        # CANCELLATION
        # -------------------------------------------------------------

        if "cancel" in normalized:
            return FailureClassification(
                failure_class=FailureClass.CANCELLATION,
                retry_disposition=RetryDisposition.DISCOURAGED,
                reason="Execution was cancelled.",
            )

        # -------------------------------------------------------------
        # CONFIGURATION
        # -------------------------------------------------------------

        if "config" in normalized:
            return FailureClassification(
                failure_class=FailureClass.CONFIGURATION,
                retry_disposition=RetryDisposition.FORBIDDEN,
                reason="Execution failed because of configuration.",
            )

        # -------------------------------------------------------------
        # HANDLER
        # -------------------------------------------------------------

        if "handler" in normalized:
            return FailureClassification(
                failure_class=FailureClass.HANDLER,
                retry_disposition=RetryDisposition.DISCOURAGED,
                reason="The execution handler failed or was unavailable.",
                transient=True,
            )

        # -------------------------------------------------------------
        # ERROR TEXT FALLBACK
        # -------------------------------------------------------------

        error_text = ""

        if error is not None:
            error_text = str(error).lower()

        transient_terms = (
            "temporarily",
            "temporary",
            "connection reset",
            "try again",
            "unavailable",
            "busy",
            "overloaded",
            "rate limit",
            "429",
        )

        if any(term in error_text for term in transient_terms):
            return FailureClassification(
                failure_class=FailureClass.TRANSIENT,
                retry_disposition=RetryDisposition.ALLOWED,
                reason="Failure appears potentially transient.",
                transient=True,
            )

        # -------------------------------------------------------------
        # UNKNOWN
        # -------------------------------------------------------------

        return FailureClassification(
            failure_class=FailureClass.UNKNOWN,
            retry_disposition=RetryDisposition.DISCOURAGED,
            reason=(
                "Failure cause could not be established strongly enough "
                "to justify an aggressive recovery action."
            ),
        )

    # ---------------------------------------------------------------------
    # FAILURE REGISTRATION
    # ---------------------------------------------------------------------

    def register_failure(
        self,
        task_id: str,
        failure: ExecutionFailure,
        classification: Optional[FailureClassification] = None,
    ) -> RecoveryRecord:
        """
        Register an actual execution failure.
        """

        task_id = str(task_id)

        with self._lock:
            if task_id not in self._records:
                self._records[task_id] = RecoveryRecord(
                    task_id=task_id,
                )

            record = self._records[task_id]

            record.state = RecoveryState.PENDING
            record.failures += 1
            record.attempts += 1
            record.last_failure = failure
            record.recovery_started_at = self._now()

        if classification is None:
            classification = self.classify_failure(
                failure=failure,
            )

        with self._lock:
            record.last_classification = classification

            if self.config.preserve_failure_history:
                record.history.append(
                    {
                        "timestamp": self._now().isoformat(),
                        "event": "failure_registered",
                        "failure_class": (
                            classification.failure_class.value
                        ),
                        "retry_disposition": (
                            classification.retry_disposition.value
                        ),
                        "reason": classification.reason,
                    }
                )

        return record

  # ---------------------------------------------------------------------
    # RESULT FAILURE ADAPTER
    # ---------------------------------------------------------------------

    def process_result(
        self,
        result: ExecutionResult,
    ) -> Optional[RecoveryDecision]:
        """
        Process an execution result.

        Returns:
            None if execution succeeded.
            RecoveryDecision if recovery is required.
        """

        success = bool(
            getattr(
                result,
                "success",
                False,
            )
        )

        task_id = str(result.task_id)

        if success:
            self.mark_recovered(task_id)
            return None

        failure = self._failure_from_result(result)

        self.register_failure(
            task_id=task_id,
            failure=failure,
        )

        return self.decide(task_id)

    def _failure_from_result(
        self,
        result: ExecutionResult,
    ) -> ExecutionFailure:
        """
        Convert an execution result into the ALPHA failure contract.

        Uses the actual failure_type/error information exposed by the
        execution result.
        """

        failure_type = getattr(
            result,
            "failure_type",
            FailureType.UNKNOWN,
        )

        error_value = getattr(
            result,
            "error",
            None,
        )

        error_message = (
            str(error_value)
            if error_value is not None
            else "Execution failed without an error message."
        )

        try:
            return ExecutionFailure(
                task_id=str(result.task_id),
                failure_type=failure_type,
                message=error_message,
            )
        except TypeError:
            # Defensive compatibility for alternative ExecutionFailure
            # implementations.
            return ExecutionFailure(
                task_id=str(result.task_id),
                failure_type=failure_type,
                error=error_message,
            )

    # ---------------------------------------------------------------------
    # DECISION ENGINE
    # ---------------------------------------------------------------------

    def decide(
        self,
        task_id: str,
    ) -> RecoveryDecision:
        """
        Select the safest recovery action supported by known evidence.
        """

        task_id = str(task_id)

        with self._lock:
            record = self._records.get(task_id)

        if record is None:
            raise RecoveryStateError(
                f"Task '{task_id}' is not registered with recovery."
            )

        classification = record.last_classification

        if classification is None:
            raise RecoveryStateError(
                f"Task '{task_id}' has no failure classification."
            )

        task = self._tasks.get(task_id)

        retry_count = record.retry_count

        # -------------------------------------------------------------
        # FORBIDDEN RETRY
        # -------------------------------------------------------------

        if classification.retry_disposition == RetryDisposition.FORBIDDEN:
            return self._decision(
                record=record,
                action=self._non_retry_action(
                    task=task,
                ),
                reason=(
                    "Retry is forbidden for this failure classification."
                ),
            )

        # -------------------------------------------------------------
        # RETRY
        # -------------------------------------------------------------

        if (
            classification.retry_disposition
            == RetryDisposition.ALLOWED
            and retry_count < self.config.max_retries
        ):
            action = (
                RecoveryAction.RETRY
                if retry_count == 0
                and self.config.retry_backoff_seconds == 0
                else RecoveryAction.RETRY_WITH_BACKOFF
            )

            return self._decision(
                record=record,
                action=action,
                reason=(
                    "Failure is retryable and the configured retry "
                    "budget has not been exhausted."
                ),
            )

        # -------------------------------------------------------------
        # REPLAN
        # -------------------------------------------------------------

        if self.config.allow_replan:
            if classification.dependency_related:
                return self._decision(
                    record=record,
                    action=RecoveryAction.REPLAN,
                    reason=(
                        "The failed dependency requires an alternative "
                        "execution path."
                    ),
                )

            if classification.failure_class in {
                FailureClass.RESOURCE,
                FailureClass.TIMEOUT,
            }:
                return self._decision(
                    record=record,
                    action=RecoveryAction.REPLAN,
                    reason=(
                        "Repeated execution failure suggests that the "
                        "current execution path should be reconsidered."
                    ),
                )

        # -------------------------------------------------------------
        # OPTIONAL TASK SKIP
        # -------------------------------------------------------------

        if (
            self.config.allow_optional_task_skip
            and self._task_is_optional(task)
        ):
            return self._decision(
                record=record,
                action=RecoveryAction.SKIP,
                reason=(
                    "The task is optional and recovery can safely continue "
                    "without it."
                ),
            )

        # -------------------------------------------------------------
        # DEGRADATION
        # -------------------------------------------------------------

        if (
            self.config.allow_degradation
            and self._task_allows_degradation(task)
        ):
            return self._decision(
                record=record,
                action=RecoveryAction.DEGRADE,
                reason=(
                    "The task explicitly permits controlled degradation."
                ),
            )

        # -------------------------------------------------------------
        # ESCALATION
        # -------------------------------------------------------------

        if self.config.escalate_after_retries:
            return self._decision(
                record=record,
                action=RecoveryAction.ESCALATE,
                reason=(
                    "Recovery options are exhausted or insufficient; "
                    "higher-level coordination is required."
                ),
            )

        # -------------------------------------------------------------
        # FINAL FAILURE
        # -------------------------------------------------------------

        return self._decision(
            record=record,
            action=RecoveryAction.FAIL,
            reason=(
                "No permitted recovery action remains for this failure."
            ),
        )

    def _non_retry_action(
        self,
        task: Optional[ExecutionTask],
    ) -> RecoveryAction:
        if (
            self.config.allow_optional_task_skip
            and self._task_is_optional(task)
        ):
            return RecoveryAction.SKIP

        if (
            self.config.allow_degradation
            and self._task_allows_degradation(task)
        ):
            return RecoveryAction.DEGRADE

        if self.config.allow_replan:
            return RecoveryAction.REPLAN

        return RecoveryAction.FAIL

    def _decision(
        self,
        record: RecoveryRecord,
        action: RecoveryAction,
        reason: str,
    ) -> RecoveryDecision:
        requires_replan = action == RecoveryAction.REPLAN

        requires_escalation = action == RecoveryAction.ESCALATE

        may_degrade = action == RecoveryAction.DEGRADE

        may_skip = action == RecoveryAction.SKIP

        backoff = 0.0

        if action == RecoveryAction.RETRY_WITH_BACKOFF:
            backoff = self.retry_backoff_seconds(
                record.task_id
            )

        state_map = {
            RecoveryAction.RETRY: RecoveryState.RETRYING,
            RecoveryAction.RETRY_WITH_BACKOFF: RecoveryState.RETRYING,
            RecoveryAction.REPLAN: RecoveryState.REPLANNING,
            RecoveryAction.DEGRADE: RecoveryState.DEGRADING,
            RecoveryAction.SKIP: RecoveryState.RECOVERED,
            RecoveryAction.CANCEL: RecoveryState.UNRECOVERABLE,
            RecoveryAction.ESCALATE: RecoveryState.ESCALATING,
            RecoveryAction.FAIL: RecoveryState.UNRECOVERABLE,
        }

        state = state_map[action]

        with self._lock:
            record.selected_action = action
            record.state = state

            if action in {
                RecoveryAction.RETRY,
                RecoveryAction.RETRY_WITH_BACKOFF,
            }:
                record.retry_count += 1

            elif action == RecoveryAction.REPLAN:
                record.replan_count += 1

            elif action == RecoveryAction.DEGRADE:
                record.degradation_count += 1

            if requires_escalation:
                record.escalation_required = True

            if self.config.preserve_failure_history:
                record.history.append(
                    {
                        "timestamp": self._now().isoformat(),
                        "event": "recovery_decision",
                        "action": action.value,
                        "reason": reason,
                    }
                )

        return RecoveryDecision(
            task_id=record.task_id,
            action=action,
            state=state,
            reason=reason,
            retry_attempt=record.retry_count,
            max_retries=self.config.max_retries,
            backoff_seconds=backoff,
            requires_replan=requires_replan,
            requires_escalation=requires_escalation,
            may_degrade=may_degrade,
            may_skip=may_skip,
            metadata={
                "failure_class": (
                    record.last_classification.failure_class.value
                    if record.last_classification
                    else None
                ),
            },
        )

    # ---------------------------------------------------------------------
    # TASK POLICY HELPERS
    # ---------------------------------------------------------------------

    def _task_is_optional(
        self,
        task: Optional[ExecutionTask],
    ) -> bool:
        if task is None:
            return False

        for field_name in (
            "optional",
            "is_optional",
        ):
            value = getattr(task, field_name, None)

            if value is not None:
                return bool(value)

        metadata = getattr(task, "metadata", None)

        if isinstance(metadata, dict):
            return bool(
                metadata.get("optional", False)
                or metadata.get("is_optional", False)
            )

        return False

    def _task_allows_degradation(
        self,
        task: Optional[ExecutionTask],
    ) -> bool:
        if task is None:
            return False

        for field_name in (
            "allow_degradation",
            "degradable",
        ):
            value = getattr(task, field_name, None)

            if value is not None:
                return bool(value)

        metadata = getattr(task, "metadata", None)

        if isinstance(metadata, dict):
            return bool(
                metadata.get("allow_degradation", False)
                or metadata.get("degradable", False)
            )

        return False

    # ---------------------------------------------------------------------
    # RETRY BACKOFF
    # ---------------------------------------------------------------------

    def retry_backoff_seconds(
        self,
        task_id: str,
    ) -> float:
        """
        Calculate exponential retry backoff.

        The manager calculates policy only. It does not sleep or block the
        scheduler.
        """

        record = self.get_record(task_id)

        if record is None:
            raise RecoveryStateError(
                f"Task '{task_id}' is not registered."
            )

        attempt_index = max(
            0,
            record.retry_count - 1,
        )

        delay = (
            self.config.retry_backoff_seconds
            * (
                self.config.backoff_multiplier
                ** attempt_index
            )
        )

        return min(
            delay,
            self.config.max_backoff_seconds,
        )

    # ---------------------------------------------------------------------
    # RECOVERY STATE
    # ---------------------------------------------------------------------

    def mark_recovered(
        self,
        task_id: str,
    ) -> Optional[RecoveryRecord]:
        """
        Mark a task as successfully recovered.

        This should only be called after an actual successful execution
        result has been observed.
        """

        task_id = str(task_id)

        with self._lock:
            record = self._records.get(task_id)

            if record is None:
                return None

            record.state = RecoveryState.RECOVERED
            record.recovered_at = self._now()

            if self.config.preserve_failure_history:
                record.history.append(
                    {
                        "timestamp": self._now().isoformat(),
                        "event": "recovered",
                    }
                )

        return record

    def mark_unrecoverable(
        self,
        task_id: str,
        reason: str,
    ) -> RecoveryRecord:
        task_id = str(task_id)

        with self._lock:
            record = self._records.get(task_id)

            if record is None:
                record = RecoveryRecord(
                    task_id=task_id,
                )
                self._records[task_id] = record

            record.state = RecoveryState.UNRECOVERABLE
            record.escalation_required = True

            if self.config.preserve_failure_history:
                record.history.append(
                    {
                        "timestamp": self._now().isoformat(),
                        "event": "unrecoverable",
                        "reason": reason,
                    }
                )

        return record

    # ---------------------------------------------------------------------
    # EXECUTION CONTEXT INTEGRATION
    # ---------------------------------------------------------------------

    def request_replan(
        self,
        task_id: str,
    ) -> bool:
        """
        Request replanning from the owning ExecutionContext.

        The recovery manager does not construct the new plan.
        """

        if not self.config.allow_replan:
            return False

        task_id = str(task_id)

        context = self._contexts.get(task_id)

        if context is None:
            return False

        try:
            context.request_replanning(
                reason=f"Recovery requested replanning for task '{task_id}'."
            )
        except TypeError:
            try:
                context.request_replanning()
            except Exception:
                return False
        except Exception:
            return False

        return True

    # ---------------------------------------------------------------------
    # BATCH PROCESSING
    # ---------------------------------------------------------------------

    def process_failures(
        self,
        failures: Iterable[ExecutionFailure],
    ) -> RecoveryCycleResult:
        """
        Process a collection of actual execution failures.
        """

        result = RecoveryCycleResult()

        for failure in failures:
            task_id = str(
                getattr(
                    failure,
                    "task_id",
                    "",
                )
            )

            if not task_id:
                continue

            self.register_failure(
                task_id=task_id,
                failure=failure,
            )

            decision = self.decide(task_id)

            result.decisions.append(decision)

            if decision.action in {
                RecoveryAction.RETRY,
                RecoveryAction.RETRY_WITH_BACKOFF,
            }:
                result.retry_task_ids.append(task_id)

            elif decision.action == RecoveryAction.REPLAN:
                result.replan_task_ids.append(task_id)
                self.request_replan(task_id)

            elif decision.action == RecoveryAction.DEGRADE:
                result.degraded_task_ids.append(task_id)

            elif decision.action == RecoveryAction.SKIP:
                result.skipped_task_ids.append(task_id)

            elif decision.action == RecoveryAction.ESCALATE:
                result.escalated_task_ids.append(task_id)

            elif decision.action in {
                RecoveryAction.FAIL,
                RecoveryAction.CANCEL,
            }:
                result.unrecoverable_task_ids.append(task_id)

        return result

    # ---------------------------------------------------------------------
    # QUERY API
    # ---------------------------------------------------------------------

    def get_record(
        self,
        task_id: str,
    ) -> Optional[RecoveryRecord]:
        with self._lock:
            return self._records.get(str(task_id))

    def recovery_required(
        self,
        task_id: str,
    ) -> bool:
        record = self.get_record(task_id)

        if record is None:
            return False

        return record.state in {
            RecoveryState.PENDING,
            RecoveryState.ANALYZING,
            RecoveryState.RETRYING,
            RecoveryState.REPLANNING,
            RecoveryState.DEGRADING,
            RecoveryState.ESCALATING,
        }

    def retry_count(
        self,
        task_id: str,
    ) -> int:
        record = self.get_record(task_id)

        if record is None:
            return 0

        return record.retry_count

    def unrecoverable_task_ids(self) -> List[str]:
        with self._lock:
            return [
                task_id
                for task_id, record in self._records.items()
                if record.state == RecoveryState.UNRECOVERABLE
            ]

    def escalation_task_ids(self) -> List[str]:
        with self._lock:
            return [
                task_id
                for task_id, record in self._records.items()
                if record.escalation_required
            ]

    # ---------------------------------------------------------------------
    # SNAPSHOT
    # ---------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            records = list(self._records.values())

        state_counts: Dict[str, int] = {}

        for record in records:
            key = record.state.value
            state_counts[key] = state_counts.get(key, 0) + 1

        return {
            "tracked_tasks": len(records),
            "state_counts": state_counts,
            "total_failures": sum(
                record.failures
                for record in records
            ),
            "total_retries": sum(
                record.retry_count
                for record in records
            ),
            "total_replans": sum(
                record.replan_count
                for record in records
            ),
            "total_degradations": sum(
                record.degradation_count
                for record in records
            ),
            "escalation_tasks": len(
                [
                    record
                    for record in records
                    if record.escalation_required
                ]
            ),
            "configuration": {
                "max_retries": self.config.max_retries,
                "allow_replan": self.config.allow_replan,
                "allow_degradation": self.config.allow_degradation,
                "allow_optional_task_skip": (
                    self.config.allow_optional_task_skip
                ),
            },
        }

    # ---------------------------------------------------------------------
    # CLEANUP
    # ---------------------------------------------------------------------

    def unregister_task(
        self,
        task_id: str,
    ) -> Optional[RecoveryRecord]:
        task_id = str(task_id)

        with self._lock:
            record = self._records.pop(task_id, None)
            self._contexts.pop(task_id, None)
            self._tasks.pop(task_id, None)

        return record

    def reset(self) -> None:
        """
        Reset recovery state for a fresh ALPHA runtime/session.
        """

        with self._lock:
            self._records.clear()
            self._contexts.clear()
            self._tasks.clear()


__all__ = [
    "RecoveryManagerError",
    "RecoveryConfigurationError",
    "RecoveryStateError",
    "RecoveryPolicyError",
    "RecoveryAction",
    "RecoveryState",
    "FailureClass",
    "RetryDisposition",
    "RecoveryManagerConfig",
    "FailureClassification",
    "RecoveryRecord",
    "RecoveryDecision",
    "RecoveryCycleResult",
    "RecoveryManager",
]
