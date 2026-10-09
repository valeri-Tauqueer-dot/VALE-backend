"""
HEROIC TASK PLANNER

Builds a preliminary plan from an objective and its tasks.
HEROIC defines what must be accomplished; ALPHA optimizes execution.
This planner does not execute tasks or activate brains.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from HEROIC.Tasks.task_state import HeroicTaskState
from HEROIC.objectives.objective_state import HeroicObjectiveState
from HEROIC.planning.plan_state import (
    HeroicPlanState,
    PlanStatus,
    PlanType,
)


class HeroicTaskPlanner:
    """Create and validate a preliminary HEROIC task plan."""

    VERSION = "0.3.0"

    def __init__(self) -> None:
        self.planner_name = "HEROIC_TASK_PLANNER"
        self.version = self.VERSION

    def build_plan(
        self,
        objective_state: HeroicObjectiveState,
        tasks: Iterable[HeroicTaskState],
        mission_id: Optional[str] = None,
        goal_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> HeroicPlanState:
        """Build a plan and check its task references and dependencies."""

        if objective_state is None:
            raise ValueError("objective_state must not be None.")

        task_list = list(tasks)

        if any(task is None for task in task_list):
            raise ValueError("tasks must not contain None.")

        task_ids = [task.task_id for task in task_list]

        if any(
            not isinstance(task_id, str) or not task_id.strip()
            for task_id in task_ids
        ):
            raise ValueError("Every task must have a non-empty task_id.")

        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Task IDs must be unique within a plan.")

        resolved_goal_id = (
            goal_id
            if goal_id is not None
            else getattr(objective_state, "goal_id", None)
        )

        plan = HeroicPlanState(
            objective_id=objective_state.objective_id,
            goal_id=resolved_goal_id,
            mission_id=mission_id,
            description=objective_state.description,
        )

        self._register_tasks(plan, task_list)
        self._transfer_objective_requirements(plan, objective_state)
        self._classify_plan_type(plan, task_list)
        self._build_initial_order(plan, task_list)
        self._build_parallel_groups(plan, task_list)
        self._apply_context(plan, context)
        self._validate_dependencies(plan, task_list)
        self._evaluate_readiness(plan)

        return plan

    def _register_tasks(
        self,
        plan: HeroicPlanState,
        tasks: List[HeroicTaskState],
    ) -> None:
        for task in tasks:
            plan.add_task(task.task_id)

            for capability in task.required_capabilities:
                plan.add_required_capability(capability)

            for brain in task.required_brains:
                plan.add_required_brain(brain)

            for output in task.expected_outputs:
                plan.add_expected_output(output)

            for criterion in task.success_criteria:
                plan.add_success_criterion(criterion)

            for constraint in task.constraints:
                plan.add_constraint(constraint)

            for assumption in task.assumptions:
                plan.add_assumption(assumption)

            for blocker in task.blockers:
                plan.add_blocker(blocker)

    def _transfer_objective_requirements(
        self,
        plan: HeroicPlanState,
        objective: HeroicObjectiveState,
    ) -> None:
        for criterion in objective.success_criteria:
            plan.add_success_criterion(criterion)

        for outcome in objective.required_outcomes:
            plan.add_expected_output(outcome)

        for constraint in objective.constraints:
            plan.add_constraint(constraint)

        for assumption in objective.assumptions:
            plan.add_assumption(assumption)

        for question in objective.unresolved_questions:
            plan.add_unresolved_question(question)

        for blocker in objective.blockers:
            plan.add_blocker(blocker)

    def _classify_plan_type(
        self,
        plan: HeroicPlanState,
        tasks: List[HeroicTaskState],
    ) -> None:
        if len(tasks) <= 1:
            plan.plan_type = PlanType.SINGLE_TASK
        else:
            plan.plan_type = PlanType.MULTI_TASK

    def _build_initial_order(
        self,
        plan: HeroicPlanState,
        tasks: List[HeroicTaskState],
    ) -> None:
        """Record the proposed order; dependency validation follows."""

        for task in tasks:
            plan.add_ordered_task(task.task_id)

    def _build_parallel_groups(
        self,
        plan: HeroicPlanState,
        tasks: List[HeroicTaskState],
    ) -> None:
        """
        Do not infer safe parallelism solely from missing dependencies.
        Dependency and resource analysis must establish that separately.
        """

        return

    def _apply_context(
        self,
        plan: HeroicPlanState,
        context: Optional[Dict[str, Any]],
    ) -> None:
        if not isinstance(context, dict):
            return

        inputs = context.get("inputs")
        if isinstance(inputs, dict):
            plan.inputs.update(inputs)

        metadata = context.get("metadata")
        if isinstance(metadata, dict):
            plan.metadata.update(metadata)

        if "verification_required" in context:
            plan.verification_required = bool(
                context["verification_required"]
            )

    def _validate_dependencies(
        self,
        plan: HeroicPlanState,
        tasks: List[HeroicTaskState],
    ) -> None:
        """Block plans with missing dependencies or dependency cycles."""

        task_map = {task.task_id: task for task in tasks}
        task_ids = set(task_map)

        for task in tasks:
            for dependency_id in task.dependency_task_ids:
                if dependency_id not in task_ids:
                    plan.add_blocker(
                        f"Task {task.task_id} references missing dependency "
                        f"{dependency_id}."
                    )

                if dependency_id == task.task_id:
                    plan.add_blocker(
                        f"Task {task.task_id} depends on itself."
                    )

        if plan.blockers:
            return

        visiting = set()
        visited = set()

        def has_cycle(task_id: str) -> bool:
            if task_id in visiting:
                return True

            if task_id in visited:
                return False

            visiting.add(task_id)

            for dependency_id in task_map[task_id].dependency_task_ids:
                if has_cycle(dependency_id):
                    return True

            visiting.remove(task_id)
            visited.add(task_id)
            return False

        for task_id in task_map:
            if has_cycle(task_id):
                plan.add_blocker(
                    "Task dependency cycle detected; the plan cannot "
                    "be considered ready."
                )
                return

    def _evaluate_readiness(self, plan: HeroicPlanState) -> None:
        if plan.blockers:
            plan.status = PlanStatus.BLOCKED
        elif plan.unresolved_questions:
            plan.status = PlanStatus.DRAFT
        elif plan.is_ready():
            plan.status = PlanStatus.READY
        else:
            plan.status = PlanStatus.DRAFT


__all__ = ["HeroicTaskPlanner"]
