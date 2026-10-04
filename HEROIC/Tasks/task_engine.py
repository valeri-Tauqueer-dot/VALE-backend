"""
HEROIC TASK ENGINE

Purpose
-------
Converts a HEROIC objective into one or more structured tasks.

Objective answers:
    "What must be accomplished?"

Task answers:
    "What specific unit of work must be performed to accomplish it?"

This engine is responsible for task creation and initial task
classification.

It does NOT:
    - execute tasks
    - determine final execution order
    - resolve dependencies
    - activate brains
    - perform verification
    - optimize resources

Those responsibilities belong to later HEROIC and VALE systems.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from HEROIC.Tasks.task_state import (
    HeroicTaskState,
    TaskStatus,
    TaskType,
)
from HEROIC.objectives.objective_state import HeroicObjectiveState


class HeroicTaskEngine:
    """
    Creates structured HEROIC tasks from objectives.
    """

    def __init__(self) -> None:
        self.engine_name = "HEROIC_TASK_ENGINE"
        self.version = "0.1.0"

    def create_tasks(
        self,
        objective_state: HeroicObjectiveState,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[HeroicTaskState]:
        """
        Create the initial task set for an objective.

        Parameters
        ----------
        objective_state:
            Objective that needs to be accomplished.

        context:
            Optional mission context.

        Returns
        -------
        list[HeroicTaskState]
            Structured tasks.
        """

        tasks: List[HeroicTaskState] = []

        if not objective_state.description.strip():
            return tasks

        primary_task = self._create_primary_task(
            objective_state=objective_state,
            context=context,
        )

        tasks.append(primary_task)

        self._add_required_information_task(
            tasks=tasks,
            objective_state=objective_state,
        )

        self._add_analysis_task(
            tasks=tasks,
            objective_state=objective_state,
        )

        self._add_verification_task(
            tasks=tasks,
            objective_state=objective_state,
        )

        return tasks

    def create_task(
        self,
        description: str,
        task_type: TaskType = TaskType.OTHER,
        objective_id: Optional[str] = None,
        goal_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> HeroicTaskState:
        """
        Create a single explicitly defined HEROIC task.
        """

        task = HeroicTaskState(
            description=description.strip(),
            task_type=task_type,
            status=TaskStatus.CREATED,
            objective_id=objective_id,
            goal_id=goal_id,
        )

        if context:
            self._apply_context(
                task=task,
                context=context,
            )

        return task

    def _create_primary_task(
        self,
        objective_state: HeroicObjectiveState,
        context: Optional[Dict[str, Any]],
    ) -> HeroicTaskState:
        """
        Create the primary task representing the objective itself.
        """

        task = HeroicTaskState(
            description=objective_state.description,
            task_type=TaskType.ANALYSIS,
            status=TaskStatus.CREATED,
            objective_id=objective_state.objective_id,
        )

        for criterion in objective_state.success_criteria:
            task.add_success_criterion(criterion)

        for constraint in objective_state.constraints:
            task.constraints.append(constraint)

        for assumption in objective_state.assumptions:
            task.assumptions.append(assumption)

        for blocker in objective_state.blockers:
            task.add_blocker(blocker)

        self._apply_context(
            task=task,
            context=context,
        )

        return task

    def _add_required_information_task(
        self,
        tasks: List[HeroicTaskState],
        objective_state: HeroicObjectiveState,
    ) -> None:
        """
        Create an information task when the objective contains
        unresolved questions.
        """

        if not objective_state.unresolved_questions:
            return

        task = HeroicTaskState(
            description="Resolve the unresolved information required by the objective.",
            task_type=TaskType.DATA_RETRIEVAL,
            status=TaskStatus.CREATED,
            objective_id=objective_state.objective_id,
        )

        for question in objective_state.unresolved_questions:
            task.add_expected_output(question)

        task.add_success_criterion(
            "Required unresolved information has been identified or resolved."
        )

        tasks.append(task)

    def _add_analysis_task(
        self,
        tasks: List[HeroicTaskState],
        objective_state: HeroicObjectiveState,
    ) -> None:
        """
        Create an analysis task for objectives requiring substantive
        reasoning.
        """

        if not objective_state.required_outcomes:
            return

        task = HeroicTaskState(
            description="Analyze the objective requirements and determine the required outcome.",
            task_type=TaskType.REASONING,
            status=TaskStatus.CREATED,
            objective_id=objective_state.objective_id,
        )

        for outcome in objective_state.required_outcomes:
            task.add_expected_output(outcome)

        task.add_success_criterion(
            "The required outcome has been logically determined."
        )

        tasks.append(task)

    def _add_verification_task(
        self,
        tasks: List[HeroicTaskState],
        objective_state: HeroicObjectiveState,
    ) -> None:
        """
        Create a verification task when the objective contains
        explicit success criteria.
        """

        if not objective_state.success_criteria:
            return

        task = HeroicTaskState(
            description="Verify that the objective result satisfies its success criteria.",
            task_type=TaskType.VERIFICATION,
            status=TaskStatus.CREATED,
            objective_id=objective_state.objective_id,
        )

        for criterion in objective_state.success_criteria:
            task.add_success_criterion(criterion)

        tasks.append(task)

    def _apply_context(
        self,
        task: HeroicTaskState,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """
        Apply explicitly supplied task context.
        """

        if not context:
            return

        inputs = context.get("inputs")

        if isinstance(inputs, dict):
            task.inputs.update(inputs)

        elif isinstance(inputs, list):
            for item in inputs:
                key = f"input_{len(task.inputs) + 1}"
                task.inputs[key] = item

        expected_outputs = context.get("expected_outputs")

        if isinstance(expected_outputs, (list, tuple, set)):
            for output in expected_outputs:
                task.add_expected_output(str(output))

        elif isinstance(expected_outputs, str) and expected_outputs.strip():
            task.add_expected_output(expected_outputs.strip())

        constraints = context.get("constraints")

        if isinstance(constraints, dict):
            for name, value in constraints.items():
                task.constraints.append(f"{name}: {value}")

        elif isinstance(constraints, (list, tuple, set)):
            for constraint in constraints:
                task.constraints.append(str(constraint))

        assumptions = context.get("assumptions")

        if isinstance(assumptions, (list, tuple, set)):
            for assumption in assumptions:
                task.assumptions.append(str(assumption))

    def classify_task(
        self,
        description: str,
    ) -> TaskType:
        """
        Classify a task description using deterministic linguistic
        signals.

        This is an initial classifier. More advanced capability
        selection will be handled separately.
        """

        text = description.lower().strip()

        if any(
            phrase in text
            for phrase in (
                "verify",
                "validate",
                "check whether",
                "confirm",
            )
        ):
            return TaskType.VERIFICATION

        if any(
            phrase in text
            for phrase in (
                "retrieve",
                "fetch",
                "get data",
                "find information",
                "collect data",
            )
        ):
            return TaskType.DATA_RETRIEVAL

        if any(
            phrase in text
            for phrase in (
                "research",
                "investigate",
                "explore",
            )
        ):
            return TaskType.RESEARCH

        if any(
            phrase in text
            for phrase in (
                "decide",
                "decision",
                "recommend",
            )
        ):
            return TaskType.DECISION_SUPPORT

        if any(
            phrase in text
            for phrase in (
                "reason",
                "analyze",
                "analyse",
                "determine",
            )
        ):
            return TaskType.REASONING

        if any(
            phrase in text
            for phrase in (
                "build",
                "create",
                "implement",
                "execute",
                "run",
                "fix",
            )
        ):
            return TaskType.ACTION

        return TaskType.OTHER
