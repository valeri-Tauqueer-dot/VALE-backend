"""
VALE AI - ALPHA Context Distribution & Routing Engine

File:
    ALPHA/routing/context_router.py

Purpose:
    Safely distribute execution context to VALE brains, capabilities,
    tasks, and execution components.

Architectural boundary:

    HEROIC
        decides WHAT intelligence/capabilities are required.

    UNITY
        owns coherent system-wide shared state.

    ALPHA
        decides HOW context is packaged, filtered, routed, and reused
        for efficient execution.

    Specialized brains
        consume the context they are authorized to receive.

    MCVL
        verifies resulting intelligence.

Core principles:
    - least-context routing
    - execution isolation
    - multi-user isolation
    - explicit context ownership
    - immutable snapshots where practical
    - provenance preservation
    - no silent context mutation
    - no fabricated context
    - deterministic routing
    - selective context distribution
    - reusable context packets
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple
from uuid import uuid4

from ALPHA.core.execution_context import ExecutionContext


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ContextRoutingError(Exception):
    """Base exception for context routing failures."""


class ContextConfigurationError(ContextRoutingError):
    """Raised when routing configuration is invalid."""


class ContextAccessDeniedError(ContextRoutingError):
    """Raised when a target is not authorized to receive context."""


class ContextNotFoundError(ContextRoutingError):
    """Raised when requested context does not exist."""


class ContextConflictError(ContextRoutingError):
    """Raised when context versions conflict."""


class ContextIsolationError(ContextRoutingError):
    """Raised when execution/context isolation would be violated."""


class ContextSizeLimitError(ContextRoutingError):
    """Raised when context exceeds configured limits."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_identifier(
    value: str,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise ContextConfigurationError(
            f"{field_name} must be a string."
        )

    value = value.strip()

    if not value:
        raise ContextConfigurationError(
            f"{field_name} cannot be empty."
        )

    return value


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ContextSensitivity(str, Enum):
    """
    Sensitivity classification for routed context.

    This is an access-control aid, not a claim that the content is
    objectively sensitive.
    """

    PUBLIC = "public"
    EXECUTION = "execution"
    PRIVATE = "private"
    RESTRICTED = "restricted"


class ContextAccess(str, Enum):
    """
    Access mode granted to a target.
    """

    READ = "read"
    READ_WRITE = "read_write"
    METADATA_ONLY = "metadata_only"


class ContextRouteMode(str, Enum):
    """
    How context is routed.
    """

    FULL = "full"
    SELECTIVE = "selective"
    REFERENCE = "reference"
    DELTA = "delta"


class ContextSourceType(str, Enum):
    """
    Origin category of a context item.
    """

    EXECUTION = "execution"
    UNITY = "unity"
    BRAIN = "brain"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"
    EXTERNAL = "external"
    SYSTEM = "system"


# ---------------------------------------------------------------------------
# Context item
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextItem:
    """
    One independently addressable piece of context.

    The router does not decide whether the content is true.
    Provenance and verification metadata travel with the item.
    """

    key: str
    value: Any

    source_type: ContextSourceType = ContextSourceType.EXECUTION
    source_id: Optional[str] = None

    version: str = "1"

    sensitivity: ContextSensitivity = ContextSensitivity.EXECUTION

    verified: bool = False
    confidence: Optional[float] = None

    timestamp: datetime = field(default_factory=_utc_now)

    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "key",
            _normalize_identifier(self.key, "key"),
        )

        if self.source_id is not None:
            object.__setattr__(
                self,
                "source_id",
                _normalize_identifier(
                    self.source_id,
                    "source_id",
                ),
            )

        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ContextConfigurationError(
                    "confidence must be between 0.0 and 1.0."
                )


# ---------------------------------------------------------------------------
# Context bundle
# ---------------------------------------------------------------------------


@dataclass
class ContextBundle:
    """
    Immutable-by-convention package of context routed to one target.

    The router creates a new bundle rather than mutating the source
    execution context.
    """

    bundle_id: str
    execution_id: str
    context_id: str

    target_id: str

    items: Dict[str, ContextItem] = field(default_factory=dict)

    route_mode: ContextRouteMode = ContextRouteMode.SELECTIVE

    source_bundle_id: Optional[str] = None

    created_at: datetime = field(default_factory=_utc_now)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def keys(self) -> List[str]:
        return list(self.items.keys())

    def get(self, key: str) -> Optional[ContextItem]:
        return self.items.get(key)

    def contains(self, key: str) -> bool:
        return key in self.items

    def item_count(self) -> int:
        return len(self.items)


