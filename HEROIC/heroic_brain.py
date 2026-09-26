"""
HEROIC BRAIN
============

VALE's mission and objective intelligence brain.

HEROIC determines what VALE actually needs to accomplish
before execution is delegated to ALPHA and specialized brains.

Current integration:

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
    Task State
        ↓
    Structured HEROIC Result

This is the foundational HEROIC integration stage.

It does not yet perform:
- advanced intent reasoning
- goal decomposition intelligence
- capability selection
- brain activation
- dependency planning
- ALPHA execution
- specialist brain execution
- MCVL verification
- replanning
- completion intelligence
- escalation intelligence

Those capabilities will be added progressively.
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

from HEROIC.Tasks import (
    HeroicTaskState,
    TaskStatus,
    TaskType,
)


class HeroicBrain(VALEBrainInterface):
    """
    Foundational HEROIC mission and objective intelligence brain.
    """

    VERSION = "0.2.2"

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
    # THINK
    # ==============================================================

    def think(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convert a user request into an initial structured
        HEROIC mission.

        This method currently builds the mission structure.
        It does not yet perform advanced reasoning or execution.
        """

        # ----------------------------------------------------------
        # 1. VALIDATE REQUEST
        # ----------------------------------------------------------

        if not isinstance(user_request, str):
            raise TypeError(
                "user_request must be a string."
            )

        user_request = user_request.strip()

        if not user_request:
            raise ValueError(
                "user_request cannot be empty."
            )

        if context is None:
            context = {}

        if not isinstance(context, dict):
            raise TypeError(
                "context must be a dictionary when provided."
            )

        # ----------------------------------------------------------
        # 2. CREATE MISSION IDENTITY
        # ----------------------------------------------------------

        mission_id = (
            f"heroic-{uuid4().hex}"
        )

        mission_identity = HeroicMissionIdentity(
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

        # ----------------------------------------------------------
        # 3. CREATE MISSION STATE
        # ----------------------------------------------------------

        mission_state = HeroicMissionState(
            mission_id=mission_id,
            user_request=user_request,
        )

        mission_state.status = (
            MissionStatus.UNDERSTANDING
        )

        mission_state.relevant_context = dict(
            context
        )

        mission_state.add_active_brain(
            "HEROIC"
        )

        # ----------------------------------------------------------
        # 4. CREATE INITIAL INTENT STATE
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
            "The request text is the current mission input."
        )

        mission_state.intent = (
            intent_state.inferred_objective
        )

        mission_state.intent_status = (
            EpistemicStatus.INFERRED
        )

        # ----------------------------------------------------------
        # 5. CREATE OBJECTIVE
        # ----------------------------------------------------------

        objective_id = (
            f"objective-{uuid4().hex}"
        )

        objective_state = HeroicObjectiveState(
            objective_id=objective_id,
            description=user_request,
            status=ObjectiveStatus.IDENTIFIED,
        )

        objective_state.add_success_criterion(
            "Produce a response that addresses "
            "the user's request."
        )

        objective_state.add_required_outcome(
            "A response relevant to the user's request."
        )

        # ----------------------------------------------------------
        # 6. CREATE GOAL
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
        # 7. CREATE TASK
        # ----------------------------------------------------------

        task_id = (
            f"task-{uuid4().hex}"
        )

        task_state = HeroicTaskState(
            task_id=task_id,
            description=(
                f"Process and address: "
                f"{user_request}"
            ),
            task_type=TaskType.ANALYSIS,
            status=TaskStatus.READY,
            objective_id=objective_id,
            goal_id=goal_id,
        )

        task_state.add_required_capability(
            "intent_understanding"
        )

        task_state.add_required_capability(
            "objective_understanding"
        )

        task_state.add_required_capability(
            "task_definition"
        )

        task_state.add_required_brain(
            "HEROIC"
        )

        task_state.add_expected_output(
            "A structured response addressing "
            "the user's request."
        )

        task_state.add_success_criterion(
            "The task produces a response "
            "relevant to the request."
        )

        task_state.assumptions.append(
            "The user request is the current "
            "mission input."
        )

        task_state.metadata.update(
            {
                "architecture_stage": (
                    self.ARCHITECTURE_STAGE
                ),
                "brain": "HEROIC",
            }
        )

        # ----------------------------------------------------------
        # 8. CONNECT INFORMATION INTO MISSION STATE
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

        mission_state.information_state = (
            mission_state.information_state.SUFFICIENT
        )

        mission_state.notes.append(
            "Initial HEROIC mission structure created."
        )

        mission_state.status = (
            MissionStatus.READY
        )

        # ----------------------------------------------------------
        # 9. BUILD RESULT
        # ----------------------------------------------------------

        return {
            "brain": "HEROIC",
            "version": self.VERSION,
            "architecture_stage": (
                self.ARCHITECTURE_STAGE
            ),
            "status": "mission_created",
            "message": (
                "HEROIC successfully created "
                "an initial structured mission."
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
            "task": (
                task_state.to_dict()
            ),
            "mission_state": (
                mission_state.to_dict()
            ),
            "context": dict(context),
        }
