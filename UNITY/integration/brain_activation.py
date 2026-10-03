"""
VALE UNITY — Brain Activation Manager

The Brain Activation Manager maintains the operational activation state of
brains and supporting systems registered with UNITY.

Its responsibility is lifecycle state:

    REGISTERED
        ↓
    AVAILABLE
        ↓
    ACTIVE
        ↓
    INACTIVE / UNAVAILABLE

Activation is deliberately separated from intelligence selection.

This manager does NOT:
- decide what the user needs
- select the best brain for a task
- perform reasoning
- perform routing
- orchestrate execution
- verify outputs
- synthesize responses

HEROIC determines required intelligence.
ALPHA determines execution strategy.
Routing determines structural destinations.
UNITY integrates the resulting cognitive state.

Version: 0.1.0
Architecture Stage: UNITY_BRAIN_ACTIVATION_FOUNDATION
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional, Set


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_BRAIN_ACTIVATION_FOUNDATION"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_name(value: str) -> str:
    return str(value).strip().upper()


@dataclass
class ActivationRecord:
    """
    Operational activation record for one registered VALE system.
    """

    name: str

    active: bool = False
    available: bool = True

    status: str = "INACTIVE"

    activation_count: int = 0
    deactivation_count: int = 0

    last_activated_at: Optional[str] = None
    last_deactivated_at: Optional[str] = None

    reason: str = ""

    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        self.name = _normalize_name(self.name)
        self.status = str(self.status).strip().upper()
        self.reason = str(self.reason).strip()
        self.metadata = dict(self.metadata or {})

    def touch(self) -> None:
        self.updated_at = _utc_now()

    def activate(self, reason: str = "") -> None:
        if not self.available:
            raise RuntimeError(
                f"System '{self.name}' is unavailable and cannot be activated."
            )

        self.active = True
        self.status = "ACTIVE"
        self.activation_count += 1
        self.last_activated_at = _utc_now()
        self.reason = str(reason).strip()
        self.touch()

    def deactivate(self, reason: str = "") -> None:
        self.active = False
        self.status = "INACTIVE"
        self.deactivation_count += 1
        self.last_deactivated_at = _utc_now()
        self.reason = str(reason).strip()
        self.touch()

    def set_available(
        self,
        available: bool,
        reason: str = "",
    ) -> None:
        self.available = bool(available)

        if not self.available:
            self.active = False
            self.status = "UNAVAILABLE"
        elif self.active:
            self.status = "ACTIVE"
        else:
            self.status = "INACTIVE"

        self.reason = str(reason).strip()
        self.touch()

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        if not self.name:
            errors.append("Activation record name cannot be empty.")

        if self.active and not self.available:
            errors.append(
                "System cannot be active while unavailable."
            )

        if self.activation_count < 0:
            errors.append("Activation count cannot be negative.")

        if self.deactivation_count < 0:
            errors.append("Deactivation count cannot be negative.")

        if not self.active and self.status == "ACTIVE":
            errors.append(
                "Status ACTIVE conflicts with active=False."
            )

        if self.active and self.status != "ACTIVE":
            errors.append(
                "Active system must have status ACTIVE."
            )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "active": self.active,
            "available": self.available,
            "status": self.status,
            "activation_count": self.activation_count,
            "deactivation_count": self.deactivation_count,
            "last_activated_at": self.last_activated_at,
            "last_deactivated_at": self.last_deactivated_at,
            "reason": self.reason,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class BrainActivationManager:
    """
    Maintains activation state for registered VALE systems.

    The manager can optionally synchronize its state with a registry-like
    object. The registry is intentionally duck-typed so this class does not
    create a hard dependency on BrainRegistry internals.
    """

    def __init__(
        self,
        registry: Optional[Any] = None,
        state: Optional[Any] = None,
    ) -> None:
        self.registry = registry
        self.state = state

        self._lock = RLock()
        self._records: Dict[str, ActivationRecord] = {}

    # ------------------------------------------------------------------
    # Registration / synchronization
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        available: bool = True,
        active: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActivationRecord:
        normalized_name = _normalize_name(name)

        if not normalized_name:
            raise ValueError("System name cannot be empty.")

        with self._lock:
            if normalized_name in self._records:
                raise ValueError(
                    f"Activation record '{normalized_name}' already exists."
                )

            record = ActivationRecord(
                name=normalized_name,
                available=available,
                active=False,
                status="INACTIVE",
                metadata=metadata or {},
            )

            self._records[normalized_name] = record

            if active:
                self._activate_locked(
                    normalized_name,
                    reason="Initial activation",
                )

            self._publish(normalized_name)

            return record

    def unregister(self, name: str) -> bool:
        normalized_name = _normalize_name(name)

        with self._lock:
            if normalized_name not in self._records:
                return False

            del self._records[normalized_name]
            self._publish_all()

            return True

    def synchronize_registry(self) -> Dict[str, Any]:
        """
        Synchronize activation records with systems currently present in the
        optional BrainRegistry.
        """

        if self.registry is None:
            return {
                "synchronized": False,
                "reason": "No registry attached.",
            }

        if not hasattr(self.registry, "all"):
            return {
                "synchronized": False,
                "reason": "Attached registry does not expose all().",
            }

        created: List[str] = []
        updated: List[str] = []

        with self._lock:
            registrations = self.registry.all()

            for registration in registrations:
                name = _normalize_name(registration.name)

                if name not in self._records:
                    self._records[name] = ActivationRecord(
                        name=name,
                        available=bool(
                            getattr(registration, "available", True)
                        ),
                        active=False,
                        metadata={
                            "system_type": getattr(
                                registration,
                                "system_type",
                                "",
                            ),
                            "role": getattr(
                                registration,
                                "role",
                                "",
                            ),
                        },
                    )
                    created.append(name)
                else:
                    record = self._records[name]

                    record.set_available(
                        bool(
                            getattr(
                                registration,
                                "available",
                                True,
                            )
                        )
                    )

                    updated.append(name)

                self._publish(name)

        return {
            "synchronized": True,
            "created": sorted(created),
            "updated": sorted(set(updated)),
        }

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[ActivationRecord]:
        normalized_name = _normalize_name(name)

        with self._lock:
            return self._records.get(normalized_name)

    def require(self, name: str) -> ActivationRecord:
        record = self.get(name)

        if record is None:
            raise KeyError(
                f"Activation record '{_normalize_name(name)}' "
                "does not exist."
            )

        return record

    def has(self, name: str) -> bool:
        normalized_name = _normalize_name(name)

        with self._lock:
            return normalized_name in self._records

    # ------------------------------------------------------------------
    # Activation lifecycle
    # ------------------------------------------------------------------

    def activate(
        self,
        name: str,
        reason: str = "",
    ) -> ActivationRecord:
        normalized_name = _normalize_name(name)

        with self._lock:
            record = self._activate_locked(
                normalized_name,
                reason=reason,
            )

            self._publish(normalized_name)

            return record

    def _activate_locked(
        self,
        name: str,
        reason: str = "",
    ) -> ActivationRecord:
        record = self.require(name)

        if self.registry is not None and hasattr(self.registry, "get"):
            registration = self.registry.get(name)

            if registration is None:
                raise KeyError(
                    f"System '{name}' is not registered with the registry."
                )

            if not getattr(registration, "available", True):
                raise RuntimeError(
                    f"System '{name}' is unavailable in the registry."
                )

        record.activate(reason=reason)

        if self.registry is not None and hasattr(
            self.registry,
            "activate",
        ):
            try:
                self.registry.activate(name)
            except (KeyError, RuntimeError):
                raise

        return record

    def deactivate(
        self,
        name: str,
        reason: str = "",
    ) -> ActivationRecord:
        normalized_name = _normalize_name(name)

        with self._lock:
            record = self.require(normalized_name)

            record.deactivate(reason=reason)

            if self.registry is not None and hasattr(
                self.registry,
                "deactivate",
            ):
                self.registry.deactivate(normalized_name)

            self._publish(normalized_name)

            return record

    def set_available(
        self,
        name: str,
        available: bool,
        reason: str = "",
    ) -> ActivationRecord:
        normalized_name = _normalize_name(name)

        with self._lock:
            record = self.require(normalized_name)

            record.set_available(
                available=available,
                reason=reason,
            )

            if self.registry is not None and hasattr(
                self.registry,
                "set_available",
            ):
                self.registry.set_available(
                    normalized_name,
                    available,
                )

            self._publish(normalized_name)

            return record

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def active(self) -> List[ActivationRecord]:
        with self._lock:
            return [
                record
                for record in self._records.values()
                if record.active
            ]

    def inactive(self) -> List[ActivationRecord]:
        with self._lock:
            return [
                record
                for record in self._records.values()
                if not record.active
            ]

    def available(self) -> List[ActivationRecord]:
        with self._lock:
            return [
                record
                for record in self._records.values()
                if record.available
            ]

    def unavailable(self) -> List[ActivationRecord]:
        with self._lock:
            return [
                record
                for record in self._records.values()
                if not record.available
            ]

    def active_names(self) -> List[str]:
        return sorted(
            record.name
            for record in self.active()
        )

    def available_names(self) -> List[str]:
        return sorted(
            record.name
            for record in self.available()
        )

    def inactive_names(self) -> List[str]:
        return sorted(
            record.name
            for record in self.inactive()
        )

    # ------------------------------------------------------------------
    # State integration
    # ------------------------------------------------------------------

    def _publish(self, name: str) -> None:
        """
        Publish activation state into UnityIntegrationState when supplied.

        This method deliberately supports the existing state's generic
        set() interface rather than requiring a stronger coupling.
        """

        if self.state is None:
            return

        record = self._records.get(_normalize_name(name))

        if record is None:
            return

        payload = record.to_dict()

        try:
            if hasattr(self.state, "set"):
                self.state.set(
                    f"unity.integration.activation.{record.name}",
                    payload,
                )

                if hasattr(self.state, "event"):
                    self.state.event(
                        event_type="BRAIN_ACTIVATION_CHANGED",
                        source="UNITY",
                        target=record.name,
                        payload=payload,
                    )
        except Exception:
            # State publication must not corrupt lifecycle management.
            # Diagnostics will still expose the local activation state.
            return

    def _publish_all(self) -> None:
        for name in list(self._records.keys()):
            self._publish(name)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def names(self) -> List[str]:
        with self._lock:
            return sorted(self._records.keys())

    def records(self) -> List[ActivationRecord]:
        with self._lock:
            return list(self._records.values())

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        with self._lock:
            for name, record in self._records.items():
                result = record.validate()

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
            return {
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "registered_count": len(self._records),
                "active_count": len(self.active()),
                "inactive_count": len(self.inactive()),
                "available_count": len(self.available()),
                "unavailable_count": len(self.unavailable()),
                "active_names": self.active_names(),
                "available_names": self.available_names(),
                "validation": self.validate(),
            }

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {
                name: record.to_dict()
                for name, record in self._records.items()
  }