# ---------------------------------------------------------------------------
# Access policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextAccessPolicy:
    """
    Defines what a target is allowed to receive.

    Explicit allow-list behavior is preferred over broad implicit access.
    """

    target_id: str

    allowed_sensitivity: Tuple[
        ContextSensitivity,
        ...
    ] = (
        ContextSensitivity.PUBLIC,
        ContextSensitivity.EXECUTION,
    )

    allowed_source_types: Tuple[
        ContextSourceType,
        ...
    ] = (
        ContextSourceType.EXECUTION,
        ContextSourceType.UNITY,
        ContextSourceType.BRAIN,
        ContextSourceType.MEMORY,
        ContextSourceType.KNOWLEDGE,
    )

    access: ContextAccess = ContextAccess.READ

    allowed_keys: Optional[Tuple[str, ...]] = None

    denied_keys: Tuple[str, ...] = ()

    max_items: Optional[int] = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_id",
            _normalize_identifier(
                self.target_id,
                "target_id",
            ),
        )

        if self.max_items is not None and self.max_items <= 0:
            raise ContextConfigurationError(
                "max_items must be greater than zero."
            )


# ---------------------------------------------------------------------------
# Route request
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextRouteRequest:
    """
    Request to route execution context to a target.
    """

    execution_id: str
    context_id: str
    target_id: str

    route_mode: ContextRouteMode = ContextRouteMode.SELECTIVE

    requested_keys: Optional[Tuple[str, ...]] = None

    include_metadata: bool = True

    source_bundle_id: Optional[str] = None

    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "execution_id",
            _normalize_identifier(
                self.execution_id,
                "execution_id",
            ),
        )

        object.__setattr__(
            self,
            "context_id",
            _normalize_identifier(
                self.context_id,
                "context_id",
            ),
        )

        object.__setattr__(
            self,
            "target_id",
            _normalize_identifier(
                self.target_id,
                "target_id",
            ),
        )


# ---------------------------------------------------------------------------
# Route result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextRouteResult:
    """
    Result of a routing operation.
    """

    success: bool

    bundle: Optional[ContextBundle]

    execution_id: str
    context_id: str
    target_id: str

    routed_item_count: int

    denied_keys: Tuple[str, ...] = ()

    missing_keys: Tuple[str, ...] = ()

    reason: Optional[str] = None

    created_at: datetime = field(default_factory=_utc_now)


# ---------------------------------------------------------------------------
# Routing event
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextRoutingEvent:
    """
    Observable routing event.
    """

    event_id: str
    event_type: str

    timestamp: datetime

    execution_id: Optional[str] = None
    context_id: Optional[str] = None
    target_id: Optional[str] = None
    bundle_id: Optional[str] = None

    metadata: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextRouterConfig:
    """
    Runtime configuration.
    """

    max_bundle_items: int = 500

    max_events: int = 10_000

    require_registered_policy: bool = True

    preserve_provenance: bool = True

    enforce_execution_isolation: bool = True

    deny_restricted_by_default: bool = True

    allow_reference_routes: bool = True

    def __post_init__(self) -> None:
        if self.max_bundle_items <= 0:
            raise ContextConfigurationError(
                "max_bundle_items must be greater than zero."
            )

        if self.max_events <= 0:
            raise ContextConfigurationError(
                "max_events must be greater than zero."
            )


# ---------------------------------------------------------------------------
# Context Router
# ---------------------------------------------------------------------------


