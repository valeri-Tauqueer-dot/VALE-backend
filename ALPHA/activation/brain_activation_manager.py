"""
VALE AI - ALPHA Brain Activation Manager

File:
    ALPHA/activation/brain_activation_manager.py

Purpose:
    Safely activate VALE brains/capabilities selected by the upstream
    decision-making layer.

Architectural boundary:
    HEROIC decides WHAT intelligence/capability is required.
    ALPHA decides HOW and WHEN that capability is activated.

Important:
    This module does not invent brain outputs.
    A brain/capability must have an explicitly registered handler before
    real activation can occur.

Design goals:
    - explicit registration
    - safe admission
    - concurrency control
    - resource-aware activation
    - execution/context isolation
    - activation lifecycle tracking
    - real handler invocation only
    - deterministic cleanup
    - failure visibility
    - no fabricated brain availability
    - no domain-specific brain logic
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional
from uuid import uuid4

from ALPHA.resources.resource_manager import (
    AdmissionDecision,
    ResourceManager,
    ResourceRequirement as ManagedResourceRequirement,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BrainActivationError(Exception):
    """Base exception for brain activation failures."""


class ActivationConfigurationError(BrainActivationError):
    """Raised when activation configuration is invalid."""


class ActivationRegistrationError(BrainActivationError):
    """Raised when a brain/capability cannot be registered."""


class ActivationTargetNotFoundError(BrainActivationError):
    """Raised when an activation target is not registered."""


class ActivationAdmissionError(BrainActivationError):
    """Raised when activation is rejected by admission controls."""


class ActivationExecutionError(BrainActivationError):
    """Raised when a registered activation handler fails."""


class ActivationStateError(BrainActivationError):
    """Raised when an invalid lifecycle transition is requested."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ActivationState(str, Enum):
    """
    Lifecycle state of one activation request.
    """

    REQUESTED = "requested"
    ADMITTED = "admitted"
    ACTIVATING = "activating"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class ActivationDecision(str, Enum):
    """
    Admission decision.
    """

    ADMIT = "admit"
    REJECT = "reject"
    ALREADY_ACTIVE = "already_active"
    UNAVAILABLE = "unavailable"


class ActivationEventType(str, Enum):
    """
    Observable activation lifecycle events.
    """

    REGISTERED = "registered"
    UNREGISTERED = "unregistered"
    REQUESTED = "requested"
    ADMITTED = "admitted"
    REJECTED = "rejected"
    ACTIVATING = "activating"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RESOURCE_ALLOCATED = "resource_allocated"
    RESOURCE_RELEASED = "resource_released"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _normalize_identifier(value: str, field_name: str) -> str:
    """
    Normalize and validate an identifier.
    """
    if not isinstance(value, str):
        raise ActivationConfigurationError(
            f"{field_name} must be a string."
        )

    normalized = value.strip()

    if not normalized:
        raise ActivationConfigurationError(
            f"{field_name} cannot be empty."
        )

    return normalized


# ---------------------------------------------------------------------------
# Activation target
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActivationTarget:
    """
    Describes the brain/capability ALPHA has been asked to activate.

    This object describes a target; it does not decide whether the target
    should be selected.
    """

    target_id: str
    display_name: str
    target_type: str = "brain"
    version: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_id",
            _normalize_identifier(self.target_id, "target_id"),
        )

        object.__setattr__(
            self,
            "display_name",
            _normalize_identifier(self.display_name, "display_name"),
        )

        object.__setattr__(
            self,
            "target_type",
            _normalize_identifier(self.target_type, "target_type"),
        )


# ---------------------------------------------------------------------------
# Activation request
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActivationRequest:
    """
    Request to activate one registered target.

    source:
        Identifies who requested activation, for example HEROIC or another
        ALPHA execution component.

    execution_id/context_id:
        Preserve execution isolation for multi-user/multi-task operation.

    resource_requirement:
        Optional logical resource requirement understood by ResourceManager.
    """

    target_id: str
    execution_id: str
    context_id: str

    source: str = "HEROIC"

    activation_id: str = field(default_factory=lambda: str(uuid4()))

    priority: int = 0
    allow_duplicate: bool = False

    resource_requirement: Optional[ManagedResourceRequirement] = None

    input_data: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_id",
            _normalize_identifier(self.target_id, "target_id"),
        )

        object.__setattr__(
            self,
            "execution_id",
            _normalize_identifier(self.execution_id, "execution_id"),
        )

        object.__setattr__(
            self,
            "context_id",
            _normalize_identifier(self.context_id, "context_id"),
        )

        object.__setattr__(
            self,
            "source",
            _normalize_identifier(self.source, "source"),
        )

        if not isinstance(self.priority, int):
            raise ActivationConfigurationError(
                "priority must be an integer."
            )


