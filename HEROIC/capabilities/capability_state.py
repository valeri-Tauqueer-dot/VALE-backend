from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class CapabilityType(str, Enum):
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
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


@dataclass
class HeroicCapabilityState:
    capability_id: str
    name: str
    capability_type: CapabilityType = CapabilityType.OTHER
    description: str = ""
    status: CapabilityStatus = CapabilityStatus.AVAILABLE
    priority: float = 0.0
    confidence: float = 1.0

    required_inputs: List[str] = field(
        default_factory=list
    )

    expected_outputs: List[str] = field(
        default_factory=list
    )

    compatible_brains: List[str] = field(
        default_factory=list
    )

    dependencies: List[str] = field(
        default_factory=list
    )

    constraints: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def add_required_input(
        self,
        input_name: str,
    ) -> None:
        if (
            input_name
            and input_name not in self.required_inputs
        ):
            self.required_inputs.append(input_name)

    def add_expected_output(
        self,
        output_name: str,
    ) -> None:
        if (
            output_name
            and output_name not in self.expected_outputs
        ):
            self.expected_outputs.append(output_name)

    def add_compatible_brain(
        self,
        brain_name: str,
    ) -> None:
        if (
            brain_name
            and brain_name not in self.compatible_brains
        ):
            self.compatible_brains.append(brain_name)

    def add_dependency(
        self,
        dependency_id: str,
    ) -> None:
        if (
            dependency_id
            and dependency_id not in self.dependencies
        ):
            self.dependencies.append(dependency_id)

    def add_constraint(
        self,
        constraint: str,
    ) -> None:
        if (
            constraint
            and constraint not in self.constraints
        ):
            self.constraints.append(constraint)

    def is_available(self) -> bool:
        return self.status == CapabilityStatus.AVAILABLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "capability_type": self.capability_type.value,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "confidence": self.confidence,
            "required_inputs": list(
                self.required_inputs
            ),
            "expected_outputs": list(
                self.expected_outputs
            ),
            "compatible_brains": list(
                self.compatible_brains
            ),
            "dependencies": list(
                self.dependencies
            ),
            "constraints": list(
                self.constraints
            ),
            "metadata": dict(self.metadata),
        }
