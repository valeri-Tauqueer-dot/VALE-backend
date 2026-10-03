"""
VALE UNITY — Routing Policy

Defines structural routing rules used by UNITY.

RoutingPolicy does not decide the user's objective and does not replace
HEROIC or ALPHA.

Responsibilities:
- Validate whether a route is structurally acceptable.
- Enforce basic routing constraints.
- Define protected/system nodes.
- Prevent invalid destinations.
- Provide deterministic policy checks.

It does NOT:
- perform intelligent objective analysis
- select the user's required capabilities
- execute brain reasoning
- perform verification
- perform final synthesis
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

from .route_plan import RoutePlan


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_ROUTING_POLICY_FOUNDATION"


class RoutingPolicy:
    """
    Structural policy layer for UNITY routing.

    The policy is intentionally conservative.

    Higher-level systems may decide that a route is necessary, but this
    policy determines whether that proposed route satisfies basic UNITY
    routing constraints.
    """

    DEFAULT_PROTECTED_NODES = {
        "UNITY",
        "SUPERVISOR",
    }

    DEFAULT_ALLOWED_STATUSES = {
        "CREATED",
        "READY",
    }

    def __init__(
        self,
        allowed_destinations: Optional[Iterable[str]] = None,
        protected_nodes: Optional[Iterable[str]] = None,
        allow_protected_destination: bool = False,
        max_priority: int = 10,
    ) -> None:

        self.allowed_destinations: Optional[Set[str]] = None

        if allowed_destinations is not None:
            self.allowed_destinations = {
                self._normalize_name(name)
                for name in allowed_destinations
            }

        self.protected_nodes: Set[str] = {
            self._normalize_name(name)
            for name in (
                protected_nodes
                if protected_nodes is not None
                else self.DEFAULT_PROTECTED_NODES
            )
        }

        self.allow_protected_destination = bool(
            allow_protected_destination
        )

        self.max_priority = max(
            0,
            min(int(max_priority), 10),
        )

    # ------------------------------------------------------------------
    # Policy Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        route: RoutePlan,
    ) -> Dict[str, Any]:
        """
        Evaluate a route against structural routing policy.

        Returns a detailed policy result rather than raising an exception.
        """

        errors: List[str] = []
        warnings: List[str] = []

        structural = route.validate()

        if not structural["valid"]:
            errors.extend(structural["errors"])

        # --------------------------------------------------------------
        # Destination policy
        # --------------------------------------------------------------

        destination = self._normalize_name(
            route.destination
        )

        if (
            self.allowed_destinations is not None
            and destination not in self.allowed_destinations
        ):
            errors.append(
                f"Destination '{destination}' is not allowed "
                "by the current routing policy."
            )

        # --------------------------------------------------------------
        # Protected-node policy
        # --------------------------------------------------------------

        if (
            destination in self.protected_nodes
            and not self.allow_protected_destination
        ):
            errors.append(
                f"Destination '{destination}' is protected and "
                "cannot be directly routed to by this policy."
            )

        # --------------------------------------------------------------
        # Priority policy
        # --------------------------------------------------------------

        if route.priority > self.max_priority:
            errors.append(
                f"Route priority {route.priority} exceeds "
                f"policy maximum {self.max_priority}."
            )

        # --------------------------------------------------------------
        # Status policy
        # --------------------------------------------------------------

        if route.status not in self.DEFAULT_ALLOWED_STATUSES:
            errors.append(
                f"Route with status '{route.status}' is not eligible "
                "for initial routing."
            )

        # --------------------------------------------------------------
        # Warnings
        # --------------------------------------------------------------

        if not route.task_id:
            warnings.append(
                "Route has no task_id; task-level traceability is reduced."
            )

        if not route.reason:
            warnings.append(
                "Route has no explicit routing reason."
            )

        if not route.required_inputs:
            warnings.append(
                "Route declares no required inputs."
            )

        if not route.expected_outputs:
            warnings.append(
                "Route declares no expected outputs."
            )

        return {
            "allowed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "route_id": route.route_id,
            "source": route.source,
            "destination": route.destination,
            "capability": route.capability,
            "policy_version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
        }

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def allows(
        self,
        route: RoutePlan,
    ) -> bool:
        """Return True if the route passes policy."""
        return bool(
            self.evaluate(route)["allowed"]
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def add_destination(
        self,
        name: str,
    ) -> None:
        """Add a destination to the explicit allow-list."""

        normalized = self._normalize_name(name)

        if self.allowed_destinations is None:
            self.allowed_destinations = set()

        self.allowed_destinations.add(normalized)

    def remove_destination(
        self,
        name: str,
    ) -> None:
        """Remove a destination from the explicit allow-list."""

        if self.allowed_destinations is None:
            return

        self.allowed_destinations.discard(
            self._normalize_name(name)
        )

    def add_protected_node(
        self,
        name: str,
    ) -> None:
        """Mark a node as protected."""

        self.protected_nodes.add(
            self._normalize_name(name)
        )

    def remove_protected_node(
        self,
        name: str,
    ) -> None:
        """Remove a node from the protected-node set."""

        self.protected_nodes.discard(
            self._normalize_name(name)
        )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        """Return the current policy configuration."""

        return {
            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
            "allowed_destinations": (
                None
                if self.allowed_destinations is None
                else sorted(self.allowed_destinations)
            ),
            "protected_nodes": sorted(
                self.protected_nodes
            ),
            "allow_protected_destination": (
                self.allow_protected_destination
            ),
            "max_priority": self.max_priority,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_name(
        name: Any,
    ) -> str:
        return str(name).strip().upper()


__all__ = [
    "VERSION",
    "ARCHITECTURE_STAGE",
    "RoutingPolicy",
      ]
