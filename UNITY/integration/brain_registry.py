"""
VALE UNITY — Brain Registry

The Brain Registry maintains the structural identity of brains and supporting
systems participating in the VALE cognitive architecture.

The registry answers questions such as:

    What systems exist?
    What type of system is this?
    What is its current availability/status?
    What capabilities does it advertise?
    Is it registered with UNITY?

The registry does NOT:
- decide which brain should solve a task
- perform reasoning
- perform routing
- orchestrate execution
- verify intelligence
- synthesize responses

Those responsibilities belong to other UNITY capabilities and VALE systems.

Version: 0.1.0
Architecture Stage: UNITY_BRAIN_REGISTRY_FOUNDATION
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional, Set


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_BRAIN_REGISTRY_FOUNDATION"


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _normalize_name(value: str) -> str:
    """Normalize a VALE system name."""
    return str(value).strip().upper()


@dataclass
class BrainRegistration:
    """
    Structural registration record for one VALE brain or supporting system.
    """

    name: str
    system_type: str
    role: str = ""

    version: str = "0.0.0"

    capabilities: Set[str] = field(default_factory=set)

    status: str = "REGISTERED"
    active: bool = False
    available: bool = True

    metadata: Dict[str, Any] = field(default_factory=dict)

    registered_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        self.name = _normalize_name(self.name)
        self.system_type = str(self.system_type).strip().upper()
        self.role = str(self.role).strip()
        self.version = str(self.version).strip()

        self.capabilities = {
            str(capability).strip().lower()
            for capability in self.capabilities
            if str(capability).strip()
        }

        self.metadata = dict(self.metadata or {})

    def touch(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = _utc_now()

    def add_capability(self, capability: str) -> None:
        capability = str(capability).strip().lower()

        if capability:
            self.capabilities.add(capability)
            self.touch()

    def remove_capability(self, capability: str) -> bool:
        capability = str(capability).strip().lower()

        if capability in self.capabilities:
            self.capabilities.remove(capability)
            self.touch()
            return True

        return False

    def set_active(self, active: bool) -> None:
        self.active = bool(active)
        self.status = "ACTIVE" if self.active else "REGISTERED"
        self.touch()

    def set_available(self, available: bool) -> None:
        self.available = bool(available)

        if not self.available:
            self.status = "UNAVAILABLE"
        elif self.active:
            self.status = "ACTIVE"
        else:
            self.status = "REGISTERED"

        self.touch()

    def set_status(self, status: str) -> None:
        self.status = str(status).strip().upper() or "REGISTERED"
        self.touch()

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        if not self.name:
            errors.append("Brain name cannot be empty.")

        if not self.system_type:
            errors.append("System type cannot be empty.")

        if not self.version:
            warnings.append("Version is empty.")

        if not isinstance(self.capabilities, set):
            errors.append("Capabilities must be stored as a set.")

        if not isinstance(self.metadata, dict):
            errors.append("Metadata must be a dictionary.")

        if self.active and not self.available:
            errors.append(
                "A brain cannot be active while marked unavailable."
            )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["capabilities"] = sorted(self.capabilities)
        return data


class BrainRegistry:
    """
    Structural registry for VALE brains and supporting systems.

    This component is intentionally deterministic.

    It stores identity and availability information but does not determine
    which system should perform a task.
    """

    CORE_BRAINS = {
        "UNITY",
        "HEROIC",
        "SUPERVISOR",
        "ALPHA",
    }

    SPECIALIZED_BRAINS = {
        "LEGEND",
        "MARCO",
        "FEELING",
    }

    SUPPORTING_SYSTEMS = {
        "COGNITIVE_FABRIC",
        "MEMORY",
        "KNOWLEDGE",
        "REASONING",
        "EVOLUTION",
        "MCVL",
        "UNITY_CELL_FABRIC",
    }

    def __init__(self) -> None:
        self._lock = RLock()
        self._registrations: Dict[str, BrainRegistration] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        system_type: str,
        role: str = "",
        version: str = "0.0.0",
        capabilities: Optional[Iterable[str]] = None,
        status: str = "REGISTERED",
        active: bool = False,
        available: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        replace: bool = False,
    ) -> BrainRegistration:
        """
        Register a brain or supporting system.

        Existing registrations are preserved unless replace=True.
        """

        normalized_name = _normalize_name(name)

        if not normalized_name:
            raise ValueError("Brain name cannot be empty.")

        with self._lock:
            if normalized_name in self._registrations and not replace:
                raise ValueError(
                    f"System '{normalized_name}' is already registered."
                )

            registration = BrainRegistration(
                name=normalized_name,
                system_type=system_type,
                role=role,
                version=version,
                capabilities=set(capabilities or []),
                status=status,
                active=active,
                available=available,
                metadata=metadata or {},
            )

            validation = registration.validate()

            if not validation["valid"]:
                raise ValueError(
                    f"Invalid registration for '{normalized_name}': "
                    f"{validation['errors']}"
                )

            self._registrations[normalized_name] = registration

            return registration

    def unregister(self, name: str) -> bool:
        """Remove a system from the registry."""
        normalized_name = _normalize_name(name)

        with self._lock:
            if normalized_name not in self._registrations:
                return False

            del self._registrations[normalized_name]
            return True

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[BrainRegistration]:
        """Return a registration by name."""
        normalized_name = _normalize_name(name)

        with self._lock:
            return self._registrations.get(normalized_name)

    def require(self, name: str) -> BrainRegistration:
        """Return a registration or raise an explicit error."""
        registration = self.get(name)

        if registration is None:
            raise KeyError(
                f"VALE system '{_normalize_name(name)}' is not registered."
            )

        return registration

    def has(self, name: str) -> bool:
        """Return whether a system is registered."""
        normalized_name = _normalize_name(name)

        with self._lock:
            return normalized_name in self._registrations

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def activate(self, name: str) -> BrainRegistration:
        """Mark a registered system active."""
        registration = self.require(name)

        with self._lock:
            if not registration.available:
                raise RuntimeError(
                    f"System '{registration.name}' is unavailable."
                )

            registration.set_active(True)
            return registration

    def deactivate(self, name: str) -> BrainRegistration:
        """Mark a registered system inactive."""
        registration = self.require(name)

        with self._lock:
            registration.set_active(False)
            return registration

    def set_available(
        self,
        name: str,
        available: bool,
    ) -> BrainRegistration:
        """Update system availability."""
        registration = self.require(name)

        with self._lock:
            registration.set_available(available)
            return registration

    def set_status(
        self,
        name: str,
        status: str,
    ) -> BrainRegistration:
        """Set an explicit operational status."""
        registration = self.require(name)

        with self._lock:
            registration.set_status(status)
            return registration

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

    def add_capability(
        self,
        name: str,
        capability: str,
    ) -> BrainRegistration:
        registration = self.require(name)

        with self._lock:
            registration.add_capability(capability)
            return registration

    def remove_capability(
        self,
        name: str,
        capability: str,
    ) -> BrainRegistration:
        registration = self.require(name)

        with self._lock:
            registration.remove_capability(capability)
            return registration

    def capabilities(self, name: str) -> List[str]:
        registration = self.require(name)
        return sorted(registration.capabilities)

    # ------------------------------------------------------------------
    # Collection queries
    # ------------------------------------------------------------------

    def all(self) -> List[BrainRegistration]:
        """Return all registered systems."""
        with self._lock:
            return list(self._registrations.values())

    def names(self) -> List[str]:
        """Return all registered system names."""
        with self._lock:
            return sorted(self._registrations.keys())

    def by_type(self, system_type: str) -> List[BrainRegistration]:
        """Return systems matching a system type."""
        normalized_type = str(system_type).strip().upper()

        with self._lock:
            return [
                registration
                for registration in self._registrations.values()
                if registration.system_type == normalized_type
            ]

    def by_capability(
        self,
        capability: str,
    ) -> List[BrainRegistration]:
        """Return systems advertising a capability."""
        normalized_capability = str(capability).strip().lower()

        with self._lock:
            return [
                registration
                for registration in self._registrations.values()
                if normalized_capability in registration.capabilities
            ]

    def active(self) -> List[BrainRegistration]:
        """Return currently active systems."""
        with self._lock:
            return [
                registration
                for registration in self._registrations.values()
                if registration.active
            ]

    def available(self) -> List[BrainRegistration]:
        """Return currently available systems."""
        with self._lock:
            return [
                registration
                for registration in self._registrations.values()
                if registration.available
            ]

    def active_names(self) -> List[str]:
        return sorted(
            registration.name
            for registration in self.active()
        )

    def available_names(self) -> List[str]:
        return sorted(
            registration.name
            for registration in self.available()
        )

    # ------------------------------------------------------------------
    # Architecture helpers
    # ------------------------------------------------------------------

    def register_core_brains(
        self,
        version: str = "0.1.0",
    ) -> None:
        """Register the structural core brains if not already present."""

        definitions = {
            "UNITY": "System-wide integration",
            "HEROIC": "Objective and mission intelligence",
            "SUPERVISOR": "System health and recovery",
            "ALPHA": "Execution orchestration and performance",
        }

        for name, role in definitions.items():
            if not self.has(name):
                self.register(
                    name=name,
                    system_type="CORE_BRAIN",
                    role=role,
                    version=version,
                )

    def register_specialized_brains(
        self,
        version: str = "0.1.0",
    ) -> None:
        """Register the structural specialized brains if absent."""

        definitions = {
            "LEGEND": "Market and trading intelligence",
            "MARCO": "General, cross-domain and evolution intelligence",
            "FEELING": "Human experience and psychological intelligence",
        }

        for name, role in definitions.items():
            if not self.has(name):
                self.register(
                    name=name,
                    system_type="SPECIALIZED_BRAIN",
                    role=role,
                    version=version,
                )

    def register_supporting_systems(
        self,
        version: str = "0.1.0",
    ) -> None:
        """Register the major supporting cognitive systems if absent."""

        definitions = {
            "COGNITIVE_FABRIC": "Shared cognitive communication and connectivity",
            "MEMORY": "Persistent and contextual memory",
            "KNOWLEDGE": "Knowledge organization and retrieval",
            "REASONING": "Structured reasoning infrastructure",
            "EVOLUTION": "Learning and system improvement",
            "MCVL": "Verification and evaluation",
            "UNITY_CELL_FABRIC": "Large-scale logical cognitive cell fabric",
        }

        for name, role in definitions.items():
            if not self.has(name):
                self.register(
                    name=name,
                    system_type="SUPPORTING_SYSTEM",
                    role=role,
                    version=version,
                )

    def register_vaIe_foundation(
        self,
        version: str = "0.1.0",
    ) -> None:
        """
        Register the known VALE foundation systems.

        This method only establishes structural identity. It does not activate
        every system automatically.
        """
        self.register_core_brains(version)
        self.register_specialized_brains(version)
        self.register_supporting_systems(version)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        with self._lock:
            for name, registration in self._registrations.items():
                result = registration.validate()

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
            type_counts: Dict[str, int] = {}

            for registration in self._registrations.values():
                type_counts[registration.system_type] = (
                    type_counts.get(registration.system_type, 0) + 1
                )

            return {
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "registered_count": len(self._registrations),
                "active_count": len(
                    [
                        item
                        for item in self._registrations.values()
                        if item.active
                    ]
                ),
                "available_count": len(
                    [
                        item
                        for item in self._registrations.values()
                        if item.available
                    ]
                ),
                "system_type_counts": type_counts,
                "registered_names": self.names(),
                "validation": self.validate(),
            }

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Serialize the complete registry."""
        with self._lock:
            return {
                name: registration.to_dict()
                for name, registration in self._registrations.items()
}
