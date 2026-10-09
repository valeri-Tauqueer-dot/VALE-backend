"""
HEROIC TASK PLANNER

Purpose:
    Build a structured plan from an objective and its tasks.

Responsibilities:
    - Register tasks and collect their requirements.
    - Preserve objective-level requirements.
    - Establish an initial task order.
    - Identify preliminary parallel task groups.
    - Apply explicitly supplied context.
    - Evaluate plan readiness.

This planner does not execute tasks, allocate resources,
activate brains, or optimize runtime performance.

ALPHA remains responsible for execution optimization.
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
    """Create a structured HEROIC plan from objective tasks."""

    def __init__(self) -> None:
        self.planner_name = "HEROIC_TASK_PLANNER"
        self.version = "0.2.0"

    def build_plan(
        self,
        objective_state: HeroicObjectiveState,
        tasks: Iterable[HeroicTaskState],
        mission_id: Optional[str] = None,
        goal_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> HeroicPlanState:
        """Build a preliminary plan from an objective and its tasks."""

        if objective_state is None:
            raise ValueError("objective_state must not be None.")

        task_list = list(tasks)

        if any(task is None for task in task_list):
            raise ValueError("tasks must not contain None.")

        task_ids = [task.task_id for task in task_list]

        if any(not isinstance(task_id, str) or not task_id.strip()
               for task_id in task_ids):
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
        self._evaluate_readiness(plan)

        return plan

    def _register_tasks(
        self,
        plan: HeroicPlanState,
        tasks: List[HeroicTaskState],
    ) -> None:
        """Register task IDs and collect task-level requirements."""

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
        """Preserve objective-level requirements at plan level."""

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
        """Assign a preliminary plan type before dependency analysis."""

        if len(tasks) <= 1:
            plan.plan_type = PlanType.SINGLE_TASK
        else:
            plan.plan_type = PlanType.MULTI_TASK

    def _build_initial_order(
        self,
        plan: HeroicPlanState,
        tasks: List[HeroicTaskState],
    ) -> None:
        """
        Preserve task creation order as the preliminary order.

        The Dependency Planner must validate or replace this order
        before downstream execution relies on it.
        """

        for task in tasks:
            plan.add_ordered_task(task.task_id)

    def _build_parallel_groups(
        self,
        plan: HeroicPlanState,
        tasks: List[HeroicTaskState],
    ) -> None:
        """
        Record a preliminary group of tasks without declared
        dependencies. This does not authorize parallel execution.
        """

        independent_tasks = [
            task.task_id
            for task in tasks
            if not task.dependency_task_ids
        ]

        if len(independent_tasks) > 1:
            plan.add_parallel_group(independent_tasks)

            if plan.plan_type == PlanType.MULTI_TASK:
                plan.plan_type = PlanType.PARALLEL

    def _apply_context(
        self,
        plan: HeroicPlanState,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """Apply explicitly supplied planning context."""

        if not context:
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

    def _evaluate_readiness(self, plan: HeroicPlanState) -> None:
        """Set the initial plan status from its current requirements."""

        if plan.blockers:
            plan.status = PlanStatus.BLOCKED
        elif plan.unresolved_questions:
            plan.status = PlanStatus.DRAFT
        elif plan.is_ready():
            plan.status = PlanStatus.READY
        else:
            plan.status = PlanStatus.DRAFT


__all__ = ["HeroicTaskPlanner"]
