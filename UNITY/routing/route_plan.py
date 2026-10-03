"""
VALE UNITY — Route Plan

Defines the structured route contract used by the UNITY routing layer.

A RoutePlan describes a routing decision without performing the routing
itself.

Responsibilities
----------------
- Represent one routing plan.
- Identify the source and destination.
- Record the capability being routed.
- Preserve task/correlation information.
- Track route lifecycle.
- Preserve routing rationale and metadata.
- Support validation and serialization.

This module does NOT:
- decide the user's objective
- replace HEROIC
- execute tasks
- perform communication transport
- perform MCVL verification
- perform final synthesis
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_ROUTE_PLAN_FOUNDATION"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _normalize_name(value: Any) -> str:
    """Normalize a brain/system name."""
    return str(value).strip().upper()


def _clamp_priority(value: Any) -> int:
    """Keep priority within the supported 0-10 range."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 5

    return max(0, min(value, 10))


# ---------------------------------------------------------------------------
# Route Plan
# ---------------------------------------------------------------------------

@dataclass
class RoutePlan:
    """
    Structured representation of one UNITY routing plan.

    A route is an integration instruction, not an independent intelligence
    decision.

    Example conceptual flow:

        HEROIC identifies required capability
                    ↓
        UNITY receives requirement
                    ↓
        RoutePlan describes destination
                    ↓
        RoutingEngine executes route
                    ↓
        Cognitive Fabric communicates
                    ↓
        destination brain/system works
    """

    source: str
    destination: str
    capability: str

    task_id: Optional[str] = None
    correlation_id: Optional[str] = None

    route_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    status: str = "CREATED"

    priority: int = 5

    reason: Optional[str] = None

    required_inputs: List[str] = field(default_factory=list)

    expected_outputs: List[str] = field(default_factory=list)

    dependencies: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        self.source = _normalize_name(self.source)
        self.destination = _normalize_name(self.destination)

        self.capability = str(
            self.capability
        ).strip()

        self.priority = _clamp_priority(self.priority)

        if self.correlation_id is None:
            self.correlation_id = self.route_id

        self.required_inputs = self._normalize_list(
            self.required_inputs
        )

        self.expected_outputs = self._normalize_list(
            self.expected_outputs
        )

        self.dependencies = self._normalize_list(
            self.dependencies
        )

        self.metadata = dict(self.metadata or {})

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def mark_ready(self) -> None:
        """Mark the route as ready for execution."""
        self.status = "READY"
        self._touch()

    def mark_active(self) -> None:
        """Mark the route as currently executing."""
        self.status = "ACTIVE"
        self._touch()

    def mark_completed(self) -> None:
        """Mark the route as successfully completed."""
        self.status = "COMPLETED"
        self._touch()

    def mark_failed(self, reason: Optional[str] = None) -> None:
        """Mark the route as failed."""
        self.status = "FAILED"

        if reason:
            self.metadata["failure_reason"] = str(reason)

        self._touch()

    def mark_cancelled(self, reason: Optional[str] = None) -> None:
        """Mark the route as cancelled."""
        self.status = "CANCELLED"

        if reason:
            self.metadata["cancellation_reason"] = str(reason)

        self._touch()

    def reset(self) -> None:
        """Return the route to its initial state."""
        self.status = "CREATED"
        self._touch()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def add_metadata(
        self,
        key: str,
        value: Any,
    ) -> None:
        """Add or replace route metadata."""
        self.metadata[str(key)] = value
        self._touch()

    def add_required_input(
        self,
        value: str,
    ) -> None:
        """Add a required input if it is not already present."""
        value = str(value).strip()

        if value and value not in self.required_inputs:
            self.required_inputs.append(value)
            self._touch()

    def add_expected_output(
        self,
        value: str,
    ) -> None:
        """Add an expected output if it is not already present."""
        value = str(value).strip()

        if value and value not in self.expected_outputs:
            self.expected_outputs.append(value)
            self._touch()

    def add_dependency(
        self,
        value: str,
    ) -> None:
        """Add a route dependency."""
        value = str(value).strip()

        if value and value not in self.dependencies:
            self.dependencies.append(value)
            self._touch()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        """
        Validate the structural integrity of the route.

        This does not determine whether the route is strategically correct.
        That belongs to higher-level intelligence.
        """

        errors: List[str] = []

        if not self.source:
            errors.append("Route source is required.")

        if not self.destination:
            errors.append("Route destination is required.")

        if not self.capability:
            errors.append("Route capability is required.")

        if self.source == self.destination:
            errors.append(
                "Route source and destination cannot be identical."
            )

        if not self.route_id:
            errors.append("Route ID is required.")

        if self.status not in {
            "CREATED",
            "READY",
            "ACTIVE",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        }:
            errors.append(
                f"Invalid route status: {self.status}"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "route_id": self.route_id,
            "source": self.source,
            "destination": self.destination,
            "capability": self.capability,
            "status": self.status,
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the complete route plan."""

        return {
            "route_id": self.route_id,
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,

            "source": self.source,
            "destination": self.destination,
            "capability": self.capability,

            "status": self.status,
            "priority": self.priority,

            "reason": self.reason,

            "required_inputs": list(
                self.required_inputs
            ),

            "expected_outputs": list(
                self.expected_outputs
            ),

            "dependencies": list(
                self.dependencies
            ),

            "metadata": dict(
                self.metadata
            ),

            "created_at": self.created_at,
            "updated_at": self.updated_at,

            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _touch(self) -> None:
        """Update the route modification timestamp."""
        self.updated_at = _utc_now()

    @staticmethod
    def _normalize_list(
        values: Optional[List[Any]],
    ) -> List[str]:
        """Normalize a list of route values."""

        if not values:
            return []

        result: List[str] = []

        for value in values:
            normalized = str(value).strip()

            if normalized and normalized not in result:
                result.append(normalized)

        return result


__all__ = [
    "VERSION",
    "ARCHITECTURE_STAGE",
    "RoutePlan",
  ]
