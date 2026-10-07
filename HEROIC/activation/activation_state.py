from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List
from uuid import uuid4


class ActivationMode(str, Enum):
    SINGLE = "single"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"


class ActivationStatus(str, Enum):
    REQUESTED = "requested"
    PLANNED = "planned"
    READY = "ready"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class HeroicActivationState:
    activation_id: str = field(
        default_factory=lambda: f"activation-{uuid4().hex}"
    )
    brain_name: str = ""
    status: ActivationStatus = ActivationStatus.REQUESTED
    mode: ActivationMode = ActivationMode.SINGLE
    reason: str = ""
    required_capabilities: List[str] = field(default_factory=list)
    required_inputs: List[str] = field(default_factory=list)
    expected_outputs: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    priority: float = 0.0
    confidence: float = 1.0
    blockers: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_capability(self, capability_id: str) -> None:
        if capability_id and capability_id not in self.required_capabilities:
            self.required_capabilities.append(capability_id)

    def add_input(self, input_name: str) -> None:
        if input_name and input_name not in self.required_inputs:
            self.required_inputs.append(input_name)

    def add_output(self, output_name: str) -> None:
        if output_name and output_name not in self.expected_outputs:
            self.expected_outputs.append(output_name)

    def add_dependency(self, dependency_id: str) -> None:
        if dependency_id and dependency_id not in self.dependencies:
            self.dependencies.append(dependency_id)

    def add_blocker(self, blocker: str) -> None:
        if blocker and blocker not in self.blockers:
            self.blockers.append(blocker)
        self.status = ActivationStatus.BLOCKED

    def add_constraint(self, constraint: str) -> None:
        if constraint and constraint not in self.constraints:
            self.constraints.append(constraint)

    def is_blocked(self) -> bool:
        return (
            self.status == ActivationStatus.BLOCKED
            or bool(self.blockers)
        )

    def is_active(self) -> bool:
        return self.status in {
            ActivationStatus.ACTIVATING,
            ActivationStatus.ACTIVE,
        }

    def mark_planned(self) -> None:
        self.status = ActivationStatus.PLANNED

    def mark_ready(self) -> None:
        if not self.is_blocked():
            self.status = ActivationStatus.READY

    def mark_activating(self) -> None:
        if not self.is_blocked():
            self.status = ActivationStatus.ACTIVATING

    def mark_active(self) -> None:
        if not self.is_blocked():
            self.status = ActivationStatus.ACTIVE

    def mark_degraded(self) -> None:
        self.status = ActivationStatus.DEGRADED

    def mark_blocked(self, reason: str = "") -> None:
        if reason:
            self.add_blocker(reason)
        self.status = ActivationStatus.BLOCKED

    def mark_failed(self, reason: str = "") -> None:
        if reason:
            self.add_blocker(reason)
        self.status = ActivationStatus.FAILED

    def mark_completed(self) -> None:
        self.status = ActivationStatus.COMPLETED

    def mark_cancelled(self) -> None:
        self.status = ActivationStatus.CANCELLED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "activation_id": self.activation_id,
            "brain_name": self.brain_name,
            "status": self.status.value,
            "mode": self.mode.value,
            "reason": self.reason,
            "required_capabilities": list(self.required_capabilities),
            "required_inputs": list(self.required_inputs),
            "expected_outputs": list(self.expected_outputs),
            "dependencies": list(self.dependencies),
            "priority": self.priority,
            "confidence": self.confidence,
            "blockers": list(self.blockers),
            "constraints": list(self.constraints),
            "metadata": dict(self.metadata),
        }
