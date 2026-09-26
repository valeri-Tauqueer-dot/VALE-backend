"""
HEROIC STATE PACKAGE

Foundational state definitions for the HEROIC Brain.

HEROIC state represents the mission/objective context that HEROIC
needs in order to understand, plan, coordinate, monitor, and
complete a VALE objective.

This package intentionally contains only foundational state.
Higher-level planning, routing, execution, verification, and
replanning intelligence will be added in separate modules.
"""

from .mission_state import HeroicMissionState

__all__ = [
    "HeroicMissionState",
]
