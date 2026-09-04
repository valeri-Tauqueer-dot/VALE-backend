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
COGNITIVE_SYSTEM_VERSION = "0.2.0"


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

class CognitiveMemoryFoundation:
    """
    Minimal working-memory foundation.

    This is NOT the final long-term Memory System.

    It exists so the Supporting Cognitive System has a controlled
    place for task-local working information without pretending
    that all information is permanent memory.
    """

    def __init__(self, state: VALEBrainState):
        self.state = state

        if self.state.get("cognitive_working_memory") is None:
            self.state.set(
                "cognitive_working_memory",
                [],
            )

    def add(
        self,
        content: Any,
        importance: float = 0.5,
        source: str = "COGNITIVE",
    ) -> Dict[str, Any]:

        importance = max(
            0.0,
            min(1.0, float(importance)),
        )

        item = {
            "memory_id": make_id("wm"),
            "content": deepcopy(content),
            "importance": importance,
            "source": source,
            "timestamp": utc_now(),
        }

        memory = self.state.get(
            "cognitive_working_memory",
            [],
        )

        if not isinstance(memory, list):
            memory = []

        memory.append(item)

        self.state.set(
            "cognitive_working_memory",
            memory,
        )

        return item

    def recent(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        memory = self.state.get(
            "cognitive_working_memory",
            [],
        )

        if not isinstance(memory, list):
            return []

        return deepcopy(
            memory[-max(1, int(limit)):]
        )

    def clear(self) -> None:
        self.state.set(
            "cognitive_working_memory",
            [],
        )


# ============================================================
# 9. KNOWLEDGE SYSTEM
# ============================================================

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

class CognitiveInfrastructureRegistry:
    """
    Central registry for the supporting cognitive subsystems.

    Advanced engines such as:
        - Epistemic State Manager
        - Evidence & Provenance Graph
        - Uncertainty Engine
        - World Model
        - Causal Model
        - Counterfactual Engine
        - Adversarial Tester
        - Cognitive Immune System
        - Simulation Sandbox
        - Skill Acquisition
        - Cognitive Genome
        - Architectural Evolution

    will be attached here in later versions.

    They are deliberately not faked in Foundation v0.1.
    """

    def __init__(self, state: VALEBrainState):

        self.state = state

        self.fabric = CognitiveFabric()
        self.router = CognitiveRouter()

        self.state_manager = CognitiveStateManager(state)

        self.state_intelligence = CognitiveStateIntelligence(
            state,
            self.state_manager,
        )

        self.memory = CognitiveMemoryFoundation(state)
        self.knowledge = CognitiveKnowledgeFoundation(state)
        self.reasoning = CognitiveReasoningFoundation(state)
        self.mcvl = CognitiveMCVLFoundation(state)

        self.safety = CognitiveSafetyFoundation()
        self.evolution = CognitiveEvolutionFoundation(state)
        self.observability = CognitiveObservability()

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
                component_id="COGNITIVE_MEMORY",
                component_type="supporting_infrastructure",
                capabilities=[
                    "working_memory",
                ],
                limitations=[
                    "not_long_term_memory_yet",
                ],
            ),
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
            "status": "FOUNDATION_READY",
            "components": self.fabric.list_components(),
            "state_version": self.state_manager.version,
            "observability": self.observability.export(),
        }


# ============================================================
# COGNITIVE BRAIN
# ============================================================

class CognitiveBrain(VALEBrainInterface):
    """
    VALE COGNITIVE BRAIN

    In the current VALE architecture this file is the home of
    the Supporting Cognitive System foundation.

    It remains compatible with:
        VALEBrainInterface
        BrainNetwork
        VALEBrainState
        VALEConnector

    It is NOT the master brain and does NOT replace UNITY.
    """

    def __init__(self, connector):

        super().__init__(
            brain_name="COGNITIVE",
            connector=connector,
        )

        self.system_name = COGNITIVE_SYSTEM_NAME
        self.system_version = COGNITIVE_SYSTEM_VERSION

        # These are created per task in think(), because the
        # existing VALEBrainState is task-specific.
        self.current_task_id: Optional[str] = None
        self.infrastructure: Optional[
            CognitiveInfrastructureRegistry
        ] = None

    # ========================================================
    # TASK INITIALIZATION
    # ========================================================

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
            ],
        )

        state.set(
            "cognitive_system_status",
            "FOUNDATION_READY",
        )

        state.event(
            "cognitive_system_initialized",
            "COGNITIVE",
            payload={
                "version": self.system_version,
                "task_id": state.task_id,
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
                "Supporting Cognitive System foundation "
                "for the unified VALE architecture."
            ),
            "task_id": state.task_id,
            "state_version": (
                infrastructure.state_manager.version
            ),
            "state_intelligence": (
                infrastructure.state_intelligence.summary()
            ),
            "components": (
                infrastructure.fabric.list_components()
            ),
            "intelligence_loaded": False,
            "next_layers": [
                "advanced_routing",
                "epistemic_state",
                "evidence_provenance",
                "uncertainty",
                "advanced_memory",
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
                "payload": payload or {},
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
                   "received": True,
            "from": source_brain.upper(),
            "message_id": cognitive_message.message_id,
            "task_id": state.task_id,
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
# END OF VALE SUPPORTING COGNITIVE SYSTEM FOUNDATION v0.1
# ============================================================
