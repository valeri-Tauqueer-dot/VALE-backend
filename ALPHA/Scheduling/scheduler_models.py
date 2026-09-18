"""
VALE ALPHA - Scheduler Models

Foundational models and contracts for ALPHA's scheduling layer.

The scheduling layer determines:

    WHAT READY WORK SHOULD RUN NOW
    WHAT SHOULD WAIT
    WHAT SHOULD RUN FIRST
    WHAT CAN RUN CONCURRENTLY
    WHAT SHOULD BE DEFERRED
    WHAT SHOULD BE CANCELLED
    WHAT SHOULD BE RETRIED
    WHAT SHOULD BE ESCALATED

Important architectural boundary:

    HEROIC
        = WHAT VALE needs to accomplish

    ALPHA PLANNER
        = HOW the work is structured

    ALPHA SCHEDULER
        = WHEN / IN WHAT ORDER the structured work should execute

    ALPHA EXECUTOR
        = ACTUALLY performs the work

    MCVL
        = verifies/challenges reliability

    UNITY
        = integrates the resulting intelligence/state

This module contains DATA CONTRACTS only.

It does NOT implement:
    - scheduling algorithms
    - worker pools
    - threads
    - asyncio
    - process management
    - resource allocation
    - task execution
    - retries
    - network calls
    - final cognitive decisions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from ..core.execution_models import (
    ExecutionTask,
    ResourceClass,
    TaskPriority,
    TaskStatus,
)


# ============================================================================
# ENUMERATIONS
# ============================================================================


class SchedulerStatus(str):
    """
    Scheduler lifecycle states.

    A simple string-backed contract is used here to avoid coupling the
    scheduler models to a specific scheduling implementation.
    """

    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    DRAINING = "DRAINING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class QueueState(str):
    """
    State of a task inside the scheduling system.
    """

    WAITING = "WAITING"
    READY = "READY"
    QUEUED = "QUEUED"
    DISPATCHED = "DISPATCHED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SchedulingDecisionType(str):
    """
    Types of decisions the scheduler can produce.

    The scheduler decides execution treatment, not cognitive truth.
    """

    DISPATCH = "DISPATCH"
    WAIT = "WAIT"
    DEFER = "DEFER"
    CANCEL = "CANCEL"
    RETRY = "RETRY"
    ESCALATE = "ESCALATE"
    REPLAN = "REPLAN"
    NO_ACTION = "NO_ACTION"


class SchedulingReason(str):
    """
    Standard reasons explaining scheduler decisions.
    """

    READY = "READY"
    DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    DEADLINE_PRESSURE = "DEADLINE_PRESSURE"
    PRIORITY = "PRIORITY"
    CAPACITY_LIMIT = "CAPACITY_LIMIT"
    EXCLUSIVE_RESOURCE = "EXCLUSIVE_RESOURCE"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"
    RETRY_REQUIRED = "RETRY_REQUIRED"
    FAILURE_RECOVERY = "FAILURE_RECOVERY"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"
    REPLANNING_REQUIRED = "REPLANNING_REQUIRED"
    SCHEDULER_PAUSED = "SCHEDULER_PAUSED"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# TASK SCHEDULING METADATA
# ============================================================================


@dataclass(frozen=True)
class SchedulingPriority:
    """
    Structured priority information for one task.

    This deliberately keeps multiple priority signals instead of reducing
    everything to one hard-coded integer.

    The actual scheduler may later calculate an effective scheduling score.
    """

    task_priority: TaskPriority = TaskPriority.NORMAL

    urgency: float = 0.0

    importance: float = 0.0

    deadline_pressure: float = 0.0

    dependency_pressure: float = 0.0

    resource_cost: float = 0.0

    starvation_protection: float = 0.0

    def __post_init__(self) -> None:
        values = {
            "urgency": self.urgency,
            "importance": self.importance,
            "deadline_pressure": self.deadline_pressure,
            "dependency_pressure": self.dependency_pressure,
            "resource_cost": self.resource_cost,
            "starvation_protection": self.starvation_protection,
        }

        for name, value in values.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0.0 and 1.0"
                )


@dataclass(frozen=True)
class SchedulingDeadline:
    """
    Deadline information for a task.

    Times are expressed as monotonic runtime values where available.

    No deadline is invented when one is not provided.
    """

    deadline_ms: Optional[float] = None

    timeout_ms: Optional[float] = None

    created_at_monotonic: Optional[float] = None

    def __post_init__(self) -> None:
        if self.deadline_ms is not None and self.deadline_ms < 0:
            raise ValueError(
                "deadline_ms cannot be negative"
            )

        if self.timeout_ms is not None and self.timeout_ms < 0:
            raise ValueError(
                "timeout_ms cannot be negative"
            )


@dataclass(frozen=True)
class SchedulingResourceProfile:
    """
    Resource information relevant to scheduling.

    This is a logical scheduling representation.

    It does not represent actual CPU/GPU allocation.
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
            raise ValueError(
                "cpu_units cannot be negative"
            )

        if self.memory_mb is not None and self.memory_mb < 0:
            raise ValueError(
                "memory_mb cannot be negative"
            )

        if self.estimated_cost is not None and self.estimated_cost < 0:
            raise ValueError(
                "estimated_cost cannot be negative"
            )


