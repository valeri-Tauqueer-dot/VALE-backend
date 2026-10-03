"""
VALE UNITY — Capability Registry

The Capability Registry maintains the relationship between VALE systems and
the capabilities they advertise.

It answers:

    Which systems provide capability X?
    What capabilities does system Y provide?
    Is a capability registered?
    What systems are associated with a capability?

This registry is structural metadata.

It does NOT:
- decide which capability is required for a task
- decide which brain should be selected
- perform routing
- execute capabilities
- perform reasoning
- verify outputs

HEROIC determines what intelligence is required.
ALPHA determines how execution should be performed.
Routing connects the selected destination.
This registry only describes available capability relationships.

Version: 0.1.0
Architecture Stage: UNITY_CAPABILITY_REGISTRY_FOUNDATION
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional, Set


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_CAPABILITY_REGISTRY_FOUNDATION"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_capability(value: str) -> str:
    return str(value).strip().lower()


def _normalize_system(value: str) -> str:
    return str(value).strip().upper()


@dataclass
class CapabilityDefinition:
    """
    Structural definition of one capability.
    """

    name: str
    description: str = ""

    providers: Set[str] = field(default_factory=set)

    enabled: bool = True

    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        self.name = _normalize_capability(self.name)
        self.description = str(self.description).strip()

        self.providers = {
            _normalize_system(provider)
            for provider in self.providers
            if str(provider).strip()
        }

        self.metadata = dict(self.metadata or {})

    def touch(self) -> None:
        self.updated_at = _utc_now()

    def add_provider(self, system_name: str) -> None:
        normalized = _normalize_system(system_name)

        if normalized:
            self.providers.add(normalized)
            self.touch()

    def remove_provider(self, system_name: str) -> bool:
        normalized = _normalize_system(system_name)

        if normalized in self.providers:
            self.providers.remove(normalized)
            self.touch()
            return True

        return False

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        self.touch()

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        if not self.name:
            errors.append("Capability name cannot be empty.")

        if not isinstance(self.providers, set):
            errors.append("Providers must be stored as a set.")

        if not self.description:
            warnings.append(
                f"Capability '{self.name}' has no description."
            )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "providers": sorted(self.providers),
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class CapabilityRegistry:
    """
    Registry mapping capabilities to their declared providers.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._capabilities: Dict[str, CapabilityDefinition] = {}

    # ------------------------------------------------------------------
    # Capability registration
    # ------------------------------------------------------------------

    def register(
        self,
        capability: str,
        description: str = "",
        providers: Optional[Iterable[str]] = None,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        replace: bool = False,
    ) -> CapabilityDefinition:
        name = _normalize_capability(capability)

        if not name:
            raise ValueError("Capability name cannot be empty.")

        with self._lock:
            if name in self._capabilities and not replace:
                raise ValueError(
                    f"Capability '{name}' is already registered."
                )

            definition = CapabilityDefinition(
                name=name,
                description=description,
                providers=set(providers or []),
                enabled=enabled,
                metadata=metadata or {},
            )

            validation = definition.validate()

            if not validation["valid"]:
                raise ValueError(
                    f"Invalid capability '{name}': "
                    f"{validation['errors']}"
                )

            self._capabilities[name] = definition

            return definition

    def unregister(self, capability: str) -> bool:
        name = _normalize_capability(capability)

        with self._lock:
            if name not in self._capabilities:
                return False

            del self._capabilities[name]
            return True

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, capability: str) -> Optional[CapabilityDefinition]:
        name = _normalize_capability(capability)

        with self._lock:
            return self._capabilities.get(name)

    def require(self, capability: str) -> CapabilityDefinition:
        definition = self.get(capability)

        if definition is None:
            raise KeyError(
                f"Capability '{_normalize_capability(capability)}' "
                "is not registered."
            )

        return definition

    def has(self, capability: str) -> bool:
        name = _normalize_capability(capability)

        with self._lock:
            return name in self._capabilities

    def names(self) -> List[str]:
        with self._lock:
            return sorted(self._capabilities.keys())

    def all(self) -> List[CapabilityDefinition]:
        with self._lock:
            return list(self._capabilities.values())

    # ------------------------------------------------------------------
    # Provider management
    # ------------------------------------------------------------------

    def add_provider(
        self,
        capability: str,
        system_name: str,
    ) -> CapabilityDefinition:
        definition = self.require(capability)

        with self._lock:
            definition.add_provider(system_name)
            return definition

    def remove_provider(
        self,
        capability: str,
        system_name: str,
    ) -> bool:
        definition = self.require(capability)

        with self._lock:
            return definition.remove_provider(system_name)

    def providers(self, capability: str) -> List[str]:
        definition = self.require(capability)

        with self._lock:
            return sorted(definition.providers)

    def capabilities_for(
        self,
        system_name: str,
    ) -> List[str]:
        normalized_system = _normalize_system(system_name)

        with self._lock:
            return sorted(
                name
                for name, definition in self._capabilities.items()
                if normalized_system in definition.providers
            )

    def capabilities_for_active_provider(
        self,
        system_name: str,
    ) -> List[str]:
        """
        Structural alias for provider lookup.

        Actual operational activity is intentionally not inferred here because
        the capability registry does not own brain lifecycle state.
        """
        return self.capabilities_for(system_name)

    # ------------------------------------------------------------------
    # Capability state
    # ------------------------------------------------------------------

    def enable(self, capability: str) -> CapabilityDefinition:
        definition = self.require(capability)

        with self._lock:
            definition.set_enabled(True)
            return definition

    def disable(self, capability: str) -> CapabilityDefinition:
        definition = self.require(capability)

        with self._lock:
            definition.set_enabled(False)
            return definition

    def enabled(self, capability: str) -> bool:
        definition = self.require(capability)
        return bool(definition.enabled)

    def enabled_capabilities(self) -> List[str]:
        with self._lock:
            return sorted(
                name
                for name, definition in self._capabilities.items()
                if definition.enabled
            )

    # ------------------------------------------------------------------
    # Architecture helpers
    # ------------------------------------------------------------------

    def register_foundation_capabilities(self) -> None:
        """
        Register structural foundation capabilities.

        These are declarations only. They do not activate implementations.
        """

        definitions = {
            "integration": (
                "System-wide VALE integration and shared cognitive state"
            ),
            "objective_intelligence": (
                "Objective and mission interpretation"
            ),
            "orchestration": (
                "Execution orchestration and resource coordination"
            ),
            "market_intelligence": (
                "Market and trading intelligence"
            ),
            "general_intelligence": (
                "General and cross-domain intelligence"
            ),
            "human_experience": (
                "Human experience and psychological context intelligence"
            ),
            "system_supervision": (
                "System health, monitoring and recovery"
            ),
            "memory": (
                "Persistent and contextual memory"
            ),
            "knowledge": (
                "Knowledge organization and retrieval"
            ),
            "reasoning": (
                "Structured reasoning infrastructure"
            ),
            "verification": (
                "Verification and evaluation"
            ),
            "communication": (
                "Shared cognitive communication"
            ),
            "routing": (
                "Structural destination routing"
            ),
            "coordination": (
                "Task and execution coordination"
            ),
            "evolution": (
                "Learning and validated system improvement"
            ),
            "cell_fabric": (
                "Large-scale logical cognitive cell connectivity"
            ),
        }

        for capability, description in definitions.items():
            if not self.has(capability):
                self.register(
                    capability=capability,
                    description=description,
                )

    def connect_provider(
        self,
        system_name: str,
        capabilities: Iterable[str],
    ) -> None:
        """
        Connect one system to multiple already-registered capabilities.

        Unknown capabilities are rejected rather than silently created.
        """

        normalized_system = _normalize_system(system_name)

        for capability in capabilities:
            if not self.has(capability):
                raise KeyError(
                    f"Capability '{_normalize_capability(capability)}' "
                    "is not registered."
                )

            self.add_provider(
                capability=capability,
                system_name=normalized_system,
            )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        with self._lock:
            for name, definition in self._capabilities.items():
                result = definition.validate()

                if not result["valid"]:
                    errors.extend(
                        f"{name}: {error}"
                        for error in result["errors"]
                    )

                warnings.extend(
                    f"{name}: {warning}"
                    for warning in result["warnings"]
                )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    def diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            provider_counts = {
                name: len(definition.providers)
                for name, definition in self._capabilities.items()
            }

            return {
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "capability_count": len(self._capabilities),
                "enabled_count": len(
                    [
                        definition
                        for definition in self._capabilities.values()
                        if definition.enabled
                    ]
                ),
                "capabilities": self.names(),
                "provider_counts": provider_counts,
                "validation": self.validate(),
            }

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {
                name: definition.to_dict()
                for name, definition in self._capabilities.items()
      }
