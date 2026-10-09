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
    Converts a HEROIC objective into structured tasks.

    This engine creates and classifies tasks. It does not execute
    tasks, activate brains, or verify task results.
    """

    def __init__(self) -> None:
        self.engine_name = "HEROIC_TASK_ENGINE"
        self.version = "0.2.0"
        self._next_task_number = 1

    def create_tasks(
        self,
        objective_state: HeroicObjectiveState,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[HeroicTaskState]:
        """Create an initial task set for an objective."""
        if not objective_state.description.strip():
            return []

        tasks: List[HeroicTaskState] = []

        primary_task = self._create_primary_task(
            objective_state=objective_state,
            context=context,
        )
        tasks.append(primary_task)

        information_task = self._create_required_information_task(
            objective_state
        )
        if information_task is not None:
            tasks.append(information_task)

        analysis_task = self._create_analysis_task(objective_state)
        if analysis_task is not None:
            tasks.append(analysis_task)

        verification_task = self._create_verification_task(
            objective_state
        )
        if verification_task is not None:
            tasks.append(verification_task)

        # Assign IDs and connect every generated task to the objective.
        for task in tasks:
            if not task.task_id:
                task.task_id = self._generate_task_id()

            if task.task_id not in objective_state.task_ids:
                objective_state.add_task(task.task_id)

        # The primary task is the first task. Later tasks depend on it
        # so that they cannot be treated as independent work.
        for task in tasks[1:]:
            task.add_dependency(primary_task.task_id)

        return tasks

    def create_task(
        self,
        description: str,
        task_type: TaskType = TaskType.OTHER,
        objective_id: Optional[str] = None,
        goal_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> HeroicTaskState:
        """Create one task from an explicit description."""
        description = str(description).strip()

        if not description:
            raise ValueError("Task description cannot be empty.")

        if isinstance(task_type, str):
            task_type = TaskType(task_type.lower())

        task = HeroicTaskState(
            task_id=self._generate_task_id(),
            description=description,
            task_type=task_type,
            status=TaskStatus.CREATED,
            objective_id=objective_id,
            goal_id=goal_id,
        )

        self._apply_context(task, context)
        return task

    def _generate_task_id(self) -> str:
        task_id = f"heroic_task_{self._next_task_number:06d}"
        self._next_task_number += 1
        return task_id

    def _create_primary_task(
        self,
        objective_state: HeroicObjectiveState,
        context: Optional[Dict[str, Any]],
    ) -> HeroicTaskState:
        task = self.create_task(
            description=objective_state.description,
            task_type=self.classify_task(
                objective_state.description
            ),
            objective_id=objective_state.objective_id,
            goal_id=objective_state.goal_id,
            context=context,
        )

        for criterion in objective_state.success_criteria:
            task.add_success_criterion(criterion)

        task.constraints.extend(
            item
            for item in objective_state.constraints
            if item not in task.constraints
        )
        task.assumptions.extend(
            item
            for item in objective_state.assumptions
            if item not in task.assumptions
        )

        for blocker in objective_state.blockers:
            task.add_blocker(blocker)

        for outcome in objective_state.required_outcomes:
            task.add_expected_output(outcome)

        return task

    def _create_required_information_task(
        self,
        objective_state: HeroicObjectiveState,
    ) -> Optional[HeroicTaskState]:
        if not objective_state.unresolved_questions:
            return None

        task = self.create_task(
            description=(
                "Resolve the unresolved information required "
                "by the objective."
            ),
            task_type=TaskType.DATA_RETRIEVAL,
            objective_id=objective_state.objective_id,
            goal_id=objective_state.goal_id,
        )

        for question in objective_state.unresolved_questions:
            task.add_expected_output(question)

        task.add_success_criterion(
            "Required information has been identified or resolved."
        )
        return task

    def _create_analysis_task(
        self,
        objective_state: HeroicObjectiveState,
    ) -> Optional[HeroicTaskState]:
        if not objective_state.required_outcomes:
            return None

        task = self.create_task(
            description=(
                "Analyze the objective requirements and determine "
                "the required outcome."
            ),
            task_type=TaskType.REASONING,
            objective_id=objective_state.objective_id,
            goal_id=objective_state.goal_id,
        )

        for outcome in objective_state.required_outcomes:
            task.add_expected_output(outcome)

        task.add_success_criterion(
            "The required outcome has been logically determined."
        )
        return task

    def _create_verification_task(
        self,
        objective_state: HeroicObjectiveState,
    ) -> Optional[HeroicTaskState]:
        if not objective_state.success_criteria:
            return None

        task = self.create_task(
            description=(
                "Verify that the objective result satisfies "
                "its success criteria."
            ),
            task_type=TaskType.VERIFICATION,
            objective_id=objective_state.objective_id,
            goal_id=objective_state.goal_id,
        )

        for criterion in objective_state.success_criteria:
            task.add_success_criterion(criterion)

        return task

    def _apply_context(
        self,
        task: HeroicTaskState,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """Apply explicitly supplied context without guessing values."""
        if not context:
            return

        inputs = context.get("inputs")

        if isinstance(inputs, dict):
            task.inputs.update(inputs)
        elif isinstance(inputs, list):
            for index, item in enumerate(inputs, start=1):
                task.inputs[f"input_{index}"] = item

        expected_outputs = context.get("expected_outputs")

        if isinstance(expected_outputs, str):
            task.add_expected_output(expected_outputs)
        elif isinstance(expected_outputs, (list, tuple, set)):
            for output in expected_outputs:
                task.add_expected_output(str(output))

        constraints = context.get("constraints")

        if isinstance(constraints, dict):
            for name, value in constraints.items():
                item = f"{name}: {value}"
                if item not in task.constraints:
                    task.constraints.append(item)
        elif isinstance(constraints, (list, tuple, set)):
            for constraint in constraints:
                item = str(constraint)
                if item not in task.constraints:
                    task.constraints.append(item)

        assumptions = context.get("assumptions")

        if isinstance(assumptions, (list, tuple, set)):
            for assumption in assumptions:
                item = str(assumption)
                if item not in task.assumptions:
                    task.assumptions.append(item)

    def classify_task(self, description: str) -> TaskType:
        """Classify a task using deterministic text signals."""
        text = str(description).lower().strip()

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
