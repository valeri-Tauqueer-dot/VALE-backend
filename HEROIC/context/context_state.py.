from future import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

class ContextScope(str, Enum):
"""
Scope of contextual information used by HEROIC.
"""

MISSION = "mission"
GOAL = "goal"
OBJECTIVE = "objective"
TASK = "task"
CAPABILITY = "capability"
BRAIN = "brain"
SYSTEM = "system"
USER = "user"
ENVIRONMENT = "environment"

class ContextSource(str, Enum):
"""
Origin classification for contextual information.
"""

USER = "user"
MEMORY = "memory"
KNOWLEDGE = "knowledge"
COGNITIVE_STATE = "cognitive_state"
BRAIN = "brain"
SYSTEM = "system"
EXTERNAL = "external"
INFERRED = "inferred"
UNKNOWN = "unknown"

@dataclass
class HeroicContextState:
"""
Structured context assembled for a HEROIC mission.

Context is kept separate from mission state so HEROIC can
distinguish the mission itself from the information used
to understand and plan that mission.
"""

context_id: str

scope: ContextScope = ContextScope.MISSION

mission_id: str = ""
goal_id: str = ""
objective_id: str = ""
task_id: str = ""

user_request: str = ""

facts: Dict[str, Any] = field(default_factory=dict)
signals: Dict[str, Any] = field(default_factory=dict)

sources: Dict[str, ContextSource] = field(default_factory=dict)

assumptions: List[str] = field(default_factory=list)
constraints: List[str] = field(default_factory=list)

relevant_capabilities: List[str] = field(default_factory=list)
relevant_brains: List[str] = field(default_factory=list)

missing_information: List[str] = field(default_factory=list)

contradictions: List[str] = field(default_factory=list)

confidence: float = 1.0

metadata: Dict[str, Any] = field(default_factory=dict)

def add_fact(
    self,
    key: str,
    value: Any,
    source: ContextSource = ContextSource.UNKNOWN,
) -> None:
    """Add or update a contextual fact."""
    if not key:
        return

    self.facts[key] = value
    self.sources[key] = source

def add_signal(
    self,
    key: str,
    value: Any,
    source: ContextSource = ContextSource.UNKNOWN,
) -> None:
    """Add or update a contextual signal."""
    if not key:
        return

    self.signals[key] = value
    self.sources[key] = source

def add_assumption(
    self,
    assumption: str,
) -> None:
    """Register an assumption used during planning."""
    if assumption and assumption not in self.assumptions:
        self.assumptions.append(assumption)

def add_constraint(
    self,
    constraint: str,
) -> None:
    """Register a contextual constraint."""
    if constraint and constraint not in self.constraints:
        self.constraints.append(constraint)

def add_capability(
    self,
    capability_id: str,
) -> None:
    """Register a capability relevant to this context."""
    if (
        capability_id
        and capability_id not in self.relevant_capabilities
    ):
        self.relevant_capabilities.append(capability_id)

def add_brain(
    self,
    brain_name: str,
) -> None:
    """Register a brain relevant to this context."""
    if (
        brain_name
        and brain_name not in self.relevant_brains
    ):
        self.relevant_brains.append(brain_name)

def add_missing_information(
    self,
    information: str,
) -> None:
    """Register missing contextual information."""
    if (
        information
        and information not in self.missing_information
    ):
        self.missing_information.append(information)

def add_contradiction(
    self,
    contradiction: str,
) -> None:
    """Register a contextual contradiction."""
    if (
        contradiction
        and contradiction not in self.contradictions
    ):
        self.contradictions.append(contradiction)

def has_missing_information(self) -> bool:
    """Return whether required context is missing."""
    return bool(self.missing_information)

def has_contradictions(self) -> bool:
    """Return whether contextual contradictions exist."""
    return bool(self.contradictions)

def is_sufficient(self) -> bool:
    """
    Return whether context is structurally sufficient.

    Actual evidence quality is evaluated by the information
    and evidence systems, not by this context container.
    """
    return (
        bool(self.user_request)
        and not self.missing_information
        and not self.contradictions
    )

def to_dict(self) -> Dict[str, Any]:
    """Serialize contextual state."""
    return {
        "context_id": self.context_id,
        "scope": self.scope.value,
        "mission_id": self.mission_id,
        "goal_id": self.goal_id,
        "objective_id": self.objective_id,
        "task_id": self.task_id,
        "user_request": self.user_request,
        "facts": dict(self.facts),
        "signals": dict(self.signals),
        "sources": {
            key: source.value
            for key, source in self.sources.items()
        },
        "assumptions": list(self.assumptions),
        "constraints": list(self.constraints),
        "relevant_capabilities": list(
            self.relevant_capabilities
        ),
        "relevant_brains": list(self.relevant_brains),
        "missing_information": list(
            self.missing_information
        ),
        "contradictions": list(self.contradictions),
        "confidence": self.confidence,
        "metadata": dict(self.metadata),
    }
