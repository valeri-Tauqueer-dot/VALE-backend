"""
VALE BRAIN STATE
================
Shared working memory for one VALE task.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class BrainContribution:
    brain: str
    kind: str
    content: Any
    confidence: float = 0.0
    importance: float = 0.5
    timestamp: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> Dict[str, Any]:
        return {"brain": self.brain, "kind": self.kind, "content": self.content,
                "confidence": self.confidence, "importance": self.importance,
                "timestamp": self.timestamp, "metadata": self.metadata}

@dataclass
class BrainEvent:
    event_type: str
    source: str
    target: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now)
    def to_dict(self) -> Dict[str, Any]:
        return {"event_type": self.event_type, "source": self.source,
                "target": self.target, "payload": self.payload,
                "timestamp": self.timestamp}

class VALEBrainState:
    def __init__(self, user_message: str = "", conversation: Optional[List[Dict[str, Any]]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.task_id = str(uuid4())
        self.created_at = utc_now()
        self.updated_at = self.created_at
        self.user_message = user_message
        self.conversation = list(conversation) if conversation else []
        self.metadata = dict(metadata) if metadata else {}
        self.shared: Dict[str, Any] = {}
        self.contributions: List[BrainContribution] = []
        self.events: List[BrainEvent] = []
        self._lock = RLock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self.shared[key] = value
            self.updated_at = utc_now()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self.shared.get(key, default)

    def delete(self, key: str) -> None:
        with self._lock:
            self.shared.pop(key, None)
            self.updated_at = utc_now()

    def snapshot_shared(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.shared)

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self.conversation.append({"role": role, "content": content,
                                      "timestamp": utc_now(), "metadata": metadata or {}})
            self.updated_at = utc_now()

    def recent_conversation(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.conversation[-limit:])

    def contribute(self, brain: str, kind: str, content: Any, confidence: float = 0.0,
                   importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> BrainContribution:
        contribution = BrainContribution(brain=brain, kind=kind, content=content,
                                         confidence=max(0.0, min(1.0, float(confidence))),
                                         importance=max(0.0, min(1.0, float(importance))),
                                         metadata=metadata or {})
        with self._lock:
            self.contributions.append(contribution)
            self.updated_at = utc_now()
        return contribution

    def contributions_from(self, brain: str) -> List[BrainContribution]:
        with self._lock:
            return [x for x in self.contributions if x.brain.upper() == brain.upper()]

    def all_contributions(self) -> List[BrainContribution]:
        with self._lock:
            return list(self.contributions)

    def event(self, event_type: str, source: str, target: Optional[str] = None,
              payload: Optional[Dict[str, Any]] = None) -> BrainEvent:
        item = BrainEvent(event_type=event_type, source=source, target=target, payload=payload or {})
        with self._lock:
            self.events.append(item)
            self.updated_at = utc_now()
        return item

    def recent_events(self, limit: int = 50) -> List[BrainEvent]:
        with self._lock:
            return list(self.events[-limit:])

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {"task_id": self.task_id, "created_at": self.created_at,
                    "updated_at": self.updated_at, "user_message": self.user_message,
                    "conversation": list(self.conversation), "metadata": dict(self.metadata),
                    "shared": dict(self.shared),
                    "contributions": [x.to_dict() for x in self.contributions],
                    "events": [x.to_dict() for x in self.events]}
