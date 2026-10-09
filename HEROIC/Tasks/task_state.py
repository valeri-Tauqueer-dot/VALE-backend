"""
HEROIC TASK STATE

Defines the lifecycle and state of one HEROIC task.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
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
        if (
            task_id
            and task_id != self.task_id
            and task_id not in self.dependency_task_ids
        ):
            self.dependency_task_ids.append(task_id)

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

    def add_blocker(self, blocker: str) -> None:
        if blocker and blocker not in self.blockers:
            self.blockers.append(blocker)

        if self.status not in (
            TaskStatus.COMPLETED,
            TaskStatus.CANCELLED,
        ):
            self.status = TaskStatus.BLOCKED

    def remove_blocker(self, blocker: str) -> bool:
        if blocker not in self.blockers:
            return False

        self.blockers.remove(blocker)

        if not self.blockers and self.status == TaskStatus.BLOCKED:
            self.status = TaskStatus.CREATED

        return True

    def dependencies_satisfied(
        self,
        task_states: Dict[str, "HeroicTaskState"],
    ) -> bool:
        """Return true only when every dependency exists and is completed."""

        for dependency_id in self.dependency_task_ids:
            dependency = task_states.get(dependency_id)

            if dependency is None:
                return False

            if dependency.status != TaskStatus.COMPLETED:
                return False

        return True

    def is_ready(
        self,
        task_states: Optional[Dict[str, "HeroicTaskState"]] = None,
    ) -> bool:
        """Check readiness without assuming missing dependencies are complete."""

        if not self.description.strip():
            return False

        if self.blockers:
            return False

        if self.status not in (
            TaskStatus.CREATED,
            TaskStatus.READY,
            TaskStatus.WAITING,
        ):
            return False

        if self.dependency_task_ids:
            if task_states is None:
                return False

            if not self.dependencies_satisfied(task_states):
                return False

        return True

    def mark_ready(
        self,
        task_states: Optional[Dict[str, "HeroicTaskState"]] = None,
    ) -> bool:
        if not self.is_ready(task_states):
            return False

        self.status = TaskStatus.READY
        return True

    def mark_running(self) -> None:
        if self.blockers:
            raise ValueError("Cannot run a task while blockers remain.")

        if self.status != TaskStatus.READY:
            raise ValueError("A task must be READY before it can run.")

        self.status = TaskStatus.RUNNING

    def mark_verifying(self) -> None:
        if self.status != TaskStatus.RUNNING:
            raise ValueError("Only a RUNNING task can enter verification.")

        self.status = TaskStatus.VERIFYING

    def mark_completed(self) -> None:
        if self.status != TaskStatus.VERIFYING:
            raise ValueError(
                "A task must be VERIFYING before it can be completed."
            )

        self.status = TaskStatus.COMPLETED

    def mark_failed(self, reason: Optional[str] = None) -> None:
        if reason:
            self.add_blocker(reason)

        self.status = TaskStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
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
