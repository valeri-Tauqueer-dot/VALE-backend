"""
HEROIC OBJECTIVE ENGINE

Purpose
-------
Converts a HEROIC goal into a concrete objective.

Goal answers:
    "What broader outcome are we trying to achieve?"

Objective answers:
    "What specifically must be accomplished to achieve that goal?"

This module does NOT:
    - execute tasks
    - activate brains
    - optimize execution
    - verify evidence
    - replace ALPHA, MCVL, or UNITY

It prepares a structured objective for later task decomposition
and execution planning.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from HEROIC.goals.goal_state import HeroicGoalState, GoalStatus
from HEROIC.objectives.objective_state import (
    HeroicObjectiveState,
    ObjectiveStatus,
)


class HeroicObjectiveEngine:
    """
    Converts a structured HEROIC goal into an actionable objective.
    """

    def __init__(self) -> None:
        self.engine_name = "HEROIC_OBJECTIVE_ENGINE"
        self.version = "0.1.0"

    def create_objective(
        self,
        goal_state: HeroicGoalState,
        context: Optional[Dict[str, Any]] = None,
    ) -> HeroicObjectiveState:
        """
        Create an objective from a HEROIC goal.

        Parameters
        ----------
        goal_state:
            Structured goal produced by the Goal Engine.

        context:
            Optional contextual information.

        Returns
        -------
        HeroicObjectiveState
            Structured objective for further HEROIC planning.
        """

        description = self._build_description(goal_state)

        objective = HeroicObjectiveState(
            description=description,
            status=ObjectiveStatus.IDENTIFIED,
        )

        self._transfer_goal_requirements(
            objective=objective,
            goal_state=goal_state,
        )

        self._define_success_criteria(
            objective=objective,
            goal_state=goal_state,
        )

        self._define_required_outcomes(
            objective=objective,
            goal_state=goal_state,
        )

        self._transfer_context_constraints(
            objective=objective,
            context=context,
        )

        self._preserve_uncertainty(
            objective=objective,
            goal_state=goal_state,
        )

        return objective

    def _build_description(
        self,
        goal_state: HeroicGoalState,
    ) -> str:
        """
        Create a concrete objective description from the goal.
        """

        description = (goal_state.description or "").strip()

        if description:
            return (
                "Accomplish the identified HEROIC goal with the "
                "required information, capabilities, and verification."
                f" Goal: {description}"
            )

        return (
            "Determine and accomplish the concrete outcome required "
            "by the current HEROIC mission."
        )

    def _transfer_goal_requirements(
        self,
        objective: HeroicObjectiveState,
        goal_state: HeroicGoalState,
    ) -> None:
        """
        Preserve relevant goal-level assumptions and unresolved
        questions without silently converting them into facts.
        """

        for assumption in goal_state.assumptions:
            objective.add_assumption(assumption)

        for question in goal_state.unresolved_questions:
            objective.add_unresolved_question(question)

        for blocker in goal_state.blockers:
            objective.add_blocker(blocker)

    def _define_success_criteria(
        self,
        objective: HeroicObjectiveState,
        goal_state: HeroicGoalState,
    ) -> None:
        """
        Convert goal success criteria into objective criteria.
        """

        for criterion in goal_state.success_criteria:
            objective.add_success_criterion(criterion)

        if not goal_state.success_criteria:
            objective.add_success_criterion(
                "Produce the outcome required by the identified goal."
            )

        objective.add_success_criterion(
            "Maintain alignment with the original user objective."
        )

    def _define_required_outcomes(
        self,
        objective: HeroicObjectiveState,
        goal_state: HeroicGoalState,
    ) -> None:
        """
        Define the concrete outputs HEROIC should ultimately obtain.
        """

        if goal_state.required_outcomes:
            for outcome in goal_state.required_outcomes:
                objective.add_required_outcome(outcome)
        else:
            objective.add_required_outcome(
                "A result that satisfies the identified goal."
            )

    def _transfer_context_constraints(
        self,
        objective: HeroicObjectiveState,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """
        Transfer explicitly supplied constraints.

        No constraints are invented.
        """

        if not context:
            return

        constraints = context.get("constraints")

        if isinstance(constraints, dict):
            for name, value in constraints.items():
                objective.add_constraint(
                    f"{name}: {value}"
                )

        elif isinstance(constraints, (list, tuple, set)):
            for constraint in constraints:
                objective.add_constraint(str(constraint))

        elif isinstance(constraints, str) and constraints.strip():
            objective.add_constraint(constraints.strip())

    def _preserve_uncertainty(
        self,
        objective: HeroicObjectiveState,
        goal_state: HeroicGoalState,
    ) -> None:
        """
        Ensure unresolved goal conditions remain visible at the
        objective layer.
        """

        if goal_state.status == GoalStatus.BLOCKED:
            objective.add_blocker(
                "The parent goal is currently blocked."
            )

        if goal_state.unresolved_questions:
            objective.add_unresolved_question(
                "One or more goal-level questions remain unresolved."
            )

    def refine_objective(
        self,
        objective: HeroicObjectiveState,
        description: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> HeroicObjectiveState:
        """
        Refine an existing objective without replacing its state.

        This method provides a controlled entry point for later
        HEROIC planning and replanning systems.
        """

        if description is not None and description.strip():
            objective.description = description.strip()

        if context:
            self._transfer_context_constraints(
                objective=objective,
                context=context,
            )

        if objective.is_ready():
            objective.status = ObjectiveStatus.READY
        else:
            objective.status = ObjectiveStatus.REFINED

        return objective
