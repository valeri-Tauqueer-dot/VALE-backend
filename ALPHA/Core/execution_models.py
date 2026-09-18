"""
VALE ALPHA - Foundational Execution Models

This module contains the core contracts/data models used by ALPHA's
execution architecture.

ALPHA is responsible for HOW VALE executes work efficiently.

This module intentionally does NOT implement:
    - scheduling algorithms
    - parallel execution
    - worker pools
    - resource allocation
    - caching
    - retries
    - networking
    - brain intelligence
    - final decision making

Those systems will consume these models later.

Design principles:
    - explicit state
    - deterministic structure
    - no fabricated telemetry
    - dependency-aware execution
    - provenance and traceability
    - failure must be visible
    - verification requirements cannot be silently removed
    - execution optimization must not change the meaning of the task
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4


# ============================================================================
# ENUMERATIONS
# ============================================================================


class ExecutionStatus(str, Enum):
    """
    Lifecycle state of an ALPHA execution request.
    """

    CREATED = "CREATED"
    PLANNING = "PLANNING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class TaskStatus(str, Enum):
    """
    Lifecycle state of an individual execution task.
    """

    CREATED = "CREATED"
    BLOCKED = "BLOCKED"
    READY = "READY"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    SKIPPED = "SKIPPED"


class TaskPriority(str, Enum):
    """
    Logical priority.

    The scheduler may later map these priorities onto an actual scheduling
    policy. The enum itself does not define that policy.
    """

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    BACKGROUND = "BACKGROUND"


class TaskKind(str, Enum):
    """
    Broad category of work ALPHA may execute.

    This is deliberately generic so specialized brains can remain responsible
    for their own intelligence.
    """

    BRAIN = "BRAIN"
    REASONING = "REASONING"
    MEMORY = "MEMORY"
    KNOWLEDGE = "KNOWLEDGE"
    VERIFICATION = "VERIFICATION"
    DATA = "DATA"
    TRANSFORMATION = "TRANSFORMATION"
    COMMUNICATION = "COMMUNICATION"
    SYSTEM = "SYSTEM"
    CUSTOM = "CUSTOM"


class ResourceClass(str, Enum):
    """
    Relative execution cost classification.

    This does NOT represent a physical CPU/GPU allocation yet.
    """

    LIGHT = "LIGHT"
    MEDIUM = "MEDIUM"
    HEAVY = "HEAVY"
    CRITICAL = "CRITICAL"


class DependencyType(str, Enum):
    """
    Relationship between two tasks.
    """

    REQUIRES = "REQUIRES"
    DATA = "DATA"
    ORDER = "ORDER"
    VERIFICATION = "VERIFICATION"
    RESOURCE = "RESOURCE"


class FailureType(str, Enum):
    """
    Broad classification of an execution failure.
    """

    VALIDATION = "VALIDATION"
    DEPENDENCY = "DEPENDENCY"
    RESOURCE = "RESOURCE"
    TIMEOUT = "TIMEOUT"
    EXECUTION = "EXECUTION"
    COMMUNICATION = "COMMUNICATION"
    INTERNAL = "INTERNAL"
    CANCELLATION = "CANCELLATION"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# EXECUTION REQUIREMENTS
# ============================================================================


@dataclass(frozen=True)
class VerificationRequirement:
    """
    Defines verification requirements attached to an execution.

    ALPHA may optimize HOW verification occurs, but it must not silently
    remove required verification.
    """

    required: bool = False

    verifier_capabilities: Tuple[str, ...] = ()

    minimum_confidence: Optional[float] = None

    contradiction_check_required: bool = False

    evidence_required: bool = False

    provenance_required: bool = False

    def __post_init__(self) -> None:
        if self.minimum_confidence is not None:
            if not 0.0 <= self.minimum_confidence <= 1.0:
                raise ValueError(
                    "minimum_confidence must be between 0.0 and 1.0"
                )


@dataclass(frozen=True)
class ResourceRequirement:
    """
    Describes the resource characteristics required by a task.

    These are logical requirements. Physical resource mapping belongs to
    ALPHA's Resource Manager and is intentionally not implemented here.
    """

    resource_class: ResourceClass = ResourceClass.LIGHT

    cpu_units: Optional[float] = None
    memory_mb: Optional[int] = None
    gpu_required: bool = False

    network_required: bool = False

    exclusive: bool = False

    estimated_cost: Optional[float] = None

    def __post_init__(self) -> None:
        if self.cpu_units is not None and self.cpu_units < 0:
            raise ValueError("cpu_units cannot be negative")

        if self.memory_mb is not None and self.memory_mb < 0:
            raise ValueError("memory_mb cannot be negative")

        if self.estimated_cost is not None and self.estimated_cost < 0:
            raise ValueError("estimated_cost cannot be negative")


@dataclass(frozen=True)
class ExecutionConstraints:
    """
    Constraints ALPHA must respect while executing work.
    """

    deadline_ms: Optional[float] = None

    timeout_ms: Optional[float] = None

    max_retries: int = 0

    allow_parallel: bool = True

    allow_cache: bool = True

    allow_reuse: bool = True

    verification: VerificationRequirement = field(
        default_factory=VerificationRequirement
    )

    def __post_init__(self) -> None:
        if self.deadline_ms is not None and self.deadline_ms < 0:
            raise ValueError("deadline_ms cannot be negative")

        if self.timeout_ms is not None and self.timeout_ms < 0:
            raise ValueError("timeout_ms cannot be negative")

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


# ============================================================================
# EXECUTION REQUEST
# ============================================================================


@dataclass
class ExecutionRequest:
    """
    Entry contract into ALPHA.

    HEROIC/UNITY or another authorized VALE component can eventually create
    an ExecutionRequest and give it to ALPHA.

    ALPHA then determines HOW the requested work should be executed.

    Important:
        The request describes the objective/work.
        It does not contain an ALPHA execution plan.

        The plan is generated later by the planning system.
    """

    objective: str

    requester: str

    request_id: str = field(default_factory=lambda: str(uuid4()))

    session_id: Optional[str] = None

    user_id: Optional[str] = None

    task_kind: TaskKind = TaskKind.CUSTOM

    priority: TaskPriority = TaskPriority.NORMAL

    constraints: ExecutionConstraints = field(
        default_factory=ExecutionConstraints
    )

    input_data: Dict[str, Any] = field(default_factory=dict)

    required_capabilities: Tuple[str, ...] = ()

    preferred_brains: Tuple[str, ...] = ()

    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at_monotonic: float = field(
        default_factory=monotonic,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not self.objective.strip():
            raise ValueError("Execution objective cannot be empty")

        if not self.requester.strip():
            raise ValueError("Execution requester cannot be empty")


# ============================================================================
# TASK DEFINITION
# ============================================================================


@dataclass
class ExecutionTask:
    """
    Atomic or near-atomic unit of work created from an ExecutionRequest.

    A task should be executable by one logical capability/brain/component.

    Tasks are intentionally independent of the actual worker implementation.
    """

    name: str

    task_kind: TaskKind

    task_id: str = field(default_factory=lambda: str(uuid4()))

    description: str = ""

    target: Optional[str] = None

    capability: Optional[str] = None

    priority: TaskPriority = TaskPriority.NORMAL

    resource_requirement: ResourceRequirement = field(
        default_factory=ResourceRequirement
    )

    constraints: ExecutionConstraints = field(
        default_factory=ExecutionConstraints
    )

    input_data: Dict[str, Any] = field(default_factory=dict)

    metadata: Dict[str, Any] = field(default_factory=dict)

    status: TaskStatus = TaskStatus.CREATED

    retry_count: int = 0

    created_at_monotonic: float = field(
        default_factory=monotonic,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Task name cannot be empty")

        if self.retry_count < 0:
            raise ValueError("retry_count cannot be negative")


# ============================================================================
# DEPENDENCIES
# ============================================================================


@dataclass(frozen=True)
class TaskDependency:
    """
    Explicit dependency relationship between two tasks.

    dependent_task_id:
        The task that must wait.

    prerequisite_task_id:
        The task that must satisfy the dependency first.
    """

    dependent_task_id: str

    prerequisite_task_id: str

    dependency_type: DependencyType = DependencyType.REQUIRES

    required: bool = True

    description: str = ""

    def __post_init__(self) -> None:
        if not self.dependent_task_id:
            raise ValueError("dependent_task_id cannot be empty")

        if not self.prerequisite_task_id:
            raise ValueError("prerequisite_task_id cannot be empty")

        if self.dependent_task_id == self.prerequisite_task_id:
            raise ValueError("A task cannot depend on itself")


# ============================================================================
# EXECUTION PLAN
# ============================================================================


@dataclass
class ExecutionPlan:
    """
    ALPHA's representation of HOW a request should be executed.

    The planner creates this.

    The scheduler consumes this.

    The executor executes the tasks.

    The monitor observes the resulting execution.

    This separation is intentional.
    """

    request_id: str

    tasks: Dict[str, ExecutionTask] = field(default_factory=dict)

    dependencies: List[TaskDependency] = field(default_factory=list)

    plan_id: str = field(default_factory=lambda: str(uuid4()))

    status: ExecutionStatus = ExecutionStatus.CREATED

    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at_monotonic: float = field(
        default_factory=monotonic,
        repr=False,
    )

    def add_task(self, task: ExecutionTask) -> None:
        """
        Add a task to the plan.

        Duplicate task IDs are rejected because task identity must remain
        deterministic inside the execution graph.
        """

        if task.task_id in self.tasks:
            raise ValueError(
                f"Task already exists in plan: {task.task_id}"
            )

        self.tasks[task.task_id] = task

    def add_dependency(self, dependency: TaskDependency) -> None:
        """
        Add a dependency after validating that both referenced tasks exist.
        """

        if dependency.dependent_task_id not in self.tasks:
            raise ValueError(
                "Dependent task does not exist in execution plan: "
                f"{dependency.dependent_task_id}"
            )

        if dependency.prerequisite_task_id not in self.tasks:
            raise ValueError(
                "Prerequisite task does not exist in execution plan: "
                f"{dependency.prerequisite_task_id}"
            )

        self.dependencies.append(dependency)

    def dependencies_for(self, task_id: str) -> List[TaskDependency]:
        """
        Return all prerequisites for a task.
        """

        return [
            dependency
            for dependency in self.dependencies
            if dependency.dependent_task_id == task_id
        ]

    def prerequisites_for(self, task_id: str) -> Set[str]:
        """
        Return prerequisite task IDs.
        """

        return {
            dependency.prerequisite_task_id
            for dependency in self.dependencies_for(task_id)
        }

    def task_count(self) -> int:
        return len(self.tasks)


# ============================================================================
# EXECUTION RESULT
# ============================================================================


@dataclass
class ExecutionResult:
    """
    Result produced by executing one task.

    This model deliberately distinguishes:
        success
        output
        failure
        timing
        provenance
        verification state

    A result must never pretend a failed task succeeded.
    """

    task_id: str

    success: bool

    status: TaskStatus

    output: Any = None

    error: Optional[str] = None

    failure_type: Optional[FailureType] = None

    retry_count: int = 0

    started_at_monotonic: Optional[float] = None

    completed_at_monotonic: Optional[float] = None

    duration_ms: Optional[float] = None

    worker_id: Optional[str] = None

    source: Optional[str] = None

    provenance: Dict[str, Any] = field(default_factory=dict)

    verification: Dict[str, Any] = field(default_factory=dict)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def finalize_timing(self) -> None:
        """
        Calculate duration from monotonic timestamps.

        No timing value is fabricated if timestamps are unavailable.
        """

        if (
            self.started_at_monotonic is not None
            and self.completed_at_monotonic is not None
        ):
            duration = (
                self.completed_at_monotonic
                - self.started_at_monotonic
            )

            self.duration_ms = max(0.0, duration * 1000.0)


# ============================================================================
# FAILURE MODEL
# ============================================================================


@dataclass
class ExecutionFailure:
    """
    Structured representation of an execution failure.

    Failure information is preserved rather than silently converted into a
    successful fallback result.
    """

    task_id: str

    failure_type: FailureType

    message: str

    failure_id: str = field(default_factory=lambda: str(uuid4()))

    retryable: bool = False

    retry_count: int = 0

    source: Optional[str] = None

    exception_type: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    occurred_at_monotonic: float = field(
        default_factory=monotonic,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Failure message cannot be empty")

        if self.retry_count < 0:
            raise ValueError("retry_count cannot be negative")


# ============================================================================
# EXECUTION TELEMETRY
# ============================================================================


@dataclass
class ExecutionTiming:
    """
    Timing information collected from real execution.

    This class stores measurements only.

    It does not invent targets or performance numbers.
    """

    execution_id: str

    started_at_monotonic: Optional[float] = None

    completed_at_monotonic: Optional[float] = None

    queue_wait_ms: Optional[float] = None

    planning_ms: Optional[float] = None

    execution_ms: Optional[float] = None

    verification_ms: Optional[float] = None

    total_ms: Optional[float] = None

    def finalize(self) -> None:
        """
        Calculate available timing values from measured timestamps.
        """

        if (
            self.started_at_monotonic is not None
            and self.completed_at_monotonic is not None
        ):
            self.total_ms = max(
                0.0,
                (
                    self.completed_at_monotonic
                    - self.started_at_monotonic
                )
                * 1000.0,
            )


# ============================================================================
# EXECUTION TRACE
# ============================================================================


@dataclass
class ExecutionTraceEvent:
    """
    One immutable-style event in an execution trace.

    Later ALPHA monitoring/replay systems can build a complete execution
    history from these events.
    """

    execution_id: str

    event_type: str

    event_id: str = field(default_factory=lambda: str(uuid4()))

    task_id: Optional[str] = None

    component: Optional[str] = None

    status: Optional[str] = None

    details: Dict[str, Any] = field(default_factory=dict)

    timestamp_monotonic: float = field(
        default_factory=monotonic,
        repr=False,
    )


# ============================================================================
# EXECUTION SUMMARY
# ============================================================================


@dataclass
class ExecutionSummary:
    """
    Aggregate state for one complete ALPHA execution.
    """

    execution_id: str

    request_id: str

    status: ExecutionStatus

    total_tasks: int = 0

    completed_tasks: int = 0

    failed_tasks: int = 0

    cancelled_tasks: int = 0

    timed_out_tasks: int = 0

    skipped_tasks: int = 0

    results: Dict[str, ExecutionResult] = field(default_factory=dict)

    failures: List[ExecutionFailure] = field(default_factory=list)

    timing: Optional[ExecutionTiming] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def successful(self) -> bool:
        """
        True only when the execution completed without task failures.
        """

        return (
            self.status == ExecutionStatus.COMPLETED
            and self.failed_tasks == 0
            and self.timed_out_tasks == 0
            and self.cancelled_tasks == 0
        )


# ============================================================================
# PUBLIC EXPORTS
# ============================================================================


__all__ = [
    # Enums
    "ExecutionStatus",
    "TaskStatus",
    "TaskPriority",
    "TaskKind",
    "ResourceClass",
    "DependencyType",
    "FailureType",

    # Requirements
    "VerificationRequirement",
    "ResourceRequirement",
    "ExecutionConstraints",

    # Request / planning
    "ExecutionRequest",
    "ExecutionTask",
    "TaskDependency",
    "ExecutionPlan",

    # Results / failures
    "ExecutionResult",
    "ExecutionFailure",

    # Monitoring / traceability
    "ExecutionTiming",
    "ExecutionTraceEvent",
    "ExecutionSummary",
  ]