class ContextRouter:
    """
    ALPHA context routing engine.

    This component is intentionally NOT a global memory owner.

    It creates controlled context bundles from execution state and routes
    them to authorized targets.
    """

    def __init__(
        self,
        config: Optional[ContextRouterConfig] = None,
    ) -> None:
        self.config = config or ContextRouterConfig()

        self._lock = RLock()

        self._policies: Dict[str, ContextAccessPolicy] = {}

        self._execution_contexts: Dict[
            str,
            ExecutionContext,
        ] = {}

        self._bundles: Dict[str, ContextBundle] = {}

        self._events: List[ContextRoutingEvent] = []

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def register_policy(
        self,
        policy: ContextAccessPolicy,
        *,
        replace: bool = False,
    ) -> None:
        """
        Register an explicit access policy for a target.
        """

        with self._lock:
            if (
                policy.target_id in self._policies
                and not replace
            ):
                raise ContextConfigurationError(
                    f"Policy already exists for "
                    f"'{policy.target_id}'."
                )

            self._policies[policy.target_id] = policy

    def unregister_policy(
        self,
        target_id: str,
    ) -> None:
        target_id = _normalize_identifier(
            target_id,
            "target_id",
        )

        with self._lock:
            self._policies.pop(target_id, None)

    def get_policy(
        self,
        target_id: str,
    ) -> ContextAccessPolicy:
        target_id = _normalize_identifier(
            target_id,
            "target_id",
        )

        with self._lock:
            policy = self._policies.get(target_id)

            if policy is None:
                raise ContextAccessDeniedError(
                    f"No context access policy is registered "
                    f"for '{target_id}'."
                )

            return policy

    # ------------------------------------------------------------------
    # Execution context registration
    # ------------------------------------------------------------------

    def register_execution_context(
        self,
        context: ExecutionContext,
    ) -> None:
        """
        Make an execution context available to the router.

        The execution ID is used as an isolation boundary.
        """

        execution_id = _normalize_identifier(
            context.execution_id,
            "execution_id",
        )

        with self._lock:
            existing = self._execution_contexts.get(
                execution_id
            )

            if (
                existing is not None
                and existing.context_id != context.context_id
            ):
                raise ContextIsolationError(
                    f"Execution '{execution_id}' is already "
                    "associated with a different context."
                )

            self._execution_contexts[
                execution_id
            ] = context

    def unregister_execution_context(
        self,
        execution_id: str,
    ) -> None:
        execution_id = _normalize_identifier(
            execution_id,
            "execution_id",
        )

        with self._lock:
            self._execution_contexts.pop(
                execution_id,
                None,
            )

    def get_execution_context(
        self,
        execution_id: str,
    ) -> ExecutionContext:
        execution_id = _normalize_identifier(
            execution_id,
            "execution_id",
        )

        with self._lock:
            context = self._execution_contexts.get(
                execution_id
            )

            if context is None:
                raise ContextNotFoundError(
                    f"No execution context exists for "
                    f"'{execution_id}'."
                )

            return context

    # ------------------------------------------------------------------
    # Context extraction
    # ------------------------------------------------------------------

    def build_source_items(
        self,
        context: ExecutionContext,
    ) -> Dict[str, ContextItem]:
        """
        Convert execution shared data into routable context items.

        This does not claim the data is verified.
        """

        items: Dict[str, ContextItem] = {}

        for key, value in context.shared_data.items():
            items[key] = ContextItem(
                key=key,
                value=value,
                source_type=ContextSourceType.EXECUTION,
                source_id=context.execution_id,
                sensitivity=ContextSensitivity.EXECUTION,
                verified=False,
                metadata={
                    "context_id": context.context_id,
                },
            )

        return items

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(
        self,
        request: ContextRouteRequest,
    ) -> ContextRouteResult:
        """
        Route context according to the registered target policy.
        """

        with self._lock:
            context = self._execution_contexts.get(
                request.execution_id
            )

            if context is None:
                raise ContextNotFoundError(
                    f"Execution context '{request.execution_id}' "
                    "is not registered."
                )

            if (
                self.config.enforce_execution_isolation
                and context.context_id != request.context_id
            ):
                raise ContextIsolationError(
                    "Context ID does not match the execution "
                    "context registered for this execution."
                )

            policy = self._policies.get(
                request.target_id
            )

            if (
                policy is None
                and self.config.require_registered_policy
            ):
                raise ContextAccessDeniedError(
                    f"No access policy exists for "
                    f"'{request.target_id}'."
                )

            if policy is None:
                policy = self._default_policy(
                    request.target_id
                )

            source_items = self.build_source_items(
                context
            )

            selected, denied, missing = (
                self._select_items(
                    source_items=source_items,
                    request=request,
                    policy=policy,
                )
            )

            if len(selected) > self.config.max_bundle_items:
                raise ContextSizeLimitError(
                    f"Context route contains {len(selected)} "
                    f"items; maximum is "
                    f"{self.config.max_bundle_items}."
                )

            bundle = ContextBundle(
                bundle_id=str(uuid4()),
                execution_id=request.execution_id,
                context_id=request.context_id,
                target_id=request.target_id,
                items=selected,
                route_mode=request.route_mode,
                source_bundle_id=request.source_bundle_id,
                metadata=dict(request.metadata),
            )

            if not request.include_metadata:
                bundle.metadata = {}

            self._bundles[bundle.bundle_id] = bundle

            self._record_event(
                event_type="context_routed",
                execution_id=request.execution_id,
                context_id=request.context_id,
                target_id=request.target_id,
                bundle_id=bundle.bundle_id,
                metadata={
                    "item_count": len(selected),
                    "denied_count": len(denied),
                    "missing_count": len(missing),
                    "route_mode": request.route_mode.value,
                },
            )

            return ContextRouteResult(
                success=True,
                bundle=bundle,
                execution_id=request.execution_id,
                context_id=request.context_id,
                target_id=request.target_id,
                routed_item_count=len(selected),
                denied_keys=tuple(denied),
                missing_keys=tuple(missing),
            )

    def route_to_many(
        self,
        requests: Iterable[ContextRouteRequest],
    ) -> List[ContextRouteResult]:
        """
        Route context to multiple targets.

        Each target is evaluated independently against its own policy.
        """

        results: List[ContextRouteResult] = []

        for request in requests:
            results.append(
                self.route(request)
            )

        return results

    # ------------------------------------------------------------------
    # Selection logic
    # ------------------------------------------------------------------

    def _select_items(
        self,
        *,
        source_items: Mapping[str, ContextItem],
        request: ContextRouteRequest,
        policy: ContextAccessPolicy,
    ) -> Tuple[
        Dict[str, ContextItem],
        List[str],
        List[str],
    ]:
        selected: Dict[str, ContextItem] = {}

        denied: List[str] = []
        missing: List[str] = []

        requested_keys = request.requested_keys

        if requested_keys is None:
            candidate_keys = list(source_items.keys())
        else:
            candidate_keys = list(requested_keys)

        if policy.allowed_keys is not None:
            allowed = set(policy.allowed_keys)
            candidate_keys = [
                key
                for key in candidate_keys
                if key in allowed
            ]

        denied_set = set(policy.denied_keys)

        for key in candidate_keys:
            item = source_items.get(key)

            if item is None:
                missing.append(key)
                continue

            if key in denied_set:
                denied.append(key)
                continue

            if item.source_type not in (
                policy.allowed_source_types
            ):
                denied.append(key)
                continue

            if item.sensitivity not in (
                policy.allowed_sensitivity
            ):
                denied.append(key)
                continue

            if (
                self.config.deny_restricted_by_default
                and item.sensitivity
                == ContextSensitivity.RESTRICTED
                and item.sensitivity
                not in policy.allowed_sensitivity
            ):
                denied.append(key)
                continue

            selected[key] = item

            if (
                policy.max_items is not None
                and len(selected) >= policy.max_items
            ):
                break

        return selected, denied, missing

    def _default_policy(
        self,
        target_id: str,
    ) -> ContextAccessPolicy:
        """
        Conservative fallback policy.

        It deliberately does not provide unrestricted context.
        """

        return ContextAccessPolicy(
            target_id=target_id,
            allowed_sensitivity=(
                ContextSensitivity.PUBLIC,
                ContextSensitivity.EXECUTION,
            ),
            allowed_source_types=(
                ContextSourceType.EXECUTION,
                ContextSourceType.SYSTEM,
            ),
            access=ContextAccess.READ,
        )

    # ------------------------------------------------------------------
    # Bundle access
    # ------------------------------------------------------------------

    def get_bundle(
        self,
        bundle_id: str,
    ) -> ContextBundle:
        bundle_id = _normalize_identifier(
            bundle_id,
            "bundle_id",
        )

        with self._lock:
            bundle = self._bundles.get(bundle_id)

            if bundle is None:
                raise ContextNotFoundError(
                    f"Context bundle '{bundle_id}' does not exist."
                )

            return bundle

    def bundles_for_execution(
        self,
        execution_id: str,
    ) -> List[ContextBundle]:
        execution_id = _normalize_identifier(
            execution_id,
            "execution_id",
        )

        with self._lock:
            return [
                bundle
                for bundle in self._bundles.values()
                if bundle.execution_id == execution_id
            ]

    def bundles_for_target(
        self,
        target_id: str,
    ) -> List[ContextBundle]:
        target_id = _normalize_identifier(
            target_id,
            "target_id",
        )

        with self._lock:
            return [
                bundle
                for bundle in self._bundles.values()
                if bundle.target_id == target_id
            ]

    # ------------------------------------------------------------------
    # Reference routing
    # ------------------------------------------------------------------

    def create_reference(
        self,
        bundle_id: str,
        target_id: str,
    ) -> ContextBundle:
        """
        Create a lightweight reference to an existing context bundle.

        The referenced content is not copied into the new bundle.

        This is useful for large context and future shared-state
        integration.
        """

        if not self.config.allow_reference_routes:
            raise ContextConfigurationError(
                "Reference routes are disabled."
            )

        source = self.get_bundle(bundle_id)

        target_id = _normalize_identifier(
            target_id,
            "target_id",
        )

        self.get_policy(target_id)

        reference = ContextBundle(
            bundle_id=str(uuid4()),
            execution_id=source.execution_id,
            context_id=source.context_id,
            target_id=target_id,
            items={},
            route_mode=ContextRouteMode.REFERENCE,
            source_bundle_id=source.bundle_id,
            metadata={
                "reference_only": True,
                "source_bundle_id": source.bundle_id,
            },
        )

        with self._lock:
            self._bundles[reference.bundle_id] = reference

            self._record_event(
                event_type="context_reference_created",
                execution_id=reference.execution_id,
                context_id=reference.context_id,
                target_id=target_id,
                bundle_id=reference.bundle_id,
                metadata={
                    "source_bundle_id": source.bundle_id,
                },
            )

        return reference

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def events(
        self,
        *,
        execution_id: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> List[ContextRoutingEvent]:
        with self._lock:
            events = list(self._events)

        if execution_id is not None:
            events = [
                event
                for event in events
                if event.execution_id == execution_id
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
        event_type: str,
        execution_id: Optional[str] = None,
        context_id: Optional[str] = None,
        target_id: Optional[str] = None,
        bundle_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        event = ContextRoutingEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            timestamp=_utc_now(),
            execution_id=execution_id,
            context_id=context_id,
            target_id=target_id,
            bundle_id=bundle_id,
            metadata=dict(metadata or {}),
        )

        self._events.append(event)

        if len(self._events) > self.config.max_events:
            overflow = len(self._events) - self.config.max_events
            del self._events[:overflow]

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear_execution(
        self,
        execution_id: str,
    ) -> Dict[str, int]:
        """
        Remove routing state belonging to one execution.

        This is useful for multi-user isolation and lifecycle cleanup.
        """

        execution_id = _normalize_identifier(
            execution_id,
            "execution_id",
        )

        with self._lock:
            bundles_to_remove = [
                bundle_id
                for bundle_id, bundle in self._bundles.items()
                if bundle.execution_id == execution_id
            ]

            for bundle_id in bundles_to_remove:
                del self._bundles[bundle_id]

            self._execution_contexts.pop(
                execution_id,
                None,
            )

            return {
                "bundles_removed": len(
                    bundles_to_remove
                ),
                "execution_context_removed": int(
                    execution_id
                    not in self._execution_contexts
                ),
            }

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "registered_policies": len(
                    self._policies
                ),
                "execution_contexts": len(
                    self._execution_contexts
                ),
                "context_bundles": len(
                    self._bundles
                ),
                "routing_events": len(
                    self._events
                ),
                "targets": list(
                    self._policies.keys()
                ),
            }


__all__ = [
    "ContextRoutingError",
    "ContextConfigurationError",
    "ContextAccessDeniedError",
    "ContextNotFoundError",
    "ContextConflictError",
    "ContextIsolationError",
    "ContextSizeLimitError",
    "ContextSensitivity",
    "ContextAccess",
    "ContextRouteMode",
    "ContextSourceType",
    "ContextItem",
    "ContextBundle",
    "ContextAccessPolicy",
    "ContextRouteRequest",
    "ContextRouteResult",
    "ContextRoutingEvent",
    "ContextRouterConfig",
    "ContextRouter",
]
  
