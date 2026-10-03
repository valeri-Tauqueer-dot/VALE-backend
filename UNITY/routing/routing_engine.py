"""
VALE UNITY — Routing Engine

Executes validated RoutePlan objects through the Cognitive Fabric.

Architecture
------------
HEROIC
   ↓
required capability
   ↓
RoutePlan
   ↓
RoutingPolicy
   ↓
RoutingEngine
   ↓
CognitiveFabric
   ↓
destination brain/system

The RoutingEngine is an execution component.

It does NOT:
- replace HEROIC objective intelligence
- replace ALPHA orchestration
- invent capabilities
- perform brain reasoning
- perform MCVL verification
- perform final UNITY synthesis
"""

from __future__ import annotations

from threading import RLock
from typing import Any, Dict, Iterable, List, Optional

from ..cognitive_fabric import (
    CognitiveFabric,
    DeliveryRecord,
    FabricMessage,
)

from .route_plan import RoutePlan
from .routing_policy import RoutingPolicy


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_ROUTING_ENGINE_FOUNDATION"


class RoutingEngine:
    """
    UNITY routing execution engine.

    The engine accepts explicit routes and passes them through policy
    validation before using the Cognitive Fabric for communication.
    """

    ENGINE_NAME = "UNITY_ROUTING_ENGINE"

    def __init__(
        self,
        fabric: CognitiveFabric,
        policy: Optional[RoutingPolicy] = None,
        state: Any = None,
    ) -> None:

        if fabric is None:
            raise ValueError(
                "RoutingEngine requires a CognitiveFabric instance."
            )

        self.fabric = fabric

        self.policy = (
            policy
            if policy is not None
            else RoutingPolicy()
        )

        self.state = state

        self._lock = RLock()

        self._routes: Dict[str, RoutePlan] = {}

        self._execution_history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Route Registration
    # ------------------------------------------------------------------

    def register_route(
        self,
        route: RoutePlan,
    ) -> Dict[str, Any]:
        """
        Register a RoutePlan without executing it.
        """

        validation = route.validate()

        if not validation["valid"]:
            return {
                "registered": False,
                "route_id": route.route_id,
                "errors": validation["errors"],
            }

        with self._lock:
            self._routes[route.route_id] = route

        return {
            "registered": True,
            "route_id": route.route_id,
            "status": route.status,
        }

    # ------------------------------------------------------------------
    # Route Creation
    # ------------------------------------------------------------------

    def create_route(
        self,
        source: str,
        destination: str,
        capability: str,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        priority: int = 5,
        reason: Optional[str] = None,
        required_inputs: Optional[Iterable[str]] = None,
        expected_outputs: Optional[Iterable[str]] = None,
        dependencies: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RoutePlan:
        """
        Create and register a RoutePlan.

        This method does not automatically execute the route.
        """

        route = RoutePlan(
            source=source,
            destination=destination,
            capability=capability,
            task_id=task_id,
            correlation_id=correlation_id,
            priority=priority,
            reason=reason,
            required_inputs=list(
                required_inputs or []
            ),
            expected_outputs=list(
                expected_outputs or []
            ),
            dependencies=list(
                dependencies or []
            ),
            metadata=dict(metadata or {}),
        )

        self.register_route(route)

        return route

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        route: RoutePlan,
        payload: Optional[Dict[str, Any]] = None,
        message_type: str = "COGNITIVE_REQUEST",
    ) -> Dict[str, Any]:
        """
        Execute one explicit route.

        Flow:

            validate
                ↓
            policy evaluation
                ↓
            route activation
                ↓
            Cognitive Fabric message
                ↓
            delivery result
                ↓
            route lifecycle update
        """

        validation = route.validate()

        if not validation["valid"]:
            return self._execution_failure(
                route,
                validation["errors"],
            )

        policy_result = self.policy.evaluate(route)

        if not policy_result["allowed"]:
            return self._execution_failure(
                route,
                policy_result["errors"],
                warnings=policy_result["warnings"],
            )

        with self._lock:
            self._routes[route.route_id] = route

        route.mark_active()

        message = self.fabric.create_message(
            source=route.source,
            target=route.destination,
            message_type=message_type,
            payload=self._build_payload(
                route,
                payload,
            ),
            task_id=route.task_id,
            correlation_id=route.correlation_id,
            priority=route.priority,
            metadata={
                "route_id": route.route_id,
                "capability": route.capability,
                "routing_engine": self.ENGINE_NAME,
            },
        )

        delivery = self.fabric.send(message)

        if delivery.status == "DELIVERED":
            route.mark_completed()
        else:
            route.mark_failed(
                delivery.error or "Route delivery failed."
            )

        result = {
            "success": delivery.status == "DELIVERED",
            "route_id": route.route_id,
            "route_status": route.status,
            "message": message.to_dict(),
            "delivery": delivery.to_dict(),
            "policy": policy_result,
        }

        self._record_execution(result)

        return result

    # ------------------------------------------------------------------
    # Broadcast Execution
    # ------------------------------------------------------------------

    def execute_broadcast(
        self,
        route: RoutePlan,
        targets: Iterable[str],
        payload: Optional[Dict[str, Any]] = None,
        message_type: str = "COGNITIVE_BROADCAST",
    ) -> Dict[str, Any]:
        """
        Execute one explicit route as a broadcast.

        The caller must explicitly provide the target set.
        """

        validation = route.validate()

        if not validation["valid"]:
            return self._execution_failure(
                route,
                validation["errors"],
            )

        policy_result = self.policy.evaluate(route)

        if not policy_result["allowed"]:
            return self._execution_failure(
                route,
                policy_result["errors"],
                warnings=policy_result["warnings"],
            )

        route.mark_active()

        deliveries = self.fabric.broadcast(
            source=route.source,
            message_type=message_type,
            payload=self._build_payload(
                route,
                payload,
            ),
            targets=list(targets),
            task_id=route.task_id,
            correlation_id=route.correlation_id,
            priority=route.priority,
            metadata={
                "route_id": route.route_id,
                "capability": route.capability,
                "routing_engine": self.ENGINE_NAME,
            },
        )

        successful = [
            delivery
            for delivery in deliveries
            if delivery.status == "DELIVERED"
        ]

        if deliveries and len(successful) == len(deliveries):
            route.mark_completed()
        elif successful:
            route.mark_failed(
                "Broadcast partially delivered."
            )
        else:
            route.mark_failed(
                "Broadcast delivery failed."
            )

        result = {
            "success": (
                bool(deliveries)
                and len(successful) == len(deliveries)
            ),
            "route_id": route.route_id,
            "route_status": route.status,
            "deliveries": [
                delivery.to_dict()
                for delivery in deliveries
            ],
            "policy": policy_result,
        }

        self._record_execution(result)

        return result

    # ------------------------------------------------------------------
    # Route Lookup
    # ------------------------------------------------------------------

    def get_route(
        self,
        route_id: str,
    ) -> Optional[RoutePlan]:
        """Return a registered route."""

        with self._lock:
            return self._routes.get(
                str(route_id)
            )

    def routes(
        self,
    ) -> List[RoutePlan]:
        """Return all registered routes."""

        with self._lock:
            return list(
                self._routes.values()
            )

    def remove_route(
        self,
        route_id: str,
    ) -> bool:
        """Remove a registered route."""

        with self._lock:
            return (
                self._routes.pop(
                    str(route_id),
                    None,
                )
                is not None
            )

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def execution_history(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent route executions."""

        with self._lock:
            history = list(
                self._execution_history
            )

        if limit is not None:
            history = history[
                -max(0, int(limit)):
            ]

        return history

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        """Return routing-engine diagnostics."""

        with self._lock:
            route_count = len(
                self._routes
            )

            execution_count = len(
                self._execution_history
            )

        return {
            "engine": self.ENGINE_NAME,
            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
            "registered_routes": route_count,
            "execution_history": execution_count,
            "fabric": self.fabric.diagnostics(),
            "policy": self.policy.diagnostics(),
        }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_payload(
        route: RoutePlan,
        payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Construct the communication payload.

        Route metadata is included so the receiving system can preserve
        integration context.
        """

        return {
            "route": route.to_dict(),
            "input": dict(payload or {}),
        }

    def _execution_failure(
        self,
        route: RoutePlan,
        errors: List[str],
        warnings: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build and record a failed route execution."""

        route.mark_failed(
            "; ".join(errors)
        )

        result = {
            "success": False,
            "route_id": route.route_id,
            "route_status": route.status,
            "errors": list(errors),
            "warnings": list(
                warnings or []
            ),
        }

        self._record_execution(result)

        return result

    def _record_execution(
        self,
        result: Dict[str, Any],
    ) -> None:
        """Store route execution history."""

        with self._lock:
            self._execution_history.append(
                dict(result)
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        """Validate the routing engine and its dependencies."""

        fabric_validation = self.fabric.validate()

        return {
            "valid": bool(
                fabric_validation["valid"]
            ),
            "engine": self.ENGINE_NAME,
            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
            "fabric": fabric_validation,
            "route_count": len(
                self._routes
            ),
        }


__all__ = [
    "VERSION",
    "ARCHITECTURE_STAGE",
    "RoutingEngine",
      ]
