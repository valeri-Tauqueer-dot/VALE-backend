"""
VALE UNITY — Event Dispatcher

Version:
    0.1.0

Architecture Stage:
    UNITY_EVENT_DISPATCHER_FOUNDATION

Purpose
-------
Provides event publication and subscription inside the UNITY communication
layer.

Architecture:

    Brain / System
          ↓
       Event
          ↓
    EventDispatcher
       ↙   ↓   ↘
    UNITY  MCVL  Other Systems

The dispatcher is responsible for:

    - event registration
    - event publication
    - subscriber management
    - event history
    - delivery tracking
    - event filtering

It does NOT:

    - perform reasoning
    - determine objectives
    - perform verification
    - resolve contradictions
    - synthesize final responses
    - replace CognitiveFabric transport
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable, Dict, List, Optional, Set


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_EVENT_DISPATCHER_FOUNDATION"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventDispatcher:
    """
    Event publication/subscription manager.

    Subscribers may be:

        - callable functions
        - objects implementing handle_event(event)

    Events are retained for traceability.
    """

    def __init__(
        self,
        state: Any = None,
    ) -> None:
        self.state = state

        self._subscribers: Dict[str, Dict[str, Any]] = {}
        self._history: List[Dict[str, Any]] = []

        self._counter = 0
        self._lock = RLock()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _next_id(self) -> str:
        self._counter += 1
        return f"event-{self._counter:06d}"

    def _normalize_event_type(self, event_type: str) -> str:
        normalized = str(event_type).strip().upper()

        if not normalized:
            raise ValueError("event_type cannot be empty.")

        return normalized

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    def subscribe(
        self,
        event_type: str,
        handler: Any,
        subscriber_id: Optional[str] = None,
    ) -> str:
        """
        Subscribe a handler to an event type.

        Event type:

            "*"

        subscribes to all events.
        """
        normalized_type = self._normalize_event_type(event_type)

        if handler is None:
            raise ValueError("Event handler cannot be None.")

        with self._lock:
            subscription_id = (
                str(subscriber_id)
                if subscriber_id is not None
                else self._next_id()
            )

            self._subscribers.setdefault(
                normalized_type,
                {},
            )[subscription_id] = handler

            return subscription_id

    def unsubscribe(
        self,
        event_type: str,
        subscriber_id: str,
    ) -> bool:
        normalized_type = self._normalize_event_type(event_type)

        with self._lock:
            subscribers = self._subscribers.get(normalized_type)

            if not subscribers:
                return False

            existed = str(subscriber_id) in subscribers

            if existed:
                del subscribers[str(subscriber_id)]

            if not subscribers:
                self._subscribers.pop(normalized_type, None)

            return existed

    def subscribers(
        self,
        event_type: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        with self._lock:
            if event_type is not None:
                normalized_type = self._normalize_event_type(
                    event_type
                )

                return {
                    normalized_type: list(
                        self._subscribers
                        .get(normalized_type, {})
                        .keys()
                    )
                }

            return {
                event_name: list(subscribers.keys())
                for event_name, subscribers
                in self._subscribers.items()
            }

    # ------------------------------------------------------------------
    # Event creation
    # ------------------------------------------------------------------

    def create_event(
        self,
        event_type: str,
        source: str,
        payload: Optional[Dict[str, Any]] = None,
        target: Optional[str] = None,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Construct a standardized event without dispatching it.
        """
        return {
            "event_id": self._next_id(),
            "event_type": self._normalize_event_type(event_type),
            "source": str(source).strip().upper(),
            "target": (
                str(target).strip().upper()
                if target is not None
                else None
            ),
            "task_id": task_id,
            "correlation_id": correlation_id,
            "payload": deepcopy(payload or {}),
            "metadata": deepcopy(metadata or {}),
            "timestamp": _utc_now(),
        }

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def publish(
        self,
        event_type: str,
        source: str,
        payload: Optional[Dict[str, Any]] = None,
        target: Optional[str] = None,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create and dispatch an event.
        """
        event = self.create_event(
            event_type=event_type,
            source=source,
            payload=payload,
            target=target,
            task_id=task_id,
            correlation_id=correlation_id,
            metadata=metadata,
        )

        return self.dispatch(event)

    def dispatch(
        self,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Dispatch an already-created event.
        """
        if not isinstance(event, dict):
            raise TypeError("event must be a dictionary.")

        event_type = self._normalize_event_type(
            event.get("event_type", "")
        )

        normalized_event = deepcopy(event)

        if not normalized_event.get("event_id"):
            normalized_event["event_id"] = self._next_id()

        if not normalized_event.get("timestamp"):
            normalized_event["timestamp"] = _utc_now()

        with self._lock:
            handlers: Dict[str, Any] = {}

            for subscriber_id, handler in self._subscribers.get(
                event_type,
                {},
            ).items():
                handlers[subscriber_id] = handler

            for subscriber_id, handler in self._subscribers.get(
                "*",
                {},
            ).items():
                handlers[subscriber_id] = handler

        deliveries: List[Dict[str, Any]] = []

        for subscriber_id, handler in handlers.items():
            delivery = self._deliver(
                subscriber_id=subscriber_id,
                handler=handler,
                event=normalized_event,
            )

            deliveries.append(delivery)

        record = {
            "event": deepcopy(normalized_event),
            "deliveries": deliveries,
            "subscriber_count": len(handlers),
            "timestamp": _utc_now(),
        }

        with self._lock:
            self._history.append(record)

        self._publish_to_state(normalized_event, deliveries)

        return record

    # ------------------------------------------------------------------
    # Handler delivery
    # ------------------------------------------------------------------

    def _deliver(
        self,
        subscriber_id: str,
        handler: Any,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            if hasattr(handler, "handle_event"):
                result = handler.handle_event(deepcopy(event))

            elif callable(handler):
                result = handler(deepcopy(event))

            else:
                raise TypeError(
                    "Event handler must be callable or implement "
                    "handle_event()."
                )

            return {
                "subscriber_id": subscriber_id,
                "status": "DELIVERED",
                "result": deepcopy(result),
                "timestamp": _utc_now(),
            }

        except Exception as exc:
            return {
                "subscriber_id": subscriber_id,
                "status": "FAILED",
                "error": str(exc),
                "error_type": type(exc).__name__,
                "timestamp": _utc_now(),
            }

    # ------------------------------------------------------------------
    # State integration
    # ------------------------------------------------------------------

    def _publish_to_state(
        self,
        event: Dict[str, Any],
        deliveries: List[Dict[str, Any]],
    ) -> None:
        if self.state is None:
            return

        payload = {
            "event": deepcopy(event),
            "deliveries": deepcopy(deliveries),
        }

        try:
            if hasattr(self.state, "event"):
                self.state.event(
                    event_type=event["event_type"],
                    source=event.get(
                        "source",
                        "UNITY_EVENT_DISPATCHER",
                    ),
                    target=event.get("target"),
                    payload=payload,
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def history(
        self,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            history = deepcopy(self._history)

        if event_type is None:
            return history

        normalized_type = self._normalize_event_type(event_type)

        return [
            item
            for item in history
            if item.get("event", {}).get("event_type")
            == normalized_type
        ]

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def event_count(self) -> int:
        with self._lock:
            return len(self._history)

    def subscription_count(self) -> int:
        with self._lock:
            return sum(
                len(items)
                for items in self._subscribers.values()
            )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        with self._lock:
            for event_type, subscribers in self._subscribers.items():
                if not event_type:
                    errors.append(
                        "Empty event type subscription detected."
                    )

                for subscriber_id, handler in subscribers.items():
                    if not subscriber_id:
                        errors.append(
                            f"{event_type}: empty subscriber ID."
                        )

                    if handler is None:
                        errors.append(
                            f"{event_type}/{subscriber_id}: "
                            "handler is None."
                        )

        if not self._subscribers:
            warnings.append(
                "No event subscribers are currently registered."
            )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
            "event_count": self.event_count(),
            "subscription_count": self.subscription_count(),
            "subscriptions": self.subscribers(),
            "validation": self.validate(),
        }

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "subscriptions": self.subscribers(),
                "history": deepcopy(self._history),
                "diagnostics": self.diagnostics(),
      }
