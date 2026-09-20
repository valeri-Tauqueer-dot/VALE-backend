"""
HEROIC GOAL STATE

Foundational representation of a larger mission goal.

A goal describes the broader outcome HEROIC is trying to achieve.
Objectives are the more concrete pieces that contribute toward
that goal.

This module defines state only.

It does not:
- interpret user intent
- decompose goals
- select capabilities
- activate brains
- execute tasks
- verify results
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GoalStatus(str, Enum):
    """
    Lifecycle status of a HEROIC goal.
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
class HeroicGoalState:
    """
    Structured state representing a HEROIC mission goal.
    """

    goal_id: str = ""

    description: str = ""

    status: GoalStatus = GoalStatus.UNDEFINED

    objective_ids: List[str] = field(default_factory=list)

    success_criteria: List[str] = field(default_factory=list)

    constraints: List[str] = field(default_factory=list)

    priorities: List[str] = field(default_factory=list)

    assumptions: List[str] = field(default_factory=list)

    unresolved_questions: List[str] = field(default_factory=list)

    blockers: List[str] = field(default_factory=list)

    parent_goal_id: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_objective(self, objective_id: str) -> None:
        """
        Associate an objective with this goal.
        """

        if objective_id and objective_id not in self.objective_ids:
            self.objective_ids.append(objective_id)

    def add_success_criterion(self, criterion: str) -> None:
        """
        Add a condition required for goal completion.
        """

        if criterion and criterion not in self.success_criteria:
            self.success_criteria.append(criterion)

    def add_constraint(self, constraint: str) -> None:
        """
        Add a constraint governing the goal.
        """

        if constraint and constraint not in self.constraints:
            self.constraints.append(constraint)

    def add_priority(self, priority: str) -> None:
        """
        Add a goal priority.
        """

        if priority and priority not in self.priorities:
            self.priorities.append(priority)

    def add_assumption(self, assumption: str) -> None:
        """
        Record an assumption associated with the goal.
        """

        if assumption and assumption not in self.assumptions:
            self.assumptions.append(assumption)

    def add_unresolved_question(self, question: str) -> None:
        """
        Record an unresolved question affecting the goal.
        """

        if question and question not in self.unresolved_questions:
            self.unresolved_questions.append(question)

    def add_blocker(self, blocker: str) -> None:
        """
        Record a condition preventing goal progress.
        """

        if blocker and blocker not in self.blockers:
            self.blockers.append(blocker)

        self.status = GoalStatus.BLOCKED

    def is_ready(self) -> bool:
        """
        Determine whether the goal is sufficiently defined
        for downstream planning.
        """

        return (
            bool(self.description)
            and self.status in {
                GoalStatus.IDENTIFIED,
                GoalStatus.REFINED,
                GoalStatus.READY,
            }
            and not self.unresolved_questions
            and not self.blockers
        )

    def mark_in_progress(self) -> None:
        """
        Mark the goal as actively being pursued.
        """

        self.status = GoalStatus.IN_PROGRESS

    def mark_completed(self) -> None:
        """
        Mark the goal as completed.
        """

        self.status = GoalStatus.COMPLETED

    def mark_failed(self, reason: Optional[str] = None) -> None:
        """
        Mark the goal as failed.
        """

        if reason:
            self.add_blocker(reason)

        self.status = GoalStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert goal state into a serializable dictionary.
        """

        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "status": self.status.value,
            "objective_ids": list(self.objective_ids),
            "success_criteria": list(self.success_criteria),
            "constraints": list(self.constraints),
            "priorities": list(self.priorities),
            "assumptions": list(self.assumptions),
            "unresolved_questions": list(
                self.unresolved_questions
            ),
            "blockers": list(self.blockers),
            "parent_goal_id": self.parent_goal_id,
            "metadata": dict(self.metadata),
  }
