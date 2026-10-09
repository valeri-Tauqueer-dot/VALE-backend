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
    """Structured state representing one HEROIC objective."""

    objective_id: str
    description: str

    status: ObjectiveStatus = ObjectiveStatus.PENDING
    goal_id: Optional[str] = None
    priority: float = 0.5

    success_criteria: List[str] = field(default_factory=list)
    required_outcomes: List[str] = field(default_factory=list)
    unresolved_questions: List[str] = field(default_factory=list)

    constraints: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)

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

        if isinstance(self.status, str):
            self.status = ObjectiveStatus(self.status.lower())

        self.priority = max(
            0.0,
            min(1.0, float(self.priority)),
        )

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def activate(self) -> None:
        if self.status in {
            ObjectiveStatus.COMPLETED,
            ObjectiveStatus.FAILED,
            ObjectiveStatus.CANCELLED,
        }:
            raise ValueError(
                f"Cannot activate objective in status "
                f"'{self.status.value}'."
            )

        self.status = ObjectiveStatus.ACTIVE
        self._touch()

    def start(self) -> None:
        if self.status in {
            ObjectiveStatus.COMPLETED,
            ObjectiveStatus.FAILED,
            ObjectiveStatus.CANCELLED,
        }:
            raise ValueError(
                f"Cannot start objective in status "
                f"'{self.status.value}'."
            )

        self.status = ObjectiveStatus.IN_PROGRESS
        self._touch()

    def complete(self) -> None:
        if self.status in {
            ObjectiveStatus.FAILED,
            ObjectiveStatus.CANCELLED,
        }:
            raise ValueError(
                f"Cannot complete objective in status "
                f"'{self.status.value}'."
            )

        if self.blockers:
            raise ValueError(
                "Cannot complete an objective while blockers remain."
            )

        self.status = ObjectiveStatus.COMPLETED
        self.failure_reason = None
        self._touch()

    def block(self, reason: Optional[str] = None) -> None:
        if self.status in {
            ObjectiveStatus.COMPLETED,
            ObjectiveStatus.CANCELLED,
        }:
            raise ValueError(
                f"Cannot block objective in status "
                f"'{self.status.value}'."
            )

        if reason and reason not in self.blockers:
            self.blockers.append(reason)

        self.status = ObjectiveStatus.BLOCKED
        self.failure_reason = reason
        self._touch()

    def unblock(self, reason: Optional[str] = None) -> None:
        if reason is None:
            self.blockers.clear()
        elif reason in self.blockers:
            self.blockers.remove(reason)

        if (
            self.status == ObjectiveStatus.BLOCKED
            and not self.blockers
        ):
            self.status = ObjectiveStatus.PENDING

        self._touch()

    def fail(self, reason: Optional[str] = None) -> None:
        if self.status == ObjectiveStatus.COMPLETED:
            raise ValueError(
                "A completed objective cannot be marked failed."
            )

        self.status = ObjectiveStatus.FAILED
        self.failure_reason = reason
        self._touch()

    def cancel(self, reason: Optional[str] = None) -> None:
        if self.status == ObjectiveStatus.COMPLETED:
            raise ValueError(
                "A completed objective cannot be cancelled."
            )

        self.status = ObjectiveStatus.CANCELLED
        self.failure_reason = reason
        self._touch()

    def add_task(self, task_id: str) -> None:
        task_id = str(task_id).strip()

        if not task_id:
            raise ValueError("task_id cannot be empty.")

        if task_id not in self.task_ids:
            self.task_ids.append(task_id)
            self._touch()

    def add_dependency(self, objective_id: str) -> None:
        objective_id = str(objective_id).strip()

        if not objective_id:
            raise ValueError(
                "Dependency objective_id cannot be empty."
            )

        if objective_id == self.objective_id:
            raise ValueError(
                "An objective cannot depend on itself."
            )

        if objective_id not in self.dependency_objective_ids:
            self.dependency_objective_ids.append(objective_id)
            self._touch()

    def add_constraint(self, constraint: str) -> None:
        constraint = str(constraint).strip()

        if constraint and constraint not in self.constraints:
            self.constraints.append(constraint)
            self._touch()

    def add_assumption(self, assumption: str) -> None:
        assumption = str(assumption).strip()

        if assumption and assumption not in self.assumptions:
            self.assumptions.append(assumption)
            self._touch()

    def add_blocker(self, blocker: str) -> None:
        blocker = str(blocker).strip()

        if blocker and blocker not in self.blockers:
            self.blockers.append(blocker)

        if blocker and self.status not in {
            ObjectiveStatus.COMPLETED,
            ObjectiveStatus.CANCELLED,
            ObjectiveStatus.FAILED,
        }:
            self.status = ObjectiveStatus.BLOCKED

        if blocker:
            self._touch()

    def add_success_criterion(self, criterion: str) -> None:
        criterion = str(criterion).strip()

        if (
            criterion
            and criterion not in self.success_criteria
        ):
            self.success_criteria.append(criterion)
            self._touch()

    def add_required_outcome(self, outcome: str) -> None:
        outcome = str(outcome).strip()

        if outcome and outcome not in self.required_outcomes:
            self.required_outcomes.append(outcome)
            self._touch()

    def add_unresolved_question(self, question: str) -> None:
        question = str(question).strip()

        if (
            question
            and question not in self.unresolved_questions
        ):
            self.unresolved_questions.append(question)
            self._touch()

    def is_terminal(self) -> bool:
        return self.status in {
            ObjectiveStatus.COMPLETED,
            ObjectiveStatus.FAILED,
            ObjectiveStatus.CANCELLED,
        }

    def is_actionable(self) -> bool:
        return (
            self.status in {
                ObjectiveStatus.PENDING,
                ObjectiveStatus.ACTIVE,
                ObjectiveStatus.IN_PROGRESS,
            }
            and not self.blockers
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "status": self.status.value,
            "goal_id": self.goal_id,
            "priority": self.priority,
            "success_criteria": list(self.success_criteria),
            "required_outcomes": list(self.required_outcomes),
            "unresolved_questions": list(
                self.unresolved_questions
            ),
            "constraints": list(self.constraints),
            "assumptions": list(self.assumptions),
            "blockers": list(self.blockers),
            "task_ids": list(self.task_ids),
            "dependency_objective_ids": list(
                self.dependency_objective_ids
            ),
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "failure_reason": self.failure_reason,
        }
