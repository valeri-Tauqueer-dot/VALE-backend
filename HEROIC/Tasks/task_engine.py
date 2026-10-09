"""
HEROIC TASK ENGINE

Converts a HEROIC objective into structured tasks.
This engine creates and classifies tasks; it does not execute them.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from HEROIC.Tasks.task_state import (
    HeroicTaskState,
    TaskStatus,
    TaskType,
)
from HEROIC.objectives.objective_state import HeroicObjectiveState


class HeroicTaskEngine:
    """Creates structured tasks from objectives."""

    VERSION = "0.2.0"

    def __init__(self) -> None:
        self.engine_name = "HEROIC_TASK_ENGINE"
        self.version = self.VERSION

    @staticmethod
    def _new_task_id() -> str:
        return f"heroic_task_{uuid4().hex}"

    def create_tasks(
        self,
        objective_state: HeroicObjectiveState,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[HeroicTaskState]:
        """Create the initial task set for an objective."""

        if objective_state is None:
            raise ValueError("objective_state must not be None.")

        if not isinstance(objective_state.description, str):
            return []

        if not objective_state.description.strip():
            return []

        tasks = [
            self._create_primary_task(objective_state, context)
        ]

        information_task = self._create_information_task(objective_state)
        if information_task is not None:
            tasks.append(information_task)

        analysis_task = self._create_analysis_task(objective_state)
        if analysis_task is not None:
            tasks.append(analysis_task)

        verification_task = self._create_verification_task(objective_state)
        if verification_task is not None:
            tasks.append(verification_task)

        return tasks

    def create_task(
        self,
        description: str,
        task_type: TaskType = TaskType.OTHER,
        objective_id: Optional[str] = None,
        goal_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> HeroicTaskState:
        """Create one explicitly defined task."""

        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-empty string.")

        task = HeroicTaskState(
            task_id=self._new_task_id(),
            description=description.strip(),
            task_type=task_type,
            status=TaskStatus.CREATED,
            objective_id=objective_id,
            goal_id=goal_id,
        )

        self._apply_context(task, context)
        return task

    def _create_primary_task(
        self,
        objective_state: HeroicObjectiveState,
        context: Optional[Dict[str, Any]],
    ) -> HeroicTaskState:
        task = HeroicTaskState(
            task_id=self._new_task_id(),
            description=objective_state.description.strip(),
            task_type=TaskType.ANALYSIS,
            status=TaskStatus.CREATED,
            objective_id=objective_state.objective_id,
        )

        for criterion in objective_state.success_criteria:
            task.add_success_criterion(str(criterion))

        for constraint in objective_state.constraints:
            if constraint:
                task.constraints.append(str(constraint))

        for assumption in objective_state.assumptions:
            if assumption:
                task.assumptions.append(str(assumption))

        for blocker in objective_state.blockers:
            if blocker:
                task.add_blocker(str(blocker))

        self._apply_context(task, context)
        return task

    def _create_information_task(
        self,
        objective_state: HeroicObjectiveState,
    ) -> Optional[HeroicTaskState]:
        questions = list(objective_state.unresolved_questions or [])
        if not questions:
            return None

        task = HeroicTaskState(
            task_id=self._new_task_id(),
            description=(
                "Resolve or explicitly identify the information "
                "gaps relevant to the objective."
            ),
            task_type=TaskType.DATA_RETRIEVAL,
            status=TaskStatus.CREATED,
            objective_id=objective_state.objective_id,
        )

        for question in questions:
            task.add_expected_output(str(question))

        task.add_success_criterion(
            "Information gaps are documented and their resolution status is clear."
        )
        return task

    def _create_analysis_task(
        self,
        objective_state: HeroicObjectiveState,
    ) -> Optional[HeroicTaskState]:
        outcomes = list(objective_state.required_outcomes or [])
        if not outcomes:
            return None

        task = HeroicTaskState(
            task_id=self._new_task_id(),
            description=(
                "Analyze the objective requirements and determine "
                "the required outcome."
            ),
            task_type=TaskType.REASONING,
            status=TaskStatus.CREATED,
            objective_id=objective_state.objective_id,
        )

        for outcome in outcomes:
            task.add_expected_output(str(outcome))

        task.add_success_criterion(
            "The required outcome is determined using the available evidence."
        )
        return task

    def _create_verification_task(
        self,
        objective_state: HeroicObjectiveState,
    ) -> Optional[HeroicTaskState]:
        criteria = list(objective_state.success_criteria or [])
        if not criteria:
            return None

        task = HeroicTaskState(
            task_id=self._new_task_id(),
            description=(
                "Verify whether the objective result satisfies "
                "the defined success criteria."
            ),
            task_type=TaskType.VERIFICATION,
            status=TaskStatus.CREATED,
            objective_id=objective_state.objective_id,
        )

        for criterion in criteria:
            task.add_success_criterion(str(criterion))

        task.add_expected_output(
            "Verification result with supporting evidence and any unmet criteria."
        )
        return task

    def _apply_context(
        self,
        task: HeroicTaskState,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """Apply explicitly supplied context without replacing task state."""

        if not isinstance(context, dict):
            return

        inputs = context.get("inputs")

        if isinstance(inputs, dict):
            task.inputs.update(inputs)
        elif isinstance(inputs, (list, tuple)):
            for item in inputs:
                key = f"input_{len(task.inputs) + 1}"
                task.inputs[key] = item

        expected_outputs = context.get("expected_outputs")

        if isinstance(expected_outputs, str):
            if expected_outputs.strip():
                task.add_expected_output(expected_outputs.strip())
        elif isinstance(expected_outputs, (list, tuple, set)):
            for output in expected_outputs:
                if output is not None and str(output).strip():
                    task.add_expected_output(str(output).strip())

        constraints = context.get("constraints")

        if isinstance(constraints, dict):
            for name, value in constraints.items():
                item = f"{name}: {value}"
                if item not in task.constraints:
                    task.constraints.append(item)
        elif isinstance(constraints, (list, tuple, set)):
            for constraint in constraints:
                item = str(constraint).strip()
                if item and item not in task.constraints:
                    task.constraints.append(item)

        assumptions = context.get("assumptions")

        if isinstance(assumptions, (list, tuple, set)):
            for assumption in assumptions:
                item = str(assumption).strip()
                if item and item not in task.assumptions:
                    task.assumptions.append(item)

        capabilities = context.get("required_capabilities")
        if isinstance(capabilities, (list, tuple, set)):
            for capability in capabilities:
                if capability:
                    task.add_required_capability(str(capability))

        brains = context.get("required_brains")
        if isinstance(brains, (list, tuple, set)):
            for brain in brains:
                if brain:
                    task.add_required_brain(str(brain))

        success_criteria = context.get("success_criteria")
        if isinstance(success_criteria, (list, tuple, set)):
            for criterion in success_criteria:
                if criterion:
                    task.add_success_criterion(str(criterion))

    def classify_task(self, description: str) -> TaskType:
        """Classify a task using deterministic keyword signals."""

        if not isinstance(description, str) or not description.strip():
            return TaskType.OTHER

        text = description.lower().strip()

        if any(
            phrase in text
            for phrase in (
                "verify",
                "validate",
                "check whether",
                "confirm",
                "test whether",
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
                "look up",
            )
        ):
            return TaskType.DATA_RETRIEVAL

        if any(
            phrase in text
            for phrase in (
                "research",
                "investigate",
                "explore",
                "survey",
            )
        ):
            return TaskType.RESEARCH

        if any(
            phrase in text
            for phrase in (
                "decide",
                "make a decision",
                "recommend",
                "evaluate options",
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
                "compare",
                "explain",
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
                "modify",
            )
        ):
            return TaskType.ACTION

        if any(
            phrase in text
            for phrase in (
                "write a message",
                "send a message",
                "communicate",
                "notify",
            )
        ):
            return TaskType.COMMUNICATION

        return TaskType.OTHER


__all__ = ["HeroicTaskEngine"]
