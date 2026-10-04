"""
HEROIC PLAN STATE

Defines the foundational state representation for a HEROIC plan.

A plan represents HEROIC's structured understanding of the work
that must be performed to accomplish an objective.

This module stores planning state only.

It does NOT:
    - execute tasks
    - optimize execution
    - activate brains
    - perform verification
    - replace ALPHA
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class PlanStatus(str, Enum):
    """
    Lifecycle state of a HEROIC plan.
    """

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
    """
    High-level classification of a HEROIC plan.
    """

    SINGLE_TASK = "single_task"
    MULTI_TASK = "multi_task"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


@dataclass
class HeroicPlanState:
    """
    Structured state for a HEROIC execution plan.
    """

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

    def add_task(self, task_id: str) -> None:
        """
        Add a task to the plan without duplicating it.
        """

        if task_id and task_id not in self.task_ids:
            self.task_ids.append(task_id)

    def add_ordered_task(self, task_id: str) -> None:
        """
        Add a task to the execution ordering.
        """

        if task_id and task_id not in self.ordered_task_ids:
            self.ordered_task_ids.append(task_id)

    def add_parallel_group(self, task_ids: List[str]) -> None:
        """
        Add a group of tasks that may execute independently.
        """

        valid_ids = [
            task_id
            for task_id in task_ids
            if task_id and task_id in self.task_ids
        ]

        if valid_ids:
            self.parallel_task_groups.append(valid_ids)

    def add_dependency(
        self,
        task_id: str,
        dependency_task_id: str,
    ) -> None:
        """
        Record that task_id depends on dependency_task_id.
        """

        if not task_id or not dependency_task_id:
            return

        dependencies = self.dependency_map.setdefault(
            task_id,
            [],
        )

        if dependency_task_id not in dependencies:
            dependencies.append(dependency_task_id)

    def add_required_capability(self, capability: str) -> None:
        """
        Add a required capability.
        """

        if capability and capability not in self.required_capabilities:
            self.required_capabilities.append(capability)

    def add_required_brain(self, brain: str) -> None:
        """
        Add a required VALE brain.
        """

        if brain and brain not in self.required_brains:
            self.required_brains.append(brain)

    def add_expected_output(self, output: str) -> None:
        """
        Add an expected plan output.
        """

        if output and output not in self.expected_outputs:
            self.expected_outputs.append(output)

    def add_success_criterion(self, criterion: str) -> None:
        """
        Add a success criterion.
        """

        if criterion and criterion not in self.success_criteria:
            self.success_criteria.append(criterion)

    def add_constraint(self, constraint: str) -> None:
        """
        Add a planning constraint.
        """

        if constraint and constraint not in self.constraints:
            self.constraints.append(constraint)

    def add_blocker(self, blocker: str) -> None:
        """
        Add a blocker and mark the plan blocked.
        """

        if blocker and blocker not in self.blockers:
            self.blockers.append(blocker)

        self.status = PlanStatus.BLOCKED

    def add_assumption(self, assumption: str) -> None:
        """
        Add an explicit planning assumption.
        """

        if assumption and assumption not in self.assumptions:
            self.assumptions.append(assumption)

    def add_unresolved_question(self, question: str) -> None:
        """
        Add an unresolved planning question.
        """

        if question and question not in self.unresolved_questions:
            self.unresolved_questions.append(question)

    def is_blocked(self) -> bool:
        """
        Return whether the plan currently contains blockers.
        """

        return bool(self.blockers)

    def is_ready(self) -> bool:
        """
        Determine whether the plan contains enough structure to
        enter execution.

        This does not mean that ALPHA has approved or executed it.
        """

        if self.is_blocked():
            return False

        if not self.task_ids:
            return False

        if self.unresolved_questions:
            return False

        if not self.success_criteria:
            return False

        return True

    def mark_ready(self) -> None:
        """
        Mark the plan ready when its readiness conditions are met.
        """

        if self.is_ready():
            self.status = PlanStatus.READY

    def mark_executing(self) -> None:
        """
        Mark the plan as entering execution.
        """

        self.status = PlanStatus.EXECUTING

    def mark_replanning(self) -> None:
        """
        Mark the plan for replanning.
        """

        self.status = PlanStatus.REPLANNING

    def mark_completed(self) -> None:
        """
        Mark the plan completed.
        """

        self.status = PlanStatus.COMPLETED

    def mark_failed(self, reason: Optional[str] = None) -> None:
        """
        Mark the plan failed and optionally record the reason.
        """

        self.status = PlanStatus.FAILED

        if reason:
            self.add_blocker(reason)

    def mark_cancelled(self) -> None:
        """
        Mark the plan cancelled.
        """

        self.status = PlanStatus.CANCELLED

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the plan state into a JSON-compatible dictionary.
        """

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
                list(group)
                for group in self.parallel_task_groups
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


__all__ = [
    "PlanStatus",
    "PlanType",
    "HeroicPlanState",
  ]
