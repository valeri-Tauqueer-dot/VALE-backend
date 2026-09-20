"""
VALE AI - ALPHA Brain
Resource Manager

File:
    ALPHA/resources/resource_manager.py

Purpose:
    Manage execution resources for ALPHA.

Responsibilities:
    - Track available execution capacity.
    - Track reservations.
    - Perform admission control.
    - Allocate resources to tasks.
    - Release resources.
    - Detect resource contention.
    - Support dynamic capacity updates.
    - Prevent over-allocation.
    - Provide resource snapshots.
    - Support multi-execution isolation.

Non-responsibilities:
    - Task execution.
    - Task scheduling.
    - Brain selection.
    - Domain reasoning.
    - Truth verification.
    - Final decision making.

Architecture:

    HEROIC
       |
       v
    ALPHA Planner
       |
       v
    Scheduler
       |
       v
    Resource Manager
       |
       +---- admission control
       +---- resource allocation
       +---- capacity tracking
       +---- reservation
       +---- contention detection
       |
       v
    Parallel Executor

Design principles:
    - Never allocate more capacity than actually exists.
    - Never fabricate resource availability.
    - Preserve execution isolation.
    - Resource state is observable.
    - Allocation is reversible through release.
    - Resource starvation must be visible.
    - Scheduler decides ordering; Resource Manager decides capacity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Set


# ============================================================================
# EXCEPTIONS
# ============================================================================


class ResourceManagerError(Exception):
    """Base exception for resource-manager failures."""


class ResourceConfigurationError(ResourceManagerError):
    """Raised when resource configuration is invalid."""


class ResourceAllocationError(ResourceManagerError):
    """Raised when a resource allocation cannot be completed."""


class ResourceReservationError(ResourceManagerError):
    """Raised when a reservation cannot be created or modified."""


class ResourceReleaseError(ResourceManagerError):
    """Raised when resource release fails."""


# ============================================================================
# ENUMS
# ============================================================================


class ResourceType(str, Enum):
    """
    Resource categories understood by ALPHA.

    These are logical execution resources rather than claims about the
    machine's exact hardware topology.
    """

    CPU = "cpu"
    MEMORY = "memory"
    CONCURRENCY = "concurrency"
    IO = "io"
    NETWORK = "network"
    GPU = "gpu"
    CUSTOM = "custom"


class AllocationState(str, Enum):
    """Lifecycle state of a resource allocation."""

    REQUESTED = "requested"
    ALLOCATED = "allocated"
    PARTIALLY_ALLOCATED = "partially_allocated"
    RELEASED = "released"
    REJECTED = "rejected"


class AdmissionDecision(str, Enum):
    """Admission-control result."""

    ACCEPT = "accept"
    ACCEPT_PARTIAL = "accept_partial"
    WAIT = "wait"
    REJECT = "reject"


class ContentionLevel(str, Enum):
    """Current resource contention level."""

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SATURATED = "saturated"


# ============================================================================
# RESOURCE CAPACITY
# ============================================================================


@dataclass
class ResourceCapacity:
    """
    Capacity and current allocation for one logical resource.
    """

    resource_type: ResourceType
    total: float
    available: float

    reserved: float = 0.0
    allocated: float = 0.0

    unit: str = "units"

    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.total < 0:
            raise ResourceConfigurationError(
                f"Resource total cannot be negative: {self.total}"
            )

        if self.available < 0:
            raise ResourceConfigurationError(
                f"Resource available cannot be negative: {self.available}"
            )

        if self.reserved < 0:
            raise ResourceConfigurationError(
                f"Resource reserved cannot be negative: {self.reserved}"
            )

        if self.allocated < 0:
            raise ResourceConfigurationError(
                f"Resource allocated cannot be negative: {self.allocated}"
            )

        self._normalize()

    def _normalize(self) -> None:
        """
        Normalize floating-point boundary noise while preserving the actual
        capacity relationship.
        """

        if self.available > self.total:
            self.available = self.total

        if self.available < 0:
            self.available = 0.0

    @property
    def utilization(self) -> float:
        if self.total <= 0:
            return 1.0

        used = self.total - self.available

        return max(
            0.0,
            min(
                1.0,
                used / self.total,
            ),
        )

    @property
    def free_capacity(self) -> float:
        return max(
            0.0,
            self.available,
        )


# ============================================================================
# RESOURCE REQUIREMENT
# ============================================================================


@dataclass(frozen=True)
class ResourceRequirement:
    """
    Resource requirements for one task.

    Values are logical resource units.

    Example:

        CPU = 1
        MEMORY = 512
        CONCURRENCY = 1
    """

    resources: Dict[ResourceType, float] = field(
        default_factory=dict
    )

    allow_partial: bool = False

    priority_multiplier: float = 1.0

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.priority_multiplier <= 0:
            raise ResourceConfigurationError(
                "priority_multiplier must be greater than zero."
            )

        for resource_type, amount in self.resources.items():
            if amount < 0:
                raise ResourceConfigurationError(
                    f"Resource requirement cannot be negative: "
                    f"{resource_type}={amount}"
                )


# ============================================================================
# RESERVATION
# ============================================================================


@dataclass
class ResourceReservation:
    """
    Resource reservation associated with a task/execution.
    """

    reservation_id: str
    owner_id: str
    requirements: Dict[ResourceType, float]

    state: AllocationState = AllocationState.REQUESTED

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    allocated_at: Optional[datetime] = None
    released_at: Optional[datetime] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================================
# ALLOCATION
# ============================================================================


@dataclass
class ResourceAllocation:
    """
    Actual resource allocation granted to a task.
    """

    allocation_id: str
    owner_id: str

    allocated: Dict[ResourceType, float]

    state: AllocationState = AllocationState.ALLOCATED

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    released_at: Optional[datetime] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================================
# ADMISSION RESULT
# ============================================================================


@dataclass(frozen=True)
class AdmissionResult:
    """
    Result of resource admission control.
    """

    owner_id: str

    decision: AdmissionDecision

    requested: Dict[ResourceType, float]
    available: Dict[ResourceType, float]

    allocatable: Dict[ResourceType, float]

    missing: Dict[ResourceType, float]

    contention: ContentionLevel

    reason: str

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ============================================================================
# RESOURCE MANAGER CONFIG
# ============================================================================


@dataclass(frozen=True)
class ResourceManagerConfig:
    """
    Resource manager behavior configuration.
    """

    default_cpu_capacity: float = 1.0
    default_concurrency_capacity: float = 4.0

    high_utilization_threshold: float = 0.75
    moderate_utilization_threshold: float = 0.50
    low_utilization_threshold: float = 0.25

    allow_partial_allocation: bool = False

    strict_unknown_resource_rejection: bool = True

    def __post_init__(self) -> None:
        if self.default_cpu_capacity < 0:
            raise ResourceConfigurationError(
                "default_cpu_capacity cannot be negative."
            )

        if self.default_concurrency_capacity < 0:
            raise ResourceConfigurationError(
                "default_concurrency_capacity cannot be negative."
            )

        if not (
            0.0
            <= self.low_utilization_threshold
            <= self.moderate_utilization_threshold
            <= self.high_utilization_threshold
            <= 1.0
        ):
            raise ResourceConfigurationError(
                "Utilization thresholds must satisfy "
                "0 <= low <= moderate <= high <= 1."
            )


# ============================================================================
# RESOURCE MANAGER
# ============================================================================


class ResourceManager:
    """
    ALPHA resource management engine.

    The manager maintains a real in-memory representation of the capacity
    that has been explicitly provided to it.

    It does not pretend to know the machine's actual CPU, RAM, GPU, network,
    or IO capacity unless that information has been supplied by the runtime.
    """

    def __init__(
        self,
        config: Optional[ResourceManagerConfig] = None,
    ) -> None:
        self.config = config or ResourceManagerConfig()

        self._capacities: Dict[
            ResourceType,
            ResourceCapacity,
        ] = {}

        self._reservations: Dict[
            str,
            ResourceReservation,
        ] = {}

        self._allocations: Dict[
            str,
            ResourceAllocation,
        ] = {}

        self._owner_allocations: Dict[
            str,
            Set[str],
        ] = {}

        self._lock = Lock()

        self._reservation_counter = 0
        self._allocation_counter = 0

        self._initialize_default_capacities()

    # ---------------------------------------------------------------------
    # INITIALIZATION
    # ---------------------------------------------------------------------

    def _initialize_default_capacities(self) -> None:
        """
        Initialize only logical defaults.

        These are configuration defaults, not claims about the host machine.
        """

        self.set_capacity(
            ResourceType.CPU,
            self.config.default_cpu_capacity,
        )

        self.set_capacity(
            ResourceType.CONCURRENCY,
            self.config.default_concurrency_capacity,
        )

    # ---------------------------------------------------------------------
    # IDENTIFIERS
    # ---------------------------------------------------------------------

    def _next_reservation_id(self) -> str:
        with self._lock:
            self._reservation_counter += 1

            return (
                f"alpha-reservation-"
                f"{self._reservation_counter}"
            )

    def _next_allocation_id(self) -> str:
        with self._lock:
            self._allocation_counter += 1

            return (
                f"alpha-allocation-"
                f"{self._allocation_counter}"
            )

    # ---------------------------------------------------------------------
    # CAPACITY MANAGEMENT
    # ---------------------------------------------------------------------

    def set_capacity(
        self,
        resource_type: ResourceType,
        total: float,
        unit: str = "units",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResourceCapacity:
        """
        Set or replace total capacity for a resource.

        This is intended to be called by the runtime/resource discovery
        layer when actual capacity information becomes available.
        """

        total = float(total)

        if total < 0:
            raise ResourceConfigurationError(
                "Resource capacity cannot be negative."
            )

        with self._lock:
            existing = self._capacities.get(resource_type)

            allocated = (
                existing.allocated
                if existing is not None
                else 0.0
            )

            reserved = (
                existing.reserved
                if existing is not None
                else 0.0
            )

            used = allocated + reserved

            if total < used:
                raise ResourceConfigurationError(
                    f"Cannot reduce {resource_type.value} capacity "
                    f"below current committed usage. "
                    f"total={total}, committed={used}"
                )

            capacity = ResourceCapacity(
                resource_type=resource_type,
                total=total,
                available=total - used,
                reserved=reserved,
                allocated=allocated,
                unit=unit,
                metadata=dict(metadata or {}),
            )

            self._capacities[resource_type] = capacity

            return capacity

    def update_capacity(
        self,
        resource_type: ResourceType,
        total: Optional[float] = None,
        available: Optional[float] = None,
        unit: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResourceCapacity:
        """
        Update capacity using explicitly supplied runtime information.

        If available is supplied, it is treated as authoritative runtime
        information. The manager does not invent the value.
        """

        with self._lock:
            current = self._capacities.get(resource_type)

            if current is None:
                if total is None:
                    raise ResourceConfigurationError(
                        f"No capacity exists for "
                        f"{resource_type.value}; total is required."
                    )

                current = ResourceCapacity(
                    resource_type=resource_type,
                    total=float(total),
                    available=float(total),
                )

                self._capacities[resource_type] = current

            if total is not None:
                total = float(total)

                if total < 0:
                    raise ResourceConfigurationError(
                        "Resource total cannot be negative."
                    )

                committed = (
                    current.allocated
                    + current.reserved
                )

                if total < committed:
                    raise ResourceConfigurationError(
                        f"New total capacity {total} is below "
                        f"committed capacity {committed}."
                    )

                current.total = total

            if available is not None:
                available = float(available)

                if available < 0:
                    raise ResourceConfigurationError(
                        "Available resource capacity cannot be negative."
                    )

                if available > current.total:
                    raise ResourceConfigurationError(
                        "Available capacity cannot exceed total capacity."
                    )

                current.available = available

            else:
                current.available = max(
                    0.0,
                    current.total
                    - current.allocated
                    - current.reserved,
                )

            if unit is not None:
                current.unit = unit

            if metadata:
                current.metadata.update(metadata)

            return current

    def get_capacity(
        self,
        resource_type: ResourceType,
    ) -> Optional[ResourceCapacity]:
        with self._lock:
            return self._capacities.get(resource_type)

    def capacities(self) -> Dict[
        ResourceType,
        ResourceCapacity,
    ]:
        with self._lock:
            return dict(self._capacities)

    # ---------------------------------------------------------------------
    # REQUIREMENT NORMALIZATION
    # ---------------------------------------------------------------------

    def normalize_requirements(
        self,
        requirements: Optional[
            ResourceRequirement
            | Dict[ResourceType, float]
        ],
    ) -> Dict[ResourceType, float]:
        if requirements is None:
            return {}

        if isinstance(
            requirements,
            ResourceRequirement,
        ):
            source = requirements.resources

        elif isinstance(
            requirements,
            dict,
        ):
            source = requirements

        else:
            raise ResourceConfigurationError(
                "Requirements must be ResourceRequirement or dict."
            )

        normalized: Dict[ResourceType, float] = {}

        for resource_type, amount in source.items():
            if isinstance(resource_type, ResourceType):
                key = resource_type
            else:
                try:
                    key = ResourceType(str(resource_type))
                except ValueError:
                    if self.config.strict_unknown_resource_rejection:
                        raise ResourceConfigurationError(
                            f"Unknown resource type: {resource_type}"
                        )

                    key = ResourceType.CUSTOM

            amount = float(amount)

            if amount < 0:
                raise ResourceConfigurationError(
                    f"Resource requirement cannot be negative: "
                    f"{key.value}={amount}"
                )

            if amount == 0:
                continue

            normalized[key] = amount

        return normalized

    # ---------------------------------------------------------------------
    # ADMISSION CONTROL
    # ---------------------------------------------------------------------

    def check_admission(
        self,
        owner_id: str,
        requirements: Optional[
            ResourceRequirement
            | Dict[ResourceType, float]
        ],
    ) -> AdmissionResult:
        """
        Determine whether requested work can currently be admitted.
        """

        owner_id = str(owner_id)

        requested = self.normalize_requirements(
            requirements
        )

        available: Dict[ResourceType, float] = {}
        allocatable: Dict[ResourceType, float] = {}
        missing: Dict[ResourceType, float] = {}

        with self._lock:
            for resource_type, amount in requested.items():
                capacity = self._capacities.get(resource_type)

                if capacity is None:
                    available[resource_type] = 0.0
                    allocatable[resource_type] = 0.0
                    missing[resource_type] = amount
                    continue

                available[resource_type] = capacity.available

                granted = min(
                    amount,
                    capacity.available,
                )

                allocatable[resource_type] = granted

                if granted < amount:
                    missing[resource_type] = (
                        amount - granted
                    )

        contention = self._contention_level()

        if not requested:
            return AdmissionResult(
                owner_id=owner_id,
                decision=AdmissionDecision.ACCEPT,
                requested={},
                available={},
                allocatable={},
                missing={},
                contention=contention,
                reason="Task does not require managed resources.",
            )

        if not missing:
            return AdmissionResult(
                owner_id=owner_id,
                decision=AdmissionDecision.ACCEPT,
                requested=requested,
                available=available,
                allocatable=allocatable,
                missing={},
                contention=contention,
                reason="All requested resources are currently available.",
            )

        requirement_obj = (
            requirements
            if isinstance(
                requirements,
                ResourceRequirement,
            )
            else None
        )

        partial_allowed = (
            requirement_obj.allow_partial
            if requirement_obj is not None
            else self.config.allow_partial_allocation
        )

        if partial_allowed and allocatable:
            return AdmissionResult(
                owner_id=owner_id,
                decision=AdmissionDecision.ACCEPT_PARTIAL,
                requested=requested,
                available=available,
                allocatable=allocatable,
                missing=missing,
                contention=contention,
                reason=(
                    "Only part of the requested resources are available, "
                    "and partial allocation is permitted."
                ),
            )

        return AdmissionResult(
            owner_id=owner_id,
            decision=AdmissionDecision.WAIT,
            requested=requested,
            available=available,
            allocatable=allocatable,
            missing=missing,
            contention=contention,
            reason=(
                "Required resources are currently unavailable; "
                "task should wait for capacity."
            ),
        )

    # ---------------------------------------------------------------------
    # ALLOCATION
    # ---------------------------------------------------------------------

    def allocate(
        self,
        owner_id: str,
        requirements: Optional[
            ResourceRequirement
            | Dict[ResourceType, float]
        ],
    ) -> ResourceAllocation:
        """
        Atomically allocate requested resources.

        Raises:
            ResourceAllocationError if resources cannot be allocated.
        """

        owner_id = str(owner_id)

        admission = self.check_admission(
            owner_id=owner_id,
            requirements=requirements,
        )

        if admission.decision not in {
            AdmissionDecision.ACCEPT,
            AdmissionDecision.ACCEPT_PARTIAL,
        }:
            raise ResourceAllocationError(
                admission.reason
            )

        allocated = dict(
            admission.allocatable
        )

        if (
            admission.decision
            == AdmissionDecision.ACCEPT_PARTIAL
        ):
            if not allocated:
                raise ResourceAllocationError(
                    "Partial allocation produced no allocatable resources."
                )

        allocation_id = self._next_allocation_id()

        with self._lock:
            for resource_type, amount in allocated.items():
                capacity = self._capacities.get(resource_type)

                if capacity is None:
                    raise ResourceAllocationError(
                        f"Resource disappeared during allocation: "
                        f"{resource_type.value}"
                    )

                if amount > capacity.available:
                    raise ResourceAllocationError(
                        f"Insufficient {resource_type.value} capacity "
                        f"during allocation."
                    )

            for resource_type, amount in allocated.items():
                capacity = self._capacities[resource_type]

                capacity.available -= amount
                capacity.allocated += amount

            allocation = ResourceAllocation(
                allocation_id=allocation_id,
                owner_id=owner_id,
                allocated=allocated,
                state=(
                    AllocationState.ALLOCATED
                    if admission.decision
                    == AdmissionDecision.ACCEPT
                    else AllocationState.PARTIALLY_ALLOCATED
                ),
            )

            self._allocations[
                allocation_id
            ] = allocation

            self._owner_allocations.setdefault(
                owner_id,
                set(),
            ).add(
                allocation_id
            )

        return allocation

    # ---------------------------------------------------------------------
    # RELEASE
    # ---------------------------------------------------------------------

    def release(
        self,
        allocation_id: str,
    ) -> ResourceAllocation:
        """
        Release a previous allocation.
        """

        allocation_id = str(allocation_id)

        with self._lock:
            allocation = self._allocations.get(
                allocation_id
            )

            if allocation is None:
                raise ResourceReleaseError(
                    f"Unknown allocation: {allocation_id}"
                )

            if allocation.state == AllocationState.RELEASED:
                return allocation

            for resource_type, amount in allocation.allocated.items():
                capacity = self._capacities.get(
                    resource_type
                )

                if capacity is None:
                    raise ResourceReleaseError(
                        f"Resource capacity no longer exists: "
                        f"{resource_type.value}"
                    )

                capacity.allocated = max(
                    0.0,
                    capacity.allocated - amount,
                )

                capacity.available = min(
                    capacity.total
                    - capacity.reserved
                    - capacity.allocated,
                    capacity.available + amount,
                )

            allocation.state = AllocationState.RELEASED
            allocation.released_at = self._now()

            owner_set = self._owner_allocations.get(
                allocation.owner_id
            )

            if owner_set is not None:
                owner_set.discard(
                    allocation_id
                )

                if not owner_set:
                    self._owner_allocations.pop(
                        allocation.owner_id,
                        None,
                    )

        return allocation

    def release_owner(
        self,
        owner_id: str,
    ) -> List[ResourceAllocation]:
        """
        Release all active allocations owned by one execution/task.
        """

        owner_id = str(owner_id)

        with self._lock:
            allocation_ids = list(
                self._owner_allocations.get(
                    owner_id,
                    set(),
                )
            )

        released: List[ResourceAllocation] = []

        for allocation_id in allocation_ids:
            released.append(
                self.release(
                    allocation_id
                )
            )

        return released

    # ---------------------------------------------------------------------
    # RESERVATIONS
    # ---------------------------------------------------------------------

    def reserve(
        self,
        owner_id: str,
        requirements: Optional[
            ResourceRequirement
            | Dict[ResourceType, float]
        ],
    ) -> ResourceReservation:
        """
        Reserve resources without yet converting them into active
        allocations.

        Reservations reduce currently available capacity so that another
        task cannot consume the same capacity.
        """

        owner_id = str(owner_id)

        normalized = self.normalize_requirements(
            requirements
        )

        admission = self.check_admission(
            owner_id=owner_id,
            requirements=normalized,
        )

        if admission.decision != AdmissionDecision.ACCEPT:
            raise ResourceReservationError(
                "Requested reservation cannot currently be satisfied."
            )

        reservation_id = self._next_reservation_id()

        with self._lock:
            for resource_type, amount in normalized.items():
                capacity = self._capacities.get(
                    resource_type
                )

                if capacity is None:
                    raise ResourceReservationError(
                        f"Unknown resource: {resource_type.value}"
                    )

                if amount > capacity.available:
                    raise ResourceReservationError(
                        f"Insufficient capacity for reservation: "
                        f"{resource_type.value}"
                    )

            for resource_type, amount in normalized.items():
                capacity = self._capacities[
                    resource_type
                ]

                capacity.available -= amount
                capacity.reserved += amount

            reservation = ResourceReservation(
                reservation_id=reservation_id,
                owner_id=owner_id,
                requirements=normalized,
                state=AllocationState.REQUESTED,
            )

            self._reservations[
                reservation_id
            ] = reservation

        return reservation

    def commit_reservation(
        self,
        reservation_id: str,
    ) -> ResourceAllocation:
        """
        Convert a reservation into an active allocation.
        """

        reservation_id = str(
            reservation_id
        )

        with self._lock:
            reservation = self._reservations.get(
                reservation_id
            )

            if reservation is None:
                raise ResourceReservationError(
                    f"Unknown reservation: {reservation_id}"
                )

            if reservation.state != AllocationState.REQUESTED:
                raise ResourceReservationError(
                    "Reservation is not available for commitment."
                )

            for resource_type, amount in reservation.requirements.items():
                capacity = self._capacities.get(
                    resource_type
                )

                if capacity is None:
                    raise ResourceReservationError(
                        f"Resource no longer exists: "
                        f"{resource_type.value}"
                    )

                capacity.reserved = max(
                    0.0,
                    capacity.reserved - amount,
                )

                capacity.allocated += amount

            allocation_id = self._next_allocation_id()

            allocation = ResourceAllocation(
                allocation_id=allocation_id,
                owner_id=reservation.owner_id,
                allocated=dict(
                    reservation.requirements
                ),
            )

            self._allocations[
                allocation_id
            ] = allocation

            self._owner_allocations.setdefault(
                reservation.owner_id,
                set(),
            ).add(
                allocation_id
            )

            reservation.state = AllocationState.ALLOCATED
            reservation.allocated_at = self._now()

        return allocation

    def release_reservation(
        self,
        reservation_id: str,
    ) -> ResourceReservation:
        """
        Release an unused reservation.
        """

        reservation_id = str(
            reservation_id
        )

        with self._lock:
            reservation = self._reservations.get(
                reservation_id
            )

            if reservation is None:
                raise ResourceReservationError(
                    f"Unknown reservation: {reservation_id}"
                )

            if reservation.state == AllocationState.RELEASED:
                return reservation

            if reservation.state != AllocationState.REQUESTED:
                raise ResourceReservationError(
                    "Only uncommitted reservations can be released."
                )

            for resource_type, amount in reservation.requirements.items():
                capacity = self._capacities.get(
                    resource_type
                )

                if capacity is None:
                    continue

                capacity.reserved = max(
                    0.0,
                    capacity.reserved - amount,
                )

                capacity.available = min(
                    capacity.total
                    - capacity.allocated
                    - capacity.reserved,
                    capacity.available + amount,
                )

            reservation.state = AllocationState.RELEASED
            reservation.released_at = self._now()

        return reservation

    # ---------------------------------------------------------------------
    # CONTENTION
    # ---------------------------------------------------------------------

    def _contention_level(self) -> ContentionLevel:
        with self._lock:
            capacities = list(
                self._capacities.values()
            )

        if not capacities:
            return ContentionLevel.NONE

        max_utilization = max(
            capacity.utilization
            for capacity in capacities
        )

        if max_utilization >= 1.0:
            return ContentionLevel.SATURATED

        if (
            max_utilization
            >= self.config.high_utilization_threshold
        ):
            return ContentionLevel.HIGH

        if (
            max_utilization
            >= self.config.moderate_utilization_threshold
        ):
            return ContentionLevel.MODERATE

        if (
            max_utilization
            >= self.config.low_utilization_threshold
        ):
            return ContentionLevel.LOW

        return ContentionLevel.NONE

    def contention_level(self) -> ContentionLevel:
        return self._contention_level()

    # ---------------------------------------------------------------------
    # RESOURCE QUERIES
    # ---------------------------------------------------------------------

    def available(
        self,
        resource_type: ResourceType,
    ) -> float:
        capacity = self.get_capacity(
            resource_type
        )

        if capacity is None:
            return 0.0

        return capacity.available

    def utilization(
        self,
        resource_type: ResourceType,
    ) -> float:
        capacity = self.get_capacity(
            resource_type
        )

        if capacity is None:
            return 0.0

        return capacity.utilization

    def owner_allocations(
        self,
        owner_id: str,
    ) -> List[ResourceAllocation]:
        owner_id = str(owner_id)

        with self._lock:
            ids = list(
                self._owner_allocations.get(
                    owner_id,
                    set(),
                )
            )

            return [
                self._allocations[allocation_id]
                for allocation_id in ids
                if allocation_id in self._allocations
            ]

    # ---------------------------------------------------------------------
    # RESOURCE PRESSURE
    # ---------------------------------------------------------------------

    def can_fit(
        self,
        requirements: Optional[
            ResourceRequirement
            | Dict[ResourceType, float]
        ],
    ) -> bool:
        admission = self.check_admission(
            owner_id="capacity-check",
            requirements=requirements,
        )

        return admission.decision == AdmissionDecision.ACCEPT

    def most_constrained_resource(
        self,
    ) -> Optional[ResourceType]:
        with self._lock:
            capacities = list(
                self._capacities.values()
            )

        if not capacities:
            return None

        return max(
            capacities,
            key=lambda capacity: capacity.utilization,
        ).resource_type

    # ---------------------------------------------------------------------
    # CLEANUP
    # ---------------------------------------------------------------------

    def cleanup_released(
        self,
    ) -> int:
        """
        Remove released allocation/reservation records.

        Returns number of removed records.
        """

        removed = 0

        with self._lock:
            allocation_ids = [
                allocation_id
                for allocation_id, allocation
                in self._allocations.items()
                if allocation.state
                == AllocationState.RELEASED
            ]

            for allocation_id in allocation_ids:
                self._allocations.pop(
                    allocation_id,
                    None,
                )
                removed += 1

            reservation_ids = [
                reservation_id
                for reservation_id, reservation
                in self._reservations.items()
                if reservation.state
                == AllocationState.RELEASED
            ]

            for reservation_id in reservation_ids:
                self._reservations.pop(
                    reservation_id,
                    None,
                )
                removed += 1

        return removed

    # ---------------------------------------------------------------------
    # SNAPSHOT
    # ---------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """
        Return the current resource state.

        No estimated or fabricated capacity is added.
        """

        with self._lock:
            capacities = dict(
                self._capacities
            )

            allocations = list(
                self._allocations.values()
            )

            reservations = list(
                self._reservations.values()
            )

        resource_snapshot: Dict[str, Any] = {}

        for resource_type, capacity in capacities.items():
            resource_snapshot[
                resource_type.value
            ] = {
                "total": capacity.total,
                "available": capacity.available,
                "reserved": capacity.reserved,
                "allocated": capacity.allocated,
                "utilization": capacity.utilization,
                "unit": capacity.unit,
                "metadata": dict(
                    capacity.metadata
                ),
            }

        return {
            "resources": resource_snapshot,
            "active_allocations": len(
                [
                    allocation
                    for allocation in allocations
                    if allocation.state
                    in {
                        AllocationState.ALLOCATED,
                        AllocationState.PARTIALLY_ALLOCATED,
                    }
                ]
            ),
            "active_reservations": len(
                [
                    reservation
                    for reservation in reservations
                    if reservation.state
                    == AllocationState.REQUESTED
                ]
            ),
            "contention": self.contention_level().value,
            "most_constrained_resource": (
                self.most_constrained_resource().value
                if self.most_constrained_resource()
                is not None
                else None
            ),
        }

    # ---------------------------------------------------------------------
    # RESET
    # ---------------------------------------------------------------------

    def reset(
        self,
        preserve_capacity: bool = True,
    ) -> None:
        """
        Reset allocations and reservations.

        By default, explicitly configured capacities remain.
        """

        with self._lock:
            self._allocations.clear()
            self._reservations.clear()
            self._owner_allocations.clear()

            self._allocation_counter = 0
            self._reservation_counter = 0

            if preserve_capacity:
                for capacity in self._capacities.values():
                    capacity.allocated = 0.0
                    capacity.reserved = 0.0
                    capacity.available = capacity.total
            else:
                self._capacities.clear()

    # ---------------------------------------------------------------------
    # TIME
    # ---------------------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


__all__ = [
    "ResourceManagerError",
    "ResourceConfigurationError",
    "ResourceAllocationError",
    "ResourceReservationError",
    "ResourceReleaseError",
    "ResourceType",
    "AllocationState",
    "AdmissionDecision",
    "ContentionLevel",
    "ResourceCapacity",
    "ResourceRequirement",
    "ResourceReservation",
    "ResourceAllocation",
    "AdmissionResult",
    "ResourceManagerConfig",
    "ResourceManager",
              ]
