"""
HEROIC TASK STATE

Foundational representation of concrete work that HEROIC
may need to coordinate.

A task is an actionable unit derived from an objective.

This module defines task state only.

It does not:
- execute the task
- select the execution engine
- activate brains
- perform specialist reasoning
- verify results
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    """
    Lifecycle status of a HEROIC task.
    """

    CREATED = "created"
    READY = "ready"
    WAITING = "waiting"
    BLOCKED = "blocked"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """
    High-level classification of a HEROIC task.
    """

    ANALYSIS = "analysis"
    RESEARCH = "research"
    REASONING = "reasoning"
    DATA_RETRIEVAL = "data_retrieval"
    VERIFICATION = "verification"
    DECISION_SUPPORT = "decision_support"
    ACTION = "action"
    COMMUNICATION = "communication"
    OTHER = "other"


@dataclass
class HeroicTaskState:
    """
    Structured state representing one concrete HEROIC task.
    """

    task_id: str = ""

    description: str = ""

    task_type: TaskType = TaskType.OTHER

    status: TaskStatus = TaskStatus.CREATED

    objective_id: Optional[str] = None

    goal_id: Optional[str] = None

    parent_task_id: Optional[str] = None

    dependency_task_ids: List[str] = field(default_factory=list)

    required_capabilities: List[str] = field(default_factory=list)

    required_brains: List[str] = field(default_factory=list)

    inputs: Dict[str, Any] = field(default_factory=dict)

    expected_outputs: List[str] = field(default_factory=list)

    success_criteria: List[str] = field(default_factory=list)

    constraints: List[str] = field(default_factory=list)

    blockers: List[str] = field(default_factory=list)

    assumptions: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_dependency(self, task_id: str) -> None:
        """
        Add a task dependency.
        """

        if task_id and task_id != self.task_id:
            if task_id not in self.dependency_task_ids:
                self.dependency_task_ids.append(task_id)

    def add_required_capability(self, capability: str) -> None:
        """
        Record a capability required by this task.
        """

        if capability and capability not in self.required_capabilities:
            self.required_capabilities.append(capability)

    def add_required_brain(self, brain: str) -> None:
        """
        Record a brain required by this task.
        """

        if brain and brain not in self.required_brains:
            self.required_brains.append(brain)

    def add_expected_output(self, output: str) -> None:
        """
        Record an expected task output.
        """

        if output and output not in self.expected_outputs:
            self.expected_outputs.append(output)

    def add_success_criterion(self, criterion: str) -> None:
        """
        Record a condition required for successful completion.
        """

        if criterion and criterion not in self.success_criteria:
            self.success_criteria.append(criterion)

    def add_blocker(self, blocker: str) -> None:
        """
        Record a condition preventing task execution.
        """

        if blocker and blocker not in self.blockers:
            self.blockers.append(blocker)

        self.status = TaskStatus.BLOCKED

    def is_ready(self) -> bool:
        """
        Determine whether the task can enter execution.
        """

        return (
            bool(self.description)
            and self.status == TaskStatus.READY
            and not self.blockers
            and all(
                dependency_id in self.dependency_task_ids
                for dependency_id in self.dependency_task_ids
            )
        )

    def mark_running(self) -> None:
        """
        Mark the task as running.
        """

        self.status = TaskStatus.RUNNING

    def mark_verifying(self) -> None:
        """
        Mark the task as awaiting verification.
        """

        self.status = TaskStatus.VERIFYING

    def mark_completed(self) -> None:
        """
        Mark the task as completed.
        """

        self.status = TaskStatus.COMPLETED

    def mark_failed(self, reason: Optional[str] = None) -> None:
        """
        Mark the task as failed.
        """

        if reason:
            self.add_blocker(reason)

        self.status = TaskStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert task state into a serializable dictionary.
        """

        return {
            "task_id": self.task_id,
            "description": self.description,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "objective_id": self.objective_id,
            "goal_id": self.goal_id,
            "parent_task_id": self.parent_task_id,
            "dependency_task_ids": list(
                self.dependency_task_ids
            ),
            "required_capabilities": list(
                self.required_capabilities
            ),
            "required_brains": list(self.required_brains),
            "inputs": dict(self.inputs),
            "expected_outputs": list(self.expected_outputs),
            "success_criteria": list(self.success_criteria),
            "constraints": list(self.constraints),
            "blockers": list(self.blockers),
            "assumptions": list(self.assumptions),
            "metadata": dict(self.metadata),
          }