# ============================================================================
# QUEUE ENTRY
# ============================================================================


@dataclass
class SchedulerQueueEntry:
    """
    Runtime representation of a task waiting inside ALPHA's scheduler.

    A queue entry references the original ExecutionTask rather than copying
    all task intelligence/state into the scheduler.

    This keeps task identity centralized.
    """

    task_id: str

    priority: SchedulingPriority

    resource_profile: SchedulingResourceProfile

    deadline: SchedulingDeadline

    state: QueueState = QueueState.WAITING

    queue_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    enqueue_sequence: int = 0

    enqueue_time_monotonic: float = field(
        default_factory=monotonic,
        repr=False,
    )

    dispatch_count: int = 0

    def mark_ready(self) -> None:
        """
        Mark the queue entry as ready.
        """

        self.state = QueueState.READY

    def mark_queued(self) -> None:
        """
        Mark the queue entry as queued.
        """

        self.state = QueueState.QUEUED

    def mark_dispatched(self) -> None:
        """
        Mark the queue entry as dispatched.
        """

        self.state = QueueState.DISPATCHED
        self.dispatch_count += 1

    def mark_deferred(self) -> None:
        """
        Mark the task as deferred.
        """

        self.state = QueueState.DEFERRED

    def mark_blocked(self) -> None:
        """
        Mark the task as dependency/resource blocked.
        """

        self.state = QueueState.BLOCKED

    def mark_cancelled(self) -> None:
        """
        Mark the task as cancelled.
        """

        self.state = QueueState.CANCELLED

    def mark_completed(self) -> None:
        """
        Mark the task as completed.
        """

        self.state = QueueState.COMPLETED

    def mark_failed(self) -> None:
        """
        Mark the task as failed.
        """

        self.state = QueueState.FAILED


# ============================================================================
# DISPATCH CANDIDATE
# ============================================================================


@dataclass(frozen=True)
class DispatchCandidate:
    """
    A task considered for dispatch.

    This is intentionally immutable.

    The scheduler can evaluate candidates without modifying task state.
    """

    task_id: str

    priority: SchedulingPriority

    resource_profile: SchedulingResourceProfile

    deadline: SchedulingDeadline

    dependency_ready: bool = False

    resource_available: bool = False

    verification_ready: bool = False

    parallel_safe: bool = False

    estimated_wait_ms: Optional[float] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================================
# SCHEDULING DECISION
# ============================================================================


@dataclass(frozen=True)
class SchedulingDecision:
    """
    Explicit scheduler decision for a task.

    A decision is a description of execution treatment.

    It is NOT a cognitive conclusion.
    """

    task_id: str

    decision: SchedulingDecisionType

    reason: SchedulingReason

    decision_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    scheduler_version: Optional[str] = None

    priority: Optional[SchedulingPriority] = None

    resource_profile: Optional[SchedulingResourceProfile] = None

    expected_delay_ms: Optional[float] = None

    retry_after_ms: Optional[float] = None

    requires_replanning: bool = False

    requires_escalation: bool = False

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================================
# DISPATCH BATCH
# ============================================================================


