from future import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from HEROIC.activation.activation_state import (
ActivationMode,
ActivationStatus,
HeroicActivationState,
)

@dataclass
class HeroicActivationPlan:
"""
Defines how HEROIC intends to activate the brains required
for a mission.

The plan is declarative. It describes activation order,
parallel activation groups, dependencies, and required
capabilities. It does not execute the brains itself.
"""

plan_id: str
mission_id: str = ""
objective_id: str = ""
goal_id: str = ""

activation_ids: List[str] = field(default_factory=list)
ordered_activation_ids: List[str] = field(default_factory=list)

parallel_activation_groups: List[List[str]] = field(
    default_factory=list
)

dependency_map: Dict[str, List[str]] = field(
    default_factory=dict
)

required_capabilities: List[str] = field(
    default_factory=list
)

required_brains: List[str] = field(
    default_factory=list
)

status: ActivationStatus = ActivationStatus.REQUESTED
mode: ActivationMode = ActivationMode.SINGLE

blockers: List[str] = field(default_factory=list)
constraints: List[str] = field(default_factory=list)

expected_outputs: List[str] = field(default_factory=list)

metadata: Dict[str, Any] = field(default_factory=dict)

def add_activation(
    self,
    activation_id: str,
) -> None:
    """Register an activation in the plan."""
    if activation_id and activation_id not in self.activation_ids:
        self.activation_ids.append(activation_id)

def add_ordered_activation(
    self,
    activation_id: str,
) -> None:
    """Add an activation to the sequential activation order."""
    self.add_activation(activation_id)

    if activation_id not in self.ordered_activation_ids:
        self.ordered_activation_ids.append(activation_id)

def add_parallel_group(
    self,
    activation_ids: Iterable[str],
) -> None:
    """
    Add a group of activations that may run in parallel.

    Empty groups are ignored.
    """
    group: List[str] = []

    for activation_id in activation_ids:
        if not activation_id:
            continue

        self.add_activation(activation_id)

        if activation_id not in group:
            group.append(activation_id)

    if group and group not in self.parallel_activation_groups:
        self.parallel_activation_groups.append(group)

def add_dependency(
    self,
    activation_id: str,
    dependency_activation_id: str,
) -> None:
    """
    Register an activation dependency.

    An activation cannot depend on itself.
    """
    if not activation_id:
        raise ValueError("Activation ID cannot be empty.")

    if not dependency_activation_id:
        raise ValueError(
            "Dependency activation ID cannot be empty."
        )

    if activation_id == dependency_activation_id:
        raise ValueError(
            "An activation cannot depend on itself."
        )

    self.add_activation(activation_id)
    self.add_activation(dependency_activation_id)

    dependencies = self.dependency_map.setdefault(
        activation_id,
        [],
    )

    if dependency_activation_id not in dependencies:
        dependencies.append(dependency_activation_id)

def add_required_capability(
    self,
    capability_id: str,
) -> None:
    """Register a capability required by the activation plan."""
    if (
        capability_id
        and capability_id not in self.required_capabilities
    ):
        self.required_capabilities.append(capability_id)

def add_required_brain(
    self,
    brain_name: str,
) -> None:
    """Register a brain required by the activation plan."""
    if (
        brain_name
        and brain_name not in self.required_brains
    ):
        self.required_brains.append(brain_name)

def add_blocker(
    self,
    blocker: str,
) -> None:
    """Register a plan blocker."""
    if blocker and blocker not in self.blockers:
        self.blockers.append(blocker)

def add_constraint(
    self,
    constraint: str,
) -> None:
    """Register an activation constraint."""
    if constraint and constraint not in self.constraints:
        self.constraints.append(constraint)

def add_expected_output(
    self,
    output_name: str,
) -> None:
    """Register an expected activation result."""
    if (
        output_name
        and output_name not in self.expected_outputs
    ):
        self.expected_outputs.append(output_name)

def is_empty(self) -> bool:
    """Return whether the activation plan contains no activations."""
    return not self.activation_ids

