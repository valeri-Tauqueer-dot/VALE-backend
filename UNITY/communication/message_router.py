"""
VALE UNITY — Message Router

Version:
    0.1.0

Architecture Stage:
    UNITY_MESSAGE_ROUTER_FOUNDATION

Purpose
-------
Provides structured message routing above the Cognitive Fabric transport
layer.

Architecture:

    Sender
      ↓
    MessageRouter
      ↓
    CognitiveFabric
      ↓
    Destination

The MessageRouter is responsible for:

    - destination validation
    - message construction
    - direct message delivery
    - broadcast delivery
    - communication history
    - delivery tracking
    - route-level traceability

It does NOT:

    - determine the user's objective
    - choose the best brain for a task
    - replace HEROIC
    - replace ALPHA
    - perform verification
    - perform synthesis
    - perform reasoning
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional

from ..cognitive_fabric import CognitiveFabric, FabricMessage


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_MESSAGE_ROUTER_FOUNDATION"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MessageRouter:
    """
    Structured message-routing layer built on CognitiveFabric.

    CognitiveFabric remains responsible for lower-level communication
    transport and delivery.

    MessageRouter adds UNITY-level communication structure and traceability.
    """

    def __init__(
        self,
        fabric: CognitiveFabric,
        state: Any = None,
    ) -> None:
        if fabric is None:
            raise ValueError("CognitiveFabric is required.")

        self.fabric = fabric
        self.state = state

        self._history: List[Dict[str, Any]] = []
        self._routes: Dict[str, Dict[str, Any]] = {}

        self._counter = 0
        self._lock = RLock()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _next_id(self) -> str:
        self._counter += 1
        return f"message-route-{self._counter:06d}"

    def _record(
        self,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        record = {
            "event_type": str(event_type),
            "source": "UNITY_MESSAGE_ROUTER",
            "payload": deepcopy(payload or {}),
            "timestamp": _utc_now(),
        }

        self._history.append(record)

        if self.state is not None:
            try:
                if hasattr(self.state, "event"):
                    self.state.event(
                        event_type=event_type,
                        source="UNITY_MESSAGE_ROUTER",
                        payload=deepcopy(payload or {}),
                    )
            except Exception:
                pass

        return record

    def _validate_destination(self, destination: str) -> str:
        normalized = str(destination).strip().upper()

        if not normalized:
            raise ValueError("Destination cannot be empty.")

        return normalized

    # ------------------------------------------------------------------
    # Node registration
    # ------------------------------------------------------------------

    def register_node(
        self,
        node_name: str,
        handler: Any,
    ) -> Dict[str, Any]:
        """
        Register a communication destination with CognitiveFabric.
        """
        name = self._validate_destination(node_name)

        self.fabric.register_node(name, handler)

        self._record(
            "UNITY_MESSAGE_NODE_REGISTERED",
            {
                "node": name,
            },
        )

        return {
            "registered": True,
            "node": name,
        }

    def unregister_node(self, node_name: str) -> bool:
        name = self._validate_destination(node_name)

        result = self.fabric.unregister_node(name)

        if result:
            self._record(
                "UNITY_MESSAGE_NODE_UNREGISTERED",
                {
                    "node": name,
                },
            )

        return bool(result)

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------

    def register_route(
        self,
        source: str,
        destination: str,
        message_type: str = "COGNITIVE_MESSAGE",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Register a reusable communication route.

        This does not perform intelligent routing.
        """
        route_id = self._next_id()

        route = {
            "route_id": route_id,
            "source": str(source).strip().upper(),
            "destination": self._validate_destination(destination),
            "message_type": str(message_type).strip().upper(),
            "metadata": deepcopy(metadata or {}),
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }

        with self._lock:
            self._routes[route_id] = route

        self._record(
            "UNITY_MESSAGE_ROUTE_REGISTERED",
            route,
        )

        return route_id

    def get_route(self, route_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            route = self._routes.get(str(route_id))
            return deepcopy(route) if route is not None else None

    def routes(self) -> List[Dict[str, Any]]:
        with self._lock:
            return deepcopy(list(self._routes.values()))

    def remove_route(self, route_id: str) -> bool:
        with self._lock:
            existed = str(route_id) in self._routes

            if existed:
                route = self._routes.pop(str(route_id))

                self._record(
                    "UNITY_MESSAGE_ROUTE_REMOVED",
                    route,
                )

            return existed

    # ------------------------------------------------------------------
    # Message construction
    # ------------------------------------------------------------------

    def create_message(
        self,
        source: str,
        destination: str,
        message: Any,
        message_type: str = "COGNITIVE_MESSAGE",
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FabricMessage:
        """
        Create a FabricMessage without delivering it.
        """
        source_name = str(source).strip().upper()
        destination_name = self._validate_destination(destination)

        return self.fabric.create_message(
            source=source_name,
            destination=destination_name,
            message=message,
            message_type=str(message_type).strip().upper(),
            task_id=task_id,
            correlation_id=correlation_id,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Direct routing
    # ------------------------------------------------------------------

    def send(
        self,
        source: str,
        destination: str,
        message: Any,
        message_type: str = "COGNITIVE_MESSAGE",
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send one message to one destination.
        """
        source_name = str(source).strip().upper()
        destination_name = self._validate_destination(destination)

        fabric_message = self.create_message(
            source=source_name,
            destination=destination_name,
            message=message,
            message_type=message_type,
            task_id=task_id,
            correlation_id=correlation_id,
            metadata=metadata,
        )

        result = self.fabric.send_message(fabric_message)

        record = {
            "message_id": getattr(
                fabric_message,
                "message_id",
                None,
            ),
            "source": source_name,
            "destination": destination_name,
            "message_type": str(message_type).upper(),
            "task_id": task_id,
            "correlation_id": correlation_id,
            "delivery": deepcopy(result),
            "timestamp": _utc_now(),
        }

        with self._lock:
            self._history.append(record)

        self._record(
            "UNITY_MESSAGE_SENT",
            record,
        )

        return record

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    def broadcast(
        self,
        source: str,
        message: Any,
        destinations: Optional[List[str]] = None,
        message_type: str = "COGNITIVE_BROADCAST",
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Broadcast a message to selected destinations or all registered
        destinations.
        """
        source_name = str(source).strip().upper()

        normalized_destinations = None

        if destinations is not None:
            normalized_destinations = [
                self._validate_destination(item)
                for item in destinations
            ]

        result = self.fabric.broadcast(
            source=source_name,
            message=message,
            destinations=normalized_destinations,
            message_type=str(message_type).upper(),
            task_id=task_id,
            correlation_id=correlation_id,
            metadata=metadata,
        )

        record = {
            "source": source_name,
            "destinations": normalized_destinations,
            "message_type": str(message_type).upper(),
            "task_id": task_id,
            "correlation_id": correlation_id,
            "delivery": deepcopy(result),
            "timestamp": _utc_now(),
        }

        with self._lock:
            self._history.append(record)

        self._record(
            "UNITY_MESSAGE_BROADCAST",
            record,
        )

        return record

    # ------------------------------------------------------------------
    # Route execution
    # ------------------------------------------------------------------

    def send_via_route(
        self,
        route_id: str,
        message: Any,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        route = self.get_route(route_id)

        if route is None:
            raise KeyError(
                f"Unknown message route: {route_id}"
            )

        merged_metadata = deepcopy(route.get("metadata", {}))
        merged_metadata.update(metadata or {})

        return self.send(
            source=route["source"],
            destination=route["destination"],
            message=message,
            message_type=route["message_type"],
            task_id=task_id,
            correlation_id=correlation_id,
            metadata=merged_metadata,
        )

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return deepcopy(self._history)

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        if self.fabric is None:
            errors.append("CognitiveFabric is not configured.")

        with self._lock:
            for route_id, route in self._routes.items():
                if not route.get("source"):
                    errors.append(
                        f"{route_id}: source is missing"
                    )

                if not route.get("destination"):
                    errors.append(
                        f"{route_id}: destination is missing"
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
                "routes": len(self._routes),
                "history_records": len(self._history),
                "fabric": (
                    self.fabric.diagnostics()
                    if hasattr(self.fabric, "diagnostics")
                    else None
                ),
                "validation": self.validate(),
            }

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "routes": deepcopy(self._routes),
                "history": deepcopy(self._history),
                "diagnostics": self.diagnostics(),
  }