@dataclass
class DispatchBatch:
    """
    Group of tasks selected for one scheduling cycle.

    The batch represents candidates selected for dispatch.

    Actual concurrent execution is handled later by ALPHA's execution layer.
    """

    decisions: List[SchedulingDecision] = field(
        default_factory=list
    )

    batch_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    created_at_monotonic: float = field(
        default_factory=monotonic,
        repr=False,
    )

    max_parallelism: Optional[int] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def dispatch_task_ids(self) -> List[str]:
        """
        Return tasks that were selected for dispatch.
        """

        return [
            decision.task_id
            for decision in self.decisions
            if decision.decision
            == SchedulingDecisionType.DISPATCH
        ]

    @property
    def has_dispatches(self) -> bool:
        """
        Determine whether this batch contains work to dispatch.
        """

        return bool(self.dispatch_task_ids)


# ============================================================================
# SCHEDULER CAPACITY
# ============================================================================


@dataclass
class SchedulerCapacity:
    """
    Snapshot of logical scheduler capacity.

    This is a state contract.

    Actual measurement comes from the resource subsystem.
    """

    max_concurrent_tasks: Optional[int] = None

    active_tasks: int = 0

    queued_tasks: int = 0

    available_cpu_units: Optional[float] = None

    available_memory_mb: Optional[int] = None

    gpu_available: Optional[bool] = None

    network_available: Optional[bool] = None

    exclusive_resource_in_use: bool = False

    timestamp_monotonic: float = field(
        default_factory=monotonic,
        repr=False,
    )

    def __post_init__(self) -> None:
        if (
            self.max_concurrent_tasks is not None
            and self.max_concurrent_tasks < 1
        ):
            raise ValueError(
                "max_concurrent_tasks must be at least 1"
            )

        if self.active_tasks < 0:
            raise ValueError(
                "active_tasks cannot be negative"
            )

        if self.queued_tasks < 0:
            raise ValueError(
                "queued_tasks cannot be negative"
            )

        if (
            self.available_cpu_units is not None
            and self.available_cpu_units < 0
        ):
            raise ValueError(
                "available_cpu_units cannot be negative"
            )

        if (
            self.available_memory_mb is not None
            and self.available_memory_mb < 0
        ):
            raise ValueError(
                "available_memory_mb cannot be negative"
            )


# ============================================================================
# SCHEDULER STATE
# ============================================================================


