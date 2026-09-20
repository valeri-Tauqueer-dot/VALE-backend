"""
HEROIC OBJECTIVE STATE

Foundational representation of what a HEROIC mission is trying
to accomplish.

This module defines objective state only.

It does not:
- interpret user intent
- select capabilities
- activate brains
- execute tasks
- verify results
- make final decisions
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ObjectiveStatus(str, Enum):
    """
    Lifecycle status of a HEROIC objective.
    """

    UNDEFINED = "undefined"
    IDENTIFIED = "identified"
    REFINED = "refined"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class HeroicObjectiveState:
    """
    Structured state representing a HEROIC objective.
    """

    objective_id: str = ""

    description: str = ""

    status: ObjectiveStatus = ObjectiveStatus.UNDEFINED

    success_criteria: List[str] = field(default_factory=list)

    constraints: List[str] = field(default_factory=list)

    required_outcomes: List[str] = field(default_factory=list)

    priorities: List[str] = field(default_factory=list)

    assumptions: List[str] = field(default_factory=list)

    unresolved_questions: List[str] = field(default_factory=list)

    blockers: List[str] = field(default_factory=list)

    parent_objective_id: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_success_criterion(self, criterion: str) -> None:
        """
        Add a condition that must be satisfied for completion.
        """

        if criterion and criterion not in self.success_criteria:
            self.success_criteria.append(criterion)

    def add_constraint(self, constraint: str) -> None:
        """
        Add a constraint governing the objective.
        """

        if constraint and constraint not in self.constraints:
            self.constraints.append(constraint)

    def add_required_outcome(self, outcome: str) -> None:
        """
        Add an outcome required by the objective.
        """

        if outcome and outcome not in self.required_outcomes:
            self.required_outcomes.append(outcome)

    def add_priority(self, priority: str) -> None:
        """
        Add an objective priority.
        """

        if priority and priority not in self.priorities:
            self.priorities.append(priority)

    def add_assumption(self, assumption: str) -> None:
        """
        Record an assumption associated with the objective.
        """

        if assumption and assumption not in self.assumptions:
            self.assumptions.append(assumption)

    def add_unresolved_question(self, question: str) -> None:
        """
        Record a question that remains unresolved.
        """

        if question and question not in self.unresolved_questions:
            self.unresolved_questions.append(question)

    def add_blocker(self, blocker: str) -> None:
        """
        Record a condition preventing objective progress.
        """

        if blocker and blocker not in self.blockers:
            self.blockers.append(blocker)

        self.status = ObjectiveStatus.BLOCKED

    def is_ready(self) -> bool:
        """
        Determine whether the objective has enough structure
        to enter execution planning.
        """

        return (
            bool(self.description)
            and self.status in {
                ObjectiveStatus.IDENTIFIED,
                ObjectiveStatus.REFINED,
                ObjectiveStatus.READY,
            }
            and not self.unresolved_questions
            and not self.blockers
        )

    def mark_in_progress(self) -> None:
        """
        Mark the objective as actively being pursued.
        """

        self.status = ObjectiveStatus.IN_PROGRESS

    def mark_completed(self) -> None:
        """
        Mark the objective as completed.
        """

        self.status = ObjectiveStatus.COMPLETED

    def mark_failed(self, reason: Optional[str] = None) -> None:
        """
        Mark the objective as failed.
        """

        if reason:
            self.add_blocker(reason)

        self.status = ObjectiveStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert objective state into a serializable dictionary.
        """

        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "status": self.status.value,
            "success_criteria": list(self.success_criteria),
            "constraints": list(self.constraints),
            "required_outcomes": list(self.required_outcomes),
            "priorities": list(self.priorities),
            "assumptions": list(self.assumptions),
            "unresolved_questions": list(self.unresolved_questions),
            "blockers": list(self.blockers),
            "parent_objective_id": self.parent_objective_id,
            "metadata": dict(self.metadata),
      }