def is_blocked(self) -> bool:
    """Return whether the activation plan is blocked."""
    return bool(self.blockers) or self.status == ActivationStatus.BLOCKED

def is_ready(self) -> bool:
    """
    Return whether the plan is structurally ready for activation.

    This checks plan-level blockers and required activation presence.
    Runtime brain health is intentionally handled elsewhere.
    """
    if self.is_empty():
        return False

    if self.is_blocked():
        return False

    return self.status in {
        ActivationStatus.REQUESTED,
        ActivationStatus.PLANNED,
        ActivationStatus.READY,
    }

def mark_planned(self) -> None:
    """Mark the activation plan as planned."""
    self.status = ActivationStatus.PLANNED

def mark_ready(self) -> None:
    """Mark the activation plan as ready."""
    if self.is_empty():
        raise ValueError(
            "Cannot mark an empty activation plan as ready."
        )

    if self.is_blocked():
        raise ValueError(
            "Cannot mark a blocked activation plan as ready."
        )

    self.status = ActivationStatus.READY

def mark_activating(self) -> None:
    """Mark the plan as currently activating."""
    self.status = ActivationStatus.ACTIVATING

def mark_active(self) -> None:
    """Mark the plan as active."""
    self.status = ActivationStatus.ACTIVE

def mark_blocked(
    self,
    blocker: str = "",
) -> None:
    """Mark the plan as blocked."""
    self.status = ActivationStatus.BLOCKED

    if blocker:
        self.add_blocker(blocker)

def mark_failed(
    self,
    reason: str = "",
) -> None:
    """Mark the plan as failed."""
    self.status = ActivationStatus.FAILED

    if reason:
        self.metadata["failure_reason"] = reason

def mark_completed(self) -> None:
    """Mark the plan as completed."""
    self.status = ActivationStatus.COMPLETED

def mark_cancelled(
    self,
    reason: str = "",
) -> None:
    """Mark the plan as cancelled."""
    self.status = ActivationStatus.CANCELLED

    if reason:
        self.metadata["cancellation_reason"] = reason

def activation_count(self) -> int:
    """Return the number of unique activations."""
    return len(self.activation_ids)

def parallel_stage_count(self) -> int:
    """Return the number of parallel activation groups."""
    return len(self.parallel_activation_groups)

def to_dict(self) -> Dict[str, Any]:
    """Serialize the activation plan."""
    return {
        "plan_id": self.plan_id,
        "mission_id": self.mission_id,
        "objective_id": self.objective_id,
        "goal_id": self.goal_id,
        "activation_ids": list(self.activation_ids),
        "ordered_activation_ids": list(
            self.ordered_activation_ids
        ),
        "parallel_activation_groups": [
            list(group)
            for group in self.parallel_activation_groups
        ],
        "dependency_map": {
            activation_id: list(dependencies)
            for activation_id, dependencies
            in self.dependency_map.items()
        },
        "required_capabilities": list(
            self.required_capabilities
        ),
        "required_brains": list(self.required_brains),
        "status": self.status.value,
        "mode": self.mode.value,
        "blockers": list(self.blockers),
        "constraints": list(self.constraints),
        "expected_outputs": list(self.expected_outputs),
        "metadata": dict(self.metadata),
    }

@classmethod
def from_activations(
    cls,
    plan_id: str,
    activations: Iterable[HeroicActivationState],
    *,
    mission_id: str = "",
    objective_id: str = "",
    goal_id: str = "",
) -> "HeroicActivationPlan":
    """
    Build an activation plan from existing activation states.
    """
    plan = cls(
        plan_id=plan_id,
        mission_id=mission_id,
        objective_id=objective_id,
        goal_id=goal_id,
    )

    for activation in activations:
        plan.add_activation(activation.activation_id)
        plan.add_required_brain(activation.brain_name)

        for capability_id in activation.required_capabilities:
            plan.add_required_capability(capability_id)

        for dependency_id in activation.dependencies:
            plan.add_dependency(
                activation.activation_id,
                dependency_id,
            )

    return plan
