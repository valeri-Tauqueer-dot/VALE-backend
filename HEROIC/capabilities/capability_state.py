from future import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

class CapabilityType(str, Enum):
"""
Broad category of cognitive capability.
"""

UNDERSTANDING = "understanding"
ANALYSIS = "analysis"
REASONING = "reasoning"
RESEARCH = "research"
DATA_RETRIEVAL = "data_retrieval"
VERIFICATION = "verification"
DECISION_SUPPORT = "decision_support"
PLANNING = "planning"
COMPARISON = "comparison"
SYNTHESIS = "synthesis"
COMMUNICATION = "communication"
MONITORING = "monitoring"
EXECUTION = "execution"
MEMORY_RETRIEVAL = "memory_retrieval"
KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
HUMAN_CONTEXT = "human_context"
MARKET_INTELLIGENCE = "market_intelligence"
OTHER = "other"

class CapabilityStatus(str, Enum):
"""
Availability state of a capability.
"""

AVAILABLE = "available"
UNAVAILABLE = "unavailable"
DEGRADED = "degraded"
DISABLED = "disabled"
UNKNOWN = "unknown"

@dataclass
class HeroicCapabilityState:
"""
Describes a capability known to HEROIC.

A capability is an ability that may be required to accomplish
an objective. It is intentionally separated from the brain that
eventually provides or executes that capability.
"""

capability_id: str
name: str
capability_type: CapabilityType = CapabilityType.OTHER

description: str = ""

status: CapabilityStatus = CapabilityStatus.AVAILABLE

priority: float = 0.0
confidence: float = 1.0

required_inputs: List[str] = field(default_factory=list)
expected_outputs: List[str] = field(default_factory=list)

compatible_brains: List[str] = field(default_factory=list)

dependencies: List[str] = field(default_factory=list)

constraints: List[str] = field(default_factory=list)

metadata: Dict[str, Any] = field(default_factory=dict)

def add_required_input(
    self,
    input_name: str,
) -> None:
    """Register a required input."""
    if input_name and input_name not in self.required_inputs:
        self.required_inputs.append(input_name)

def add_expected_output(
    self,
    output_name: str,
) -> None:
    """Register an expected output."""
    if output_name and output_name not in self.expected_outputs:
        self.expected_outputs.append(output_name)

def add_compatible_brain(
    self,
    brain_name: str,
) -> None:
    """Register a brain capable of providing this capability."""
    if brain_name and brain_name not in self.compatible_brains:
        self.compatible_brains.append(brain_name)

def add_dependency(
    self,
    capability_id: str,
) -> None:
    """Register another capability required first."""
    if capability_id and capability_id not in self.dependencies:
        self.dependencies.append(capability_id)

def add_constraint(
    self,
    constraint: str,
) -> None:
    """Register a capability constraint."""
    if constraint and constraint not in self.constraints:
        self.constraints.append(constraint)

def is_available(self) -> bool:
    """Return whether the capability can currently be selected."""
    return self.status == CapabilityStatus.AVAILABLE

def to_dict(self) -> Dict[str, Any]:
    """Serialize the capability state."""
    return {
        "capability_id": self.capability_id,
        "name": self.name,
        "capability_type": self.capability_type.value,
        "description": self.description,
        "status": self.status.value,
        "priority": self.priority,
        "confidence": self.confidence,
        "required_inputs": list(self.required_inputs),
        "expected_outputs": list(self.expected_outputs),
        "compatible_brains": list(self.compatible_brains),
        "dependencies": list(self.dependencies),
        "constraints": list(self.constraints),
        "metadata": dict(self.metadata),
}
