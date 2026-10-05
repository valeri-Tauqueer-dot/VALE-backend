from future import annotations

from typing import Iterable, List, Optional

from HEROIC.capabilities.capability_registry import (
HeroicCapabilityRegistry,
)
from HEROIC.capabilities.capability_state import (
CapabilityStatus,
HeroicCapabilityState,
)

class HeroicCapabilitySelector:
"""
Selects capabilities required to accomplish a HEROIC objective.

The selector does not execute capabilities and does not activate
brains. It determines which registered capabilities best match
the requested capability IDs, names, or required task capabilities.
"""

def __init__(
    self,
    registry: HeroicCapabilityRegistry,
) -> None:
    self.registry = registry

def select(
    self,
    required_capabilities: Optional[Iterable[str]] = None,
    *,
    include_unavailable: bool = False,
) -> List[HeroicCapabilityState]:
    """
    Select registered capabilities matching the requested IDs or names.

    Selection preserves the order supplied by the caller while avoiding
    duplicate capability objects.
    """
    if required_capabilities is None:
        return []

    selected: List[HeroicCapabilityState] = []
    selected_ids = set()

    for requested in required_capabilities:
        if not requested:
            continue

        capability = self.registry.get(requested)

        if capability is None:
            capability = self._find_by_name(requested)

        if capability is None:
            continue

        if (
            not include_unavailable
            and capability.status != CapabilityStatus.AVAILABLE
        ):
            continue

        if capability.capability_id in selected_ids:
            continue

        selected.append(capability)
        selected_ids.add(capability.capability_id)

    return selected

def select_available(
    self,
    required_capabilities: Iterable[str],
) -> List[HeroicCapabilityState]:
    """Select only capabilities that are currently available."""
    return self.select(
        required_capabilities,
        include_unavailable=False,
    )

def select_all(
    self,
    required_capabilities: Iterable[str],
) -> List[HeroicCapabilityState]:
    """Select capabilities regardless of current availability."""
    return self.select(
        required_capabilities,
        include_unavailable=True,
    )

def missing(
    self,
    required_capabilities: Iterable[str],
) -> List[str]:
    """
    Return requested capabilities that are not registered.

    A capability that exists but is currently unavailable is not
    considered missing; availability is a separate condition.
    """
    missing: List[str] = []

    for requested in required_capabilities:
        if not requested:
            continue

        if self.registry.get(requested) is not None:
            continue

        if self._find_by_name(requested) is not None:
            continue

        missing.append(requested)

    return missing

def unavailable(
    self,
    required_capabilities: Iterable[str],
) -> List[HeroicCapabilityState]:
    """Return registered capabilities that are currently unavailable."""
    selected = self.select_all(required_capabilities)

    return [
        capability
        for capability in selected
        if capability.status != CapabilityStatus.AVAILABLE
    ]

def rank(
    self,
    capabilities: Iterable[HeroicCapabilityState],
) -> List[HeroicCapabilityState]:
    """
    Rank capabilities by priority and confidence.

    Higher priority is preferred first. Confidence is used as the
    secondary ordering factor.
    """
    return sorted(
        capabilities,
        key=lambda capability: (
            capability.priority,
            capability.confidence,
        ),
        reverse=True,
    )

def _find_by_name(
    self,
    requested_name: str,
) -> Optional[HeroicCapabilityState]:
    """Find a capability using its human-readable name."""
    normalized = requested_name.strip().lower()

    if not normalized:
        return None

    for capability in self.registry.list_all():
        if capability.name.strip().lower() == normalized:
            return capability

    return None
