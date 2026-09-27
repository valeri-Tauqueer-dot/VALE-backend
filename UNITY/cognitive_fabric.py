"""
VALE UNITY — Cognitive Fabric Foundation

Purpose
-------
Provides the foundational communication and coordination fabric used by
UNITY to connect VALE brains and supporting cognitive systems.

This module is infrastructure/state-aware communication logic.

It does NOT:
- decide the user's objective
- replace HEROIC
- decide execution strategy
- replace ALPHA
- perform market intelligence
- perform human-experience intelligence
- perform verification intelligence
- perform final UNITY synthesis
- replace VALEBrainState
- replace UnityIntegrationState

Architecture
------------
UNITY
  │
  └── Cognitive Fabric
       ├── Message routing foundation
       ├── Brain-to-brain communication
       ├── Broadcast communication
       ├── Message envelopes
       ├── Communication history
       ├── Delivery tracking
       └── Fabric diagnostics

Future extensions
-----------------
Actual intelligent routing should eventually be handled by the broader
Cognitive Fabric / routing architecture rather than hard-coded here.

Version
-------
0.1.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "COGNITIVE_FABRIC_COMMUNICATION_FOUNDATION"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _normalize_brain_name(name: Any) -> str:
    """Normalize a brain/system name for fabric operations."""
    return str(name).strip().upper()


# ---------------------------------------------------------------------------
# Message Envelope
# ---------------------------------------------------------------------------

@dataclass
class FabricMessage:
    """
    Standard communication envelope moving through the Cognitive Fabric.

    The envelope separates communication metadata from the actual payload.

    This is important because VALE should be able to reason about:
    - who produced information
    - where it is going
    - why it was sent
    - what task it belongs to
    - what kind of communication it represents
    - whether delivery succeeded
    """

    source: str
    target: Optional[str]
    message_type: str
    payload: Dict[str, Any] = field(default_factory=dict)

    task_id: Optional[str] = None
    correlation_id: Optional[str] = None
    message_id: str = field(default_factory=lambda: str(uuid4()))

    priority: int = 5
    created_at: str = field(default_factory=_utc_now)

    status: str = "CREATED"

    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source = _normalize_brain_name(self.source)

        if self.target is not None:
            self.target = _normalize_brain_name(self.target)

        self.message_type = str(self.message_type).strip().upper()

        if self.correlation_id is None:
            self.correlation_id = self.message_id

        self.priority = max(0, min(int(self.priority), 10))

    def mark_sent(self) -> None:
        """Mark the message as successfully dispatched."""
        self.status = "SENT"

    def mark_delivered(self) -> None:
        """Mark the message as delivered to its target."""
        self.status = "DELIVERED"

    def mark_failed(self, reason: Optional[str] = None) -> None:
        """Mark the message as failed."""
        self.status = "FAILED"

        if reason:
            self.metadata["failure_reason"] = str(reason)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the message into a plain dictionary."""
        return {
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "task_id": self.task_id,
            "source": self.source,
            "target": self.target,
            "message_type": self.message_type,
            "payload": dict(self.payload),
            "priority": self.priority,
            "created_at": self.created_at,
            "status": self.status,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Delivery Record
# ---------------------------------------------------------------------------

@dataclass
class DeliveryRecord:
    """
    Records the lifecycle of one fabric message delivery.
    """

    message_id: str
    source: str
    target: Optional[str]

    status: str
    timestamp: str = field(default_factory=_utc_now)

    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "source": self.source,
            "target": self.target,
            "status": self.status,
            "timestamp": self.timestamp,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Cognitive Fabric
# ---------------------------------------------------------------------------

class CognitiveFabric:
    """
    Foundational communication fabric for VALE.

    The fabric provides a controlled communication layer between brains and
    supporting cognitive systems.

    It deliberately does NOT decide which brain should receive a message.
    That higher-level routing intelligence belongs to the broader VALE
    Cognitive Fabric / HEROIC / ALPHA architecture.

    This class currently provides:
        - registration
        - direct messaging
        - broadcast messaging
        - communication history
        - delivery tracking
        - handlers
        - diagnostics
    """

    FABRIC_NAME = "COGNITIVE_FABRIC"

    def __init__(self, state: Any = None) -> None:
        self.state = state

        self._lock = RLock()

        self._registered_nodes: Dict[str, Dict[str, Any]] = {}
        self._handlers: Dict[str, Any] = {}

        self._message_history: List[FabricMessage] = []
        self._delivery_history: List[DeliveryRecord] = []

        self._stats: Dict[str, int] = {
            "messages_created": 0,
            "messages_sent": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
            "broadcasts": 0,
        }

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_node(
        self,
        name: str,
        node_type: str = "BRAIN",
        metadata: Optional[Dict[str, Any]] = None,
        handler: Any = None,
    ) -> Dict[str, Any]:
        """
        Register a brain or supporting system with the fabric.

        Registration does not activate the node for a task.
        It only makes the node known to the communication layer.
        """

        normalized = _normalize_brain_name(name)

        record = {
            "name": normalized,
            "node_type": str(node_type).strip().upper(),
            "registered_at": _utc_now(),
            "active": True,
            "metadata": dict(metadata or {}),
        }

        with self._lock:
            self._registered_nodes[normalized] = record

            if handler is not None:
                self._handlers[normalized] = handler

        return dict(record)

    def unregister_node(self, name: str) -> bool:
        """Remove a node from the active communication registry."""

        normalized = _normalize_brain_name(name)

        with self._lock:
            existed = normalized in self._registered_nodes

            self._registered_nodes.pop(normalized, None)
            self._handlers.pop(normalized, None)

        return existed

    def has_node(self, name: str) -> bool:
        """Return whether a node is registered."""
        normalized = _normalize_brain_name(name)

        with self._lock:
            return normalized in self._registered_nodes

    def registered_nodes(self) -> List[str]:
        """Return registered node names."""
        with self._lock:
            return sorted(self._registered_nodes.keys())

    # ------------------------------------------------------------------
    # Handler management
    # ------------------------------------------------------------------

    def attach_handler(self, name: str, handler: Any) -> bool:
        """
        Attach a callable/object handler to an already registered node.
        """

        normalized = _normalize_brain_name(name)

        with self._lock:
            if normalized not in self._registered_nodes:
                return False

            self._handlers[normalized] = handler

        return True

    def detach_handler(self, name: str) -> bool:
        """Detach a node's communication handler."""

        normalized = _normalize_brain_name(name)

        with self._lock:
            existed = normalized in self._handlers
            self._handlers.pop(normalized, None)

        return existed

    # ------------------------------------------------------------------
    # Message construction
    # ------------------------------------------------------------------

    def create_message(
        self,
        source: str,
        target: Optional[str],
        message_type: str,
        payload: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        priority: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FabricMessage:
        """
        Create a standardized fabric message.
        """

        message = FabricMessage(
            source=source,
            target=target,
            message_type=message_type,
            payload=dict(payload or {}),
            task_id=task_id,
            correlation_id=correlation_id,
            priority=priority,
            metadata=dict(metadata or {}),
        )

        with self._lock:
            self._message_history.append(message)
            self._stats["messages_created"] += 1

        return message

    # ------------------------------------------------------------------
    # Direct messaging
    # ------------------------------------------------------------------

    def send(
        self,
        message: FabricMessage,
    ) -> DeliveryRecord:
        """
        Send one message to one registered target.

        This is transport/communication behavior, not intelligent routing.
        """

        if message.target is None:
            return self._fail_delivery(
                message,
                "Direct message requires a target.",
            )

        target = _normalize_brain_name(message.target)

        with self._lock:
            registered = target in self._registered_nodes
            handler = self._handlers.get(target)

        if not registered:
            return self._fail_delivery(
                message,
                f"Target '{target}' is not registered.",
            )

        message.mark_sent()

        with self._lock:
            self._stats["messages_sent"] += 1

        try:
            self._deliver_to_handler(handler, message)

            message.mark_delivered()

            record = DeliveryRecord(
                message_id=message.message_id,
                source=message.source,
                target=target,
                status="DELIVERED",
            )

            with self._lock:
                self._delivery_history.append(record)
                self._stats["messages_delivered"] += 1

            return record

        except Exception as exc:
            return self._fail_delivery(
                message,
                str(exc),
            )

    def send_message(
        self,
        source: str,
        target: str,
        message_type: str,
        payload: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        priority: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DeliveryRecord:
        """
        Convenience method for creating and sending one message.
        """

        message = self.create_message(
            source=source,
            target=target,
            message_type=message_type,
            payload=payload,
            task_id=task_id,
            correlation_id=correlation_id,
            priority=priority,
            metadata=metadata,
        )

        return self.send(message)

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    def broadcast(
        self,
        source: str,
        message_type: str,
        payload: Optional[Dict[str, Any]] = None,
        targets: Optional[List[str]] = None,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        priority: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DeliveryRecord]:
        """
        Broadcast one logical message to multiple registered nodes.

        Broadcast is explicit.

        The fabric does not automatically decide recipients here.
        """

        source_name = _normalize_brain_name(source)

        if targets is None:
            with self._lock:
                target_names = [
                    name
                    for name in self._registered_nodes
                    if name != source_name
                ]
        else:
            target_names = [
                _normalize_brain_name(name)
                for name in targets
                if _normalize_brain_name(name) != source_name
            ]

        with self._lock:
            self._stats["broadcasts"] += 1

        results: List[DeliveryRecord] = []

        for target in target_names:
            message = self.create_message(
                source=source_name,
                target=target,
                message_type=message_type,
                payload=payload,
                task_id=task_id,
                correlation_id=correlation_id,
                priority=priority,
                metadata={
                    **dict(metadata or {}),
                    "broadcast": True,
                },
            )

            results.append(self.send(message))

        return results

    # ------------------------------------------------------------------
    # Delivery internals
    # ------------------------------------------------------------------

    def _deliver_to_handler(
        self,
        handler: Any,
        message: FabricMessage,
    ) -> Any:
        """
        Deliver a message to the registered handler.

        Supported handler patterns:
            handler(message)
            handler.receive_message(...)
            handler.handle_message(message)
        """

        if handler is None:
            # Registration without a handler is still considered a valid
            # transport destination. The message reaches the node boundary.
            return None

        if callable(handler):
            return handler(message)

        receive_message = getattr(handler, "receive_message", None)

        if callable(receive_message):
            try:
                return receive_message(message)
            except TypeError:
                # Compatibility with VALEBrainInterface-style signatures.
                return receive_message(
                    message,
                    self.state,
                    message.source,
                    message.payload,
                )

        handle_message = getattr(handler, "handle_message", None)

        if callable(handle_message):
            return handle_message(message)

        raise TypeError(
            f"Handler for '{message.target}' does not expose a supported "
            "message interface."
        )

    def _fail_delivery(
        self,
        message: FabricMessage,
        reason: str,
    ) -> DeliveryRecord:
        """Record a failed delivery."""

        message.mark_failed(reason)

        record = DeliveryRecord(
            message_id=message.message_id,
            source=message.source,
            target=message.target,
            status="FAILED",
            error=reason,
        )

        with self._lock:
            self._delivery_history.append(record)
            self._stats["messages_failed"] += 1

        return record

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def message_history(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent message history."""

        with self._lock:
            messages = list(self._message_history)

        if limit is not None:
            messages = messages[-max(0, int(limit)):]

        return [message.to_dict() for message in messages]

    def delivery_history(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent delivery history."""

        with self._lock:
            records = list(self._delivery_history)

        if limit is not None:
            records = records[-max(0, int(limit)):]

        return [record.to_dict() for record in records]

    # ------------------------------------------------------------------
    # State integration
    # ------------------------------------------------------------------

    def publish_to_state(
        self,
        message: FabricMessage,
    ) -> None:
        """
        Publish communication metadata into shared VALE state when a
        compatible state object is available.

        This method intentionally remains lightweight.
        """

        if self.state is None:
            return

        setter = getattr(self.state, "set", None)

        if not callable(setter):
            return

        try:
            setter(
                f"cognitive_fabric.messages.{message.message_id}",
                message.to_dict(),
            )
        except Exception:
            # State publication must never destroy communication itself.
            pass

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        """Return communication-fabric diagnostics."""

        with self._lock:
            return {
                "fabric": self.FABRIC_NAME,
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "registered_nodes": sorted(
                    self._registered_nodes.keys()
                ),
                "handler_nodes": sorted(
                    self._handlers.keys()
                ),
                "message_count": len(self._message_history),
                "delivery_count": len(self._delivery_history),
                "statistics": dict(self._stats),
            }

    def clear_history(self) -> None:
        """
        Clear communication history.

        This does not unregister nodes or modify active state.
        """

        with self._lock:
            self._message_history.clear()
            self._delivery_history.clear()

            self._stats["messages_created"] = 0
            self._stats["messages_sent"] = 0
            self._stats["messages_delivered"] = 0
            self._stats["messages_failed"] = 0
            self._stats["broadcasts"] = 0

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        """
        Validate basic fabric invariants.

        This is structural validation only.
        It is not MCVL verification.
        """

        with self._lock:
            registered = list(self._registered_nodes.keys())
            handlers = list(self._handlers.keys())

        invalid_handlers = [
            name
            for name in handlers
            if name not in registered
        ]

        return {
            "valid": len(invalid_handlers) == 0,
            "registered_nodes": sorted(registered),
            "invalid_handlers": sorted(invalid_handlers),
            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
        }


__all__ = [
    "VERSION",
    "ARCHITECTURE_STAGE",
    "FabricMessage",
    "DeliveryRecord",
    "CognitiveFabric",
]