@dataclass
class SchedulerState:
    """
    Complete runtime state contract for one ALPHA scheduler.

    This object does not perform scheduling.

    It gives the future Scheduler implementation a consistent place to
    maintain queue/task state.
    """

    scheduler_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    status: str = SchedulerStatus.CREATED

    execution_id: Optional[str] = None

    queue_entries: Dict[str, SchedulerQueueEntry] = field(
        default_factory=dict
    )

    active_task_ids: Set[str] = field(
        default_factory=set
    )

    completed_task_ids: Set[str] = field(
        default_factory=set
    )

    failed_task_ids: Set[str] = field(
        default_factory=set
    )

    blocked_task_ids: Set[str] = field(
        default_factory=set
    )

    cancelled_task_ids: Set[str] = field(
        default_factory=set
    )

    deferred_task_ids: Set[str] = field(
        default_factory=set
    )

    decisions: List[SchedulingDecision] = field(
        default_factory=list
    )

    dispatch_batches: List[DispatchBatch] = field(
        default_factory=list
    )

    capacity: Optional[SchedulerCapacity] = None

    scheduling_cycle_count: int = 0

    last_cycle_at_monotonic: Optional[float] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def register_task(
        self,
        entry: SchedulerQueueEntry,
    ) -> None:
        """
        Register a task with the scheduler state.
        """

        if entry.task_id in self.queue_entries:
            raise ValueError(
                "Task already registered with scheduler: "
                f"{entry.task_id}"
            )

        self.queue_entries[entry.task_id] = entry

    def record_decision(
        self,
        decision: SchedulingDecision,
    ) -> None:
        """
        Record a scheduling decision.
        """

        self.decisions.append(decision)

    def record_batch(
        self,
        batch: DispatchBatch,
    ) -> None:
        """
        Record a dispatch batch.
        """

        self.dispatch_batches.append(batch)

    def mark_active(
        self,
        task_id: str,
    ) -> None:
        """
        Mark task active.
        """

        self.active_task_ids.add(task_id)

        self.blocked_task_ids.discard(task_id)
        self.deferred_task_ids.discard(task_id)

        entry = self.queue_entries.get(task_id)

        if entry is not None:
            entry.mark_dispatched()

    def mark_completed(
        self,
        task_id: str,
    ) -> None:
        """
        Mark task completed.
        """

        self.active_task_ids.discard(task_id)

        self.completed_task_ids.add(task_id)

        self.failed_task_ids.discard(task_id)
        self.blocked_task_ids.discard(task_id)
        self.deferred_task_ids.discard(task_id)
        self.cancelled_task_ids.discard(task_id)

        entry = self.queue_entries.get(task_id)

        if entry is not None:
            entry.mark_completed()

    def mark_failed(
        self,
        task_id: str,
    ) -> None:
        """
        Mark task failed.
        """

        self.active_task_ids.discard(task_id)

        self.failed_task_ids.add(task_id)

        self.completed_task_ids.discard(task_id)
        self.blocked_task_ids.discard(task_id)
        self.deferred_task_ids.discard(task_id)

        entry = self.queue_entries.get(task_id)

        if entry is not None:
            entry.mark_failed()

    def mark_blocked(
        self,
        task_id: str,
    ) -> None:
        """
        Mark task blocked.
        """

        self.blocked_task_ids.add(task_id)

        self.deferred_task_ids.discard(task_id)

        entry = self.queue_entries.get(task_id)

        if entry is not None:
            entry.mark_blocked()

    def mark_deferred(
        self,
        task_id: str,
    ) -> None:
        """
        Mark task deferred.
        """

        self.deferred_task_ids.add(task_id)

        self.blocked_task_ids.discard(task_id)

        entry = self.queue_entries.get(task_id)

        if entry is not None:
            entry.mark_deferred()

    def mark_cancelled(
        self,
        task_id: str,
    ) -> None:
        """
        Mark task cancelled.
        """

        self.active_task_ids.discard(task_id)

        self.cancelled_task_ids.add(task_id)

        self.blocked_task_ids.discard(task_id)
        self.deferred_task_ids.discard(task_id)

        entry = self.queue_entries.get(task_id)

        if entry is not None:
            entry.mark_cancelled()

    def begin_cycle(self) -> None:
        """
        Begin a new scheduler evaluation cycle.
        """

        self.scheduling_cycle_count += 1

        self.last_cycle_at_monotonic = monotonic()

    # ========================================================================
    # STATE QUERIES
    # ========================================================================

    def is_active(
        self,
        task_id: str,
    ) -> bool:
        return task_id in self.active_task_ids

    def is_completed(
        self,
        task_id: str,
    ) -> bool:
        return task_id in self.completed_task_ids

    def is_failed(
        self,
        task_id: str,
    ) -> bool:
        return task_id in self.failed_task_ids

    def is_blocked(
        self,
        task_id: str,
    ) -> bool:
        return task_id in self.blocked_task_ids

    def is_cancelled(
        self,
        task_id: str,
    ) -> bool:
        return task_id in self.cancelled_task_ids

    def terminal_task_ids(self) -> Set[str]:
        """
        Return tasks that reached a terminal scheduling state.
        """

        return (
            self.completed_task_ids
            | self.failed_task_ids
            | self.cancelled_task_ids
        )

    def pending_task_ids(self) -> Set[str]:
        """
        Return tasks that remain unfinished.
        """

        all_task_ids = set(
            self.queue_entries.keys()
        )

        return (
            all_task_ids
            - self.terminal_task_ids()
        )

    # ========================================================================
    # SNAPSHOT
    # ========================================================================

    def snapshot(self) -> Dict[str, Any]:
        """
        Produce a machine-readable scheduler state snapshot.
        """

        return {
            "scheduler_id": self.scheduler_id,
            "status": self.status,
            "execution_id": self.execution_id,
            "queue_size": len(
                self.queue_entries
            ),
            "active_count": len(
                self.active_task_ids
            ),
            "completed_count": len(
                self.completed_task_ids
            ),
            "failed_count": len(
                self.failed_task_ids
            ),
            "blocked_count": len(
                self.blocked_task_ids
            ),
            "cancelled_count": len(
                self.cancelled_task_ids
            ),
            "deferred_count": len(
                self.deferred_task_ids
            ),
            "pending_count": len(
                self.pending_task_ids()
            ),
            "scheduling_cycle_count": (
                self.scheduling_cycle_count
            ),
        }


