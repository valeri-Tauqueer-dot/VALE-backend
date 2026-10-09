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
    """Lifecycle state of a HEROIC plan."""

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
    """High-level classification of a HEROIC plan."""

    SINGLE_TASK = "single_task"
    MULTI_TASK = "multi_task"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


@dataclass
class HeroicPlanState:
    """Structured state for a HEROIC execution plan."""

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
        """Normalize enum values and remove duplicate state entries."""

        if not isinstance(self.status, PlanStatus):
            self.status = PlanStatus(self.status)

        if not isinstance(self.plan_type, PlanType):
            self.plan_type = PlanType(self.plan_type)

        self.task_ids = self._unique_strings(self.task_ids)
        self.ordered_task_ids = self._unique_strings(
            self.ordered_task_ids
        )
        self.required_capabilities = self._unique_strings(
            self.required_capabilities
        )
        self.required_brains = self._unique_strings(
            self.required_brains
        )
        self.expected_outputs = self._unique_strings(
            self.expected_outputs
        )
        self.success_criteria = self._unique_strings(
            self.success_criteria
        )
        self.constraints = self._unique_strings(self.constraints)
        self.blockers = self._unique_strings(self.blockers)
        self.assumptions = self._unique_strings(self.assumptions)
        self.unresolved_questions = self._unique_strings(
            self.unresolved_questions
        )

        normalized_groups: List[List[str]] = []
        for group in self.parallel_task_groups:
            valid_group = self._unique_strings(group)
            if valid_group and valid_group not in normalized_groups:
                normalized_groups.append(valid_group)
        self.parallel_task_groups = normalized_groups

        normalized_dependencies: Dict[str, List[str]] = {}
        for task_id, dependencies in self.dependency_map.items():
            if not task_id:
                continue

            valid_dependencies = [
                dependency_id
                for dependency_id in self._unique_strings(dependencies)
                if dependency_id != task_id
            ]

            if valid_dependencies:
                normalized_dependencies[task_id] = valid_dependencies

        self.dependency_map = normalized_dependencies

    @staticmethod
    def _unique_strings(values: List[str]) -> List[str]:
        """Return non-empty, unique strings while preserving order."""

        result: List[str] = []
        for value in values or []:
            if isinstance(value, str):
                value = value.strip()
                if value and value not in result:
                    result.append(value)
        return result

    def _is_terminal(self) -> bool:
        """Return whether the plan has reached a terminal state."""

        return self.status in {
            PlanStatus.COMPLETED,
            PlanStatus.FAILED,
            PlanStatus.CANCELLED,
        }

    def add_task(self, task_id: str) -> None:
        """Register a task without duplicating it."""

        if not task_id or not task_id.strip():
            return

        task_id = task_id.strip()

        if task_id not in self.task_ids:
            self.task_ids.append(task_id)

    def add_ordered_task(self, task_id: str) -> None:
        """Add a registered task to the preliminary task ordering."""

        if not task_id or not task_id.strip():
            return

        task_id = task_id.strip()
        self.add_task(task_id)

        if task_id not in self.ordered_task_ids:
            self.ordered_task_ids.append(task_id)

    def add_parallel_group(self, task_ids: List[str]) -> None:
        """Register a group of tasks that may be independent."""

        valid_ids: List[str] = []

        for task_id in task_ids or []:
            if not task_id or not task_id.strip():
                continue

            task_id = task_id.strip()

            if task_id in self.task_ids and task_id not in valid_ids:
                valid_ids.append(task_id)

        if len(valid_ids) < 2:
            return

        if valid_ids not in self.parallel_task_groups:
            self.parallel_task_groups.append(valid_ids)

    def add_dependency(
        self,
        task_id: str,
        dependency_task_id: str,
    ) -> None:
        """
        Record that task_id depends on dependency_task_id.

        Both tasks must already belong to the plan. Self-dependencies
        are rejected. Longer dependency cycles must be checked by the
        dependency-planning subsystem.
        """

        if not task_id or not dependency_task_id:
            return

        task_id = task_id.strip()
        dependency_task_id = dependency_task_id.strip()

        if not task_id or not dependency_task_id:
            return

        if task_id == dependency_task_id:
            return

        if task_id not in self.task_ids:
            return

        if dependency_task_id not in self.task_ids:
            return

        dependencies = self.dependency_map.setdefault(task_id, [])

        if dependency_task_id not in dependencies:
            dependencies.append(dependency_task_id)

    def add_required_capability(self, capability: str) -> None:
        """Add a required capability."""

        if capability and capability not in self.required_capabilities:
            self.required_capabilities.append(capability)

    def add_required_brain(self, brain: str) -> None:
        """Add a required VALE brain."""

        if brain and brain not in self.required_brains:
            self.required_brains.append(brain)

    def add_expected_output(self, output: str) -> None:
        """Add an expected plan output."""

        if output and output not in self.expected_outputs:
            self.expected_outputs.append(output)

    def add_success_criterion(self, criterion: str) -> None:
        """Add a plan success criterion."""

        if criterion and criterion not in self.success_criteria:
            self.success_criteria.append(criterion)

    def add_constraint(self, constraint: str) -> None:
        """Add a planning constraint."""

        if constraint and constraint not in self.constraints:
            self.constraints.append(constraint)

    def add_blocker(self, blocker: str) -> None:
        """
        Record a blocker without overwriting a terminal status.

        A failed plan remains FAILED; a cancelled plan remains CANCELLED.
        """

        if not blocker or not blocker.strip():
            return

        blocker = blocker.strip()

        if blocker not in self.blockers:
            self.blockers.append(blocker)

        if not self._is_terminal():
            self.status = PlanStatus.BLOCKED

    def remove_blocker(self, blocker: str) -> bool:
        """Remove a blocker and report whether it was present."""

        if blocker not in self.blockers:
            return False

        self.blockers.remove(blocker)

        if (
            not self.blockers
            and self.status == PlanStatus.BLOCKED
        ):
            self.status = PlanStatus.DRAFT

        return True

    def add_assumption(self, assumption: str) -> None:
        """Add an explicit planning assumption."""

        if assumption and assumption not in self.assumptions:
            self.assumptions.append(assumption)

    def add_unresolved_question(self, question: str) -> None:
        """Record an unresolved planning question."""

        if (
            question
            and question not in self.unresolved_questions
        ):
            self.unresolved_questions.append(question)

    def is_blocked(self) -> bool:
        """Return whether the plan currently contains blockers."""

        return bool(self.blockers)

    def is_ready(self) -> bool:
        """
        Determine whether the plan has enough structure to be ready.

        Readiness does not mean ALPHA has approved or executed it.
        """

        if self._is_terminal():
            return False

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
        """Mark the plan READY only when its requirements are met."""

        if self.is_ready():
            self.status = PlanStatus.READY

    def mark_executing(self) -> None:
        """Mark a ready plan as entering execution."""

        if self.status == PlanStatus.READY and self.is_ready():
            self.status = PlanStatus.EXECUTING

    def mark_replanning(self) -> None:
        """Mark a non-terminal plan for replanning."""

        if not self._is_terminal():
            self.status = PlanStatus.REPLANNING

    def mark_completed(self) -> None:
        """Complete a plan only if it is not blocked or terminal."""

        if self._is_terminal():
            return

        if self.blockers:
            return

        if self.unresolved_questions:
            return

        self.status = PlanStatus.COMPLETED

    def mark_failed(self, reason: Optional[str] = None) -> None:
        """Mark the plan FAILED and preserve its failure reason."""

        if self.status in {
            PlanStatus.COMPLETED,
            PlanStatus.CANCELLED,
        }:
            return

        if reason and reason.strip():
            reason = reason.strip()
            if reason not in self.blockers:
                self.blockers.append(reason)

        self.status = PlanStatus.FAILED

    def mark_cancelled(self) -> None:
        """Cancel a plan unless it is already completed or failed."""

        if self.status in {
            PlanStatus.COMPLETED,
            PlanStatus.FAILED,
        }:
            return

        self.status = PlanStatus.CANCELLED

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the plan into a JSON-compatible dictionary."""

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
