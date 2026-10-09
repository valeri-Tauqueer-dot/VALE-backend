"""
VALE HEROIC BRAIN

HEROIC determines what must be accomplished.
ALPHA optimizes how the work is executed.
HEROIC does not execute tasks or claim unverified completion.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from vale_brain_interface import VALEBrainInterface
from brain_state import VALEBrainState

from HEROIC.state.mission_state import HeroicMissionState
from HEROIC.objectives.objective_state import HeroicObjectiveState
from HEROIC.objectives.objective_engine import HeroicObjectiveEngine
from HEROIC.Tasks.task_engine import HeroicTaskEngine
from HEROIC.planning.task_planner import HeroicTaskPlanner
from HEROIC.planning.dependency_planner import HeroicDependencyPlanner
from HEROIC.planning.execution_plan import HeroicExecutionPlan


class HeroicBrain(VALEBrainInterface):
    """VALE-compatible mission and objective coordination brain."""

    VERSION = "0.2.0"
    BRAIN_NAME = "HEROIC"

    def __init__(self, connector: Any) -> None:
        super().__init__(
            brain_name=self.BRAIN_NAME,
            connector=connector,
        )

        self.version = self.VERSION
        self._mission_states: Dict[str, HeroicMissionState] = {}
        self._objective_engine = HeroicObjectiveEngine()
        self._task_engine = HeroicTaskEngine()
        self._task_planner = HeroicTaskPlanner()
        self._dependency_planner = HeroicDependencyPlanner()

    @staticmethod
    def _extract_request(state: VALEBrainState) -> str:
        """Extract the user request from known state fields."""

        for key in (
            "user_request",
            "user_input",
            "message",
            "request",
            "query",
        ):
            value = state.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""

    def _get_or_create_mission(
        self,
        state: VALEBrainState,
        user_request: str,
    ) -> HeroicMissionState:
        task_id = str(state.task_id)
        mission = self._mission_states.get(task_id)

        if mission is None:
            mission = HeroicMissionState(
                mission_id=task_id,
                user_request=user_request,
            )
            self._mission_states[task_id] = mission
        elif user_request and mission.user_request != user_request:
            mission.user_request = user_request

        return mission

    def _build_plan(
        self,
        mission: HeroicMissionState,
        user_request: str,
    ) -> Dict[str, Any]:
        """Build a preliminary plan without executing its tasks."""

        objective = self._objective_engine.create_objective(
            user_request
        )

        if objective is None:
            return {
                "planning_performed": False,
                "planning_status": "OBJECTIVE_NOT_CREATED",
                "objective": None,
                "tasks": [],
                "plan": None,
                "execution_plan": None,
                "planning_error": (
                    "The objective engine did not return an objective."
                ),
            }

        if not isinstance(objective, HeroicObjectiveState):
            raise TypeError(
                "HeroicObjectiveEngine.create_objective() must return "
                "HeroicObjectiveState."
            )

        tasks = self._task_engine.create_tasks(objective)

        plan = self._task_planner.build_plan(
            objective_state=objective,
            tasks=tasks,
            mission_id=mission.mission_id,
        )

        plan = self._dependency_planner.build_dependency_plan(
            plan=plan,
            tasks=tasks,
        )

        execution_plan = HeroicExecutionPlan.from_plan_state(plan)

        return {
            "planning_performed": True,
            "planning_status": plan.status.value,
            "objective": objective.to_dict(),
            "tasks": [task.to_dict() for task in tasks],
            "plan": plan.to_dict(),
            "execution_plan": execution_plan.to_dict(),
            "planning_error": None,
        }

    def think(self, state: VALEBrainState) -> Dict[str, Any]:
        """Capture the mission and build a preliminary plan."""

        if state is None:
            raise ValueError("state must not be None.")

        user_request = self._extract_request(state)
        mission = self._get_or_create_mission(state, user_request)

        if not user_request:
            mission.add_missing_information(
                "A non-empty user request is required to define "
                "the mission."
            )

            result = {
                "brain": self.BRAIN_NAME,
                "version": self.version,
                "status": "NEEDS_INFORMATION",
                "role": "MISSION_AND_OBJECTIVE_COORDINATION",
                "task_id": str(state.task_id),
                "mission": mission.to_dict(),
                "planning_performed": False,
                "execution_performed": False,
                "verification_performed": False,
                "planning_error": None,
            }
        else:
            planning_result = self._build_plan(mission, user_request)

            result = {
                "brain": self.BRAIN_NAME,
                "version": self.version,
                "status": (
                    "PLAN_BUILT"
                    if planning_result["planning_performed"]
                    else "PLANNING_BLOCKED"
                ),
                "role": "MISSION_AND_OBJECTIVE_COORDINATION",
                "task_id": str(state.task_id),
                "mission": mission.to_dict(),
                **planning_result,
                "execution_performed": False,
                "verification_performed": False,
            }

        state.set("heroic_status", result["status"])
        state.set("heroic_mission", mission.to_dict())
        state.set("heroic_result", result)

        state.event(
            "heroic_mission_state_updated",
            self.BRAIN_NAME,
            payload={
                "task_id": str(state.task_id),
                "status": result["status"],
                "has_user_request": bool(user_request),
                "planning_performed": result["planning_performed"],
            },
        )

        return result

    def get_mission_state(
        self,
        task_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return the serialized mission state for a task."""

        mission = self._mission_states.get(str(task_id))
        return mission.to_dict() if mission is not None else None

    def identity(self) -> Dict[str, Any]:
        """Expose HEROIC's identity through the VALE interface."""

        base = super().identity()
        if not isinstance(base, dict):
            base = {}

        base.update(
            {
                "brain": self.BRAIN_NAME,
                "version": self.version,
                "role": "MISSION_AND_OBJECTIVE_COORDINATION",
            }
        )
        return base


__all__ = ["HeroicBrain"]
