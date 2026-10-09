"""
VALE HEROIC BRAIN

HEROIC understands the mission, defines objectives, creates tasks,
builds dependency-aware plans, and prepares execution information
for downstream systems such as ALPHA.

HEROIC does not execute tasks or claim unverified completion.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from vale_brain_interface import VALEBrainInterface
from brain_state import VALEBrainState

from HEROIC.state.mission_state import HeroicMissionState
from HEROIC.objectives.objective_engine import HeroicObjectiveEngine
from HEROIC.objectives.objective_state import HeroicObjectiveState
from HEROIC.Tasks.task_engine import HeroicTaskEngine
from HEROIC.planning.task_planner import HeroicTaskPlanner
from HEROIC.planning.dependency_planner import HeroicDependencyPlanner
from HEROIC.planning.execution_plan import HeroicExecutionPlan


class HeroicBrain(VALEBrainInterface):
    """VALE-compatible HEROIC mission and planning brain."""

    VERSION = "0.3.0"
    BRAIN_NAME = "HEROIC"

    def __init__(self, connector: Any) -> None:
        super().__init__(
            brain_name=self.BRAIN_NAME,
            connector=connector,
        )

        self.version = self.VERSION

        self._mission_states: Dict[str, HeroicMissionState] = {}
        self._planning_cache: Dict[
            str, Tuple[str, Dict[str, Any]]
        ] = {}

        self._objective_engine = HeroicObjectiveEngine()
        self._task_engine = HeroicTaskEngine()
        self._task_planner = HeroicTaskPlanner()
        self._dependency_planner = HeroicDependencyPlanner()

    @staticmethod
    def _extract_request(state: VALEBrainState) -> str:
        """Extract the user request from known VALE state fields."""

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
        """Maintain mission state for the current VALE task."""

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
            description=user_request,
            metadata={
                "mission_id": mission.mission_id,
                "source": "HEROIC",
            },
        )

        if not isinstance(objective, HeroicObjectiveState):
            raise TypeError(
                "The objective engine did not return a "
                "HeroicObjectiveState."
            )

        tasks = self._task_engine.create_tasks(objective)

        if not tasks:
            raise ValueError(
                "The task engine did not generate any tasks "
                "for the objective."
            )

        for task in tasks:
            objective.add_task(task.task_id)

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

        plan_status = plan.status.value

        if plan_status == "ready":
            result_status = "PLAN_READY"
        elif plan_status == "blocked":
            result_status = "PLAN_BLOCKED"
        else:
            result_status = "PLAN_DRAFT"

        return {
            "status": result_status,
            "planning_status": plan_status,
            "objective": objective.to_dict(),
            "tasks": [task.to_dict() for task in tasks],
            "plan": plan.to_dict(),
            "execution_plan": execution_plan.to_dict(),
            "planning_performed": True,
            "planning_error": None,
        }

    def _create_result(
        self,
        state: VALEBrainState,
        mission: HeroicMissionState,
        user_request: str,
    ) -> Dict[str, Any]:
        """Create a truthful mission and planning result."""

        if not user_request:
            mission.add_missing_information(
                "A non-empty user request is required to define "
                "the mission."
            )

            return {
                "brain": self.BRAIN_NAME,
                "version": self.version,
                "status": "NEEDS_INFORMATION",
                "role": "MISSION_AND_OBJECTIVE_COORDINATION",
                "task_id": str(state.task_id),
                "mission": mission.to_dict(),
                "planning_performed": False,
                "planning_status": "NOT_STARTED",
                "objective": None,
                "tasks": [],
                "plan": None,
                "execution_plan": None,
                "execution_performed": False,
                "verification_performed": False,
                "planning_error": None,
            }

        try:
            planning_result = self._build_plan(
                mission=mission,
                user_request=user_request,
            )

        except Exception as exc:
            # Report the failure rather than inventing a successful plan.
            return {
                "brain": self.BRAIN_NAME,
                "version": self.version,
                "status": "PLANNING_ERROR",
                "role": "MISSION_AND_OBJECTIVE_COORDINATION",
                "task_id": str(state.task_id),
                "mission": mission.to_dict(),
                "planning_performed": False,
                "planning_status": "ERROR",
                "objective": None,
                "tasks": [],
                "plan": None,
                "execution_plan": None,
                "execution_performed": False,
                "verification_performed": False,
                "planning_error": (
                    f"{type(exc).__name__}: {exc}"
                ),
            }

        return {
            "brain": self.BRAIN_NAME,
            "version": self.version,
            "role": "MISSION_AND_OBJECTIVE_COORDINATION",
            "task_id": str(state.task_id),
            "mission": mission.to_dict(),
            **planning_result,
            "execution_performed": False,
            "verification_performed": False,
        }

    def think(self, state: VALEBrainState) -> Dict[str, Any]:
        """
        Capture a mission, build a preliminary plan, and publish
        the result to VALE's shared task state.
        """

        if state is None:
            raise ValueError("state must not be None.")

        task_id = str(state.task_id)
        user_request = self._extract_request(state)
        mission = self._get_or_create_mission(
            state=state,
            user_request=user_request,
        )

        cached = self._planning_cache.get(task_id)

        if cached is not None and cached[0] == user_request:
            result = dict(cached[1])
            result["mission"] = mission.to_dict()
        else:
            result = self._create_result(
                state=state,
                mission=mission,
                user_request=user_request,
            )

            if user_request and result["status"] != "PLANNING_ERROR":
                self._planning_cache[task_id] = (
                    user_request,
                    dict(result),
                )

        state.set("heroic_status", result["status"])
        state.set("heroic_mission", mission.to_dict())
        state.set("heroic_result", result)

        state.event(
            "heroic_mission_state_updated",
            self.BRAIN_NAME,
            payload={
                "task_id": task_id,
                "status": result["status"],
                "has_user_request": bool(user_request),
                "planning_performed": result["planning_performed"],
                "execution_performed": False,
                "verification_performed": False,
            },
        )

        return result

    def get_mission_state(
        self,
        task_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return the serialized mission state for a VALE task."""

        mission = self._mission_states.get(str(task_id))

        if mission is None:
            return None

        return mission.to_dict()

    def identity(self) -> Dict[str, Any]:
        """Expose HEROIC identity through the VALE brain interface."""

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
