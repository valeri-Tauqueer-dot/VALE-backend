from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Dict, List, Mapping, Optional
from uuid import uuid4

KERNEL_VERSION = "0.1.0"

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class KernelError(Exception):
    """Base exception for Cognitive Kernel failures."""

class InvalidStateTransition(KernelError):
    """Raised when a lifecycle transition is not permitted."""

class UnknownExecutionContext(KernelError):
    """Raised when a context ID is unknown."""

class CognitiveLifecycle(str, Enum):
    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"
    TERMINATED = "TERMINATED"

class CognitiveEventType(str, Enum):
    CONTEXT_CREATED = "CONTEXT_CREATED"
    STATE_CHANGED = "STATE_CHANGED"
    CONTEXT_PAUSED = "CONTEXT_PAUSED"
    CONTEXT_RESUMED = "CONTEXT_RESUMED"
    CONTEXT_COMPLETED = "CONTEXT_COMPLETED"
    CONTEXT_FAILED = "CONTEXT_FAILED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    CONTEXT_TERMINATED = "CONTEXT_TERMINATED"

@dataclass(frozen=True)
class CognitiveEvent:
    event_id: str
    event_type: CognitiveEventType
    context_id: str
    timestamp: datetime
    source: str
    payload: Mapping[str, Any] = field(default_factory=dict)

@dataclass
class CognitiveExecutionContext:
    context_id: str
    task_id: str
    lifecycle: CognitiveLifecycle = CognitiveLifecycle.CREATED
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    events: List[CognitiveEvent] = field(default_factory=list)

class CognitiveKernel:
    """Low-level runtime foundation for the Generation AI OS."""
    NAME = "VALE_COGNITIVE_KERNEL"
    VERSION = KERNEL_VERSION

    _ALLOWED_TRANSITIONS = {
        CognitiveLifecycle.CREATED: {CognitiveLifecycle.INITIALIZING, CognitiveLifecycle.TERMINATED},
        CognitiveLifecycle.INITIALIZING: {CognitiveLifecycle.READY, CognitiveLifecycle.FAILED, CognitiveLifecycle.TERMINATED},
        CognitiveLifecycle.READY: {CognitiveLifecycle.ACTIVE, CognitiveLifecycle.TERMINATED},
        CognitiveLifecycle.ACTIVE: {CognitiveLifecycle.PAUSED, CognitiveLifecycle.VERIFYING, CognitiveLifecycle.COMPLETED, CognitiveLifecycle.FAILED, CognitiveLifecycle.TERMINATED},
        CognitiveLifecycle.PAUSED: {CognitiveLifecycle.ACTIVE, CognitiveLifecycle.TERMINATED},
        CognitiveLifecycle.VERIFYING: {CognitiveLifecycle.ACTIVE, CognitiveLifecycle.COMPLETED, CognitiveLifecycle.FAILED},
        CognitiveLifecycle.FAILED: {CognitiveLifecycle.RECOVERING, CognitiveLifecycle.TERMINATED},
        CognitiveLifecycle.RECOVERING: {CognitiveLifecycle.READY, CognitiveLifecycle.ACTIVE, CognitiveLifecycle.FAILED, CognitiveLifecycle.TERMINATED},
        CognitiveLifecycle.COMPLETED: {CognitiveLifecycle.TERMINATED},
        CognitiveLifecycle.TERMINATED: set(),
    }

    def __init__(self) -> None:
        self._contexts: Dict[str, CognitiveExecutionContext] = {}
        self._lock = RLock()

    def create_context(self, task_id: str, metadata: Optional[Mapping[str, Any]] = None) -> CognitiveExecutionContext:
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        with self._lock:
            context = CognitiveExecutionContext(
                context_id=str(uuid4()), task_id=task_id.strip(), metadata=dict(metadata or {})
            )
            self._contexts[context.context_id] = context
            self._record_event(context, CognitiveEventType.CONTEXT_CREATED, {"task_id": context.task_id})
            return context

    def get_context(self, context_id: str) -> CognitiveExecutionContext:
        with self._lock:
            try:
                return self._contexts[context_id]
            except KeyError as exc:
                raise UnknownExecutionContext(f"Unknown cognitive context: {context_id}") from exc

    def transition(self, context_id: str, new_state: CognitiveLifecycle, *, reason: Optional[str] = None) -> CognitiveExecutionContext:
        with self._lock:
            context = self.get_context(context_id)
            old_state = context.lifecycle
            if new_state == old_state:
                raise InvalidStateTransition(f"Context {context_id} is already {old_state.value}")
            if new_state not in self._ALLOWED_TRANSITIONS.get(old_state, set()):
                raise InvalidStateTransition(f"Invalid transition: {old_state.value} -> {new_state.value}")
            context.lifecycle = new_state
            context.updated_at = utc_now()
            event_type = CognitiveEventType.STATE_CHANGED
            if new_state == CognitiveLifecycle.PAUSED:
                event_type = CognitiveEventType.CONTEXT_PAUSED
            elif new_state == CognitiveLifecycle.ACTIVE:
                event_type = CognitiveEventType.CONTEXT_RESUMED
            elif new_state == CognitiveLifecycle.COMPLETED:
                event_type = CognitiveEventType.CONTEXT_COMPLETED
            elif new_state == CognitiveLifecycle.FAILED:
                event_type = CognitiveEventType.CONTEXT_FAILED
            elif new_state == CognitiveLifecycle.RECOVERING:
                event_type = CognitiveEventType.RECOVERY_STARTED
            elif new_state == CognitiveLifecycle.TERMINATED:
                event_type = CognitiveEventType.CONTEXT_TERMINATED
            self._record_event(context, event_type, {"previous_state": old_state.value, "new_state": new_state.value, "reason": reason})
            return context

    def list_contexts(self) -> List[CognitiveExecutionContext]:
        with self._lock:
            return list(self._contexts.values())

    def status(self) -> Dict[str, Any]:
        with self._lock:
            counts: Dict[str, int] = {}
            for context in self._contexts.values():
                state = context.lifecycle.value
                counts[state] = counts.get(state, 0) + 1
            return {"name": self.NAME, "version": self.VERSION, "context_count": len(self._contexts), "contexts_by_state": counts}

    def _record_event(self, context: CognitiveExecutionContext, event_type: CognitiveEventType, payload: Optional[Mapping[str, Any]] = None) -> CognitiveEvent:
        event = CognitiveEvent(
            event_id=str(uuid4()), event_type=event_type, context_id=context.context_id,
            timestamp=utc_now(), source=self.NAME, payload=dict(payload or {})
        )
        context.events.append(event)
        return event

__all__ = [
    "KERNEL_VERSION", "KernelError", "InvalidStateTransition", "UnknownExecutionContext",
    "CognitiveLifecycle", "CognitiveEventType", "CognitiveEvent",
    "CognitiveExecutionContext", "CognitiveKernel",
]
