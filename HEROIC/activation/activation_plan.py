from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable

from .activation_state import (
    ActivationMode,
    ActivationStatus,
    HeroicActivationState,
)


@dataclass
class HeroicActivationPlan:
    """
    Structured plan describing which VALE brains HEROIC intends
    to activate and in what order.
    """

    plan_id: str = ""
    mission_id: str = ""
    objective_id: str = ""
    goal_id: str = ""

    activation_ids: list[str] = field(default_factory=list)
    ordered_activation_ids: list[str] = field(default_factory=list)
    parallel_activation_groups: list[list[str]] = field(
        default_factory=list
    )
    dependency_map: Dict[str, list[str]] = field(
        default_factory=dict
    )

    required_capabilities: list[str] = field(
        default_factory=list
    )
    required_brains: list[str] = field(default_factory=list)

    status: ActivationStatus = ActivationStatus.REQUESTED
    mode: ActivationMode = ActivationMode.SINGLE

    blockers: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_activation(self, activation_id: str) -> None:
        if activation_id and activation_id not in self.activation_ids:
            self.activation_ids.append(activation_id)

    def add_ordered_activation(
        self,
        activation_id: str,
    ) -> None:
        self.add_activation(activation_id)

        if activation_id not in self.ordered_activation_ids:
            self.ordered_activation_ids.append(activation_id)

    def add_parallel_group(
        self,
        activation_ids: Iterable[str],
    ) -> None:
        group: list[str] = []

        for activation_id in activation_ids:
            if not activation_id:
                continue

            self.add_activation(activation_id)

            if activation_id not in group:
                group.append(activation_id)

        if group:
            self.parallel_activation_groups.append(group)

    def add_dependency(
        self,
        activation_id: str,
        dependency_id: str,
    ) -> None:
        if not activation_id or not dependency_id:
            return

        self.add_activation(activation_id)
        self.add_activation(dependency_id)

        dependencies = self.dependency_map.setdefault(
            activation_id,
            [],
        )

        if dependency_id not in dependencies:
            dependencies.append(dependency_id)

    def add_required_capability(
        self,
        capability_id: str,
    ) -> None:
        if (
            capability_id
            and capability_id not in self.required_capabilities
        ):
            self.required_capabilities.append(capability_id)

    def add_required_brain(
        self,
        brain_name: str,
    ) -> None:
        if (
            brain_name
            and brain_name not in self.required_brains
        ):
            self.required_brains.append(brain_name)

    def add_blocker(
        self,
        blocker: str,
    ) -> None:
        if blocker and blocker not in self.blockers:
            self.blockers.append(blocker)

        if blocker:
            self.status = ActivationStatus.BLOCKED

    def add_constraint(
        self,
        constraint: str,
    ) -> None:
        if (
            constraint
            and constraint not in self.constraints
        ):
            self.constraints.append(constraint)

    def add_expected_output(
        self,
        output_name: str,
    ) -> None:
        if (
            output_name
            and output_name not in self.expected_outputs
        ):
            self.expected_outputs.append(output_name)

    def is_empty(self) -> bool:
        return not self.activation_ids

    def is_blocked(self) -> bool:
        return (
            self.status == ActivationStatus.BLOCKED
            or bool(self.blockers)
        )

    def is_ready(self) -> bool:
        return (
            bool(self.activation_ids)
            and not self.is_blocked()
            and self.status
            in {
                ActivationStatus.READY,
                ActivationStatus.ACTIVATING,
                ActivationStatus.ACTIVE,
            }
        )

    def mark_planned(self) -> None:
        if not self.is_blocked():
            self.status = ActivationStatus.PLANNED

    def mark_ready(self) -> None:
        if not self.is_blocked() and self.activation_ids:
            self.status = ActivationStatus.READY

    def mark_activating(self) -> None:
        if self.is_ready():
            self.status = ActivationStatus.ACTIVATING

    def mark_active(self) -> None:
        if not self.is_blocked() and self.activation_ids:
            self.status = ActivationStatus.ACTIVE

    def mark_blocked(
        self,
        reason: str = "",
    ) -> None:
        if reason:
            self.add_blocker(reason)

        self.status = ActivationStatus.BLOCKED

    def mark_failed(
        self,
        reason: str = "",
    ) -> None:
        if reason:
            self.add_blocker(reason)

        self.status = ActivationStatus.FAILED

    def mark_completed(self) -> None:
        self.status = ActivationStatus.COMPLETED

    def mark_cancelled(self) -> None:
        self.status = ActivationStatus.CANCELLED

    def activation_count(self) -> int:
        return len(self.activation_ids)

    def parallel_stage_count(self) -> int:
        return len(self.parallel_activation_groups)

    def to_dict(self) -> Dict[str, Any]:
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
                key: list(value)
                for key, value in self.dependency_map.items()
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
        activations: Iterable[HeroicActivationState],
        plan_id: str = "",
        mission_id: str = "",
        objective_id: str = "",
        goal_id: str = "",
    ) -> "HeroicActivationPlan":
        """
        Build an activation plan from activation states.
        """

        plan = cls(
            plan_id=plan_id,
            mission_id=mission_id,
            objective_id=objective_id,
            goal_id=goal_id,
        )

        for activation in activations:
            if not isinstance(
                activation,
                HeroicActivationState,
            ):
                raise TypeError(
                    "All activations must be "
                    "HeroicActivationState instances."
                )

            plan.add_activation(
                activation.activation_id
            )

            plan.add_ordered_activation(
                activation.activation_id
            )

            for capability_id in (
                activation.required_capabilities
            ):
                plan.add_required_capability(
                    capability_id
                )

            if activation.brain_name:
                plan.add_required_brain(
                    activation.brain_name
                )

            for dependency_id in activation.dependencies:
                plan.add_dependency(
                    activation.activation_id,
                    dependency_id,
                )

            for output_name in activation.expected_outputs:
                plan.add_expected_output(
                    output_name
                )

            for blocker in activation.blockers:
                plan.add_blocker(blocker)

        if plan.blockers:
            plan.status = ActivationStatus.BLOCKED
        elif plan.activation_ids:
            plan.status = ActivationStatus.PLANNED

        return plan
