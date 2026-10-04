"""
HEROIC GOAL ENGINE

Purpose
-------
The Goal Engine converts HEROIC's interpreted intent into a
structured goal.

The Goal Engine answers:

    "What broader outcome is HEROIC trying to achieve?"

It does NOT:
    - execute the goal
    - select the final execution method
    - activate brains
    - perform verification
    - make trading decisions
    - replace ALPHA, MCVL, or UNITY

It creates the goal representation that later HEROIC components
can use for objective decomposition and task planning.

Design principle
----------------
A goal must describe the intended outcome, not prematurely
describe how that outcome will be executed.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from HEROIC.Intent.intent_state import HeroicIntentState, IntentType
from HEROIC.goals.goal_state import HeroicGoalState, GoalStatus


class HeroicGoalEngine:
    """
    Converts a HeroicIntentState into a HeroicGoalState.
    """

    def __init__(self) -> None:
        self.engine_name = "HEROIC_GOAL_ENGINE"
        self.version = "0.1.0"

    def create_goal(
        self,
        intent_state: HeroicIntentState,
        context: Optional[Dict[str, Any]] = None,
    ) -> HeroicGoalState:
        """
        Create a structured goal from an interpreted intent.

        Parameters
        ----------
        intent_state:
            Structured intent produced by the HEROIC Intent Engine.

        context:
            Optional contextual information.

        Returns
        -------
        HeroicGoalState
            Structured HEROIC goal.
        """

        description = self._build_goal_description(intent_state)

        goal = HeroicGoalState(
            description=description,
            status=GoalStatus.IDENTIFIED,
        )

        self._populate_success_criteria(goal, intent_state)
        self._populate_priorities(goal, intent_state)
        self._populate_constraints(goal, context)
        self._populate_assumptions(goal, intent_state)

        if not intent_state.is_sufficient():
            goal.add_unresolved_question(
                "The user's intent contains unresolved ambiguity."
            )

        if intent_state.required_clarifications:
            for clarification in intent_state.required_clarifications:
                goal.add_unresolved_question(clarification)

        return goal

    def _build_goal_description(
        self,
        intent_state: HeroicIntentState,
    ) -> str:
        """
        Convert intent into a goal-oriented outcome.
        """

        inferred = (intent_state.inferred_objective or "").strip()

        if inferred:
            return inferred

        explicit = (intent_state.explicit_request or "").strip()

        if explicit:
            return f"Determine and satisfy the user's requested outcome: {explicit}"

        return "Determine the user's required outcome before execution."

    def _populate_success_criteria(
        self,
        goal: HeroicGoalState,
        intent_state: HeroicIntentState,
    ) -> None:
        """
        Define conservative success criteria based on intent type.
        """

        intent_type = intent_state.intent_type

        if intent_type == IntentType.INFORMATION_REQUEST:
            goal.add_success_criterion(
                "Provide the requested information accurately and appropriately."
            )

        elif intent_type == IntentType.DECISION_REQUEST:
            goal.add_success_criterion(
                "Provide decision support addressing the user's stated choice."
            )
            goal.add_success_criterion(
                "Identify material uncertainty or missing information."
            )

        elif intent_type == IntentType.ACTION_REQUEST:
            goal.add_success_criterion(
                "Identify the requested action and determine the requirements "
                "necessary to complete it."
            )

        elif intent_type == IntentType.ANALYSIS:
            goal.add_success_criterion(
                "Produce an analysis addressing the user's requested subject."
            )
            goal.add_success_criterion(
                "Separate established information from inference and uncertainty."
            )

        elif intent_type == IntentType.COMPARISON:
            goal.add_success_criterion(
                "Compare the requested subjects using relevant criteria."
            )

        elif intent_type == IntentType.EXPLORATION:
            goal.add_success_criterion(
                "Investigate the requested subject sufficiently to address "
                "the user's objective."
            )

        elif intent_type == IntentType.CLARIFICATION:
            goal.add_success_criterion(
                "Resolve the ambiguity or question identified by the user."
            )

        elif intent_type == IntentType.CORRECTION:
            goal.add_success_criterion(
                "Identify and correct the previously identified issue."
            )

        elif intent_type == IntentType.CONTINUATION:
            goal.add_success_criterion(
                "Continue the previously established objective without "
                "unnecessary task drift."
            )

        else:
            goal.add_success_criterion(
                "Determine and satisfy the outcome required by the user."
            )

    def _populate_priorities(
        self,
        goal: HeroicGoalState,
        intent_state: HeroicIntentState,
    ) -> None:
        """
        Add goal-level priorities.

        Execution priority is not determined here. ALPHA may later
        optimize execution priority and resource allocation.
        """

        goal.add_priority("Preserve the user's actual objective.")

        if intent_state.ambiguity_detected:
            goal.add_priority(
                "Resolve material ambiguity before committing to execution."
            )

        if intent_state.intent_type in (
            IntentType.DECISION_REQUEST,
            IntentType.ANALYSIS,
        ):
            goal.add_priority(
                "Avoid unsupported conclusions and identify relevant uncertainty."
            )

        goal.add_priority(
            "Avoid unnecessary scope expansion."
        )

    def _populate_constraints(
        self,
        goal: HeroicGoalState,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """
        Transfer explicit goal-relevant constraints from context.

        Only constraints represented explicitly in the supplied
        context are transferred. The engine does not invent them.
        """

        if not context:
            return

        constraints = context.get("constraints")

        if isinstance(constraints, dict):
            for name, value in constraints.items():
                goal.add_constraint(
                    f"{name}: {value}"
                )

        elif isinstance(constraints, (list, tuple, set)):
            for constraint in constraints:
                goal.add_constraint(str(constraint))

        elif isinstance(constraints, str) and constraints.strip():
            goal.add_constraint(constraints.strip())

    def _populate_assumptions(
        self,
        goal: HeroicGoalState,
        intent_state: HeroicIntentState,
    ) -> None:
        """
        Preserve intent assumptions as explicit assumptions.

        Assumptions are never silently treated as facts.
        """

        for assumption in intent_state.assumptions:
            goal.add_assumption(assumption)

        if intent_state.intent_type == IntentType.CONTINUATION:
            goal.add_assumption(
                "Relevant previous mission context may be required."
            )

        if intent_state.intent_type == IntentType.CORRECTION:
            goal.add_assumption(
                "A previous result or statement may require reassessment."
          )
