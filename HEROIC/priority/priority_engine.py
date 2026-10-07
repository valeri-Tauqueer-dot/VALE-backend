from future import annotations

from typing import Iterable, List, Optional, Tuple

from HEROIC.Tasks.task_state import HeroicTaskState
from HEROIC.goals.goal_state import HeroicGoalState
from HEROIC.objectives.objective_state import HeroicObjectiveState

class HeroicPriorityEngine:
"""
Determines relative priority across HEROIC goals, objectives,
and tasks.

Priority is a planning signal, not an execution command.
HEROIC uses it to determine what should receive attention first;
ALPHA remains responsible for execution optimization.
"""

def __init__(
    self,
    *,
    default_priority: float = 0.5,
) -> None:
    self.default_priority = self._clamp(default_priority)

def score_goal(
    self,
    goal: HeroicGoalState,
) -> float:
    """
    Calculate a goal priority score.

    Explicit goal priorities take precedence. Otherwise the score
    is derived from goal state and structural urgency.
    """
    explicit = self._extract_explicit_priority(
        goal.priorities
    )

    if explicit is not None:
        return self._clamp(explicit)

    score = self.default_priority

    if goal.status.value == "IN_PROGRESS":
        score += 0.15

    if goal.status.value == "BLOCKED":
        score += 0.10

    if goal.unresolved_questions:
        score += 0.05

    return self._clamp(score)

def score_objective(
    self,
    objective: HeroicObjectiveState,
) -> float:
    """
    Calculate an objective priority score.
    """
    explicit = self._extract_explicit_priority(
        objective.priorities
    )

    if explicit is not None:
        return self._clamp(explicit)

    score = self.default_priority

    if objective.status.value == "IN_PROGRESS":
        score += 0.15

    if objective.status.value == "BLOCKED":
        score += 0.10

    if objective.blockers:
        score += 0.05

    if objective.unresolved_questions:
        score += 0.05

    return self._clamp(score)

def score_task(
    self,
    task: HeroicTaskState,
) -> float:
    """
    Calculate a task priority score from task characteristics.
    """
    score = self.default_priority

    if task.status.value == "RUNNING":
        score += 0.20

    elif task.status.value == "READY":
        score += 0.10

    elif task.status.value == "BLOCKED":
        score += 0.15

    if task.blockers:
        score += 0.05

    if task.dependency_task_ids:
        score += 0.05

    if task.success_criteria:
        score += 0.02

    return self._clamp(score)

def rank_goals(
    self,
    goals: Iterable[HeroicGoalState],
) -> List[Tuple[HeroicGoalState, float]]:
    """Rank goals from highest to lowest priority."""
    scored = [
        (goal, self.score_goal(goal))
        for goal in goals
    ]

    return sorted(
        scored,
        key=lambda item: item[1],
        reverse=True,
    )

def rank_objectives(
    self,
    objectives: Iterable[HeroicObjectiveState],
) -> List[Tuple[HeroicObjectiveState, float]]:
    """Rank objectives from highest to lowest priority."""
    scored = [
        (objective, self.score_objective(objective))
        for objective in objectives
    ]

    return sorted(
        scored,
        key=lambda item: item[1],
        reverse=True,
    )

def rank_tasks(
    self,
    tasks: Iterable[HeroicTaskState],
) -> List[Tuple[HeroicTaskState, float]]:
    """Rank tasks from highest to lowest priority."""
    scored = [
        (task, self.score_task(task))
        for task in tasks
    ]

    return sorted(
        scored,
        key=lambda item: item[1],
        reverse=True,
    )

def highest_priority_goal(
    self,
    goals: Iterable[HeroicGoalState],
) -> Optional[HeroicGoalState]:
    """Return the highest-priority goal, if any."""
    ranked = self.rank_goals(goals)

    return ranked[0][0] if ranked else None

def highest_priority_objective(
    self,
    objectives: Iterable[HeroicObjectiveState],
) -> Optional[HeroicObjectiveState]:
    """Return the highest-priority objective, if any."""
    ranked = self.rank_objectives(objectives)

    return ranked[0][0] if ranked else None

def highest_priority_task(
    self,
    tasks: Iterable[HeroicTaskState],
) -> Optional[HeroicTaskState]:
    """Return the highest-priority task, if any."""
    ranked = self.rank_tasks(tasks)

    return ranked[0][0] if ranked else None

def _extract_explicit_priority(
    self,
    priorities: Iterable[str],
) -> Optional[float]:
    """
    Extract a numeric priority when a priority entry contains one.

    Supported forms include:
        "0.8"
        "priority:0.8"
        "high:0.8"
    """
    for priority in priorities:
        if not priority:
            continue

        value = priority.strip().lower()

        try:
            return float(value)
        except ValueError:
            pass

        if ":" in value:
            _, raw_value = value.rsplit(":", 1)

            try:
                return float(raw_value.strip())
            except ValueError:
                continue

    return None

@staticmethod
def _clamp(
    value: float,
) -> float:
    """Keep priority within the normalized 0.0–1.0 range."""
    return max(0.0, min(1.0, float(value)))
