from future import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

class ActivationMode(str, Enum):
"""
Execution mode for activating a HEROIC-required brain.
"""

SINGLE = "single"
PARALLEL = "parallel"
SEQUENTIAL = "sequential"
CONDITIONAL = "conditional"

class ActivationStatus(str, Enum):
"""
Current state of a brain activation request.
"""

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
"""
Represents HEROIC's activation state for a required brain.

This object describes the activation requirement and its lifecycle.
It does not itself execute or control the brain.
"""

activation_id: str
brain_name: str

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

def add_capability(
    self,
    capability_id: str,
) -> None:
    """Register a capability required from this brain."""
    if capability_id and capability_id not in self.required_capabilities:
        self.required_capabilities.append(capability_id)

def add_input(
    self,
    input_name: str,
) -> None:
    """Register a required activation input."""
    if input_name and input_name not in self.required_inputs:
        self.required_inputs.append(input_name)

def add_output(
    self,
    output_name: str,
) -> None:
    """Register an expected activation output."""
    if output_name and output_name not in self.expected_outputs:
        self.expected_outputs.append(output_name)

def add_dependency(
    self,
    activation_id: str,
) -> None:
    """Register another activation that must precede this one."""
    if activation_id and activation_id not in self.dependencies:
        self.dependencies.append(activation_id)

def add_blocker(
    self,
    blocker: str,
) -> None:
    """Register a condition preventing activation."""
    if blocker and blocker not in self.blockers:
        self.blockers.append(blocker)

def add_constraint(
    self,
    constraint: str,
) -> None:
    """Register an activation constraint."""
    if constraint and constraint not in self.constraints:
        self.constraints.append(constraint)

def is_blocked(self) -> bool:
    """Return whether activation is currently blocked."""
    return (
        self.status == ActivationStatus.BLOCKED
        or bool(self.blockers)
    )

def is_active(self) -> bool:
    """Return whether the brain is currently active."""
    return self.status == ActivationStatus.ACTIVE

def mark_planned(self) -> None:
    """Mark activation as planned."""
    self.status = ActivationStatus.PLANNED

def mark_ready(self) -> None:
    """Mark activation as ready."""
    self.status = ActivationStatus.READY

def mark_activating(self) -> None:
    """Mark activation as currently being activated."""
    self.status = ActivationStatus.ACTIVATING

def mark_active(self) -> None:
    """Mark activation as active."""
    self.status = ActivationStatus.ACTIVE

def mark_degraded(self) -> None:
    """Mark activation as degraded."""
    self.status = ActivationStatus.DEGRADED

def mark_blocked(
    self,
    blocker: str = "",
) -> None:
    """Mark activation as blocked."""
    self.status = ActivationStatus.BLOCKED

    if blocker:
        self.add_blocker(blocker)

def mark_failed(
    self,
    reason: str = "",
) -> None:
    """Mark activation as failed."""
    self.status = ActivationStatus.FAILED

    if reason:
        self.metadata["failure_reason"] = reason

def mark_completed(self) -> None:
    """Mark activation as completed."""
    self.status = ActivationStatus.COMPLETED

def mark_cancelled(
    self,
    reason: str = "",
) -> None:
    """Mark activation as cancelled."""
    self.status = ActivationStatus.CANCELLED

    if reason:
        self.metadata["cancellation_reason"] = reason

def to_dict(self) -> Dict[str, Any]:
    """Serialize activation state."""
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
