from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ObjectiveStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class HeroicObjectiveState:
    objective_id: str
    description: str
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    goal_id: Optional[str] = None
    priority: float = 0.5
    success_criteria: List[str] = field(default_factory=list)
    task_ids: List[str] = field(default_factory=list)
    dependency_objective_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    failure_reason: Optional[str] = None

    def __post_init__(self) -> None:
        self.objective_id = str(self.objective_id).strip()
        self.description = str(self.description).strip()

        if not self.objective_id:
            raise ValueError("objective_id cannot be empty.")

        if not self.description:
            raise ValueError("description cannot be empty.")

        self.priority = max(0.0, min(1.0, float(self.priority)))

        if isinstance(self.status, str):
            self.status = ObjectiveStatus(self.status.lower())

    def activate(self) -> None:
        if self.status in {
            ObjectiveStatus.COMPLETED,
            ObjectiveStatus.CANCELLED,
            ObjectiveStatus.FAILED,
        }:
            raise ValueError(
                f"Cannot activate an objective with status "
                f"'{self.status.value}'."
            )

        self.status = ObjectiveStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)

    def start(self) -> None:
        if self.status in {
            ObjectiveStatus.COMPLETED,
            ObjectiveStatus.CANCELLED,
            ObjectiveStatus.FAILED,
        }:
            raise ValueError(
                f"Cannot start an objective with status "
                f"'{self.status.value}'."
            )

        self.status = ObjectiveStatus.IN_PROGRESS
        self.updated_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        if self.status in {
            ObjectiveStatus.CANCELLED,
            ObjectiveStatus.FAILED,
        }:
            raise ValueError(
                f"Cannot complete an objective with status "
                f"'{self.status.value}'."
            )

        self.status = ObjectiveStatus.COMPLETED
        self.failure_reason = None
        self.updated_at = datetime.now(timezone.utc)

    def block(self, reason: Optional[str] = None) -> None:
        if self.status == ObjectiveStatus.COMPLETED:
            raise ValueError("A completed objective cannot be blocked.")

        self.status = ObjectiveStatus.BLOCKED
        self.failure_reason = reason
        self.updated_at = datetime.now(timezone.utc)

    def fail(self, reason: Optional[str] = None) -> None:
        if self.status == ObjectiveStatus.COMPLETED:
            raise ValueError("A completed objective cannot be marked failed.")

        self.status = ObjectiveStatus.FAILED
        self.failure_reason = reason
        self.updated_at = datetime.now(timezone.utc)

    def cancel(self, reason: Optional[str] = None) -> None:
        if self.status == ObjectiveStatus.COMPLETED:
            raise ValueError("A completed objective cannot be cancelled.")

        self.status = ObjectiveStatus.CANCELLED
        self.failure_reason = reason
        self.updated_at = datetime.now(timezone.utc)

    def add_task(self, task_id: str) -> None:
        task_id = str(task_id).strip()

        if not task_id:
            raise ValueError("task_id cannot be empty.")

        if task_id not in self.task_ids:
            self.task_ids.append(task_id)
            self.updated_at = datetime.now(timezone.utc)

    def add_dependency(self, objective_id: str) -> None:
        objective_id = str(objective_id).strip()

        if not objective_id:
            raise ValueError("dependency objective_id cannot be empty.")

        if objective_id == self.objective_id:
            raise ValueError("An objective cannot depend on itself.")

        if objective_id not in self.dependency_objective_ids:
            self.dependency_objective_ids.append(objective_id)
            self.updated_at = datetime.now(timezone.utc)

    def is_terminal(self) -> bool:
        return self.status in {
            ObjectiveStatus.COMPLETED,
            ObjectiveStatus.FAILED,
            ObjectiveStatus.CANCELLED,
        }

    def is_actionable(self) -> bool:
        return self.status in {
            ObjectiveStatus.PENDING,
            ObjectiveStatus.ACTIVE,
            ObjectiveStatus.IN_PROGRESS,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "status": self.status.value,
            "goal_id": self.goal_id,
            "priority": self.priority,
            "success_criteria": list(self.success_criteria),
            "task_ids": list(self.task_ids),
            "dependency_objective_ids": list(
                self.dependency_objective_ids
            ),
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "failure_reason": self.failure_reason,
    }
