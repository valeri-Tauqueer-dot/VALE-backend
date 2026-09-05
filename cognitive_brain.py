# ============================================================
# VALE SUPPORTING COGNITIVE SYSTEM
# FOUNDATION v0.1
#
# This file is designed specifically for the current VALE
# backend architecture.
#
# Current integration:
#   cognitive_brain.py
#       -> VALEBrainInterface
#       -> VALEBrainState
#       -> BrainNetwork (through the existing interface)
#       -> VALEConnector
#
# IMPORTANT:
#   This file does NOT replace UNITY, HEROIC, SUPERVISOR,
#   ALPHA, LEGEND, MARCO, FEELINGS, or AI_OS_GENERATION.
#   It is supporting cognitive infrastructure.
# ============================================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from copy import deepcopy
import inspect
import uuid

from vale_brain_interface import VALEBrainInterface
from brain_state import VALEBrainState


# ============================================================
# 1. CORE MODELS
# ============================================================

COGNITIVE_SYSTEM_NAME = "VALE SUPPORTING COGNITIVE SYSTEM"
COGNITIVE_SYSTEM_VERSION = "0.5.0"


def utc_now() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str) -> str:
    """Create a unique VALE cognitive identifier."""
    return f"{prefix}_{uuid.uuid4().hex}"


# ============================================================
# 2. COGNITIVE CONTRACTS
# ============================================================

@dataclass
class CognitiveContract:
    """
    Contract describing what a cognitive component can provide.

    The contract is descriptive and defensive. It does not give
    a component permission to perform an operation by itself.
    """

    component_id: str
    component_type: str

    capabilities: List[str] = field(default_factory=list)
    guarantees: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    input_types: List[str] = field(default_factory=list)
    output_types: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_handle(self, capability: str) -> bool:
        return capability in self.capabilities

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "capabilities": list(self.capabilities),
            "guarantees": list(self.guarantees),
            "limitations": list(self.limitations),
            "input_types": list(self.input_types),
            "output_types": list(self.output_types),
            "metadata": deepcopy(self.metadata),
        }


# ============================================================
# 3. COMMUNICATION SYSTEM
# ============================================================

@dataclass
class CognitiveMessage:

    """
    Standard internal message envelope.

    BrainNetwork remains the existing VALE brain-to-brain
    communication mechanism for now. This envelope gives the
    Supporting Cognitive System a richer, traceable format
    without breaking that existing network.
    """

    source: str
    destination: str
    message_type: str
    data: Dict[str, Any]

    task_id: str = field(default_factory=lambda: make_id("task"))
    session_id: Optional[str] = None
    priority: int = 5
    confidence: Optional[float] = None

    version: int = 1
    timestamp: str = field(default_factory=utc_now)
    message_id: str = field(default_factory=lambda: make_id("msg"))

    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        if not self.source:
            return False
        if not self.destination:
            return False
        if not self.message_type:
            return False
        if not isinstance(self.data, dict):
            return False
        if not isinstance(self.priority, int) or not 0 <= self.priority <= 10:
            return False
        if self.confidence is not None:
            if not isinstance(self.confidence, (int, float)):
                return False
            if not 0.0 <= float(self.confidence) <= 1.0:
                return False
        if self.version < 1:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "source": self.source,
            "destination": self.destination,
            "message_type": self.message_type,
            "data": deepcopy(self.data),
            "priority": self.priority,
            "confidence": self.confidence,
            "version": self.version,
            "timestamp": self.timestamp,
            "metadata": deepcopy(self.metadata),
        }


# ============================================================
# 4. EVENT BUS
# ============================================================

@dataclass
class CognitiveEvent:
    """Internal event used by the supporting cognitive system."""

    event_type: str
    source: str
    data: Dict[str, Any]

    event_id: str = field(default_factory=lambda: make_id("event"))
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "data": deepcopy(self.data),
            "timestamp": self.timestamp,
        }


