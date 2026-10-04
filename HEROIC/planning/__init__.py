"""
HEROIC PLANNING PACKAGE

The Planning layer transforms HEROIC's objectives and tasks into
structured execution plans.

Planning is responsible for determining:
    - what work needs to happen
    - how work is structured
    - task relationships
    - execution readiness
    - the logical execution plan

Planning does NOT perform execution itself.

ALPHA remains responsible for execution optimization,
parallelism, resource allocation, and performance.
"""

from .plan_state import HeroicPlanState
from .task_planner import HeroicTaskPlanner
from .dependency_planner import HeroicDependencyPlanner
from .execution_plan import HeroicExecutionPlan

__all__ = [
    "HeroicPlanState",
    "HeroicTaskPlanner",
    "HeroicDependencyPlanner",
    "HeroicExecutionPlan",
]
