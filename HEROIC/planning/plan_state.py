"""
HEROIC PLAN STATE

Stores the structured planning state for a HEROIC objective.
Does not execute tasks, activate brains, or optimize runtime execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class PlanStatus(str, Enum):
    CREATED = "created"
    DRAFT = "draft"
    READY = "ready"
    EXECUTING = "executing"
    BLOCKED = "blocked"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanType(str, Enum):
    SINGLE_TASK = "single_task"
    MULTI_TASK = "multi_task"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


@dataclass
class HeroicPlanState:
    """Structured state for one HEROIC plan."""

    plan_id: str = field(
        default_factory=lambda: f"heroic-plan-{uuid4().hex}"
    )
    objective_id: Optional[str] = None
    goal_id: Optional[str] = None
    mission_id: Optional[str] = None
    description: str = ""

    status: PlanStatus = PlanStatus.CREATED
    plan_type: PlanType = PlanType.MULTI_TASK

    task_ids: List[str] = field(default_factory=list)
    ordered_task_ids: List[str] = field(default_factory=list)
    parallel_task_groups: List[List[str]] = field(default_factory=list)
    dependency_map: Dict[str, List[str]] = field(default_factory=dict)

    required_capabilities: List[str] = field(default_factory=list)
    required_brains: List[str] = field(default_factory=list)

    inputs: Dict[str, Any] = field(default_factory=dict)
    expected_outputs: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    unresolved_questions: List[str] = field(default_factory=list)

    verification_required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.status, PlanStatus):
            self.status = PlanStatus(self.status)

        if not isinstance(self.plan_type, PlanType):
            self.plan_type = PlanType(self.plan_type)

        for name in (
            "task_ids",
            "ordered_task_ids",
            "required_capabilities",
            "required_brains",
            "expected_outputs",
            "success_criteria",
            "constraints",
            "blockers",
            "assumptions",
            "unresolved_questions",
        ):
            setattr(self, name, self._unique_strings(getattr(self, name)))

        valid_ids = set(self.task_ids)

        self.ordered_task_ids = [
            task_id
            for task_id in self.ordered_task_ids
            if task_id in valid_ids
        ]

        normalized_groups: List[List[str]] = []
        for group in self.parallel_task_groups:
            valid_group = [
                task_id
                for task_id in self._unique_strings(group)
                if task_id in valid_ids
            ]
            if len(valid_group) > 1 and valid_group not in normalized_groups:
                normalized_groups.append(valid_group)
        self.parallel_task_groups = normalized_groups

        normalized_dependencies: Dict[str, List[str]] = {}
        for task_id, dependencies in self.dependency_map.items():
            if task_id not in valid_ids:
                continue

            valid_dependencies = [
                dependency_id
                for dependency_id in self._unique_strings(dependencies)
                if dependency_id in valid_ids and dependency_id != task_id
            ]

            if valid_dependencies:
                normalized_dependencies[task_id] = valid_dependencies

        self.dependency_map = normalized_dependencies

    @staticmethod
    def _unique_strings(values: Optional[List[str]]) -> List[str]:
        result: List[str] = []
        for value in values or []:
            if isinstance(value, str):
                value = value.strip()
                if value and value not in result:
                    result.append(value)
        return result

    def _is_terminal(self) -> bool:
        return self.status in {
            PlanStatus.COMPLETED,
            PlanStatus.FAILED,
            PlanStatus.CANCELLED,
        }

    def add_task(self, task_id: str) -> None:
        if not isinstance(task_id, str) or not task_id.strip():
            return

        task_id = task_id.strip()
        if task_id not in self.task_ids:
            self.task_ids.append(task_id)

    def add_ordered_task(self, task_id: str) -> None:
        if not isinstance(task_id, str) or not task_id.strip():
            return

        task_id = task_id.strip()
        self.add_task(task_id)

        if task_id not in self.ordered_task_ids:
            self.ordered_task_ids.append(task_id)

    def add_parallel_group(self, task_ids: List[str]) -> None:
        valid_ids: List[str] = []

        for task_id in task_ids or []:
            if not isinstance(task_id, str) or not task_id.strip():
                continue

            task_id = task_id.strip()
            if task_id in self.task_ids and task_id not in valid_ids:
                valid_ids.append(task_id)

        if len(valid_ids) > 1 and valid_ids not in self.parallel_task_groups:
            self.parallel_task_groups.append(valid_ids)

    def add_dependency(
        self,
        task_id: str,
        dependency_task_id: str,
    ) -> None:
        if not isinstance(task_id, str) or not isinstance(
            dependency_task_id, str
        ):
            return

        task_id = task_id.strip()
        dependency_task_id = dependency_task_id.strip()

        if not task_id or not dependency_task_id:
            return

        if task_id == dependency_task_id:
            raise ValueError("A task cannot depend on itself.")

        if task_id not in self.task_ids:
            raise ValueError(f"Unknown dependent task: {task_id}")

        if dependency_task_id not in self.task_ids:
            raise ValueError(f"Unknown dependency task: {dependency_task_id}")

        dependencies = self.dependency_map.setdefault(task_id, [])
        if dependency_task_id not in dependencies:
            dependencies.append(dependency_task_id)

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

    def add_blocker(self, blocker: str) -> None:
        if not isinstance(blocker, str) or not blocker.strip():
            return

        blocker = blocker.strip()
        if blocker not in self.blockers:
            self.blockers.append(blocker)

        if not self._is_terminal():
            self.status = PlanStatus.BLOCKED

    def remove_blocker(self, blocker: str) -> bool:
        if blocker not in self.blockers:
            return False

        self.blockers.remove(blocker)

        if not self.blockers and self.status == PlanStatus.BLOCKED:
            self.status = PlanStatus.DRAFT

        return True

    def add_assumption(self, assumption: str) -> None:
        if assumption and assumption not in self.assumptions:
            self.assumptions.append(assumption)

    def add_unresolved_question(self, question: str) -> None:
        if question and question not in self.unresolved_questions:
            self.unresolved_questions.append(question)

    def is_blocked(self) -> bool:
        return bool(self.blockers)

    def is_ready(self) -> bool:
        if self._is_terminal() or self.is_blocked():
            return False

        if not self.task_ids or self.unresolved_questions:
            return False

        if not self.success_criteria:
            return False

        if set(self.ordered_task_ids) != set(self.task_ids):
            return False

        return True

    def mark_ready(self) -> None:
        if self.is_ready():
            self.status = PlanStatus.READY

    def mark_executing(self) -> None:
        if self.status == PlanStatus.READY and self.is_ready():
            self.status = PlanStatus.EXECUTING

    def mark_replanning(self) -> None:
        if not self._is_terminal():
            self.status = PlanStatus.REPLANNING

    def mark_completed(self) -> None:
        if self._is_terminal():
            return

        if self.blockers or self.unresolved_questions:
            return

        if self.verification_required and not self.metadata.get(
            "verification_passed", False
        ):
            return

        self.status = PlanStatus.COMPLETED

    def mark_failed(self, reason: Optional[str] = None) -> None:
        if self.status in {PlanStatus.COMPLETED, PlanStatus.CANCELLED}:
            return

        if reason and reason.strip():
            reason = reason.strip()
            if reason not in self.blockers:
                self.blockers.append(reason)

        self.status = PlanStatus.FAILED

    def mark_cancelled(self) -> None:
        if self.status not in {PlanStatus.COMPLETED, PlanStatus.FAILED}:
            self.status = PlanStatus.CANCELLED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "objective_id": self.objective_id,
            "goal_id": self.goal_id,
            "mission_id": self.mission_id,
            "description": self.description,
            "status": self.status.value,
            "plan_type": self.plan_type.value,
            "task_ids": list(self.task_ids),
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
            "blockers": list(self.blockers),
            "assumptions": list(self.assumptions),
            "unresolved_questions": list(self.unresolved_questions),
            "verification_required": self.verification_required,
            "metadata": dict(self.metadata),
        }


__all__ = ["PlanStatus", "PlanType", "HeroicPlanState"]