# ---------------------------------------------------------------------------
# Activation record
# ---------------------------------------------------------------------------


@dataclass
class ActivationRecord:
    """
    Runtime record for an activation request.
    """

    activation_id: str
    target_id: str
    execution_id: str
    context_id: str
    source: str

    state: ActivationState = ActivationState.REQUESTED
    decision: Optional[ActivationDecision] = None

    requested_at: datetime = field(default_factory=_utc_now)
    admitted_at: Optional[datetime] = None
    activating_at: Optional[datetime] = None
    active_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    output: Any = None
    error: Optional[str] = None

    resource_allocation_id: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_terminal(self) -> bool:
        return self.state in {
            ActivationState.COMPLETED,
            ActivationState.FAILED,
            ActivationState.CANCELLED,
            ActivationState.REJECTED,
        }


# ---------------------------------------------------------------------------
# Activation event
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActivationEvent:
    """
    Immutable activation lifecycle event.
    """

    event_id: str
    activation_id: str
    target_id: str
    event_type: ActivationEventType
    timestamp: datetime

    execution_id: Optional[str] = None
    context_id: Optional[str] = None

    state: Optional[ActivationState] = None
    message: Optional[str] = None

    metadata: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Handler definition
# ---------------------------------------------------------------------------


ActivationHandler = Callable[[ActivationRequest], Any]


@dataclass
class RegisteredActivation:
    """
    Registered runtime activation target.
    """

    target: ActivationTarget
    handler: ActivationHandler

    max_concurrent: Optional[int] = None

    enabled: bool = True

    registered_at: datetime = field(default_factory=_utc_now)

    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BrainActivationManagerConfig:
    """
    Configuration for BrainActivationManager.
    """

    max_global_concurrent: int = 32
    max_events: int = 10_000

    reject_unregistered_targets: bool = True
    require_explicit_handler: bool = True

    enforce_target_concurrency: bool = True
    enforce_global_concurrency: bool = True

    allow_activation_after_failure: bool = True

    def __post_init__(self) -> None:
        if self.max_global_concurrent <= 0:
            raise ActivationConfigurationError(
                "max_global_concurrent must be greater than zero."
            )

        if self.max_events <= 0:
            raise ActivationConfigurationError(
                "max_events must be greater than zero."
            )


# ---------------------------------------------------------------------------
# Brain Activation Manager
# ---------------------------------------------------------------------------


