from future import annotations

from typing import Dict, Iterable, List, Optional

from HEROIC.capabilities.capability_state import (
CapabilityStatus,
HeroicCapabilityState,
)

class HeroicCapabilityRegistry:
"""
Registry of capabilities known to HEROIC.

The registry stores capability definitions and availability.
It does not decide which capabilities are needed for a mission;
that responsibility belongs to HeroicCapabilitySelector.
"""

def __init__(
    self,
    capabilities: Optional[Iterable[HeroicCapabilityState]] = None,
) -> None:
    self._capabilities: Dict[str, HeroicCapabilityState] = {}

    if capabilities:
        for capability in capabilities:
            self.register(capability)

def register(
    self,
    capability: HeroicCapabilityState,
    overwrite: bool = False,
) -> HeroicCapabilityState:
    """
    Register a capability.

    Raises:
        ValueError:
            If the capability already exists and overwrite is False.
    """
    if not capability.capability_id:
        raise ValueError("Capability ID cannot be empty.")

    if (
        capability.capability_id in self._capabilities
        and not overwrite
    ):
        raise ValueError(
            f"Capability already registered: "
            f"{capability.capability_id}"
        )

    self._capabilities[capability.capability_id] = capability

    return capability

def unregister(
    self,
    capability_id: str,
) -> bool:
    """Remove a capability from the registry."""
    if capability_id not in self._capabilities:
        return False

    del self._capabilities[capability_id]
    return True

def get(
    self,
    capability_id: str,
) -> Optional[HeroicCapabilityState]:
    """Retrieve a capability by ID."""
    return self._capabilities.get(capability_id)

def require(
    self,
    capability_id: str,
) -> HeroicCapabilityState:
    """
    Retrieve a capability or raise an explicit error.
    """
    capability = self.get(capability_id)

    if capability is None:
        raise KeyError(
            f"Unknown HEROIC capability: {capability_id}"
        )

    return capability

def contains(
    self,
    capability_id: str,
) -> bool:
    """Return whether a capability is registered."""
    return capability_id in self._capabilities

def list_all(self) -> List[HeroicCapabilityState]:
    """Return all registered capabilities."""
    return list(self._capabilities.values())

def available(self) -> List[HeroicCapabilityState]:
    """Return currently available capabilities."""
    return [
        capability
        for capability in self._capabilities.values()
        if capability.status == CapabilityStatus.AVAILABLE
    ]

def unavailable(self) -> List[HeroicCapabilityState]:
    """Return capabilities that cannot currently be used."""
    return [
        capability
        for capability in self._capabilities.values()
        if capability.status != CapabilityStatus.AVAILABLE
    ]

def set_status(
    self,
    capability_id: str,
    status: CapabilityStatus,
) -> HeroicCapabilityState:
    """Update capability availability."""
    capability = self.require(capability_id)
    capability.status = status
    return capability

def clear(self) -> None:
    """Remove all registered capabilities."""
    self._capabilities.clear()

def __len__(self) -> int:
    return len(self._capabilities)

def __contains__(
    self,
    capability_id: str,
) -> bool:
    return self.contains(capability_id)

def to_dict(self) -> Dict[str, dict]:
    """Serialize the complete registry."""
    return {
        capability_id: capability.to_dict()
        for capability_id, capability
        in self._capabilities.items()
    }
