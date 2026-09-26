"""
HEROIC BRAIN

VALE's mission and objective intelligence brain.

HEROIC determines what VALE actually needs to accomplish
before execution is delegated to ALPHA and specialized brains.

This version establishes the first working integration between:

- Mission Identity
- Mission State
- Intent State
- Goal State
- Objective State
- Task State

This is an initial integration foundation.

It does not yet:
- perform advanced intent reasoning
- select specialist brains
- execute tasks
- perform verification
- communicate with ALPHA
- perform final UNITY synthesis

Those capabilities will be added incrementally.
"""

from typing import Any, Dict, Optional
from uuid import uuid4

from vale_connector import VALEConnector
from vale_brain_interface import VALEBrainInterface

from HEROIC.identity import HeroicMissionIdentity
from HEROIC.state import HeroicMissionState
from HEROIC.intent import HeroicIntentState, IntentType
from HEROIC.goals import HeroicGoalState, GoalStatus
from HEROIC.objectives import HeroicObjectiveState, ObjectiveStatus
from HEROIC.tasks import HeroicTaskState, TaskStatus, TaskType


class HeroicBrain(VALEBrainInterface):
    """
    HEROIC mission and objective intelligence brain.

    The current implementation creates a structured HEROIC mission
    from an incoming request.

    Later versions will progressively add:
    - real intent intelligence
    - goal decomposition
    - objective decomposition
    - task planning
    - capability selection
    - brain activation
    - dependency planning
    - information sufficiency
    - evidence requirements
    - verification coordination
    - replanning
    - completion intelligence
    """

    VERSION = "0.2.0"
    ARCHITECTURE_STAGE = "HEROIC_FOUNDATIONAL_INTEGRATION"

    def __init__(self, connector: VALEConnector):
        super().__init__(
            brain_name="HEROIC",
            connector=connector
        )

    def think(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user request through the current HEROIC foundation.

        The current pipeline is:

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
        """

        if not isinstance(user_request, str):
            raise TypeError("user_request must be a string.")

        user_request = user_request.strip()

        if not user_request:
            raise ValueError("user_request cannot be empty.")

        context = context or {}

        # ---------------------------------------------------------
        # 1. CREATE MISSION IDENTITY
        # ---------------------------------------------------------

        mission_identity = HeroicMissionIdentity(
            mission_id=f"heroic-{uuid4().hex}",
            source="user",
            metadata={
                "brain": "HEROIC",
                "version": self.VERSION,
            }
        )

        # ---------------------------------------------------------
        # 2. CREATE MISSION STATE
        # ---------------------------------------------------------

        mission_state = HeroicMissionState(
            mission_id=mission_identity.mission_id,
            user_request=user_request,
            objective="",
        )

        mission_state.status = mission_state.status.UNDERSTANDING

        # ---------------------------------------------------------
        # 3. CREATE INITIAL INTENT STATE
        # ---------------------------------------------------------

        intent_state = HeroicIntentState(
            intent_type=IntentType.DIRECT_REQUEST,
            explicit_request=user_request,
            inferred_objective=user_request,
            confidence=0.5,
        )

        intent_state.add_signal(
            "The user supplied a direct request."
        )

        # ---------------------------------------------------------
        # 4. ESTABLISH INITIAL OBJECTIVE
        # ---------------------------------------------------------

        objective_id = f"objective-{uuid4().hex}"

        objective_state = HeroicObjectiveState(
            objective_id=objective_id,
            description=user_request,
            status=ObjectiveStatus.IDENTIFIED,
        )

        objective_state.add_success_criterion(
            "Produce a response addressing the user's request."
        )

        # ---------------------------------------------------------
        # 5. ESTABLISH INITIAL GOAL
        # ---------------------------------------------------------

        goal_id = f"goal-{uuid4().hex}"

        goal_state = HeroicGoalState(
            goal_id=goal_id,
            description=f"Successfully address the user's request: {user_request}",
            status=GoalStatus.IDENTIFIED,
        )

        goal_state.add_objective(objective_id)

        goal_state.add_success_criterion(
            "The user's requested outcome is addressed."
        )

        # ---------------------------------------------------------
        # 6. ESTABLISH INITIAL TASK
        # ---------------------------------------------------------

        task_id = f"task-{uuid4().hex}"

        task_state = HeroicTaskState(
            task_id=task_id,
            description=f"Process and address: {user_request}",
            task_type=TaskType.ANALYSIS,
            status=TaskStatus.READY,
            objective_id=objective_id,
            goal_id=goal_id,
        )

        task_state.add_expected_output(
            "A structured response addressing the user request."
        )

        task_state.add_success_criterion(
            "The task produces a response relevant to the request."
        )

        # ---------------------------------------------------------
        # 7. UPDATE MISSION STATE
        # ---------------------------------------------------------

        mission_state.objective = objective_state.description
        mission_state.intent = intent_state.explicit_request
        mission_state.intent_status = intent_state.confidence

        mission_state.add_required_capability(
            "objective_understanding"
        )

        mission_state.add_required_capability(
            "intent_understanding"
        )

        mission_state.add_required_capability(
            "task_definition"
        )

        mission_state.notes.append(
            "Initial HEROIC mission structure created."
        )

        mission_state.status = mission_state.status.READY

        # ---------------------------------------------------------
        # 8. BUILD STRUCTURED RESULT
        # ---------------------------------------------------------

        result = {
            "brain": "HEROIC",
            "version": self.VERSION,
            "architecture_stage": self.ARCHITECTURE_STAGE,
            "status": "mission_created",
            "message": (
                "HEROIC successfully created an initial mission "
                "structure from the user request."
            ),
            "mission": mission_identity.to_dict(),
            "intent": intent_state.to_dict(),
            "goal": goal_state.to_dict(),
            "objective": objective_state.to_dict(),
            "task": task_state.to_dict(),
            "mission_state": mission_state.to_dict(),
            "context": dict(context),
        }

        return result
