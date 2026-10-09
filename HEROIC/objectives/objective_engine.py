from __future__ import annotations

from typing import Dict, List, Optional

from .objective_state import (
    HeroicObjectiveState,
    ObjectiveStatus,
)


class HeroicObjectiveEngine:
    """Creates, tracks, and evaluates HEROIC objectives."""

    def __init__(self) -> None:
        self.objectives: Dict[str, HeroicObjectiveState] = {}

    def create_objective(
        self,
        objective_id: str,
        description: str,
        goal_id: Optional[str] = None,
        priority: float = 0.5,
        success_criteria: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> HeroicObjectiveState:
        objective_id = str(objective_id).strip()

        if not objective_id:
            raise ValueError("objective_id cannot be empty.")

        if objective_id in self.objectives:
            raise ValueError(
                f"Objective '{objective_id}' already exists."
            )

        objective = HeroicObjectiveState(
            objective_id=objective_id,
            description=description,
            goal_id=goal_id,
            priority=priority,
            success_criteria=list(success_criteria or []),
            metadata=dict(metadata or {}),
        )

        self.objectives[objective_id] = objective
        return objective

    def get_objective(
        self,
        objective_id: str,
    ) -> Optional[HeroicObjectiveState]:
        return self.objectives.get(str(objective_id).strip())

    def require_objective(
        self,
        objective_id: str,
    ) -> HeroicObjectiveState:
        objective = self.get_objective(objective_id)

        if objective is None:
            raise KeyError(f"Objective '{objective_id}' was not found.")

        return objective

    def add_dependency(
        self,
        objective_id: str,
        dependency_objective_id: str,
    ) -> None:
        objective = self.require_objective(objective_id)
        dependency = self.require_objective(dependency_objective_id)

        if dependency.objective_id == objective.objective_id:
            raise ValueError("An objective cannot depend on itself.")

        if self._would_create_cycle(
            objective.objective_id,
            dependency.objective_id,
        ):
            raise ValueError(
                "This dependency would create an objective cycle."
            )

        objective.add_dependency(dependency.objective_id)

    def _would_create_cycle(
        self,
        objective_id: str,
        dependency_id: str,
    ) -> bool:
        """Check whether adding objective -> dependency creates a cycle."""
        pending = [dependency_id]
        visited = set()

        while pending:
            current_id = pending.pop()

            if current_id == objective_id:
                return True

            if current_id in visited:
                continue

            visited.add(current_id)
            current = self.objectives.get(current_id)

            if current is not None:
                pending.extend(current.dependency_objective_ids)

        return False

    def get_ready_objectives(self) -> List[HeroicObjectiveState]:
        """Return actionable objectives whose dependencies are complete."""
        ready = []

        for objective in self.objectives.values():
            if objective.status not in {
                ObjectiveStatus.PENDING,
                ObjectiveStatus.ACTIVE,
            }:
                continue

            dependencies_complete = all(
                (
                    dependency := self.objectives.get(dependency_id)
                ) is not None
                and dependency.status == ObjectiveStatus.COMPLETED
                for dependency_id in objective.dependency_objective_ids
            )

            if dependencies_complete:
                ready.append(objective)

        return sorted(
            ready,
            key=lambda item: (-item.priority, item.created_at),
        )

    def complete_objective(
        self,
        objective_id: str,
    ) -> HeroicObjectiveState:
        objective = self.require_objective(objective_id)

        incomplete_dependencies = [
            dependency_id
            for dependency_id in objective.dependency_objective_ids
            if (
                dependency_id not in self.objectives
                or self.objectives[dependency_id].status
                != ObjectiveStatus.COMPLETED
            )
        ]

        if incomplete_dependencies:
            raise ValueError(
                "Cannot complete objective before its dependencies: "
                + ", ".join(incomplete_dependencies)
            )

        objective.complete()
        return objective

    def list_objectives(self) -> List[HeroicObjectiveState]:
        return list(self.objectives.values())

    def get_summary(self) -> dict:
        counts = {
            status.value: sum(
                objective.status == status
                for objective in self.objectives.values()
            )
            for status in ObjectiveStatus
        }

        return {
            "total": len(self.objectives),
            "status_counts": counts,
            "ready_objective_ids": [
                objective.objective_id
                for objective in self.get_ready_objectives()
            ],
        }

    def clear(self) -> None:
        self.objectives.clear()
