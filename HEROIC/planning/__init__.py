"""
HEROIC PLANNING PACKAGE

Transforms HEROIC objectives and tasks into structured plans.

Planning determines:
    - what work needs to happen
    - how tasks are structured
    - task dependencies
    - plan readiness
    - logical execution order

Planning does NOT execute tasks or optimize runtime performance.

ALPHA remains responsible for execution optimization,
resource allocation, and runtime performance.
"""

from .plan_state import (
    HeroicPlanState,
    PlanStatus,
    PlanType,
)
from .task_planner import HeroicTaskPlanner
from .dependency_planner import HeroicDependencyPlanner
from .execution_plan import HeroicExecutionPlan

__all__ = [
    "HeroicPlanState",
    "PlanStatus",
    "PlanType",
    "HeroicTaskPlanner",
    "HeroicDependencyPlanner",
    "HeroicExecutionPlan",
]
