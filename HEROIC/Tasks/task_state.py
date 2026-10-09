from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class TaskStatus(str, Enum):
    """Lifecycle status of a HEROIC task."""

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
    """High-level classification of a HEROIC task."""

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
    """Structured state representing one concrete HEROIC task."""

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

    def __post_init__(self) -> None:
        self.task_id = str(self.task_id).strip()
        self.description = str(self.description).strip()

        if isinstance(self.task_type, str):
            self.task_type = TaskType(self.task_type.lower())

        if isinstance(self.status, str):
            self.status = TaskStatus(self.status.lower())

        self.dependency_task_ids = list(
            dict.fromkeys(self.dependency_task_ids)
        )
        self.required_capabilities = list(
            dict.fromkeys(self.required_capabilities)
        )
        self.required_brains = list(
            dict.fromkeys(self.required_brains)
        )

    def add_dependency(self, task_id: str) -> None:
        """Add a dependency without creating a self-dependency."""
        task_id = str(task_id).strip()

        if not task_id:
            raise ValueError("Dependency task_id cannot be empty.")

        if self.task_id and task_id == self.task_id:
            raise ValueError("A task cannot depend on itself.")

        if task_id not in self.dependency_task_ids:
            self.dependency_task_ids.append(task_id)

    def add_required_capability(self, capability: str) -> None:
        capability = str(capability).strip()

        if (
            capability
            and capability not in self.required_capabilities
        ):
            self.required_capabilities.append(capability)

    def add_required_brain(self, brain: str) -> None:
        brain = str(brain).strip()

        if brain and brain not in self.required_brains:
            self.required_brains.append(brain)

    def add_expected_output(self, output: str) -> None:
        output = str(output).strip()

        if output and output not in self.expected_outputs:
            self.expected_outputs.append(output)

    def add_success_criterion(self, criterion: str) -> None:
        criterion = str(criterion).strip()

        if criterion and criterion not in self.success_criteria:
            self.success_criteria.append(criterion)

    def add_blocker(self, blocker: str) -> None:
        blocker = str(blocker).strip()

        if blocker and blocker not in self.blockers:
            self.blockers.append(blocker)

        if blocker and self.status not in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            self.status = TaskStatus.BLOCKED

    def remove_blocker(self, blocker: str) -> None:
        if blocker in self.blockers:
            self.blockers.remove(blocker)

        if (
            not self.blockers
            and self.status == TaskStatus.BLOCKED
        ):
            self.status = TaskStatus.WAITING

    def is_ready(
        self,
        completed_task_ids: Optional[Set[str]] = None,
    ) -> bool:
        """
        Check whether this task is eligible to execute.

        If dependencies exist, their completion must be confirmed
        by supplying completed_task_ids. Missing confirmation is
        never treated as successful dependency completion.
        """
        if not self.description:
            return False

        if self.status != TaskStatus.READY:
            return False

        if self.blockers:
            return False

        if not self.dependency_task_ids:
            return True

        if completed_task_ids is None:
            return False

        completed = set(completed_task_ids)

        return all(
            dependency_id in completed
            for dependency_id in self.dependency_task_ids
        )

    def mark_ready(
        self,
        completed_task_ids: Optional[Set[str]] = None,
    ) -> bool:
        """Mark ready only when blockers and dependencies permit it."""
        if self.blockers:
            self.status = TaskStatus.BLOCKED
            return False

        if self.dependency_task_ids:
            if completed_task_ids is None:
                self.status = TaskStatus.WAITING
                return False

            completed = set(completed_task_ids)

            if not all(
                dependency_id in completed
                for dependency_id in self.dependency_task_ids
            ):
                self.status = TaskStatus.WAITING
                return False

        if not self.description:
            return False

        self.status = TaskStatus.READY
        return True

    def mark_running(self) -> None:
        if self.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            raise ValueError(
                f"Cannot run a task with status '{self.status.value}'."
            )

        if self.blockers:
            raise ValueError("Cannot run a task while blockers remain.")

        self.status = TaskStatus.RUNNING

    def mark_verifying(self) -> None:
        if self.status != TaskStatus.RUNNING:
            raise ValueError(
                "Only a running task can enter verification."
            )

        self.status = TaskStatus.VERIFYING

    def mark_completed(self) -> None:
        if self.status in {
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            raise ValueError(
                f"Cannot complete a task with status '{self.status.value}'."
            )

        if self.blockers:
            raise ValueError(
                "Cannot complete a task while blockers remain."
            )

        self.status = TaskStatus.COMPLETED

    def mark_failed(self, reason: Optional[str] = None) -> None:
        if self.status == TaskStatus.COMPLETED:
            raise ValueError("A completed task cannot be marked failed.")

        if reason:
            if reason not in self.blockers:
                self.blockers.append(reason)

        self.status = TaskStatus.FAILED

    def mark_cancelled(self) -> None:
        if self.status == TaskStatus.COMPLETED:
            raise ValueError("A completed task cannot be cancelled.")

        self.status = TaskStatus.CANCELLED

    def to_dict(self) -> Dict[str, Any]:
        """Convert task state into a serializable dictionary."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "objective_id": self.objective_id,
            "goal_id": self.goal_id,
            "parent_task_id": self.parent_task_id,
            "dependency_task_ids": list(self.dependency_task_ids),
            "required_capabilities": list(self.required_capabilities),
            "required_brains": list(self.required_brains),
            "inputs": dict(self.inputs),
            "expected_outputs": list(self.expected_outputs),
            "success_criteria": list(self.success_criteria),
            "constraints": list(self.constraints),
            "blockers": list(self.blockers),
            "assumptions": list(self.assumptions),
            "metadata": dict(self.metadata),
            }