class EventBus:
    """
    Lightweight in-process event bus.

    It is intentionally small in Foundation v0.1. A future
    distributed event layer can replace the implementation
    without changing the event model.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[..., Any]]] = {}

    def subscribe(
        self,
        event_type: str,
        handler: Callable[..., Any],
    ) -> None:
        if not event_type:
            raise ValueError("event_type cannot be empty.")
        if not callable(handler):
            raise TypeError("handler must be callable.")

        handlers = self._subscribers.setdefault(event_type, [])

        if handler not in handlers:
            handlers.append(handler)

    def unsubscribe(
        self,
        event_type: str,
        handler: Callable[..., Any],
    ) -> bool:
        handlers = self._subscribers.get(event_type, [])

        if handler in handlers:
            handlers.remove(handler)
            return True

        return False

    async def publish(self, event: CognitiveEvent) -> None:
        handlers = list(self._subscribers.get(event.event_type, []))

        for handler in handlers:
            result = handler(event)

            if inspect.isawaitable(result):
                await result

    def subscriber_count(self, event_type: str) -> int:
        return len(self._subscribers.get(event_type, []))


# ============================================================
# 5. COGNITIVE FABRIC
# ============================================================

class CognitiveFabric:
    """
    Supporting connective layer.

    Current responsibility:
      - component contracts
      - internal event propagation
      - cognitive message validation
      - safe access to the existing VALE task state

    It deliberately does NOT replace BrainNetwork yet.
    """

    def __init__(self):
        self.components: Dict[str, CognitiveContract] = {}
        self.events = EventBus()

    def register_contract(self, contract: CognitiveContract) -> None:
        if contract.component_id in self.components:
            raise ValueError(
                f"Cognitive component already registered: "
                f"{contract.component_id}"
            )

        self.components[contract.component_id] = contract

    def unregister_contract(self, component_id: str) -> bool:
        return self.components.pop(component_id, None) is not None

    def get_contract(
        self,
        component_id: str,
    ) -> Optional[CognitiveContract]:
        return self.components.get(component_id)

    def list_components(self) -> List[str]:
        return list(self.components.keys())

    def validate_message(self, message: CognitiveMessage) -> bool:
        return message.validate()

    async def emit(
        self,
        event_type: str,
        source: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> CognitiveEvent:
        event = CognitiveEvent(
            event_type=event_type,
            source=source,
            data=data or {},
        )

        await self.events.publish(event)
        return event


# ============================================================
# 6. SHARED COGNITIVE STATE
# ============================================================

class CognitiveStateManager:
    """
    Adapter around the EXISTING VALEBrainState.

    We do not create a second competing task-state system.

    Existing:
        VALEBrainState
        -> task_id
        -> shared
        -> contributions
        -> events
        -> conversation

    This manager adds:
        -> versioning
        -> snapshots
        -> cognitive metadata
    """

    def __init__(self, state: VALEBrainState):
        if not isinstance(state, VALEBrainState):
            raise TypeError("state must be a VALEBrainState.")

        self.state = state
        self._version = 0
        self._snapshots: List[Dict[str, Any]] = []

        self.state.set(
            "cognitive_system_version",
            COGNITIVE_SYSTEM_VERSION,
        )

        self.state.set(
            "cognitive_state_version",
            self._version,
        )

    @property
    def version(self) -> int:
        return self._version

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> int:
        self.state.set(key, deepcopy(value))
        self._version += 1

        self.state.set(
            "cognitive_state_version",
            self._version,
        )

        return self._version

    def update(self, values: Dict[str, Any]) -> int:
        if not isinstance(values, dict):
            raise TypeError("values must be a dictionary.")

        for key, value in values.items():
            self.state.set(key, deepcopy(value))

        self._version += 1

        self.state.set(
            "cognitive_state_version",
            self._version,
        )

        return self._version

    def append(self, key: str, value: Any) -> int:
        current = self.state.get(key)

        if current is None:
            current = []

        if not isinstance(current, list):
            raise TypeError(
                f"State key '{key}' must contain a list."
            )

        current.append(deepcopy(value))
        self.state.set(key, current)

        self._version += 1

        self.state.set(
            "cognitive_state_version",
            self._version,
        )

        return self._version

    def snapshot(self) -> Dict[str, Any]:
        snapshot = {
            "snapshot_id": make_id("snapshot"),
            "version": self._version,
            "timestamp": utc_now(),
            "shared_state": self.state.snapshot_shared(),
        }

        self._snapshots.append(deepcopy(snapshot))
        return snapshot

    def restore(self, snapshot: Dict[str, Any]) -> int:
        if not isinstance(snapshot, dict):
            raise TypeError("snapshot must be a dictionary.")

        shared_state = snapshot.get("shared_state")

        if not isinstance(shared_state, dict):
            raise ValueError("Invalid cognitive state snapshot.")

        current_keys = set(
            self.state.snapshot_shared().keys()
        )

        for key in current_keys:
            if key not in shared_state:
                self.state.set(key, None)

        for key, value in shared_state.items():
            self.state.set(key, deepcopy(value))

        self._version += 1

        self.state.set(
            "cognitive_state_version",
            self._version,
        )

        return self._version


# ============================================================
# 7. COGNITIVE STATE INTELLIGENCE
# ============================================================

class CognitiveStateIntelligence:
    """
    State intelligence layer for the Supporting Cognitive System.

    It tracks:
        - cognitive system identity
        - active brains
        - active capabilities
        - context
        - objective
        - hypotheses
        - uncertainties
        - decisions
    """

    STATE_KEY = "cognitive_state_intelligence"

    def __init__(
        self,
        state: VALEBrainState,
        state_manager: CognitiveStateManager,
    ):
        self.state = state
        self.state_manager = state_manager

        existing = self.state.get(
            self.STATE_KEY
        )

        if not isinstance(existing, dict):
            existing = {
                "objective": None,
                "context": {},
                "active_brains": [],
                "active_capabilities": [],
                "constraints": {},
                "facts": [],
                "hypotheses": [],
                "uncertainties": [],
                "decisions": [],
                "pending_questions": [],
                "last_update": utc_now(),
            }

            self.state_manager.set(
                self.STATE_KEY,
                existing,
            )

    def get_state(self) -> Dict[str, Any]:
        current = self.state.get(
            self.STATE_KEY,
            {},
        )

        if not isinstance(current, dict):
            current = {}

        return deepcopy(current)

    def update(
        self,
        objective: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        active_brains: Optional[List[str]] = None,
        active_capabilities: Optional[List[str]] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        current = self.get_state()

        if objective is not None:
            current["objective"] = str(objective)

        if context is not None:
            current["context"].update(
                deepcopy(context)
            )

        if active_brains is not None:
            current["active_brains"] = sorted(
                {
                    str(brain).upper()
                    for brain in active_brains
                }
            )

        if active_capabilities is not None:
            current["active_capabilities"] = sorted(
                {
                    str(capability)
                    for capability in active_capabilities
                }
            )

        if constraints is not None:
            current["constraints"] = deepcopy(
                constraints
            )

        current["last_update"] = utc_now()

        self.state_manager.set(
            self.STATE_KEY,
            current,
        )

        self.state.event(
            "cognitive_state_updated",
            "COGNITIVE",
            payload={
                "state_version": self.state_manager.version,
                "objective": current["objective"],
            },
        )

        return deepcopy(current)

    def add_fact(
        self,
        fact: Any,
        source: str = "COGNITIVE",
    ) -> Dict[str, Any]:

        current = self.get_state()

        item = {
            "fact_id": make_id("fact"),
            "content": deepcopy(fact),
            "source": str(source).upper(),
            "timestamp": utc_now(),
        }

        current["facts"].append(item)
        current["last_update"] = utc_now()

        self.state_manager.set(
            self.STATE_KEY,
            current,
        )

        return item

    def add_hypothesis(
        self,
        hypothesis: Any,
        confidence: float = 0.0,
        source: str = "COGNITIVE",
    ) -> Dict[str, Any]:

        confidence = max(
            0.0,
            min(1.0, float(confidence)),
        )

        current = self.get_state()

        item = {
            "hypothesis_id": make_id("hypothesis"),
            "content": deepcopy(hypothesis),
            "confidence": confidence,
            "source": str(source).upper(),
            "status": "ACTIVE",
            "timestamp": utc_now(),
        }

        current["hypotheses"].append(item)
        current["last_update"] = utc_now()

        self.state_manager.set(
            self.STATE_KEY,
            current,
        )

        return item

    def add_uncertainty(
        self,
        subject: Any,
        reason: str,
        severity: str = "MEDIUM",
    ) -> Dict[str, Any]:

        severity = str(severity).upper()

        allowed = {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }

        if severity not in allowed:
            severity = "MEDIUM"

        current = self.get_state()

        item = {
            "uncertainty_id": make_id("uncertainty"),
            "subject": deepcopy(subject),
            "reason": str(reason),
            "severity": severity,
            "status": "OPEN",
            "timestamp": utc_now(),
        }

        current["uncertainties"].append(item)
        current["last_update"] = utc_now()

        self.state_manager.set(
            self.STATE_KEY,
            current,
        )

        return item

    def add_decision(
        self,
        decision: Any,
        basis: Optional[List[Any]] = None,
        confidence: float = 0.0,
    ) -> Dict[str, Any]:

        confidence = max(
            0.0,
            min(1.0, float(confidence)),
        )

        current = self.get_state()

        item = {
            "decision_id": make_id("decision"),
            "decision": deepcopy(decision),
            "basis": deepcopy(basis or []),
            "confidence": confidence,
            "status": "PROPOSED",
            "timestamp": utc_now(),
        }

        current["decisions"].append(item)
        current["last_update"] = utc_now()

        self.state_manager.set(
            self.STATE_KEY,
            current,
        )

        return item

    def add_question(
        self,
        question: str,
        priority: int = 5,
    ) -> Dict[str, Any]:

        priority = max(
            0,
            min(10, int(priority)),
        )

        current = self.get_state()

        item = {
            "question_id": make_id("question"),
            "question": str(question),
            "priority": priority,
            "status": "OPEN",
            "timestamp": utc_now(),
        }

        current["pending_questions"].append(item)
        current["last_update"] = utc_now()

        self.state_manager.set(
            self.STATE_KEY,
            current,
        )

        return item

    def snapshot(self) -> Dict[str, Any]:
        snapshot = {
            "snapshot_id": make_id("cognitive_state"),
            "state_version": self.state_manager.version,
            "timestamp": utc_now(),
            "state": self.get_state(),
        }

        self.state_manager.snapshot()

        return snapshot

    def summary(self) -> Dict[str, Any]:
        current = self.get_state()

        return {
            "objective": current["objective"],
            "active_brains": list(
                current["active_brains"]
            ),
            "active_capabilities": list(
                current["active_capabilities"]
            ),
            "facts": len(current["facts"]),
            "hypotheses": len(
                current["hypotheses"]
            ),
            "open_uncertainties": len(
                [
                    item
                    for item in current["uncertainties"]
                    if item.get("status") == "OPEN"
                ]
            ),
            "proposed_decisions": len(
                [
                    item
                    for item in current["decisions"]
                    if item.get("status") == "PROPOSED"
                ]
            ),
            "pending_questions": len(
                [
                    item
                    for item in current["pending_questions"]
                    if item.get("status") == "OPEN"
                ]
            ),
            "state_version": self.state_manager.version,
            "last_update": current["last_update"],
        }


# ============================================================
# 8. MEMORY SYSTEM
# ============================================================


# ============================================================
# 8. WORKING MEMORY MANAGER v0.3
# ============================================================

class CognitiveWorkingMemory:
    """
    Task-local working memory manager.

    v0.3 upgrades the previous minimal memory list with:
        - bounded capacity
        - importance
        - relevance
        - priority
        - memory type
        - access tracking
        - promotion candidates
        - pinning
        - explicit lifecycle status

    This is NOT the permanent VALE Memory System.
    It does NOT decide what is true.
    """

    STATE_KEY = "cognitive_working_memory"
    DEFAULT_CAPACITY = 64

    def __init__(
        self,
        state: VALEBrainState,
        state_manager: CognitiveStateManager,
        observability: Optional["CognitiveObservability"] = None,
        capacity: int = DEFAULT_CAPACITY,
    ):
        self.state = state
        self.state_manager = state_manager
        self.observability = observability
        self.capacity = max(8, int(capacity))

        existing = self.state.get(self.STATE_KEY)

        if not isinstance(existing, list):
            self.state_manager.set(self.STATE_KEY, [])

    def _load(self) -> List[Dict[str, Any]]:
        value = self.state.get(self.STATE_KEY, [])

        if not isinstance(value, list):
            return []

        return deepcopy(value)

    def _save(self, memory: List[Dict[str, Any]]) -> None:
        self.state_manager.set(
            self.STATE_KEY,
            deepcopy(memory),
        )

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    def _score(self, item: Dict[str, Any]) -> float:
        importance = self._clamp(
            item.get("importance", 0.0)
        )
        relevance = self._clamp(
            item.get("relevance", 0.0)
        )

        try:
            priority = max(
                0,
                min(10, int(item.get("priority", 0))),
            ) / 10.0
        except (TypeError, ValueError):
            priority = 0.0

        try:
            access = min(
                1.0,
                max(
                    0.0,
                    float(item.get("access_count", 0)),
                ) / 10.0,
            )
        except (TypeError, ValueError):
            access = 0.0

        return (
            importance * 0.40
            + relevance * 0.35
            + priority * 0.20
            + access * 0.05
        )

    def _enforce_capacity(
        self,
        memory: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        evicted = []

        while len(memory) > self.capacity:
            candidates = [
                item
                for item in memory
                if item.get("status") == "ACTIVE"
                and not item.get("pinned", False)
            ]

            if not candidates:
                break

            victim = min(
                candidates,
                key=self._score,
            )

            memory.remove(victim)

            evicted.append({
                "memory_id": victim.get("memory_id"),
                "reason": "CAPACITY",
            })

        return evicted

    def add(
        self,
        content: Any,
        importance: float = 0.5,
        source: str = "COGNITIVE",
        relevance: float = 0.5,
        priority: int = 5,
        memory_type: str = "CONTEXT",
        metadata: Optional[Dict[str, Any]] = None,
        pinned: bool = False,
    ) -> Dict[str, Any]:

        importance = self._clamp(importance)
        relevance = self._clamp(relevance)

        try:
            priority = max(0, min(10, int(priority)))
        except (TypeError, ValueError):
            priority = 5

        item = {
            "memory_id": make_id("wm"),
            "content": deepcopy(content),
            "importance": importance,
            "relevance": relevance,
            "priority": priority,
            "source": str(source).upper(),
            "memory_type": str(memory_type).upper(),
            "status": "ACTIVE",
            "access_count": 0,
            "promotion_candidate": False,
            "pinned": bool(pinned),
            "created_at": utc_now(),
            "last_accessed_at": utc_now(),
            "metadata": deepcopy(metadata or {}),
        }

        memory = self._load()
        memory.append(item)

        evicted = self._enforce_capacity(memory)
        self._save(memory)

        if self.observability:
            self.observability.increment(
                "working_memory_additions"
            )
            self.observability.increment(
                "working_memory_evictions",
                len(evicted),
            )

        return deepcopy(item)

    def retrieve(
        self,
        limit: int = 20,
        min_relevance: float = 0.0,
        memory_type: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        try:
            limit = max(1, int(limit))
        except (TypeError, ValueError):
            limit = 20

        min_relevance = self._clamp(min_relevance)

        memory = self._load()
        candidates = []

        for item in memory:
            if item.get("status") != "ACTIVE":
                continue

            if self._clamp(
                item.get("relevance", 0.0)
            ) < min_relevance:
                continue

            if (
                memory_type is not None
                and item.get("memory_type")
                != str(memory_type).upper()
            ):
                continue

            if (
                source is not None
                and item.get("source")
                != str(source).upper()
            ):
                continue

            candidates.append(item)

        candidates.sort(
            key=self._score,
            reverse=True,
        )

        selected_ids = {
            item.get("memory_id")
            for item in candidates[:limit]
        }

        now = utc_now()

        for item in memory:
            if item.get("memory_id") in selected_ids:
                item["access_count"] = (
                    int(item.get("access_count", 0)) + 1
                )
                item["last_accessed_at"] = now

        self._save(memory)

        if self.observability:
            self.observability.increment(
                "working_memory_retrievals"
            )

        return deepcopy([
            item
            for item in memory
            if item.get("memory_id") in selected_ids
        ])

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            limit = max(1, int(limit))
        except (TypeError, ValueError):
            limit = 20

        memory = self._load()

        active = [
            item
            for item in memory
            if item.get("status") == "ACTIVE"
        ]

        return deepcopy(active[-limit:])

    def get(
        self,
        memory_id: str,
    ) -> Optional[Dict[str, Any]]:

        for item in self._load():
            if item.get("memory_id") == memory_id:
                return deepcopy(item)

        return None

    def update(
        self,
        memory_id: str,
        *,
        importance: Optional[float] = None,
        relevance: Optional[float] = None,
        priority: Optional[int] = None,
        status: Optional[str] = None,
        promotion_candidate: Optional[bool] = None,
        pinned: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:

        memory = self._load()

        for item in memory:
            if item.get("memory_id") != memory_id:
                continue

            if importance is not None:
                item["importance"] = self._clamp(
                    importance
                )

            if relevance is not None:
                item["relevance"] = self._clamp(
                    relevance
                )

            if priority is not None:
                try:
                    item["priority"] = max(
                        0,
                        min(10, int(priority)),
                    )
                except (TypeError, ValueError):
                    pass

            if status is not None:
                item["status"] = str(status).upper()

            if promotion_candidate is not None:
                item["promotion_candidate"] = bool(
                    promotion_candidate
                )

            if pinned is not None:
                item["pinned"] = bool(pinned)

            if metadata is not None:
                if not isinstance(item.get("metadata"), dict):
                    item["metadata"] = {}

                item["metadata"].update(
                    deepcopy(metadata)
                )

            self._save(memory)
            return deepcopy(item)

        return None

    def mark_promotion_candidate(
        self,
        memory_id: str,
        value: bool = True,
    ) -> Optional[Dict[str, Any]]:

        return self.update(
            memory_id,
            promotion_candidate=value,
        )

    def promote_candidates(self) -> List[Dict[str, Any]]:
        return deepcopy([
            item
            for item in self._load()
            if (
                item.get("status") == "ACTIVE"
                and item.get("promotion_candidate") is True
            )
        ])

    def remove(self, memory_id: str) -> bool:
        memory = self._load()

        for item in memory:
            if item.get("memory_id") == memory_id:
                item["status"] = "REMOVED"
                self._save(memory)
                return True

        return False

    def clear(self) -> None:
        self._save([])

    def stats(self) -> Dict[str, Any]:
        memory = self._load()

        active = [
            item
            for item in memory
            if item.get("status") == "ACTIVE"
        ]

        pinned = [
            item
            for item in active
            if item.get("pinned") is True
        ]

        promotions = [
            item
            for item in active
            if item.get("promotion_candidate") is True
        ]

        return {
            "capacity": self.capacity,
            "total_items": len(memory),
            "active_items": len(active),
            "pinned_items": len(pinned),
            "promotion_candidates": len(promotions),
            "utilization": (
                len(active) / self.capacity
                if self.capacity
                else 0.0
            ),
        }


# Backward-compatible public name.
CognitiveMemoryFoundation = CognitiveWorkingMemory


# ============================================================
# 9. COGNITIVE ATTENTION / FOCUS ENGINE
# ============================================================

class CognitiveAttentionFocus:
    """
    Attention prioritization infrastructure.

    It ranks information for the workspace. It does NOT reason,
    make decisions, or determine truth.
    """

    STATE_KEY = "cognitive_attention_focus"

    def __init__(
        self,
        state: VALEBrainState,
        state_manager: CognitiveStateManager,
        observability: Optional["CognitiveObservability"] = None,
    ):
        self.state = state
        self.state_manager = state_manager
        self.observability = observability

        existing = self.state.get(self.STATE_KEY)

        if not isinstance(existing, dict):
            self.state_manager.set(
                self.STATE_KEY,
                {
                    "focus_target": None,
                    "focus_items": [],
                    "last_refresh": utc_now(),
                },
            )

    def _load(self) -> Dict[str, Any]:
        current = self.state.get(
            self.STATE_KEY,
            {},
        )

        if not isinstance(current, dict):
            return {
                "focus_target": None,
                "focus_items": [],
                "last_refresh": utc_now(),
            }

        return deepcopy(current)

    def _save(self, value: Dict[str, Any]) -> None:
        self.state_manager.set(
            self.STATE_KEY,
            deepcopy(value),
        )

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    def score(self, item: Dict[str, Any]) -> float:
        importance = self._clamp(
            item.get("importance", 0.0)
        )
        relevance = self._clamp(
            item.get("relevance", 0.0)
        )

        try:
            priority = max(
                0,
                min(10, int(item.get("priority", 0))),
            ) / 10.0
        except (TypeError, ValueError):
            priority = 0.0

        return max(
            0.0,
            min(
                1.0,
                importance * 0.45
                + relevance * 0.40
                + priority * 0.15,
            ),
        )

    def refresh(
        self,
        items: List[Dict[str, Any]],
        focus_target: Optional[str] = None,
        limit: int = 12,
    ) -> Dict[str, Any]:

        try:
            limit = max(1, int(limit))
        except (TypeError, ValueError):
            limit = 12

        ranked = []

        for item in items:
            candidate = deepcopy(item)
            candidate["focus_score"] = self.score(
                candidate
            )
            ranked.append(candidate)

        ranked.sort(
            key=lambda item: item.get(
                "focus_score",
                0.0,
            ),
            reverse=True,
        )

        current = self._load()

        if focus_target is not None:
            current["focus_target"] = str(
                focus_target
            )

        current["focus_items"] = ranked[:limit]
        current["last_refresh"] = utc_now()

        self._save(current)

        if self.observability:
            self.observability.increment(
                "attention_refreshes"
            )

        return deepcopy(current)

    def get_focus(
        self,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:

        try:
            limit = max(1, int(limit))
        except (TypeError, ValueError):
            limit = 12

        current = self._load()
        items = current.get("focus_items", [])

        if not isinstance(items, list):
            return []

        return deepcopy(items[:limit])

    def set_target(
        self,
        target: Optional[str],
    ) -> Dict[str, Any]:

        current = self._load()
        current["focus_target"] = (
            str(target)
            if target is not None
            else None
        )
        current["last_refresh"] = utc_now()

        self._save(current)
        return deepcopy(current)

    def clear(self) -> None:
        self._save({
            "focus_target": None,
            "focus_items": [],
            "last_refresh": utc_now(),
        })


# ============================================================
# 10. COGNITIVE WORKSPACE
# ============================================================

class CognitiveWorkspace:
    """
    Bounded active workspace for the current cognitive task.

    The workspace exposes relevant current context to downstream
    cognition. It is not a reasoning engine or decision maker.
    """

    STATE_KEY = "cognitive_workspace"

    def __init__(
        self,
        state: VALEBrainState,
        state_manager: CognitiveStateManager,
        working_memory: CognitiveWorkingMemory,
        attention: CognitiveAttentionFocus,
        observability: Optional["CognitiveObservability"] = None,
    ):
        self.state = state
        self.state_manager = state_manager
        self.working_memory = working_memory
        self.attention = attention
        self.observability = observability

        existing = self.state.get(self.STATE_KEY)

        if not isinstance(existing, dict):
            self.state_manager.set(
                self.STATE_KEY,
                self._empty(),
            )

    def _empty(self) -> Dict[str, Any]:
        return {
            "workspace_id": make_id("workspace"),
            "objective": None,
            "context": {},
            "constraints": {},
            "focus_target": None,
            "focus_items": [],
            "active_facts": [],
            "active_hypotheses": [],
            "active_uncertainties": [],
            "active_decisions": [],
            "pending_questions": [],
            "selected_memories": [],
            "workspace_status": "READY",
            "last_refresh": utc_now(),
        }

    def _load(self) -> Dict[str, Any]:
        current = self.state.get(
            self.STATE_KEY,
            {},
        )

        if not isinstance(current, dict):
            return self._empty()

        return deepcopy(current)

    def _save(self, workspace: Dict[str, Any]) -> None:
        self.state_manager.set(
            self.STATE_KEY,
            deepcopy(workspace),
        )

    def initialize(
        self,
        state_intelligence: CognitiveStateIntelligence,
        focus_target: Optional[str] = None,
    ) -> Dict[str, Any]:

        cognitive_state = state_intelligence.get_state()
        workspace = self._load()

        workspace["objective"] = cognitive_state.get(
            "objective"
        )
        workspace["context"] = deepcopy(
            cognitive_state.get("context", {})
        )
        workspace["constraints"] = deepcopy(
            cognitive_state.get("constraints", {})
        )

        if focus_target is not None:
            workspace["focus_target"] = str(
                focus_target
            )

        workspace["workspace_status"] = "ACTIVE"
        workspace["last_refresh"] = utc_now()

        self._save(workspace)

        return self.refresh()

    def refresh(self) -> Dict[str, Any]:
        workspace = self._load()

        cognitive_state = self.state.get(
            CognitiveStateIntelligence.STATE_KEY,
            {},
        )

        if not isinstance(cognitive_state, dict):
            cognitive_state = {}

        workspace["objective"] = cognitive_state.get(
            "objective"
        )
        workspace["context"] = deepcopy(
            cognitive_state.get("context", {})
        )
        workspace["constraints"] = deepcopy(
            cognitive_state.get("constraints", {})
        )

        facts = cognitive_state.get("facts", [])
        hypotheses = cognitive_state.get(
            "hypotheses",
            [],
        )
        uncertainties = cognitive_state.get(
            "uncertainties",
            [],
        )
        decisions = cognitive_state.get(
            "decisions",
            [],
        )
        questions = cognitive_state.get(
            "pending_questions",
            [],
        )

        workspace["active_facts"] = deepcopy(
            facts[-20:] if isinstance(facts, list)
            else []
        )

        workspace["active_hypotheses"] = deepcopy(
            hypotheses[-20:] if isinstance(hypotheses, list)
            else []
        )

        workspace["active_uncertainties"] = deepcopy([
            item
            for item in uncertainties
            if isinstance(item, dict)
            and item.get("status") == "OPEN"
        ][-20:] if isinstance(uncertainties, list) else [])

        workspace["active_decisions"] = deepcopy([
            item
            for item in decisions
            if isinstance(item, dict)
            and item.get("status") == "PROPOSED"
        ][-20:] if isinstance(decisions, list) else [])

        workspace["pending_questions"] = deepcopy([
            item
            for item in questions
            if isinstance(item, dict)
            and item.get("status") == "OPEN"
        ][-20:] if isinstance(questions, list) else [])

        selected = self.working_memory.retrieve(
            limit=20
        )

        workspace["selected_memories"] = selected

        attention_state = self.attention.refresh(
            selected,
            focus_target=workspace.get(
                "focus_target"
            ),
            limit=12,
        )

        workspace["focus_items"] = deepcopy(
            attention_state.get(
                "focus_items",
                [],
            )
        )

        workspace["workspace_status"] = "ACTIVE"
        workspace["last_refresh"] = utc_now()

        self._save(workspace)

        if self.observability:
            self.observability.increment(
                "workspace_refreshes"
            )

        return deepcopy(workspace)

    def set_focus_target(
        self,
        target: Optional[str],
    ) -> Dict[str, Any]:

        self.attention.set_target(target)

        workspace = self._load()
        workspace["focus_target"] = (
            str(target)
            if target is not None
            else None
        )

        self._save(workspace)

        return self.refresh()

    def get(self) -> Dict[str, Any]:
        return self._load()

    def summary(self) -> Dict[str, Any]:
        workspace = self._load()

        return {
            "workspace_id": workspace.get(
                "workspace_id"
            ),
            "objective": workspace.get(
                "objective"
            ),
            "workspace_status": workspace.get(
                "workspace_status"
            ),
            "focus_target": workspace.get(
                "focus_target"
            ),
            "focus_items": len(
                workspace.get(
                    "focus_items",
                    [],
                )
            ),
            "selected_memories": len(
                workspace.get(
                    "selected_memories",
                    [],
                )
            ),
            "active_facts": len(
                workspace.get(
                    "active_facts",
                    [],
                )
            ),
            "active_hypotheses": len(
                workspace.get(
                    "active_hypotheses",
                    [],
                )
            ),
            "active_uncertainties": len(
                workspace.get(
                    "active_uncertainties",
                    [],
                )
            ),
            "active_decisions": len(
                workspace.get(
                    "active_decisions",
                    [],
                )
            ),
            "pending_questions": len(
                workspace.get(
                    "pending_questions",
                    [],
                )
            ),
            "last_refresh": workspace.get(
                "last_refresh"
            ),
        }

    def clear(self) -> None:
        self._save(self._empty())
class CognitiveKnowledgeFoundation:
    """
    Foundation registry for knowledge claims.

    Full evidence/provenance/epistemic-state architecture will
    be added in later versions.
    """

    def __init__(self, state: VALEBrainState):
        self.state = state

        if self.state.get(
            "cognitive_knowledge_claims"
        ) is None:
            self.state.set(
                "cognitive_knowledge_claims",
                [],
            )

    def add_claim(
        self,
        claim: str,
        status: str = "UNKNOWN",
        confidence: float = 0.0,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:

        confidence = max(
            0.0,
            min(1.0, float(confidence)),
        )

        item = {
            "claim_id": make_id("claim"),
            "claim": str(claim),
            "epistemic_status": str(status).upper(),
            "confidence": confidence,
            "source": source,
            "timestamp": utc_now(),
        }

        claims = self.state.get(
            "cognitive_knowledge_claims",
            [],
        )

        if not isinstance(claims, list):
            claims = []

        claims.append(item)

        self.state.set(
            "cognitive_knowledge_claims",
            claims,
        )

        return item

    def claims(self) -> List[Dict[str, Any]]:
        return deepcopy(
            self.state.get(
                "cognitive_knowledge_claims",
                [],
            )
        )


# ============================================================
# 10. REASONING INFRASTRUCTURE
# ============================================================

class CognitiveReasoningFoundation:
    """
    Foundation metadata for reasoning work.

    No artificial 'intelligence' is claimed here.
    Actual reasoning engines will be built after the
    cognitive substrate is stable.
    """

    def __init__(self, state: VALEBrainState):
        self.state = state

    def start_reasoning_cycle(
        self,
        objective: str,
    ) -> Dict[str, Any]:

        cycle = {
            "cycle_id": make_id("reasoning"),
            "objective": str(objective),
            "status": "STARTED",
            "timestamp": utc_now(),
        }

        self.state.set(
            "active_reasoning_cycle",
            cycle,
        )

        self.state.event(
            "cognitive_reasoning_started",
            "COGNITIVE",
            payload=cycle,
        )

        return cycle


# ============================================================
# 11. MCVL
# ============================================================

class CognitiveMCVLFoundation:
    """
    Foundation interface for MCVL.

    It does not approve arbitrary conclusions yet.
    It records verification requests for the future
    verification/evaluation layer.
    """

    VALID_STATUSES = {
        "VALID",
        "INVALID",
        "UNCERTAIN",
        "INSUFFICIENT_INFORMATION",
        "PENDING",
    }

    def __init__(self, state: VALEBrainState):
        self.state = state

    def request_verification(
        self,
        claim: Any,
        evidence: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:

        request = {
            "verification_id": make_id("verify"),
            "claim": deepcopy(claim),
            "evidence": deepcopy(evidence or []),
            "status": "PENDING",
            "timestamp": utc_now(),
        }

        requests = self.state.get(
            "mcvl_requests",
            [],
        )

        if not isinstance(requests, list):
            requests = []

        requests.append(request)

        self.state.set(
            "mcvl_requests",
            requests,
        )

        return request


# ============================================================
# 12. SAFETY
# ============================================================

class CognitiveSafetyFoundation:
    """
    Basic safety gate for the Supporting Cognitive System.

    It is intentionally conservative and does not make trading
    decisions or override the Supervisor/UNITY architecture.
    """

    def __init__(self):
        self.enabled = True

    def validate_message(
        self,
        message: CognitiveMessage,
    ) -> Dict[str, Any]:

        valid = message.validate()

        return {
            "allowed": bool(valid),
            "reason": "VALID_MESSAGE"
            if valid
            else "INVALID_COGNITIVE_MESSAGE",
        }


# ============================================================
# 13. EVOLUTION
# ============================================================

class CognitiveEvolutionFoundation:
    """
    Foundation for future controlled learning.

    No automatic self-modification occurs here.
    """

    def __init__(self, state: VALEBrainState):
        self.state = state

    def create_learning_candidate(
        self,
        observation: Any,
        reason: str,
    ) -> Dict[str, Any]:

        candidate = {
            "candidate_id": make_id("learning"),
            "observation": deepcopy(observation),
            "reason": str(reason),
            "status": "CANDIDATE",
            "requires_validation": True,
            "timestamp": utc_now(),
        }

        candidates = self.state.get(
            "learning_candidates",
            [],
        )

        if not isinstance(candidates, list):
            candidates = []

        candidates.append(candidate)

        self.state.set(
            "learning_candidates",
            candidates,
        )

        return candidate


# ============================================================
# 14. OBSERVABILITY
# ============================================================

class CognitiveObservability:
    """
    Runtime health/telemetry foundation.
    """

    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "events_emitted": 0,
            "messages_validated": 0,
            "verification_requests": 0,
            "learning_candidates": 0,
        }

    def increment(
        self,
        metric: str,
        amount: int = 1,
    ) -> None:

        self.metrics[metric] = (
            int(self.metrics.get(metric, 0)) + amount
        )

    def export(self) -> Dict[str, Any]:
        return deepcopy(self.metrics)


# ============================================================
# 15. ADVANCED COGNITIVE INFRASTRUCTURE
# ============================================================


# ============================================================
# 15. ADVANCED COGNITIVE INFRASTRUCTURE
# ============================================================



# ============================================================
# v0.4-v0.5 COGNITIVE INTELLIGENCE LAYERS
# ============================================================

class CognitiveTemporalIntelligence:
    """Task-local timeline and change tracker; does not infer causality by itself."""
    def __init__(self, state: VALEBrainState):
        self.state = state
        self.events = []
        self.previous = {}

    def record(self, subject: str, value: Any, source: str = "unknown", valid_from: Optional[str] = None) -> Dict[str, Any]:
        event = {"event_id": make_id("time"), "subject": subject, "value": deepcopy(value), "source": source,
                 "timestamp": utc_now(), "valid_from": valid_from or utc_now(), "sequence": len(self.events)+1}
        if subject in self.previous:
            event["previous_value"] = deepcopy(self.previous[subject])
            event["changed"] = self.previous[subject] != value
        else:
            event["previous_value"] = None
            event["changed"] = True
        self.previous[subject] = deepcopy(value); self.events.append(event)
        return deepcopy(event)

    def history(self, subject: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        rows = [e for e in self.events if subject is None or e["subject"] == subject]
        return deepcopy(rows[-max(1, limit):])

    def summary(self):
        return {"event_count": len(self.events), "tracked_subjects": len(self.previous)}


class CognitiveProvenanceGraph:
    """Records evidence/source lineage for cognitive objects."""
    def __init__(self): self.nodes = {}; self.edges = []
    def add_node(self, node_id: str, node_type: str, data: Optional[Dict[str, Any]] = None):
        self.nodes[node_id] = {"node_id": node_id, "node_type": node_type, "data": deepcopy(data or {}), "created_at": utc_now()}
        return deepcopy(self.nodes[node_id])
    def link(self, source_id: str, target_id: str, relation: str, confidence: Optional[float] = None):
        edge={"edge_id":make_id("edge"),"source":source_id,"target":target_id,"relation":relation,"confidence":confidence,"created_at":utc_now()}
        self.edges.append(edge); return deepcopy(edge)
    def lineage(self, node_id: str, depth: int = 5):
        found=[]; frontier={node_id}
        for _ in range(max(0, depth)):
            parents={e["source"] for e in self.edges if e["target"] in frontier}
            found.extend([deepcopy(e) for e in self.edges if e["target"] in frontier])
            frontier=parents-set(frontier)
            if not frontier: break
        return found
    def summary(self): return {"nodes":len(self.nodes),"edges":len(self.edges)}


class CognitiveDependencyGraph:
    """Tracks which cognitive objects depend on which other objects."""
    def __init__(self): self.dependencies = {}
    def add_dependency(self, dependent: str, dependency: str, relation: str = "depends_on"):
        self.dependencies.setdefault(dependent, []).append({"dependency":dependency,"relation":relation,"created_at":utc_now()})
    def affected(self, changed_id: str) -> List[str]:
        return [k for k,v in self.dependencies.items() if any(x["dependency"] == changed_id for x in v)]
    def summary(self): return {"dependents":len(self.dependencies),"links":sum(len(v) for v in self.dependencies.values())}


class CognitiveUncertaintyMap:
    """Explicit epistemic labels; confidence is metadata, never truth."""
    LEVELS = {"KNOWN", "SUPPORTED", "PROBABLE", "UNCERTAIN", "CONTRADICTED", "UNKNOWN", "INSUFFICIENT_INFORMATION"}
    def __init__(self): self.items={}
    def set(self, item_id: str, status: str, confidence: Optional[float] = None, reasons: Optional[List[str]] = None):
        status=status.upper()
        if status not in self.LEVELS: status="UNCERTAIN"
        self.items[item_id]={"item_id":item_id,"status":status,"confidence":confidence,"reasons":list(reasons or []),"updated_at":utc_now()}
        return deepcopy(self.items[item_id])
    def get(self, item_id: str): return deepcopy(self.items.get(item_id))
    def summary(self):
        counts={k:0 for k in self.LEVELS}
        for x in self.items.values(): counts[x["status"]]=counts.get(x["status"],0)+1
        return {"items":len(self.items),"status_counts":counts}


class CognitiveHypothesisManager:
    """Maintains competing hypotheses without automatically selecting truth."""
    def __init__(self): self.hypotheses={}
    def create(self, statement: str, evidence: Optional[List[str]]=None, confidence: Optional[float]=None, assumptions: Optional[List[str]]=None):
        hid=make_id("hyp")
        self.hypotheses[hid]={"hypothesis_id":hid,"statement":statement,"supporting_evidence":list(evidence or []),"contradicting_evidence":[],"assumptions":list(assumptions or []),"confidence":confidence,"status":"ACTIVE","created_at":utc_now(),"updated_at":utc_now()}
        return deepcopy(self.hypotheses[hid])
    def add_evidence(self, hypothesis_id: str, evidence_id: str, supports: bool=True):
        h=self.hypotheses.get(hypothesis_id)
        if not h: return None
        key="supporting_evidence" if supports else "contradicting_evidence"
        if evidence_id not in h[key]: h[key].append(evidence_id)
        h["updated_at"]=utc_now(); return deepcopy(h)
    def update(self, hypothesis_id: str, **fields):
        h=self.hypotheses.get(hypothesis_id)
        if not h: return None
        for k,v in fields.items():
            if k in h and k not in {"hypothesis_id","created_at"}: h[k]=deepcopy(v)
        h["updated_at"]=utc_now(); return deepcopy(h)
    def list(self): return deepcopy(list(self.hypotheses.values()))


class CognitiveCausalModelEngine:
    """Stores causal hypotheses and mechanisms; does not claim causality is proven."""
    def __init__(self): self.relations=[]
    def add_relation(self, cause: str, effect: str, mechanism: Optional[str]=None, status: str="HYPOTHESIZED", evidence: Optional[List[str]]=None):
        row={"relation_id":make_id("cause"),"cause":cause,"effect":effect,"mechanism":mechanism,"status":status,"evidence":list(evidence or []),"created_at":utc_now()}
        self.relations.append(row); return deepcopy(row)
    def related_to(self, node: str): return deepcopy([r for r in self.relations if r["cause"]==node or r["effect"]==node])
    def summary(self): return {"relations":len(self.relations)}


class CognitiveCounterfactualEngine:
    """Stores explicit what-if scenarios; it does not pretend simulation equals reality."""
    def __init__(self): self.scenarios=[]
    def create(self, baseline: str, intervention: str, predicted_outcome: Optional[str]=None, confidence: Optional[float]=None):
        row={"scenario_id":make_id("cf"),"baseline":baseline,"intervention":intervention,"predicted_outcome":predicted_outcome,"confidence":confidence,"status":"HYPOTHETICAL","created_at":utc_now()}
        self.scenarios.append(row); return deepcopy(row)
    def summary(self): return {"scenarios":len(self.scenarios)}


class CognitiveMultiHorizonReasoning:
    """Keeps conclusions separated by time horizon."""
    HORIZONS=("NOW","SHORT_TERM","MEDIUM_TERM","LONG_TERM")
    def __init__(self): self.items=[]
    def add(self, horizon: str, conclusion: str, confidence: Optional[float]=None, evidence: Optional[List[str]]=None):
        h=horizon.upper()
        if h not in self.HORIZONS: h="MEDIUM_TERM"
        row={"item_id":make_id("horizon"),"horizon":h,"conclusion":conclusion,"confidence":confidence,"evidence":list(evidence or []),"created_at":utc_now()}
        self.items.append(row); return deepcopy(row)
    def get(self, horizon: Optional[str]=None): return deepcopy([x for x in self.items if horizon is None or x["horizon"]==horizon.upper()])
    def summary(self): return {h:len(self.get(h)) for h in self.HORIZONS}


class CognitiveBeliefState:
    """Versioned belief records with reasons and revision history."""
    def __init__(self): self.beliefs={}; self.history=[]
    def set(self, proposition: str, status: str, confidence: Optional[float]=None, reasons: Optional[List[str]]=None):
        bid=make_id("belief")
        row={"belief_id":bid,"proposition":proposition,"status":status,"confidence":confidence,"reasons":list(reasons or []),"updated_at":utc_now()}
        old=self.beliefs.get(proposition)
        if old: self.history.append({"previous":deepcopy(old),"replaced_at":utc_now()})
        self.beliefs[proposition]=row; return deepcopy(row)
    def get(self, proposition: Optional[str]=None): return deepcopy(self.beliefs.get(proposition)) if proposition else deepcopy(list(self.beliefs.values()))
    def summary(self): return {"beliefs":len(self.beliefs),"revisions":len(self.history)}


class CognitiveInfrastructureRegistry:
    """
    Central registry for the Supporting Cognitive System.

    v0.3 integrates:
        - Cognitive State Intelligence
        - Working Memory Manager
        - Attention / Focus
        - Cognitive Workspace

    Future engines remain explicitly unimplemented until their
    architecture is designed and validated.
    """

    def __init__(self, state: VALEBrainState):

        self.state = state

        self.fabric = CognitiveFabric()
        self.router = CognitiveRouter()

        self.state_manager = CognitiveStateManager(state)

        self.observability = CognitiveObservability()

        self.state_intelligence = CognitiveStateIntelligence(
            state,
            self.state_manager,
        )

        self.memory = CognitiveWorkingMemory(
            state,
            self.state_manager,
            self.observability,
        )

        self.attention = CognitiveAttentionFocus(
            state,
            self.state_manager,
            self.observability,
        )

        self.workspace = CognitiveWorkspace(
            state, self.state_manager, self.memory, self.attention, self.observability,
        )

        self.temporal = CognitiveTemporalIntelligence(state)
        self.provenance = CognitiveProvenanceGraph()
        self.dependencies = CognitiveDependencyGraph()
        self.uncertainty_map = CognitiveUncertaintyMap()
        self.hypotheses = CognitiveHypothesisManager()
        self.causal = CognitiveCausalModelEngine()
        self.counterfactual = CognitiveCounterfactualEngine()
        self.multi_horizon = CognitiveMultiHorizonReasoning()
        self.beliefs = CognitiveBeliefState()

        self.knowledge = CognitiveKnowledgeFoundation(
            state
        )
        self.reasoning = CognitiveReasoningFoundation(
            state
        )
        self.mcvl = CognitiveMCVLFoundation(state)

        self.safety = CognitiveSafetyFoundation()
        self.evolution = CognitiveEvolutionFoundation(
            state
        )

        self._register_core_contracts()

    def _register_core_contracts(self) -> None:

        contracts = [
            CognitiveContract(
                component_id="COGNITIVE_FABRIC",
                component_type="supporting_infrastructure",
                capabilities=[
                    "event_propagation",
                    "contract_registry",
                    "message_validation",
                ],
                limitations=[
                    "not_a_reasoning_brain",
                    "not_a_decision_brain",
                ],
            ),
            CognitiveContract(
                component_id="COGNITIVE_STATE",
                component_type="supporting_infrastructure",
                capabilities=[
                    "state_management",
                    "state_versioning",
                    "state_snapshot",
                    "state_restore",
                ],
                limitations=[
                    "task_local_foundation",
                ],
            ),
            CognitiveContract(
                component_id="COGNITIVE_STATE_INTELLIGENCE",
                component_type="supporting_cognitive_intelligence",
                capabilities=[
                    "cognitive_state_tracking",
                    "objective_tracking",
                    "context_tracking",
                    "brain_activity_tracking",
                    "hypothesis_tracking",
                    "uncertainty_tracking",
                    "decision_tracking",
                    "state_snapshot",
                ],
                guarantees=[
                    "uses_existing_vale_brain_state",
                    "task_local_state",
                    "traceable_state_updates",
                ],
                limitations=[
                    "not_a_decision_brain",
                    "not_a_reasoning_engine",
                    "not_an_autonomous_controller",
                ],
            ),
            CognitiveContract(
                component_id="COGNITIVE_WORKING_MEMORY",
                component_type="supporting_cognitive_intelligence",
                capabilities=[
                    "working_memory",
                    "memory_retrieval",
                    "memory_prioritization",
                    "memory_capacity_control",
                    "memory_promotion_candidates",
                ],
                guarantees=[
                    "bounded_capacity",
                    "task_local",
                    "traceable_items",
                ],
                limitations=[
                    "not_long_term_memory",
                    "not_a_reasoning_engine",
                ],
            ),
            CognitiveContract(
                component_id="COGNITIVE_ATTENTION",
                component_type="supporting_cognitive_intelligence",
                capabilities=[
                    "attention_prioritization",
                    "focus_ranking",
                    "focus_target_tracking",
                ],
                limitations=[
                    "not_a_reasoning_engine",
                    "not_a_decision_maker",
                ],
            ),
            CognitiveContract(
                component_id="COGNITIVE_WORKSPACE",
                component_type="supporting_cognitive_intelligence",
                capabilities=[
                    "active_context_workspace",
                    "objective_workspace",
                    "focus_workspace",
                    "memory_selection",
                    "uncertainty_visibility",
                    "question_visibility",
                ],
                guarantees=[
                    "bounded_active_context",
                    "task_local",
                    "traceable_inputs",
                ],
                limitations=[
                    "not_a_reasoning_engine",
                    "not_a_decision_brain",
                ],
            ),
            CognitiveContract(component_id="COGNITIVE_TEMPORAL", component_type="supporting_cognitive_intelligence", capabilities=["temporal_tracking","change_history"], limitations=["not_a_causal_engine"]),
            CognitiveContract(component_id="COGNITIVE_PROVENANCE", component_type="evidence_infrastructure", capabilities=["provenance_graph","evidence_lineage"]),
            CognitiveContract(component_id="COGNITIVE_DEPENDENCIES", component_type="supporting_infrastructure", capabilities=["dependency_tracking","impact_analysis"]),
            CognitiveContract(component_id="COGNITIVE_UNCERTAINTY", component_type="epistemic_infrastructure", capabilities=["uncertainty_mapping","epistemic_status"]),
            CognitiveContract(component_id="COGNITIVE_HYPOTHESES", component_type="supporting_cognitive_intelligence", capabilities=["hypothesis_management","competing_hypotheses"]),
            CognitiveContract(component_id="COGNITIVE_CAUSAL", component_type="reasoning_support", capabilities=["causal_modeling"]),
            CognitiveContract(component_id="COGNITIVE_COUNTERFACTUAL", component_type="reasoning_support", capabilities=["counterfactual_scenarios"]),
            CognitiveContract(component_id="COGNITIVE_MULTI_HORIZON", component_type="reasoning_support", capabilities=["multi_horizon_reasoning"]),
            CognitiveContract(component_id="COGNITIVE_BELIEF_STATE", component_type="epistemic_infrastructure", capabilities=["belief_state","belief_revision"]),
            CognitiveContract(
                component_id="COGNITIVE_KNOWLEDGE",
                component_type="supporting_infrastructure",
                capabilities=[
                    "knowledge_claim_registry",
                ],
                limitations=[
                    "full_provenance_graph_not_implemented",
                ],
            ),
            CognitiveContract(
                component_id="COGNITIVE_MCVL",
                component_type="verification_infrastructure",
                capabilities=[
                    "verification_request_creation",
                ],
                limitations=[
                    "full_verification_engine_not_implemented",
                ],
            ),
        ]

        for contract in contracts:
            self.fabric.register_contract(contract)

    def status(self) -> Dict[str, Any]:
        return {
            "system": COGNITIVE_SYSTEM_NAME,
            "version": COGNITIVE_SYSTEM_VERSION,
            "status": "V0_5_REASONING_SUPPORT_READY",
            "components": self.fabric.list_components(),
            "state_version": self.state_manager.version,
            "working_memory": self.memory.stats(),
            "workspace": self.workspace.summary(),
            "observability": self.observability.export(),
        }


# ============================================================
# COGNITIVE BRAIN
# ============================================================

class CognitiveBrain(VALEBrainInterface):
    """
    VALE COGNITIVE BRAIN

    v0.3 adds the Supporting Cognitive System's:
        - Working Memory Manager
        - Attention / Focus Engine
        - Cognitive Workspace

    It remains compatible with the existing VALE brain
    interface/state architecture and does not replace UNITY.
    """

    def __init__(self, connector):

        super().__init__(
            brain_name="COGNITIVE",
            connector=connector,
        )

        self.system_name = COGNITIVE_SYSTEM_NAME
        self.system_version = COGNITIVE_SYSTEM_VERSION

        self.current_task_id: Optional[str] = None
        self.infrastructure: Optional[
            CognitiveInfrastructureRegistry
        ] = None

    def _ensure_task(
        self,
        state: VALEBrainState,
    ) -> CognitiveInfrastructureRegistry:

        if (
            self.infrastructure is None
            or self.current_task_id != state.task_id
        ):
            self.infrastructure = (
                CognitiveInfrastructureRegistry(state)
            )

            self.current_task_id = state.task_id

        return self.infrastructure

    # ========================================================
    # THINK
    # ========================================================

    def think(
        self,
        state: VALEBrainState,
    ) -> Dict[str, Any]:

        infrastructure = self._ensure_task(state)

        state.set(
            "cognitive_system_active",
            True,
        )

        state_intelligence = (
            infrastructure.state_intelligence
        )

        state_intelligence.update(
            context={
                "cognitive_system": self.system_name,
                "cognitive_version": self.system_version,
            },
            active_brains=[
                "COGNITIVE",
            ],
            active_capabilities=[
                "cognitive_state_tracking",
                "objective_tracking",
                "context_tracking",
                "working_memory",
                "memory_retrieval",
                "memory_prioritization",
                "attention_prioritization", "cognitive_workspace",
                "temporal_tracking", "provenance_graph", "dependency_tracking", "uncertainty_mapping",
                "hypothesis_management", "causal_modeling", "counterfactual_scenarios",
                "multi_horizon_reasoning", "belief_state", "belief_revision",
            ],
        )

        infrastructure.workspace.initialize(
            state_intelligence
        )

        state.set(
            "cognitive_system_status",
            "V0_5_REASONING_SUPPORT_READY",
        )

        state.event(
            "cognitive_system_initialized",
            "COGNITIVE",
            payload={
                "version": self.system_version,
                "task_id": state.task_id,
                "implemented_layers": [
                    "cognitive_state_intelligence",
                    "working_memory_manager",
                    "cognitive_attention_focus",
                    "cognitive_workspace", "cognitive_temporal_intelligence",
                    "cognitive_provenance_graph", "cognitive_dependency_graph", "cognitive_uncertainty_map",
                    "hypothesis_management", "causal_model_engine", "counterfactual_reasoning",
                    "multi_horizon_reasoning", "belief_state_management",
                ],
            },
        )

        infrastructure.observability.increment(
            "events_emitted"
        )

        return {
            "brain": "COGNITIVE",
            "status": "READY",
            "system": self.system_name,
            "version": self.system_version,
            "role": (
                "Supporting Cognitive System for the "
                "unified VALE architecture."
            ),
            "task_id": state.task_id,
            "state_version": (
                infrastructure.state_manager.version
            ),
            "state_intelligence": (
                infrastructure.state_intelligence.summary()
            ),
            "working_memory": (
                infrastructure.memory.stats()
            ),
            "attention": {
                "focus_items": len(
                    infrastructure.attention.get_focus()
                ),
                "focus_target": (
                    infrastructure.workspace.get().get(
                        "focus_target"
                    )
                ),
            },
            "workspace": infrastructure.workspace.summary(),
            "temporal": infrastructure.temporal.summary(),
            "provenance": infrastructure.provenance.summary(),
            "dependencies": infrastructure.dependencies.summary(),
            "uncertainty": infrastructure.uncertainty_map.summary(),
            "hypotheses": {"count": len(infrastructure.hypotheses.list())},
            "causal": infrastructure.causal.summary(),
            "counterfactual": infrastructure.counterfactual.summary(),
            "multi_horizon": infrastructure.multi_horizon.summary(),
            "belief_state": infrastructure.beliefs.summary(),
            "components": (
                infrastructure.fabric.list_components()
            ),
            "intelligence_loaded": True,
            "implemented_layers": [
                "cognitive_state_intelligence",
                "working_memory_manager",
                "cognitive_attention_focus",
                "cognitive_workspace", "cognitive_temporal_intelligence", "cognitive_provenance_graph",
                "cognitive_dependency_graph", "cognitive_uncertainty_map", "hypothesis_management",
                "causal_model_engine", "counterfactual_reasoning", "multi_horizon_reasoning", "belief_state_management",
            ],
            "next_layers": [
                "cognitive_temporal_reasoning",
                "cognitive_provenance",
                "epistemic_state",
                "uncertainty_engine",
                "knowledge_graph",
                "reasoning_engines",
                "mcvl_engine",
                "safety_engine",
                "evolution_engine",
            ],
        }

    # ========================================================
    # MESSAGE RECEPTION
    # ========================================================

    def receive_message(
        self,
        message: str,
        state: VALEBrainState,
        source_brain: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        infrastructure = self._ensure_task(state)

        cognitive_message = CognitiveMessage(
            source=source_brain.upper(),
            destination="COGNITIVE",
            message_type="BRAIN_MESSAGE",
            data={
                "message": message,
                "payload": deepcopy(payload or {}),
            },
            task_id=state.task_id,
        )

        safety_result = (
            infrastructure.safety.validate_message(
                cognitive_message
            )
        )

        infrastructure.observability.increment(
            "messages_validated"
        )

        if not safety_result["allowed"]:
            state.event(
                "cognitive_message_rejected",
                "COGNITIVE",
                target=source_brain.upper(),
                payload=safety_result,
            )

            return {
                "success": False,
                "brain": "COGNITIVE",
                "received": False,
                "from": source_brain.upper(),
                "message_id": cognitive_message.message_id,
                "task_id": state.task_id,
                "reason": safety_result["reason"],
            }

        memory_item = infrastructure.memory.add(
            content={
                "message": str(message),
                "payload": deepcopy(payload or {}),
            },
            importance=0.6,
            relevance=0.7,
            priority=6,
            source=source_brain.upper(),
            memory_type="BRAIN_MESSAGE",
        )

        # Receiving a message records information; it does NOT
        # assert that the message is true.
        infrastructure.workspace.refresh()

        return {
            "success": True,
            "brain": "COGNITIVE",
            "received": True,
            "from": source_brain.upper(),
            "message_id": cognitive_message.message_id,
            "task_id": state.task_id,
            "working_memory_id": memory_item[
                "memory_id"
            ],
        }

    # ========================================================
    # IDENTITY
    # ========================================================

    def identity(self) -> Dict[str, Any]:
        base = super().identity()

        base.update({
            "system": self.system_name,
            "version": self.system_version,
            "role": "SUPPORTING_COGNITIVE_SYSTEM",
        })

        return base


# ============================================================
# END OF VALE SUPPORTING COGNITIVE SYSTEM v0.3.0
# ============================================================
