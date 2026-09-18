"""
VALE ALPHA - Parallel Execution Engine

File:
    ALPHA/parallel/parallel_executor.py

Purpose:
    Execute dependency-ready ALPHA tasks concurrently when it is safe and
    useful to do so.

Architectural boundary:

    HEROIC
        decides WHAT VALE needs to accomplish.

    ALPHA Planner
        determines HOW the work is structured.

    ALPHA Scheduler
        determines WHAT work is ready to be dispatched.

    ALPHA Parallel Executor
        determines HOW ready work is physically executed concurrently.

    Specialist Brains / Capabilities
        perform the actual intelligence.

    MCVL
        verifies and challenges results where required.

This module is intentionally execution-focused.

It does NOT:
    - determine truth
    - make final cognitive decisions
    - replace HEROIC
    - replace UNITY
    - replace MCVL
    - fabricate telemetry
    - ignore dependencies
    - execute tasks that have not been authorized for dispatch
    - silently downgrade verification requirements

The executor accepts task handlers from the surrounding runtime. It does
not invent handlers or pretend that an unimplemented brain has executed.

Concurrency implementation:
    Python ThreadPoolExecutor is used initially because the ALPHA layer
    must remain compatible with the existing backend architecture.

Future evolution may introduce:
    - process pools
    - async execution
    - dedicated worker pools
    - model-specific workers
    - remote workers
    - distributed execution

Those are future implementation decisions and should not be assumed here.
"""


from __future__ import annotations

from concurrent.futures import (
    Future,
    ThreadPoolExecutor,
    as_completed,
)
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
)

from ALPHA.core.execution_context import ExecutionContext
from ALPHA.core.execution_models import (
    ExecutionResult,
    ExecutionStatus,
    ExecutionTask,
    FailureType,
    TaskStatus,
)
from ALPHA.scheduling.scheduler_models import (
    DispatchBatch,
    DispatchCandidate,
)


class ParallelExecutionError(RuntimeError):
    """Base exception for parallel execution failures."""


class ExecutorConfigurationError(ParallelExecutionError):
    """Raised when executor configuration is invalid."""


class TaskHandlerNotFoundError(ParallelExecutionError):
    """Raised when no execution handler exists for a task."""


class UnsafeParallelExecutionError(ParallelExecutionError):
    """Raised when a task cannot safely be executed in the requested batch."""


@dataclass(frozen=True)
class ParallelExecutionConfig:
    """
    Configuration for the initial parallel executor.

    max_workers is an execution limit, not a claim about actual machine
    capacity. Runtime resource management will eventually provide richer
    capacity information.
    """

    max_workers: int = 4

    thread_name_prefix: str = "vale-alpha"

    fail_fast: bool = False

    allow_partial_results: bool = True

    require_explicit_handlers: bool = True

    preserve_result_order: bool = True

    def __post_init__(self) -> None:
        if self.max_workers < 1:
            raise ExecutorConfigurationError(
                "max_workers must be at least 1."
            )


@dataclass
class TaskExecutionInput:
    """
    Input supplied to a task handler.

    The handler receives the execution task plus the shared execution
    context and results that are already available.

    This keeps task execution connected to the same ALPHA execution
    context rather than creating isolated state.
    """

    task: ExecutionTask
    context: ExecutionContext
    dependency_results: Dict[str, ExecutionResult] = field(
        default_factory=dict
    )

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class TaskExecutionOutput:
    """
    Normalized output returned by a task handler.

    A handler may return:
        - ExecutionResult
        - TaskExecutionOutput
        - any other Python value

    Non-ExecutionResult values are wrapped by the executor.
    """

    task_id: str
    value: Any = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


TaskHandler = Callable[[TaskExecutionInput], Any]


@dataclass
class ParallelExecutionReport:
    """
    Result of one parallel execution batch.
    """

    started_at: datetime
    completed_at: datetime

    task_ids: List[str]

    completed_task_ids: List[str] = field(default_factory=list)
    failed_task_ids: List[str] = field(default_factory=list)

    results: Dict[str, ExecutionResult] = field(
        default_factory=dict
    )

    errors: Dict[str, str] = field(
        default_factory=dict
    )

    worker_count: int = 0

    @property
    def success(self) -> bool:
        """
        True when no task failed.
        """

        return not self.failed_task_ids

    @property
    def partial_success(self) -> bool:
        """
        True when at least one task completed and at least one failed.
        """

        return bool(
            self.completed_task_ids
            and self.failed_task_ids
        )

    @property
    def task_count(self) -> int:
        return len(self.task_ids)


