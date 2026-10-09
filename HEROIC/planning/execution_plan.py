"""
HEROIC EXECUTION PLAN

Execution-oriented representation of a HEROIC plan.
This object describes work for downstream systems such as ALPHA.
It does not execute tasks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HeroicExecutionPlan:
    """Validated execution representation of a HEROIC plan."""

    plan_id: str
    mission_id: Optional[str] = None
    objective_id: Optional[str] = None
    goal_id: Optional[str] = None

    ordered_task_ids: List[str] = field(default_factory=list)
    parallel_task_groups: List[List[str]] = field(default_factory=list)
    dependency_map: Dict[str, List[str]] = field(default_factory=dict)

    required_capabilities: List[str] = field(default_factory=list)
    required_brains: List[str] = field(default_factory=list)

    inputs: Dict[str, Any] = field(default_factory=dict)
    expected_outputs: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    verification_required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.plan_id, str) or not self.plan_id.strip():
            raise ValueError("plan_id must be a non-empty string.")

        self.plan_id = self.plan_id.strip()
        self.ordered_task_ids = self._unique_strings(self.ordered_task_ids)

        task_ids = set(self.ordered_task_ids)

        normalized_groups: List[List[str]] = []
        for group in self.parallel_task_groups:
            normalized = [
                task_id
                for task_id in self._unique_strings(group)
                if task_id in task_ids
            ]
            if len(normalized) > 1 and normalized not in normalized_groups:
                normalized_groups.append(normalized)
        self.parallel_task_groups = normalized_groups

        normalized_dependencies: Dict[str, List[str]] = {}
        for task_id, dependencies in self.dependency_map.items():
            if task_id not in task_ids:
                raise ValueError(
                    f"Dependency map contains unknown task: {task_id}"
                )

            valid_dependencies = self._unique_strings(dependencies)

            for dependency_id in valid_dependencies:
                if dependency_id not in task_ids:
                    raise ValueError(
                        f"Task '{task_id}' depends on unknown task "
                        f"'{dependency_id}'."
                    )
                if dependency_id == task_id:
                    raise ValueError(
                        f"Task '{task_id}' cannot depend on itself."
                    )

            if valid_dependencies:
                normalized_dependencies[task_id] = valid_dependencies

        self.dependency_map = normalized_dependencies
        self._validate_dependency_order()

        for name in (
            "required_capabilities",
            "required_brains",
            "expected_outputs",
            "success_criteria",
            "constraints",
        ):
            setattr(self, name, self._unique_strings(getattr(self, name)))

    @staticmethod
    def _unique_strings(values: Optional[List[str]]) -> List[str]:
        result: List[str] = []

        for value in values or []:
            if isinstance(value, str):
                value = value.strip()
                if value and value not in result:
                    result.append(value)

        return result

    def _validate_dependency_order(self) -> None:
        """Ensure dependencies appear before the tasks that require them."""

        positions = {
            task_id: index
            for index, task_id in enumerate(self.ordered_task_ids)
        }

        for task_id, dependencies in self.dependency_map.items():
            for dependency_id in dependencies:
                if positions[dependency_id] >= positions[task_id]:
                    raise ValueError(
                        f"Execution order is not dependency-safe: "
                        f"'{dependency_id}' must precede '{task_id}'."
                    )

    def add_task(self, task_id: str) -> None:
        if not isinstance(task_id, str) or not task_id.strip():
            return

        task_id = task_id.strip()
        if task_id not in self.ordered_task_ids:
            self.ordered_task_ids.append(task_id)

    def add_parallel_group(self, task_ids: List[str]) -> None:
        normalized = self._unique_strings(task_ids)

        if any(task_id not in self.ordered_task_ids for task_id in normalized):
            raise ValueError("Parallel groups may contain only registered tasks.")

        if len(normalized) < 2:
            return

        if normalized not in self.parallel_task_groups:
            self.parallel_task_groups.append(normalized)

    def add_dependency(
        self,
        task_id: str,
        dependency_task_id: str,
    ) -> None:
        if task_id not in self.ordered_task_ids:
            raise ValueError(f"Unknown task: {task_id}")

        if dependency_task_id not in self.ordered_task_ids:
            raise ValueError(f"Unknown dependency task: {dependency_task_id}")

        if task_id == dependency_task_id:
            raise ValueError("A task cannot depend on itself.")

        dependencies = self.dependency_map.setdefault(task_id, [])

        if dependency_task_id not in dependencies:
            dependencies.append(dependency_task_id)

        try:
            self._validate_dependency_order()
        except ValueError:
            dependencies.remove(dependency_task_id)
            if not dependencies:
                self.dependency_map.pop(task_id, None)
            raise

    def add_required_capability(self, capability: str) -> None:
        if capability and capability not in self.required_capabilities:
            self.required_capabilities.append(capability)

    def add_required_brain(self, brain: str) -> None:
        if brain and brain not in self.required_brains:
            self.required_brains.append(brain)

    def add_expected_output(self, output: str) -> None:
        if output and output not in self.expected_outputs:
            self.expected_outputs.append(output)

    def add_success_criterion(self, criterion: str) -> None:
        if criterion and criterion not in self.success_criteria:
            self.success_criteria.append(criterion)

    def add_constraint(self, constraint: str) -> None:
        if constraint and constraint not in self.constraints:
            self.constraints.append(constraint)

    def is_empty(self) -> bool:
        return not self.ordered_task_ids

    def task_count(self) -> int:
        return len(self.ordered_task_ids)

    def parallel_stage_count(self) -> int:
        return len(self.parallel_task_groups)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "mission_id": self.mission_id,
            "objective_id": self.objective_id,
            "goal_id": self.goal_id,
            "ordered_task_ids": list(self.ordered_task_ids),
            "parallel_task_groups": [
                list(group) for group in self.parallel_task_groups
            ],
            "dependency_map": {
                task_id: list(dependencies)
                for task_id, dependencies in self.dependency_map.items()
            },
            "required_capabilities": list(self.required_capabilities),
            "required_brains": list(self.required_brains),
            "inputs": dict(self.inputs),
            "expected_outputs": list(self.expected_outputs),
            "success_criteria": list(self.success_criteria),
            "constraints": list(self.constraints),
            "verification_required": self.verification_required,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_plan_state(
        cls,
        plan: Any,
    ) -> "HeroicExecutionPlan":
        """Convert a planning state into a downstream execution plan."""

        if not getattr(plan, "plan_id", None):
            raise ValueError("Cannot convert a plan without a plan ID.")

        return cls(
            plan_id=plan.plan_id,
            mission_id=getattr(plan, "mission_id", None),
            objective_id=getattr(plan, "objective_id", None),
            goal_id=getattr(plan, "goal_id", None),
            ordered_task_ids=list(getattr(plan, "ordered_task_ids", [])),
            parallel_task_groups=[
                list(group)
                for group in getattr(plan, "parallel_task_groups", [])
            ],
            dependency_map={
                task_id: list(dependencies)
                for task_id, dependencies in getattr(
                    plan, "dependency_map", {}
                ).items()
            },
            required_capabilities=list(
                getattr(plan, "required_capabilities", [])
            ),
            required_brains=list(getattr(plan, "required_brains", [])),
            inputs=dict(getattr(plan, "inputs", {})),
            expected_outputs=list(getattr(plan, "expected_outputs", [])),
            success_criteria=list(getattr(plan, "success_criteria", [])),
            constraints=list(getattr(plan, "constraints", [])),
            verification_required=getattr(
                plan, "verification_required", True
            ),
            metadata=dict(getattr(plan, "metadata", {})),
        )


__all__ = ["HeroicExecutionPlan"]
