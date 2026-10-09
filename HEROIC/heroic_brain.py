"""
VALE HEROIC BRAIN

Role:
Mission understanding and objective coordination.

HEROIC determines what must be accomplished.
ALPHA remains responsible for execution optimization.
HEROIC does not claim that a task is complete without
the required verification.
"""

from future import annotations

from typing import Any, Dict, Optional

from vale_brain_interface import VALEBrainInterface
from brain_state import VALEBrainState

from HEROIC.state.mission_state import (
HeroicMissionState,
MissionStatus,
)

class HeroicBrain(VALEBrainInterface):
"""Main VALE-compatible entry point for HEROIC."""

VERSION = "0.1.0"
BRAIN_NAME = "HEROIC"

def __init__(self, connector: Any) -> None:
    super().__init__(
        brain_name=self.BRAIN_NAME,
        connector=connector,
    )

    self.version = self.VERSION
    self._mission_states: Dict[str, HeroicMissionState] = {}

@staticmethod
def _extract_request(state: VALEBrainState) -> str:
    """Read a request from known task-state fields."""

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
    """Keep one mission-state object per VALE task."""

    task_id = str(state.task_id)
    mission = self._mission_states.get(task_id)

    if mission is None:
        mission = HeroicMissionState(
            mission_id=task_id,
            user_request=user_request,
        )
        self._mission_states[task_id] = mission

    elif user_request and not mission.user_request:
        mission.user_request = user_request

    return mission

def think(self, state: VALEBrainState) -> Dict[str, Any]:
    """
    Capture the current mission and expose its state.

    This foundation does not claim to have built an execution
    plan, activated other brains, or verified an outcome.
    """

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
        "status": "MISSION_CAPTURED" if user_request else "NEEDS_INFORMATION",
        "role": "MISSION_AND_OBJECTIVE_COORDINATION",
        "task_id": str(state.task_id),
        "mission": mission.to_dict(),
        "planning_performed": False,
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
        },
    )

    return result

def get_mission_state(
    self,
    task_id: str,
) -> Optional[Dict[str, Any]]:
    """Return a copy of the serialized mission state."""

    mission = self._mission_states.get(str(task_id))

    if mission is None:
        return None

    return mission.to_dict()

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

all = ["HeroicBrain"]
