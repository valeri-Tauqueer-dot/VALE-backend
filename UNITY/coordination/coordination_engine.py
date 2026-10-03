"""
VALE UNITY — Coordination Engine

Coordinates TaskContext and ExecutionContext around one VALE workflow.

This is a coordination mechanism, not another reasoning brain.

Responsibilities:
- Create task context.
- Create execution context.
- Synchronize task/execution state.
- Track participating brains.
- Track capabilities.
- Track routes and operations.
- Provide coordination diagnostics.

It does NOT:
- determine the user's objective
- replace HEROIC
- optimize execution like ALPHA
- perform routing intelligence
- perform MCVL verification
- perform final synthesis
"""

from __future__ import annotations

from threading import RLock
from typing import Any, Dict, Iterable, List, Optional

from .task_context import TaskContext
from .execution_context import ExecutionContext


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_COORDINATION_ENGINE_FOUNDATION"


class CoordinationEngine:
    """
    UNITY coordination layer.

    TaskContext and ExecutionContext are deliberately kept separate:

        TaskContext
            = stable task identity and shared task information

        ExecutionContext
            = live execution state

    The engine connects them without collapsing them into one giant object.
    """

    ENGINE_NAME = "UNITY_COORDINATION_ENGINE"

    def __init__(
        self,
        state: Any = None,
    ) -> None:

        self.state = state

        self._lock = RLock()

        self._tasks: Dict[str, TaskContext] = {}

        self._executions: Dict[
            str,
            ExecutionContext,
        ] = {}

        self._task_execution: Dict[
            str,
            str,
        ] = {}

    # ------------------------------------------------------------------
    # Task creation
    # ------------------------------------------------------------------

    def create_task(
        self,
        user_message: str,
        objective: Optional[str] = None,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskContext:
        """
        Create and register a shared task context.
        """

        context = TaskContext(
            user_message=user_message,
            task_id=task_id
            if task_id is not None
            else self._new_id(),
            correlation_id=correlation_id,
            objective=objective,
            metadata=dict(metadata or {}),
        )

        with self._lock:
            self._tasks[
                context.task_id
            ] = context

        self._publish_task(context)

        return context

    # ------------------------------------------------------------------
    # Execution creation
    # ------------------------------------------------------------------

    def create_execution(
        self,
        task: TaskContext,
        stage: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionContext:
        """
        Create an execution context for an existing task.
        """

        validation = task.validate()

        if not validation["valid"]:
            raise ValueError(
                "Cannot create execution for invalid task: "
                + "; ".join(
                    validation["errors"]
                )
            )

        execution = ExecutionContext(
            task_id=task.task_id,
            metadata=dict(metadata or {}),
        )

        if stage:
            execution.set_stage(stage)

        with self._lock:
            self._executions[
                execution.execution_id
            ] = execution

            self._task_execution[
                task.task_id
            ] = execution.execution_id

        self._publish_execution(execution)

        return execution

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get_task(
        self,
        task_id: str,
    ) -> Optional[TaskContext]:

        with self._lock:
            return self._tasks.get(
                str(task_id)
            )

    def get_execution(
        self,
        execution_id: str,
    ) -> Optional[ExecutionContext]:

        with self._lock:
            return self._executions.get(
                str(execution_id)
            )

    def get_execution_for_task(
        self,
        task_id: str,
    ) -> Optional[ExecutionContext]:

        with self._lock:
            execution_id = self._task_execution.get(
                str(task_id)
            )

            if not execution_id:
                return None

            return self._executions.get(
                execution_id
            )

    # ------------------------------------------------------------------
    # Brain coordination
    # ------------------------------------------------------------------

    def activate_brain(
        self,
        task: TaskContext,
        brain_name: str,
    ) -> None:
        """Register a brain as active for the task."""

        task.add_brain(
            brain_name
        )

        self._publish_task(task)

    def deactivate_brain(
        self,
        task: TaskContext,
        brain_name: str,
    ) -> None:
        """Remove a brain from active task participation."""

        task.remove_brain(
            brain_name
        )

        self._publish_task(task)

    # ------------------------------------------------------------------
    # Capability coordination
    # ------------------------------------------------------------------

    def require_capabilities(
        self,
        task: TaskContext,
        capabilities: Iterable[str],
    ) -> None:
        """Register required capabilities."""

        for capability in capabilities:
            task.require_capability(
                capability
            )

        self._publish_task(task)

    def complete_capability(
        self,
        task: TaskContext,
        capability: str,
    ) -> None:
        """Mark one capability complete."""

        task.complete_capability(
            capability
        )

        self._publish_task(task)

    # ------------------------------------------------------------------
    # Route coordination
    # ------------------------------------------------------------------

    def activate_route(
        self,
        execution: ExecutionContext,
        route_id: str,
    ) -> None:

        execution.activate_route(
            route_id
        )

        self._publish_execution(
            execution
        )

    def complete_route(
        self,
        execution: ExecutionContext,
        route_id: str,
    ) -> None:

        execution.complete_route(
            route_id
        )

        self._publish_execution(
            execution
        )

    def fail_route(
        self,
        execution: ExecutionContext,
        route_id: str,
        reason: Optional[str] = None,
    ) -> None:

        execution.fail_route(
            route_id,
            reason,
        )

        self._publish_execution(
            execution
        )

    # ------------------------------------------------------------------
    # Stage coordination
    # ------------------------------------------------------------------

    def set_stage(
        self,
        execution: ExecutionContext,
        stage: str,
    ) -> None:

        execution.set_stage(
            stage
        )

        self._publish_execution(
            execution
        )

    def set_current_brain(
        self,
        execution: ExecutionContext,
        brain_name: Optional[str],
    ) -> None:

        execution.set_current_brain(
            brain_name
        )

        self._publish_execution(
            execution
        )

    # ------------------------------------------------------------------
    # Synchronization
    # ------------------------------------------------------------------

    def synchronize(
        self,
        task: TaskContext,
        execution: ExecutionContext,
    ) -> Dict[str, Any]:
        """
        Synchronize high-level task/execution relationship.

        This does not merge their data structures.

        It only establishes the relationship and validates consistency.
        """

        if task.task_id != execution.task_id:
            raise ValueError(
                "TaskContext and ExecutionContext belong to "
                "different tasks."
            )

        with self._lock:
            self._tasks[
                task.task_id
            ] = task

            self._executions[
                execution.execution_id
            ] = execution

            self._task_execution[
                task.task_id
            ] = execution.execution_id

        self._publish_task(task)
        self._publish_execution(execution)

        return self.snapshot_task(
            task
        )

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    def start_task(
        self,
        task: TaskContext,
        execution: Optional[ExecutionContext] = None,
    ) -> None:

        task.start()

        if execution:
            execution.start()

        self._publish_task(task)

        if execution:
            self._publish_execution(
                execution
            )

    def complete_task(
        self,
        task: TaskContext,
        execution: Optional[ExecutionContext] = None,
    ) -> None:

        task.complete()

        if execution:
            execution.complete()

        self._publish_task(task)

        if execution:
            self._publish_execution(
                execution
            )

    def fail_task(
        self,
        task: TaskContext,
        reason: Optional[str] = None,
        execution: Optional[ExecutionContext] = None,
    ) -> None:

        task.fail(
            reason
        )

        if execution:
            execution.fail(
                reason
            )

        self._publish_task(task)

        if execution:
            self._publish_execution(
                execution
            )

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def snapshot_task(
        self,
        task: TaskContext,
    ) -> Dict[str, Any]:

        execution = self.get_execution_for_task(
            task.task_id
        )

        return {
            "task": task.to_dict(),
            "execution": (
                execution.to_dict()
                if execution
                else None
            ),
        }

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:

        with self._lock:
            tasks = len(
                self._tasks
            )

            executions = len(
                self._executions
            )

            links = len(
                self._task_execution
            )

        return {
            "engine": self.ENGINE_NAME,
            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
            "tasks": tasks,
            "executions": executions,
            "task_execution_links": links,
        }

    # ------------------------------------------------------------------
    # State integration
    # ------------------------------------------------------------------

    def _publish_task(
        self,
        task: TaskContext,
    ) -> None:

        if self.state is None:
            return

        setter = getattr(
            self.state,
            "set",
            None,
        )

        if not callable(setter):
            return

        try:
            setter(
                f"unity.coordination.tasks.{task.task_id}",
                task.to_dict(),
            )
        except Exception:
            pass

    def _publish_execution(
        self,
        execution: ExecutionContext,
    ) -> None:

        if self.state is None:
            return

        setter = getattr(
            self.state,
            "set",
            None,
        )

        if not callable(setter):
            return

        try:
            setter(
                (
                    "unity.coordination.executions."
                    f"{execution.execution_id}"
                ),
                execution.to_dict(),
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _new_id() -> str:
        from uuid import uuid4

        return str(
            uuid4()
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:

        errors: List[str] = []

        with self._lock:
            tasks = list(
                self._tasks.values()
            )

            executions = list(
                self._executions.values()
            )

        for task in tasks:
            result = task.validate()

            if not result["valid"]:
                errors.extend(
                    result["errors"]
                )

        for execution in executions:
            result = execution.validate()

            if not result["valid"]:
                errors.extend(
                    result["errors"]
                )

        for task_id, execution_id in self._task_execution.items():

            execution = self._executions.get(
                execution_id
            )

            if execution is None:
                errors.append(
                    f"Task '{task_id}' references missing "
                    f"execution '{execution_id}'."
                )
                continue

            if execution.task_id != task_id:
                errors.append(
                    f"Execution '{execution_id}' is linked to "
                    f"the wrong task."
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "engine": self.ENGINE_NAME,
            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
        }


__all__ = [
    "VERSION",
    "ARCHITECTURE_STAGE",
    "CoordinationEngine",
  ]
