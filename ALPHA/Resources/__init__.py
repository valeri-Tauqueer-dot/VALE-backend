"""
VALE AI - ALPHA Resources Package

Resource capacity, admission control, allocation, reservation,
contention, and resource-state management.
"""

from .resource_manager import (
    AdmissionDecision,
    AdmissionResult,
    AllocationState,
    ContentionLevel,
    ResourceAllocation,
    ResourceAllocationError,
    ResourceCapacity,
    ResourceConfigurationError,
    ResourceManager,
    ResourceManagerConfig,
    ResourceManagerError,
    ResourceReleaseError,
    ResourceReservation,
    ResourceReservationError,
    ResourceRequirement,
    ResourceType,
)

__all__ = [
    "AdmissionDecision",
    "AdmissionResult",
    "AllocationState",
    "ContentionLevel",
    "ResourceAllocation",
    "ResourceAllocationError",
    "ResourceCapacity",
    "ResourceConfigurationError",
    "ResourceManager",
    "ResourceManagerConfig",
    "ResourceManagerError",
    "ResourceReleaseError",
    "ResourceReservation",
    "ResourceReservationError",
    "ResourceRequirement",
    "ResourceType",
]
