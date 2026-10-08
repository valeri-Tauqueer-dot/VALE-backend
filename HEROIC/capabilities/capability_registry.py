from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from .capability_state import (
    CapabilityStatus,
    HeroicCapabilityState,
)


class HeroicCapabilityRegistry:
    """
    Registry for HEROIC capabilities.

    The registry stores capability definitions. It does not
    execute capabilities.
    """

    def __init__(
        self,
        capabilities: Optional[
            Iterable[HeroicCapabilityState]
        ] = None,
    ) -> None:
        self._capabilities: Dict[
            str,
            HeroicCapabilityState,
        ] = {}

        if capabilities:
            for capability in capabilities:
                self.register(capability)

    def register(
        self,
        capability: HeroicCapabilityState,
        overwrite: bool = False,
    ) -> HeroicCapabilityState:
        if not isinstance(
            capability,
            HeroicCapabilityState,
        ):
            raise TypeError(
                "capability must be a "
                "HeroicCapabilityState instance."
            )

        capability_id = capability.capability_id

        if (
            capability_id in self._capabilities
            and not overwrite
        ):
            raise ValueError(
                f"Capability already registered: "
                f"{capability_id}"
            )

        self._capabilities[capability_id] = capability

        return capability

    def unregister(
        self,
        capability_id: str,
    ) -> Optional[HeroicCapabilityState]:
        return self._capabilities.pop(
            capability_id,
            None,
        )

    def get(
        self,
        capability_id: str,
    ) -> Optional[HeroicCapabilityState]:
        return self._capabilities.get(
            capability_id
        )

    def require(
        self,
        capability_id: str,
    ) -> HeroicCapabilityState:
        capability = self.get(capability_id)

        if capability is None:
            raise KeyError(
                f"Unknown HEROIC capability: "
                f"{capability_id}"
            )

        return capability

    def list_all(self) -> List[HeroicCapabilityState]:
        return list(
            self._capabilities.values()
        )

    def available(self) -> List[HeroicCapabilityState]:
        return [
            capability
            for capability in self._capabilities.values()
            if capability.status
            == CapabilityStatus.AVAILABLE
        ]

    def unavailable(self) -> List[HeroicCapabilityState]:
        return [
            capability
            for capability in self._capabilities.values()
            if capability.status
            != CapabilityStatus.AVAILABLE
        ]

    def set_status(
        self,
        capability_id: str,
        status: CapabilityStatus,
    ) -> HeroicCapabilityState:
        capability = self.require(
            capability_id
        )

        capability.status = status

        return capability

    def clear(self) -> None:
        self._capabilities.clear()

    def __len__(self) -> int:
        return len(self._capabilities)

    def __contains__(
        self,
        capability_id: str,
    ) -> bool:
        return capability_id in self._capabilities

    def to_dict(self) -> Dict[str, dict]:
        return {
            capability_id: capability.to_dict()
            for capability_id, capability
            in self._capabilities.items()
        }