class BrainActivationManager:
    """
    ALPHA's brain/capability activation manager.

    Responsibilities:
        - register activation targets
        - validate activation requests
        - perform admission checks
        - enforce concurrency limits
        - request logical resources
        - invoke explicitly registered handlers
        - track activation lifecycle
        - release resources
        - expose activation state and telemetry

    Non-responsibilities:
        - deciding WHAT intelligence is needed
        - deciding truth of brain outputs
        - final synthesis
        - market/trading decisions
        - supervision/recovery policy owned by Supervisor
    """

    def __init__(
        self,
        resource_manager: Optional[ResourceManager] = None,
        config: Optional[BrainActivationManagerConfig] = None,
    ) -> None:
        self.config = config or BrainActivationManagerConfig()

        self.resource_manager = resource_manager

        self._lock = RLock()

        self._registrations: Dict[str, RegisteredActivation] = {}
        self._activations: Dict[str, ActivationRecord] = {}

        self._events: List[ActivationEvent] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        target: ActivationTarget,
        handler: ActivationHandler,
        *,
        max_concurrent: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        replace: bool = False,
    ) -> RegisteredActivation:
        """
        Register a brain/capability activation handler.

        No target is considered executable merely because its name exists.
        A real handler must be registered.
        """

        if not callable(handler):
            raise ActivationRegistrationError(
                f"Handler for '{target.target_id}' is not callable."
            )

        if max_concurrent is not None and max_concurrent <= 0:
            raise ActivationRegistrationError(
                "max_concurrent must be greater than zero."
            )

        with self._lock:
            if target.target_id in self._registrations and not replace:
                raise ActivationRegistrationError(
                    f"Activation target '{target.target_id}' is already registered."
                )

            registration = RegisteredActivation(
                target=target,
                handler=handler,
                max_concurrent=max_concurrent,
                metadata=dict(metadata or {}),
            )

            self._registrations[target.target_id] = registration

            self._record_event(
                activation_id="",
                target_id=target.target_id,
                event_type=ActivationEventType.REGISTERED,
                message="Activation target registered.",
                metadata={
                    "target_type": target.target_type,
                    "version": target.version,
                },
            )

            return registration

    def unregister(
        self,
        target_id: str,
        *,
        force: bool = False,
    ) -> None:
        """
        Remove a registered target.

        By default active executions prevent unregistering.
        """

        target_id = _normalize_identifier(target_id, "target_id")

        with self._lock:
            if target_id not in self._registrations:
                raise ActivationTargetNotFoundError(
                    f"Activation target '{target_id}' is not registered."
                )

            active = self.active_for_target(target_id)

            if active and not force:
                raise ActivationRegistrationError(
                    f"Target '{target_id}' has active activations."
                )

            del self._registrations[target_id]

            self._record_event(
                activation_id="",
                target_id=target_id,
                event_type=ActivationEventType.UNREGISTERED,
                message="Activation target unregistered.",
            )

    def set_enabled(
        self,
        target_id: str,
        enabled: bool,
    ) -> None:
        """
        Enable or disable future activation of a registered target.
        """

        target_id = _normalize_identifier(target_id, "target_id")

        with self._lock:
            registration = self._registrations.get(target_id)

            if registration is None:
                raise ActivationTargetNotFoundError(
                    f"Activation target '{target_id}' is not registered."
                )

            registration.enabled = bool(enabled)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def is_registered(self, target_id: str) -> bool:
        target_id = _normalize_identifier(target_id, "target_id")

        with self._lock:
            return target_id in self._registrations

    def is_available(self, target_id: str) -> bool:
        target_id = _normalize_identifier(target_id, "target_id")

        with self._lock:
            registration = self._registrations.get(target_id)

            return bool(
                registration is not None
                and registration.enabled
                and callable(registration.handler)
            )

    def registered_targets(self) -> List[ActivationTarget]:
        with self._lock:
            return [
                registration.target
                for registration in self._registrations.values()
            ]

    def get_registration(
        self,
        target_id: str,
    ) -> RegisteredActivation:
        target_id = _normalize_identifier(target_id, "target_id")

        with self._lock:
            registration = self._registrations.get(target_id)

            if registration is None:
                raise ActivationTargetNotFoundError(
                    f"Activation target '{target_id}' is not registered."
                )

            return registration

     # ------------------------------------------------------------------
    # Request / admission
    # ------------------------------------------------------------------

    def request_activation(
        self,
        request: ActivationRequest,
    ) -> ActivationRecord:
        """
        Create and admit an activation request.

        This method does not automatically execute the handler.
        Use activate() when actual activation is desired.
        """

        with self._lock:
            record = ActivationRecord(
                activation_id=request.activation_id,
                target_id=request.target_id,
                execution_id=request.execution_id,
                context_id=request.context_id,
                source=request.source,
                metadata=dict(request.metadata),
            )

            self._activations[record.activation_id] = record

            self._record_event(
                activation_id=record.activation_id,
                target_id=record.target_id,
                event_type=ActivationEventType.REQUESTED,
                execution_id=record.execution_id,
                context_id=record.context_id,
                state=record.state,
            )

            decision = self._admission_decision(request)

            record.decision = decision

            if decision != ActivationDecision.ADMIT:
                record.state = ActivationState.REJECTED
                record.error = (
                    f"Activation rejected: {decision.value}"
                )

                self._record_event(
                    activation_id=record.activation_id,
                    target_id=record.target_id,
                    event_type=ActivationEventType.REJECTED,
                    execution_id=record.execution_id,
                    context_id=record.context_id,
                    state=record.state,
                    message=record.error,
                )

                raise ActivationAdmissionError(record.error)

            record.state = ActivationState.ADMITTED
            record.admitted_at = _utc_now()

            self._record_event(
                activation_id=record.activation_id,
                target_id=record.target_id,
                event_type=ActivationEventType.ADMITTED,
                execution_id=record.execution_id,
                context_id=record.context_id,
                state=record.state,
            )

            return record

    def _admission_decision(
        self,
        request: ActivationRequest,
    ) -> ActivationDecision:
        """
        Perform activation admission checks.
        """

        registration = self._registrations.get(request.target_id)

        if registration is None:
            if self.config.reject_unregistered_targets:
                return ActivationDecision.UNAVAILABLE

            return ActivationDecision.ADMIT

        if not registration.enabled:
            return ActivationDecision.UNAVAILABLE

        if self.config.enforce_global_concurrency:
            active_total = self._active_count()

            if active_total >= self.config.max_global_concurrent:
                return ActivationDecision.REJECT

        if (
            self.config.enforce_target_concurrency
            and registration.max_concurrent is not None
        ):
            active_target = self._active_count(
                target_id=request.target_id
            )

            if active_target >= registration.max_concurrent:
                return ActivationDecision.REJECT

        if not request.allow_duplicate:
            existing = self._find_active_duplicate(
                request.target_id,
                request.execution_id,
                request.context_id,
            )

            if existing is not None:
                return ActivationDecision.ALREADY_ACTIVE

        return ActivationDecision.ADMIT

    # ------------------------------------------------------------------
    # Actual activation
    # ------------------------------------------------------------------

    def activate(
        self,
        request: ActivationRequest,
    ) -> ActivationRecord:
        """
        Admit and execute one activation request.

        The registered handler is the only source of actual brain output.
        """

        with self._lock:
            record = self._activations.get(request.activation_id)

            if record is None:
                record = self.request_activation(request)

            if record.state != ActivationState.ADMITTED:
                raise ActivationStateError(
                    f"Activation '{record.activation_id}' is not admitted."
                )

            registration = self._registrations.get(request.target_id)

            if registration is None:
                record.state = ActivationState.FAILED
                record.error = (
                    f"No registered activation handler for "
                    f"'{request.target_id}'."
                )
                record.failed_at = _utc_now()

                self._record_event(
                    activation_id=record.activation_id,
                    target_id=record.target_id,
                    event_type=ActivationEventType.FAILED,
                    execution_id=record.execution_id,
                    context_id=record.context_id,
                    state=record.state,
                    message=record.error,
                )

                raise ActivationTargetNotFoundError(record.error)

            if not registration.enabled:
                record.state = ActivationState.REJECTED
                record.error = (
                    f"Activation target '{request.target_id}' is disabled."
                )

                raise ActivationAdmissionError(record.error)

            resource_allocation_id: Optional[str] = None

            try:
                # ------------------------------------------------------
                # Resource admission
                # ------------------------------------------------------

                if (
                    self.resource_manager is not None
                    and request.resource_requirement is not None
                ):
                    admission = self.resource_manager.admit(
                        owner_id=record.activation_id,
                        requirement=request.resource_requirement,
                    )

                    if admission.decision != AdmissionDecision.ADMIT:
                        record.state = ActivationState.REJECTED
                        record.error = (
                            "Resource admission rejected activation."
                        )

                        self._record_event(
                            activation_id=record.activation_id,
                            target_id=record.target_id,
                            event_type=ActivationEventType.REJECTED,
                            execution_id=record.execution_id,
                            context_id=record.context_id,
                            state=record.state,
                            message=record.error,
                            metadata={
                                "resource_decision": str(
                                    admission.decision
                                )
                            },
                        )

                        raise ActivationAdmissionError(
                            record.error
                        )

                    allocation = self.resource_manager.allocate(
                        owner_id=record.activation_id,
                        requirement=request.resource_requirement,
                    )

                    resource_allocation_id = allocation.allocation_id
                    record.resource_allocation_id = resource_allocation_id

                    self._record_event(
                        activation_id=record.activation_id,
                        target_id=record.target_id,
                        event_type=ActivationEventType.RESOURCE_ALLOCATED,
                        execution_id=record.execution_id,
                        context_id=record.context_id,
                        state=record.state,
                        metadata={
                            "allocation_id": resource_allocation_id
                        },
                    )

                # ------------------------------------------------------
                # Activation lifecycle
                # ------------------------------------------------------

                record.state = ActivationState.ACTIVATING
                record.activating_at = _utc_now()

                self._record_event(
                    activation_id=record.activation_id,
                    target_id=record.target_id,
                    event_type=ActivationEventType.ACTIVATING,
                    execution_id=record.execution_id,
                    context_id=record.context_id,
                    state=record.state,
                )

                handler = registration.handler

                if self.config.require_explicit_handler and not callable(
                    handler
                ):
                    raise ActivationExecutionError(
                        f"Activation handler for '{request.target_id}' "
                        "is not callable."
                    )

                record.state = ActivationState.ACTIVE
                record.active_at = _utc_now()

                self._record_event(
                    activation_id=record.activation_id,
                    target_id=record.target_id,
                    event_type=ActivationEventType.ACTIVE,
                    execution_id=record.execution_id,
                    context_id=record.context_id,
                    state=record.state,
                )

                # ------------------------------------------------------
                # Real invocation
                # ------------------------------------------------------

                try:
                    output = handler(request)
                except Exception as exc:
                    raise ActivationExecutionError(
                        f"Activation handler for '{request.target_id}' "
                        f"failed: {exc}"
                    ) from exc

                record.output = output
                record.state = ActivationState.COMPLETED
                record.completed_at = _utc_now()

                self._record_event(
                    activation_id=record.activation_id,
                    target_id=record.target_id,
                    event_type=ActivationEventType.COMPLETED,
                    execution_id=record.execution_id,
                    context_id=record.context_id,
                    state=record.state,
                )

                return record

            except ActivationAdmissionError:
                raise

            except Exception as exc:
                record.state = ActivationState.FAILED
                record.error = str(exc)
                record.failed_at = _utc_now()

                self._record_event(
                    activation_id=record.activation_id,
                    target_id=record.target_id,
                    event_type=ActivationEventType.FAILED,
                    execution_id=record.execution_id,
                    context_id=record.context_id,
                    state=record.state,
                    message=record.error,
                )

                raise ActivationExecutionError(
                    record.error
                ) from exc

            finally:
                # ------------------------------------------------------
                # Deterministic resource release
                # ------------------------------------------------------

                if (
                    self.resource_manager is not None
                    and resource_allocation_id is not None
                ):
                    try:
                        self.resource_manager.release(
                            resource_allocation_id
                        )

                        self._record_event(
                            activation_id=record.activation_id,
                            target_id=record.target_id,
                            event_type=ActivationEventType.RESOURCE_RELEASED,
                            execution_id=record.execution_id,
                            context_id=record.context_id,
                            state=record.state,
                            metadata={
                                "allocation_id": resource_allocation_id
                            },
                        )

                    except Exception as release_error:
                        record.metadata[
                            "resource_release_error"
                        ] = str(release_error)

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def cancel(
        self,
        activation_id: str,
        reason: Optional[str] = None,
    ) -> ActivationRecord:
        """
        Mark an activation as cancelled.

        This does not forcibly terminate arbitrary Python code running
        inside a handler. It records cancellation state safely.
        """

        activation_id = _normalize_identifier(
            activation_id,
            "activation_id",
        )

        with self._lock:
            record = self._activations.get(activation_id)

            if record is None:
                raise ActivationStateError(
                    f"Activation '{activation_id}' does not exist."
                )

            if record.is_terminal():
                return record

            record.state = ActivationState.CANCELLED
            record.cancelled_at = _utc_now()

            if reason:
                record.metadata["cancellation_reason"] = reason

            self._record_event(
                activation_id=record.activation_id,
                target_id=record.target_id,
                event_type=ActivationEventType.CANCELLED,
                execution_id=record.execution_id,
                context_id=record.context_id,
                state=record.state,
                message=reason,
            )

            return record

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_activation(
        self,
        activation_id: str,
    ) -> ActivationRecord:
        activation_id = _normalize_identifier(
            activation_id,
            "activation_id",
        )

        with self._lock:
            record = self._activations.get(activation_id)

            if record is None:
                raise ActivationStateError(
                    f"Activation '{activation_id}' does not exist."
                )

            return record

    def active_activations(self) -> List[ActivationRecord]:
        with self._lock:
            return [
                record
                for record in self._activations.values()
                if record.state
                in {
                    ActivationState.ADMITTED,
                    ActivationState.ACTIVATING,
                    ActivationState.ACTIVE,
                }
            ]

    def active_for_target(
        self,
        target_id: str,
    ) -> List[ActivationRecord]:
        target_id = _normalize_identifier(target_id, "target_id")

        with self._lock:
            return [
                record
                for record in self._activations.values()
                if record.target_id == target_id
                and record.state
                in {
                    ActivationState.ADMITTED,
                    ActivationState.ACTIVATING,
                    ActivationState.ACTIVE,
                }
            ]

    def active_for_execution(
        self,
        execution_id: str,
    ) -> List[ActivationRecord]:
        execution_id = _normalize_identifier(
            execution_id,
            "execution_id",
        )

        with self._lock:
            return [
                record
                for record in self._activations.values()
                if record.execution_id == execution_id
                and record.state
                in {
                    ActivationState.ADMITTED,
                    ActivationState.ACTIVATING,
                    ActivationState.ACTIVE,
                }
            ]

    def active_for_context(
        self,
        context_id: str,
    ) -> List[ActivationRecord]:
        context_id = _normalize_identifier(
            context_id,
            "context_id",
        )

        with self._lock:
            return [
                record
                for record in self._activations.values()
                if record.context_id == context_id
                and record.state
                in {
                    ActivationState.ADMITTED,
                    ActivationState.ACTIVATING,
                    ActivationState.ACTIVE,
                }
            ]

    def _active_count(
        self,
        target_id: Optional[str] = None,
    ) -> int:
        records = self.active_activations()

        if target_id is None:
            return len(records)

        return sum(
            1
            for record in records
            if record.target_id == target_id
        )

    def _find_active_duplicate(
        self,
        target_id: str,
        execution_id: str,
        context_id: str,
    ) -> Optional[ActivationRecord]:
        for record in self._activations.values():
            if (
                record.target_id == target_id
                and record.execution_id == execution_id
                and record.context_id == context_id
                and record.state
                in {
                    ActivationState.ADMITTED,
                    ActivationState.ACTIVATING,
                    ActivationState.ACTIVE,
                }
            ):
                return record

        return None

     # ------------------------------------------------------------------
    # Event / telemetry
    # ------------------------------------------------------------------

    def events(
        self,
        *,
        activation_id: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> List[ActivationEvent]:
        with self._lock:
            events = list(self._events)

        if activation_id is not None:
            events = [
                event
                for event in events
                if event.activation_id == activation_id
            ]

        if target_id is not None:
            events = [
                event
                for event in events
                if event.target_id == target_id
            ]

        return events

    def _record_event(
        self,
        *,
        activation_id: str,
        target_id: str,
        event_type: ActivationEventType,
        execution_id: Optional[str] = None,
        context_id: Optional[str] = None,
        state: Optional[ActivationState] = None,
        message: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        event = ActivationEvent(
            event_id=str(uuid4()),
            activation_id=activation_id,
            target_id=target_id,
            event_type=event_type,
            timestamp=_utc_now(),
            execution_id=execution_id,
            context_id=context_id,
            state=state,
            message=message,
            metadata=dict(metadata or {}),
        )

        self._events.append(event)

        if len(self._events) > self.config.max_events:
            overflow = len(self._events) - self.config.max_events
            del self._events[:overflow]

    # ------------------------------------------------------------------
    # Snapshots / maintenance
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """
        Return a runtime snapshot.

        Counts are derived from actual manager state.
        """

        with self._lock:
            records = list(self._activations.values())

            state_counts: Dict[str, int] = {}

            for record in records:
                key = record.state.value
                state_counts[key] = state_counts.get(key, 0) + 1

            return {
                "registered_targets": len(self._registrations),
                "total_activations": len(records),
                "active_activations": self._active_count(),
                "state_counts": state_counts,
                "event_count": len(self._events),
                "targets": [
                    {
                        "target_id": registration.target.target_id,
                        "display_name": registration.target.display_name,
                        "target_type": registration.target.target_type,
                        "version": registration.target.version,
                        "enabled": registration.enabled,
                        "max_concurrent": registration.max_concurrent,
                    }
                    for registration in self._registrations.values()
                ],
            }

    def clear_completed(
        self,
        *,
        execution_id: Optional[str] = None,
    ) -> int:
        """
        Remove terminal activation records from memory.

        Returns the number actually removed.
        """

        with self._lock:
            removable: List[str] = []

            for activation_id, record in self._activations.items():
                if not record.is_terminal():
                    continue

                if (
                    execution_id is not None
                    and record.execution_id != execution_id
                ):
                    continue

                removable.append(activation_id)

            for activation_id in removable:
                del self._activations[activation_id]

            return len(removable)


__all__ = [
    "BrainActivationError",
    "ActivationConfigurationError",
    "ActivationRegistrationError",
    "ActivationTargetNotFoundError",
    "ActivationAdmissionError",
    "ActivationExecutionError",
    "ActivationStateError",
    "ActivationState",
    "ActivationDecision",
    "ActivationEventType",
    "ActivationTarget",
    "ActivationRequest",
    "ActivationRecord",
    "ActivationEvent",
    "ActivationHandler",
    "RegisteredActivation",
    "BrainActivationManagerConfig",
    "BrainActivationManager",
  ]
