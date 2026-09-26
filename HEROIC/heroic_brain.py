"""
HEROIC BRAIN
============

VALE's mission and objective intelligence brain.

HEROIC determines what VALE actually needs to accomplish
before execution is delegated to ALPHA and specialized brains.

Current stage:

    User Request
        ↓
    Mission Identity
        ↓
    Mission State
        ↓
    Intent State
        ↓
    Goal State
        ↓
    Objective State
        ↓
    Initial Task Definition
        ↓
    Structured HEROIC Result

This version intentionally does NOT import HEROIC.Tasks because
the current repository contains:

    HEROIC/Tasks/mission_state.py

while HEROIC/Tasks/__init__.py currently references:

    HEROIC/Tasks/task_state.py

which does not exist yet.

That Tasks package will be corrected as a separate step.

This module therefore keeps the application startup safe while
still integrating the currently valid HEROIC foundation modules.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from vale_connector import VALEConnector
from vale_brain_interface import VALEBrainInterface

from HEROIC.identity import HeroicMissionIdentity

from HEROIC.state import (
    HeroicMissionState,
    MissionStatus,
    EpistemicStatus,
)

from HEROIC.Intent import (
    HeroicIntentState,
    IntentType,
)

from HEROIC.goals import (
    HeroicGoalState,
    GoalStatus,
)

from HEROIC.objectives import (
    HeroicObjectiveState,
    ObjectiveStatus,
)


class HeroicBrain(VALEBrainInterface):
    """
    HEROIC mission and objective intelligence brain.

    Current responsibilities:

    - create mission identity
    - create mission state
    - represent initial user intent
    - establish an initial goal
    - establish an initial objective
    - define an initial task
    - return a structured HEROIC result

    Future responsibilities will be added incrementally:

    - advanced intent intelligence
    - goal decomposition
    - objective decomposition
    - task planning
    - capability selection
    - brain activation
    - dependency planning
    - information sufficiency
    - evidence requirements
    - coordination
    - ALPHA execution planning
    - verification coordination
    - replanning
    - completion intelligence
    - escalation
    """

    VERSION = "0.2.1"

    ARCHITECTURE_STAGE = (
        "HEROIC_FOUNDATIONAL_INTEGRATION"
    )

    def __init__(
        self,
        connector: VALEConnector,
    ):
        super().__init__(
            brain_name="HEROIC",
            connector=connector,
        )

    # ==============================================================
    # PUBLIC THINK
    # ==============================================================

    def think(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a user request through the current HEROIC foundation.

        This is intentionally a foundational mission-construction
        step, not the complete HEROIC reasoning system.
        """

        # ----------------------------------------------------------
        # Validate request
        # ----------------------------------------------------------

        if not isinstance(
            user_request,
            str,
        ):
            raise TypeError(
                "user_request must be a string."
            )

        user_request = user_request.strip()

        if not user_request:
            raise ValueError(
                "user_request cannot be empty."
            )

        context = (
            dict(context)
            if isinstance(context, dict)
            else {}
        )

        # ----------------------------------------------------------
        # 1. MISSION IDENTITY
        # ----------------------------------------------------------

        mission_id = (
            f"heroic-{uuid4().hex}"
        )

        mission_identity = (
            HeroicMissionIdentity(
                mission_id=mission_id,
                source="user",
                metadata={
                    "brain": "HEROIC",
                    "version": self.VERSION,
                    "architecture_stage": (
                        self.ARCHITECTURE_STAGE
                    ),
                },
            )
        )

        # ----------------------------------------------------------
        # 2. MISSION STATE
        # ----------------------------------------------------------

        mission_state = HeroicMissionState(
            mission_id=mission_id,
            user_request=user_request,
        )

        mission_state.status = (
            MissionStatus.UNDERSTANDING
        )

        mission_state.relevant_context = (
            dict(context)
        )

        # HEROIC itself is active for this mission.
        mission_state.add_active_brain(
            "HEROIC"
        )

        # ----------------------------------------------------------
        # 3. INTENT STATE
        # ----------------------------------------------------------

        intent_state = HeroicIntentState(
            intent_type=IntentType.DIRECT_REQUEST,
            explicit_request=user_request,
            inferred_objective=user_request,
            confidence=0.5,
        )

        intent_state.add_signal(
            "The user supplied a direct request."
        )

        intent_state.add_assumption(
            "The request text is the current authoritative "
            "description of the requested task."
        )

        # IMPORTANT:
        #
        # confidence is a numeric property of IntentState.
        #
        # mission_state.intent_status is an EpistemicStatus.
        #
        # They must not be mixed.

        mission_state.intent = (
            intent_state.inferred_objective
        )

        mission_state.intent_status = (
            EpistemicStatus.INFERRED
        )

        # ----------------------------------------------------------
        # 4. OBJECTIVE
        # ----------------------------------------------------------

        objective_id = (
            f"objective-{uuid4().hex}"
        )

        objective_state = (
            HeroicObjectiveState(
                objective_id=objective_id,
                description=user_request,
                status=ObjectiveStatus.IDENTIFIED,
            )
        )

        objective_state.add_success_criterion(
            "Produce a response that addresses "
            "the user's request."
        )

        objective_state.add_required_outcome(
            "A response relevant to the user's request."
        )

        # ----------------------------------------------------------
        # 5. GOAL
        # ----------------------------------------------------------

        goal_id = (
            f"goal-{uuid4().hex}"
        )

        goal_state = HeroicGoalState(
            goal_id=goal_id,
            description=(
                "Successfully address the user's "
                "current request."
            ),
            status=GoalStatus.IDENTIFIED,
        )

        goal_state.add_objective(
            objective_id
        )

        goal_state.add_success_criterion(
            "The user's requested outcome is addressed."
        )

        # ----------------------------------------------------------
        # 6. INITIAL TASK
        #
        # The repository's Tasks package is not yet safe to import.
        #
        # Therefore we represent the initial task as structured
        # mission data here.
        #
        # Once the dedicated HeroicTaskState file is corrected,
        # this dictionary will be replaced by that state object.
        # ----------------------------------------------------------

        task_id = (
            f"task-{uuid4().hex}"
        )

        task_state = {
            "task_id": task_id,
            "description": (
                f"Process and address: "
                f"{user_request}"
            ),
            "task_type": "analysis",
            "status": "ready",
            "objective_id": objective_id,
            "goal_id": goal_id,
            "dependency_task_ids": [],
            "required_capabilities": [
                "objective_understanding",
                "intent_understanding",
                "task_definition",
            ],
            "required_brains": [
                "HEROIC",
            ],
            "inputs": {
                "user_request": user_request,
            },
            "expected_outputs": [
                "A structured response addressing "
                "the user request."
            ],
            "success_criteria": [
                "The task produces a response "
                "relevant to the request."
            ],
            "constraints": [],
            "blockers": [],
            "assumptions": [
                "The user request is the current "
                "mission input."
            ],
            "metadata": {
                "architecture_stage": (
                    self.ARCHITECTURE_STAGE
                ),
            },
        }

        # ----------------------------------------------------------
        # 7. CONNECT MISSION STATE
        # ----------------------------------------------------------

        mission_state.objective = (
            objective_state.description
        )

        mission_state.add_required_capability(
            "intent_understanding"
        )

        mission_state.add_required_capability(
            "objective_understanding"
        )

        mission_state.add_required_capability(
            "goal_definition"
        )

        mission_state.add_required_capability(
            "task_definition"
        )

        mission_state.notes.append(
            "Initial HEROIC mission structure created."
        )

        mission_state.status = (
            MissionStatus.READY
        )

        # ----------------------------------------------------------
        # 8. BUILD STRUCTURED RESULT
        # ----------------------------------------------------------

        result = {
            "brain": "HEROIC",
            "version": self.VERSION,
            "architecture_stage": (
                self.ARCHITECTURE_STAGE
            ),
            "status": "mission_created",
            "message": (
                "HEROIC successfully created an "
                "initial mission structure from "
                "the user request."
            ),
            "mission": (
                mission_identity.to_dict()
            ),
            "intent": (
                intent_state.to_dict()
            ),
            "goal": (
                goal_state.to_dict()
            ),
            "objective": (
                objective_state.to_dict()
            ),
            "task": task_state,
            "mission_state": (
                mission_state.to_dict()
            ),
            "context": dict(context),
        }

        return result