# ============================================================================
# SCHEDULER POLICY CONTRACT
# ============================================================================


@dataclass(frozen=True)
class SchedulerPolicy:
    """
    Configuration contract for future scheduler implementations.

    This is intentionally policy-neutral.

    It exposes controls without committing ALPHA to one scheduling algorithm.
    """

    allow_parallel: bool = True

    max_parallel_tasks: Optional[int] = None

    priority_enabled: bool = True

    deadline_awareness_enabled: bool = True

    dependency_awareness_enabled: bool = True

    resource_awareness_enabled: bool = True

    starvation_protection_enabled: bool = True

    retry_scheduling_enabled: bool = True

    adaptive_replanning_enabled: bool = True

    strict_verification_preservation: bool = True

    def __post_init__(self) -> None:
        if (
            self.max_parallel_tasks is not None
            and self.max_parallel_tasks < 1
        ):
            raise ValueError(
                "max_parallel_tasks must be at least 1"
            )


# ============================================================================
# SCHEDULER INPUT
# ============================================================================


@dataclass(frozen=True)
class SchedulerInput:
    """
    Input snapshot provided to a scheduler cycle.

    The scheduler should make decisions from explicit state rather than
    hidden global state.
    """

    execution_id: str

    ready_tasks: Tuple[ExecutionTask, ...] = ()

    blocked_tasks: Tuple[ExecutionTask, ...] = ()

    active_task_ids: Tuple[str, ...] = ()

    completed_task_ids: Tuple[str, ...] = ()

    failed_task_ids: Tuple[str, ...] = ()

    capacity: Optional[SchedulerCapacity] = None

    policy: SchedulerPolicy = field(
        default_factory=SchedulerPolicy
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================================
# SCHEDULER CYCLE RESULT
# ============================================================================


@dataclass
class SchedulerCycleResult:
    """
    Result of one scheduler evaluation cycle.

    It records what the scheduler decided without executing those decisions.
    """

    execution_id: str

    cycle_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    decisions: List[SchedulingDecision] = field(
        default_factory=list
    )

    dispatch_batch: Optional[DispatchBatch] = None

    generated_at_monotonic: float = field(
        default_factory=monotonic,
        repr=False,
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def dispatch_task_ids(self) -> List[str]:
        """
        Return tasks selected for execution.
        """

        if self.dispatch_batch is None:
            return []

        return self.dispatch_batch.dispatch_task_ids

    @property
    def requires_replanning(self) -> bool:
        """
        Determine whether any scheduler decision requests replanning.
        """

        return any(
            decision.requires_replanning
            for decision in self.decisions
        )

    @property
    def requires_escalation(self) -> bool:
        """
        Determine whether any scheduler decision requests escalation.
        """

        return any(
            decision.requires_escalation
            for decision in self.decisions
        )


# ============================================================================
# PUBLIC EXPORTS
# ============================================================================


__all__ = [
    # State enums/contracts
    "SchedulerStatus",
    "QueueState",
    "SchedulingDecisionType",
    "SchedulingReason",

    # Scheduling metadata
    "SchedulingPriority",
    "SchedulingDeadline",
    "SchedulingResourceProfile",

    # Queue
    "SchedulerQueueEntry",

    # Decisions
    "DispatchCandidate",
    "SchedulingDecision",
    "DispatchBatch",

    # Capacity/state
    "SchedulerCapacity",
    "SchedulerState",

    # Policy/input/output
    "SchedulerPolicy",
    "SchedulerInput",
    "SchedulerCycleResult",
  ]