class ParallelExecutor:
    """
    ALPHA's initial concurrent execution engine.

    The executor operates on a DispatchBatch produced by the scheduler.

    Example lifecycle:

        Scheduler
            ↓
        DispatchBatch
            ↓
        ParallelExecutor
            ↓
        Task handlers
            ↓
        ExecutionResult
            ↓
        ExecutionContext
            ↓
        Scheduler / MCVL / UNITY

    The executor never decides whether a result is correct. It only
    records what the handler returned and whether execution succeeded.
    """

    def __init__(
        self,
        *,
        config: Optional[ParallelExecutionConfig] = None,
    ) -> None:
        self.config = config or ParallelExecutionConfig()

        self._handlers: Dict[str, TaskHandler] = {}

        self._lock = Lock()

        self._active_futures: Dict[
            Future[Any],
            str,
        ] = {}

    # ------------------------------------------------------------------
    # HANDLER REGISTRATION
    # ------------------------------------------------------------------

    def register_handler(
        self,
        task_id: str,
        handler: TaskHandler,
    ) -> None:
        """
        Register a handler for one specific task ID.
        """

        if not task_id:
            raise ValueError("task_id cannot be empty.")

        if not callable(handler):
            raise TypeError(
                "handler must be callable."
            )

        with self._lock:
            self._handlers[task_id] = handler

    def register_handlers(
        self,
        handlers: Mapping[str, TaskHandler],
    ) -> None:
        """
        Register multiple task handlers.
        """

        for task_id, handler in handlers.items():
            self.register_handler(
                task_id,
                handler,
            )

    def unregister_handler(
        self,
        task_id: str,
    ) -> None:
        """
        Remove a task-specific handler.
        """

        with self._lock:
            self._handlers.pop(
                task_id,
                None,
            )

    def clear_handlers(self) -> None:
        """
        Remove all registered handlers.
        """

        with self._lock:
            self._handlers.clear()

    def has_handler(
        self,
        task_id: str,
    ) -> bool:
        with self._lock:
            return task_id in self._handlers

    # ------------------------------------------------------------------
    # PUBLIC EXECUTION API
    # ------------------------------------------------------------------

    def execute(
        self,
        *,
        dispatch_batch: DispatchBatch,
        context: ExecutionContext,
    ) -> ParallelExecutionReport:
        """
        Execute all tasks contained in a dispatch batch concurrently.

        Only tasks explicitly present in the dispatch batch are eligible
        for execution.

        The scheduler therefore remains the authority for dispatch.
        """

        if context is None:
            raise ValueError(
                "Execution context cannot be None."
            )

        if dispatch_batch is None:
            raise ValueError(
                "Dispatch batch cannot be None."
            )

        candidates = list(
            dispatch_batch.candidates
        )

        if not candidates:
            now = self._utc_now()

            return ParallelExecutionReport(
                started_at=now,
                completed_at=now,
                task_ids=[],
                worker_count=0,
            )

        self._validate_batch(
            candidates=candidates,
            context=context,
        )

        started_at = self._utc_now()

        task_ids = [
            candidate.task_id
            for candidate in candidates
        ]

        context.runtime_metadata[
            "parallel_executor_worker_limit"
        ] = self.config.max_workers

        context.runtime_metadata[
            "parallel_executor_started_at"
        ] = started_at.isoformat()

        report = ParallelExecutionReport(
            started_at=started_at,
            completed_at=started_at,
            task_ids=task_ids,
            worker_count=min(
                self.config.max_workers,
                len(candidates),
            ),
        )

        context.set_status(
            ExecutionStatus.EXECUTING
        )

        for candidate in candidates:
            context.mark_task_active(
                candidate.task_id
            )

        with ThreadPoolExecutor(
            max_workers=self.config.max_workers,
            thread_name_prefix=self.config.thread_name_prefix,
        ) as executor:

            future_map: Dict[
                Future[Any],
                DispatchCandidate,
            ] = {}

            for candidate in candidates:
                task = context.get_task(
                    candidate.task_id
                )

                if task is None:
                    raise ParallelExecutionError(
                        "Task disappeared from execution context: "
                        f"{candidate.task_id}"
                    )

                future = executor.submit(
                    self._execute_single_task,
                    task,
                    context,
                )

                future_map[future] = candidate

                with self._lock:
                    self._active_futures[
                        future
                    ] = candidate.task_id

            self._collect_futures(
                future_map=future_map,
                context=context,
                report=report,
            )

        report.completed_at = self._utc_now()

        context.runtime_metadata[
            "parallel_executor_completed_at"
        ] = report.completed_at.isoformat()

        return report

    # ------------------------------------------------------------------
    # BATCH VALIDATION
    # ------------------------------------------------------------------

    def _validate_batch(
        self,
        *,
        candidates: Sequence[DispatchCandidate],
        context: ExecutionContext,
    ) -> None:
        """
        Validate that every dispatched task is present and executable.

        Structural dependency readiness should already have been checked
        by the scheduler. This layer performs an additional defensive
        check before execution.
        """

        seen: set[str] = set()

        for candidate in candidates:
            task_id = candidate.task_id

            if task_id in seen:
                raise UnsafeParallelExecutionError(
                    "Duplicate task in dispatch batch: "
                    f"{task_id}"
                )

            seen.add(task_id)

            task = context.get_task(task_id)

            if task is None:
                raise UnsafeParallelExecutionError(
                    "Dispatch batch references unknown task: "
                    f"{task_id}"
                )

            if task.status not in (
                TaskStatus.PENDING,
                TaskStatus.READY,
            ):
                raise UnsafeParallelExecutionError(
                    "Task is not executable in its current state: "
                    f"{task_id} ({task.status})"
                )

            if self.config.require_explicit_handlers:
                if not self.has_handler(task_id):
                    raise TaskHandlerNotFoundError(
                        "No registered execution handler for task: "
                        f"{task_id}"
                    )

        self._validate_dependency_results(
            task_ids=seen,
            context=context,
        )

    def _validate_dependency_results(
        self,
        *,
        task_ids: set[str],
        context: ExecutionContext,
    ) -> None:
        """
        Defensive dependency check.

        A task may execute only when its prerequisites have completed
        successfully.

        Failed prerequisite results are never treated as successful
        prerequisites.
        """

        if context.plan is None:
            return

        graph = context.plan

        for task_id in task_ids:
            prerequisites = (
                context.dependency_state(task_id)
            )

            unresolved = prerequisites.get(
                "unresolved",
                [],
            )

            if unresolved:
                raise UnsafeParallelExecutionError(
                    "Task has unresolved prerequisites: "
                    f"{task_id} -> {unresolved}"
                )

            failed = prerequisites.get(
                "failed",
                [],
            )

            if failed:
                raise UnsafeParallelExecutionError(
                    "Task depends on failed prerequisite(s): "
                    f"{task_id} -> {failed}"
                )

    # ------------------------------------------------------------------
    # SINGLE TASK EXECUTION
    # ------------------------------------------------------------------

    def _execute_single_task(
        self,
        task: ExecutionTask,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """
        Execute one task through its registered handler.
        """

        started_at = self._utc_now()

        handler = self._get_handler(
            task.task_id
        )

        dependency_results = self._dependency_results(
            task,
            context,
        )

        execution_input = TaskExecutionInput(
            task=task,
            context=context,
            dependency_results=dependency_results,
            created_at=started_at,
        )

        try:
            raw_output = handler(
                execution_input
            )

            result = self._normalize_handler_output(
                task=task,
                output=raw_output,
                started_at=started_at,
            )

            if result.success:
                context.mark_task_completed(
                    task.task_id,
                    result=result,
                )
            else:
                context.mark_task_failed(
                    task.task_id,
                    result=result,
                )

            return result

        except Exception as exc:
            completed_at = self._utc_now()

            result = ExecutionResult(
                task_id=task.task_id,
                success=False,
                output=None,
                error=str(exc),
                started_at=started_at,
                completed_at=completed_at,
                failure_type=FailureType.EXECUTION_ERROR,
                metadata={
                    "exception_type": type(exc).__name__,
                },
            )

            context.mark_task_failed(
                task.task_id,
                result=result,
            )

            return result

    # ------------------------------------------------------------------
    # FUTURE COLLECTION
    # ------------------------------------------------------------------

    def _collect_futures(
        self,
        *,
        future_map: Mapping[
            Future[Any],
            DispatchCandidate,
        ],
        context: ExecutionContext,
        report: ParallelExecutionReport,
    ) -> None:
        """
        Collect concurrently completed futures.

        Results are written into the execution context as they arrive.
        """

        ordered_results: Dict[
            str,
            ExecutionResult,
        ] = {}

        try:
            for future in as_completed(
                future_map
            ):
                candidate = future_map[future]
                task_id = candidate.task_id

                try:
                    result = future.result()

                    if not isinstance(
                        result,
                        ExecutionResult,
                    ):
                        raise ParallelExecutionError(
                            "Task handler returned an invalid "
                            "execution result for "
                            f"{task_id}"
                        )

                    ordered_results[
                        task_id
                    ] = result

                    report.results[
                        task_id
                    ] = result

                    if result.success:
                        report.completed_task_ids.append(
                            task_id
                        )
                    else:
                        report.failed_task_ids.append(
                            task_id
                        )

                        if result.error:
                            report.errors[
                                task_id
                            ] = result.error

                    if (
                        self.config.fail_fast
                        and not result.success
                    ):
                        self._cancel_pending_futures(
                            future_map
                        )
                        break

                except Exception as exc:
                    error = str(exc)

                    result = self._build_collection_failure(
                        task_id=task_id,
                        error=error,
                    )

                    ordered_results[
                        task_id
                    ] = result

                    report.results[
                        task_id
                    ] = result

                    report.failed_task_ids.append(
                        task_id
                    )

                    report.errors[
                        task_id
                    ] = error

                    if self.config.fail_fast:
                        self._cancel_pending_futures(
                            future_map
                        )
                        break

                finally:
                    with self._lock:
                        self._active_futures.pop(
                            future,
                            None,
                        )

        finally:
            if self.config.preserve_result_order:
                self._restore_result_order(
                    report=report,
                    context=context,
                    ordered_results=ordered_results,
                )

    def _cancel_pending_futures(
        self,
        future_map: Mapping[
            Future[Any],
            DispatchCandidate,
        ],
    ) -> None:
        """
        Request cancellation for futures that have not started.

        Running tasks cannot safely be forcefully killed by the standard
        Python ThreadPoolExecutor.
        """

        for future in future_map:
            if not future.done():
                future.cancel()

    # ------------------------------------------------------------------
    # OUTPUT NORMALIZATION
    # ------------------------------------------------------------------

    def _normalize_handler_output(
        self,
        *,
        task: ExecutionTask,
        output: Any,
        started_at: datetime,
    ) -> ExecutionResult:
        """
        Normalize handler output into the common ALPHA result contract.
        """

        completed_at = self._utc_now()

        if isinstance(
            output,
            ExecutionResult,
        ):
            if output.completed_at is None:
                output.completed_at = completed_at

            if output.started_at is None:
                output.started_at = started_at

            return output

        if isinstance(
            output,
            TaskExecutionOutput,
        ):
            return ExecutionResult(
                task_id=task.task_id,
                success=output.success,
                output=output.value,
                error=output.error,
                started_at=started_at,
                completed_at=completed_at,
                metadata=dict(
                    output.metadata
                ),
            )

        return ExecutionResult(
            task_id=task.task_id,
            success=True,
            output=output,
            error=None,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _build_collection_failure(
        self,
        *,
        task_id: str,
        error: str,
    ) -> ExecutionResult:
        now = self._utc_now()

        return ExecutionResult(
            task_id=task_id,
            success=False,
            output=None,
            error=error,
            started_at=now,
            completed_at=now,
            failure_type=FailureType.EXECUTION_ERROR,
        )

    # ------------------------------------------------------------------
    # DEPENDENCY DATA
    # ------------------------------------------------------------------

    def _dependency_results(
        self,
        task: ExecutionTask,
        context: ExecutionContext,
    ) -> Dict[str, ExecutionResult]:
        """
        Return completed prerequisite results for the task.
        """

        state = context.dependency_state(
            task.task_id
        )

        prerequisite_ids = state.get(
            "prerequisites",
            [],
        )

        results: Dict[
            str,
            ExecutionResult,
        ] = {}

        for prerequisite_id in prerequisite_ids:
            result = context.get_result(
                prerequisite_id
            )

            if result is not None:
                results[
                    prerequisite_id
                ] = result

        return results

    # ------------------------------------------------------------------
    # HANDLERS
    # ------------------------------------------------------------------

    def _get_handler(
        self,
        task_id: str,
    ) -> TaskHandler:
        with self._lock:
            handler = self._handlers.get(
                task_id
            )

        if handler is None:
            raise TaskHandlerNotFoundError(
                "No execution handler registered for task: "
                f"{task_id}"
            )

        return handler

    # ------------------------------------------------------------------
    # RESULT ORDER
    # ------------------------------------------------------------------

    def _restore_result_order(
        self,
        *,
        report: ParallelExecutionReport,
        context: ExecutionContext,
        ordered_results: Mapping[
            str,
            ExecutionResult,
        ],
    ) -> None:
        """
        Restore task order based on the original dispatch batch.

        Actual completion remains concurrent; this only controls the
        deterministic presentation order of the report.
        """

        report.results = {
            task_id: ordered_results[task_id]
            for task_id in report.task_ids
            if task_id in ordered_results
        }

        report.completed_task_ids = [
            task_id
            for task_id in report.task_ids
            if task_id in report.results
            and report.results[
                task_id
            ].success
        ]

        report.failed_task_ids = [
            task_id
            for task_id in report.task_ids
            if task_id in report.results
            and not report.results[
                task_id
            ].success
        ]

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)


__all__ = [
    "ParallelExecutionError",
    "ExecutorConfigurationError",
    "TaskHandlerNotFoundError",
    "UnsafeParallelExecutionError",
    "ParallelExecutionConfig",
    "TaskExecutionInput",
    "TaskExecutionOutput",
    "ParallelExecutionReport",
    "ParallelExecutor",
              ]
