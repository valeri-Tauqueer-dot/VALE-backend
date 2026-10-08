from __future__ import annotations

from typing import Iterable, List, Optional

from .capability_registry import HeroicCapabilityRegistry
from .capability_state import (
    CapabilityStatus,
    HeroicCapabilityState,
)


class HeroicCapabilitySelector:
    """
    Selects capabilities from the HEROIC capability registry.

    Selection is declarative only. It does not execute the
    selected capabilities.
    """

    def __init__(
        self,
        registry: Optional[
            HeroicCapabilityRegistry
        ] = None,
    ) -> None:
        self.registry = (
            registry
            if registry is not None
            else HeroicCapabilityRegistry()
        )

    def select(
        self,
        capability_ids: Iterable[str],
    ) -> List[HeroicCapabilityState]:
        selected: List[HeroicCapabilityState] = []

        for capability_id in capability_ids:
            capability = self.registry.get(
                capability_id
            )

            if capability is not None:
                selected.append(capability)

        return selected

    def select_available(
        self,
        capability_ids: Iterable[str],
    ) -> List[HeroicCapabilityState]:
        return [
            capability
            for capability in self.select(
                capability_ids
            )
            if capability.status
            == CapabilityStatus.AVAILABLE
        ]

    def select_all(self) -> List[HeroicCapabilityState]:
        return self.registry.list_all()

    def missing(
        self,
        capability_ids: Iterable[str],
    ) -> List[str]:
        return [
            capability_id
            for capability_id in capability_ids
            if capability_id not in self.registry
        ]

    def unavailable(
        self,
        capability_ids: Iterable[str],
    ) -> List[HeroicCapabilityState]:
        return [
            capability
            for capability in self.select(
                capability_ids
            )
            if capability.status
            != CapabilityStatus.AVAILABLE
        ]

    def rank(
        self,
        capabilities: Iterable[HeroicCapabilityState],
    ) -> List[HeroicCapabilityState]:
        return sorted(
            list(capabilities),
            key=lambda capability: (
                capability.priority,
                capability.confidence,
            ),
            reverse=True,
        )

    def _find_by_name(
        self,
        name: str,
    ) -> Optional[HeroicCapabilityState]:
        normalized = name.strip().lower()

        if not normalized:
            return None

        for capability in self.registry.list_all():
            if capability.name.strip().lower() == normalized:
                return capability

        return None
