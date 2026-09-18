"""
VALE ALPHA - Execution Planner

Transforms an ExecutionRequest into a structured ExecutionPlan.

The ExecutionPlanner is responsible for the initial construction of
ALPHA's execution strategy.

Architectural boundary:

    HEROIC
        ↓
    Determines WHAT VALE needs to accomplish
        ↓
    ALPHA
        ↓
    Determines HOW that work should be organized and executed
        ↓
    Scheduler / Executor
        ↓
    Performs the work

The planner does NOT:
    - perform brain reasoning
    - determine final truth
    - make final user decisions
    - verify intelligence
    - execute tasks
    - allocate physical workers
    - run threads/processes
    - perform network calls
    - silently remove verification requirements

This file establishes a clean planning boundary so later ALPHA systems
can evolve independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..core.execution_models import (
    DependencyType,
    ExecutionConstraints,
    ExecutionPlan,
    ExecutionRequest,
    ExecutionTask,
    ResourceClass,
    ResourceRequirement,
    TaskDependency,
    TaskKind,
    TaskPriority,
    VerificationRequirement,
)

from .task_graph import (
    DependencyCycleError,
    TaskDependencyGraph,
    TaskGraphError,
)


# ============================================================================
# PLANNING ERRORS
# ============================================================================


class PlanningError(Exception):
    """
    Base exception for ALPHA planning failures.
    """


class InvalidExecutionRequestError(PlanningError):
    """
    Raised when an execution request cannot be converted into a valid plan.
    """


class PlanningConfigurationError(PlanningError):
    """
    Raised when planner configuration is invalid.
    """


# ============================================================================
# PLANNING SPECIFICATIONS
# ============================================================================


@dataclass(frozen=True)
class TaskSpecification:
    """
    Declarative description of a task that should appear in an execution plan.

    TaskSpecification is intentionally separate from ExecutionTask.

    TaskSpecification describes what the planner wants to create.

    ExecutionTask is the actual task model stored inside the execution plan.
    """

    name: str

    task_kind: TaskKind = TaskKind.CUSTOM

    description: str = ""

    target: Optional[str] = None

    capability: Optional[str] = None

    priority: Optional[TaskPriority] = None

    resource_requirement: Optional[ResourceRequirement] = None

    constraints: Optional[ExecutionConstraints] = None

    input_data: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class DependencySpecification:
    """
    Declarative dependency between two planned tasks.

    Names are used here because task IDs do not exist until the planner
    materializes the TaskSpecification objects into ExecutionTask objects.
    """

    dependent_task_name: str

    prerequisite_task_name: str

    dependency_type: DependencyType = DependencyType.REQUIRES

    required: bool = True

    description: str = ""


@dataclass(frozen=True)
class PlanningBlueprint:
    """
    Optional blueprint supplied to the planner.

    A blueprint allows HEROIC or another authorized VALE component to provide
    an already-understood decomposition without forcing ALPHA to rediscover
    the cognitive objective.

    ALPHA still decides the execution representation and validates it.
    """

    tasks: Tuple[TaskSpecification, ...] = ()

    dependencies: Tuple[DependencySpecification, ...] = ()

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================================
# EXECUTION PLANNER
# ============================================================================


class ExecutionPlanner:
    """
    Builds an ExecutionPlan from an ExecutionRequest.

    The planner supports two modes:

    1. Blueprint mode
        A higher-level VALE component provides explicit task structure.

    2. Request-only mode
        The planner creates a minimal execution task representing the
        requested work.

    Important:

    ALPHA should not invent specialist cognitive work merely because a brain
    exists. Specialized decomposition belongs to the higher-level objective
    and capability-selection architecture.

    The planner therefore prefers explicit task specifications when complex
    decomposition is required.
    """

    VERSION = "0.1.0"

    COMPONENT_NAME = "ALPHA_EXECUTION_PLANNER"

    def __init__(
        self,
        *,
        default_priority: TaskPriority = TaskPriority.NORMAL,
        default_resource_class: ResourceClass = ResourceClass.LIGHT,
    ) -> None:
        self.default_priority = default_priority
        self.default_resource_class = default_resource_class

        self._validate_configuration()

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def create_plan(
        self,
        request: ExecutionRequest,
        blueprint: Optional[PlanningBlueprint] = None,
    ) -> ExecutionPlan:
        """
        Create and validate an ExecutionPlan.

        Args:
            request:
                Original execution request.

            blueprint:
                Optional explicit decomposition supplied by an authorized
                higher-level component.

        Returns:
            A validated ExecutionPlan.

        Raises:
            InvalidExecutionRequestError:
                When the request is invalid.

            PlanningError:
                When the generated plan is structurally invalid.
        """

        self._validate_request(request)

        plan = ExecutionPlan(
            request_id=request.request_id,
            metadata={
                "planner": self.COMPONENT_NAME,
                "planner_version": self.VERSION,
                "planning_mode": (
                    "BLUEPRINT"
                    if blueprint is not None
                    else "REQUEST_ONLY"
                ),
            },
        )

        if blueprint is None:
            self._create_request_only_plan(
                plan=plan,
                request=request,
            )
        else:
            self._create_blueprint_plan(
                plan=plan,
                request=request,
                blueprint=blueprint,
            )

        self._validate_plan(plan)

        plan.metadata["validated"] = True
        plan.metadata["task_count"] = plan.task_count()
        plan.metadata["dependency_count"] = len(
            plan.dependencies
        )

        return plan

    # ========================================================================
    # REQUEST-ONLY PLANNING
    # ========================================================================

    def _create_request_only_plan(
        self,
        *,
        plan: ExecutionPlan,
        request: ExecutionRequest,
    ) -> None:
        """
        Create a minimal plan when no explicit decomposition is supplied.

        This is intentionally conservative.

        ALPHA does not fabricate a complex cognitive pipeline simply because
        the request exists.

        Later HEROIC/ALPHA integration can provide richer blueprints.
        """

        resource_requirement = ResourceRequirement(
            resource_class=self.default_resource_class
        )

        task = ExecutionTask(
            name="execute_request",
            task_kind=request.task_kind,
            description=request.objective,
            target=(
                request.preferred_brains[0]
                if request.preferred_brains
                else None
            ),
            capability=(
                request.required_capabilities[0]
                if request.required_capabilities
                else None
            ),
            priority=request.priority or self.default_priority,
            resource_requirement=resource_requirement,
            constraints=request.constraints,
            input_data=dict(request.input_data),
            metadata={
                "source": "ExecutionRequest",
                "request_id": request.request_id,
                "required_capabilities": list(
                    request.required_capabilities
                ),
                "preferred_brains": list(
                    request.preferred_brains
                ),
            },
        )

        plan.add_task(task)

    # ========================================================================
    # BLUEPRINT PLANNING
    # ========================================================================

    def _create_blueprint_plan(
        self,
        *,
        plan: ExecutionPlan,
        request: ExecutionRequest,
        blueprint: PlanningBlueprint,
    ) -> None:
        """
        Materialize a PlanningBlueprint into an ExecutionPlan.
        """

        if not blueprint.tasks:
            raise PlanningError(
                "Planning blueprint contains no tasks"
            )

        task_name_to_id: Dict[str, str] = {}

        for specification in blueprint.tasks:
            task = self._materialize_task(
                request=request,
                specification=specification,
            )

            normalized_name = self._normalize_task_name(
                specification.name
            )

            if normalized_name in task_name_to_id:
                raise PlanningError(
                    "Duplicate task name in planning blueprint: "
                    f"{specification.name}"
                )

            task_name_to_id[normalized_name] = task.task_id

            plan.add_task(task)

        for dependency in blueprint.dependencies:
            self._materialize_dependency(
                plan=plan,
                dependency=dependency,
                task_name_to_id=task_name_to_id,
            )

        plan.metadata.update(
            {
                "blueprint_metadata": dict(
                    blueprint.metadata
                ),
            }
        )

    # ========================================================================
    # TASK MATERIALIZATION
    # ========================================================================

    def _materialize_task(
        self,
        *,
        request: ExecutionRequest,
        specification: TaskSpecification,
    ) -> ExecutionTask:
        """
        Convert a TaskSpecification into an ExecutionTask.
        """

        if not specification.name.strip():
            raise PlanningError(
                "Task specification name cannot be empty"
            )

        priority = (
            specification.priority
            if specification.priority is not None
            else request.priority
        )

        resource_requirement = (
            specification.resource_requirement
            if specification.resource_requirement is not None
            else ResourceRequirement(
                resource_class=self.default_resource_class
            )
        )

        constraints = (
            specification.constraints
            if specification.constraints is not None
            else request.constraints
        )

        metadata = dict(specification.metadata)

        metadata.update(
            {
                "request_id": request.request_id,
                "planner": self.COMPONENT_NAME,
            }
        )

        return ExecutionTask(
            name=specification.name,
            task_kind=specification.task_kind,
            description=specification.description,
            target=specification.target,
            capability=specification.capability,
            priority=priority,
            resource_requirement=resource_requirement,
            constraints=constraints,
            input_data=dict(specification.input_data),
            metadata=metadata,
        )

    # ========================================================================
    # DEPENDENCY MATERIALIZATION
    # ========================================================================

    def _materialize_dependency(
        self,
        *,
        plan: ExecutionPlan,
        dependency: DependencySpecification,
        task_name_to_id: Dict[str, str],
    ) -> None:
        """
        Convert a name-based dependency specification into a task-ID-based
        TaskDependency.
        """

        dependent_name = self._normalize_task_name(
            dependency.dependent_task_name
        )

        prerequisite_name = self._normalize_task_name(
            dependency.prerequisite_task_name
        )

        if dependent_name not in task_name_to_id:
            raise PlanningError(
                "Dependency references unknown dependent task: "
                f"{dependency.dependent_task_name}"
            )

        if prerequisite_name not in task_name_to_id:
            raise PlanningError(
                "Dependency references unknown prerequisite task: "
                f"{dependency.prerequisite_task_name}"
            )

        task_dependency = TaskDependency(
            dependent_task_id=task_name_to_id[
                dependent_name
            ],
            prerequisite_task_id=task_name_to_id[
                prerequisite_name
            ],
            dependency_type=dependency.dependency_type,
            required=dependency.required,
            description=dependency.description,
        )

        plan.add_dependency(task_dependency)

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def _validate_request(
        self,
        request: ExecutionRequest,
    ) -> None:
        """
        Validate the incoming request before planning.
        """

        if not isinstance(request, ExecutionRequest):
            raise InvalidExecutionRequestError(
                "request must be an ExecutionRequest"
            )

        if not request.objective.strip():
            raise InvalidExecutionRequestError(
                "Execution objective cannot be empty"
            )

        if not request.requester.strip():
            raise InvalidExecutionRequestError(
                "Execution requester cannot be empty"
            )

        self._validate_verification_requirements(
            request.constraints.verification
        )

    def _validate_plan(
        self,
        plan: ExecutionPlan,
    ) -> None:
        """
        Validate the complete execution plan.

        Validation is intentionally structural.

        Semantic truth/reliability is handled elsewhere.
        """

        if not plan.tasks:
            raise PlanningError(
                "Execution plan contains no tasks"
            )

        for task in plan.tasks.values():
            self._validate_task(task)

        try:
            graph = TaskDependencyGraph.from_plan(
                plan
            )

            graph.validate()

        except DependencyCycleError as exc:
            raise PlanningError(
                "Execution plan contains a dependency cycle"
            ) from exc

        except TaskGraphError as exc:
            raise PlanningError(
                f"Invalid execution dependency graph: {exc}"
            ) from exc

    def _validate_task(
        self,
        task: ExecutionTask,
    ) -> None:
        """
        Validate an individual execution task.
        """

        if not task.name.strip():
            raise PlanningError(
                "Execution task name cannot be empty"
            )

        if task.retry_count < 0:
            raise PlanningError(
                f"Task retry_count cannot be negative: "
                f"{task.task_id}"
            )

        self._validate_verification_requirements(
            task.constraints.verification
        )

    def _validate_verification_requirements(
        self,
        verification: VerificationRequirement,
    ) -> None:
        """
        Validate verification requirements.

        ALPHA records and preserves these requirements.
        It does not satisfy them itself.
        """

        if not isinstance(
            verification,
            VerificationRequirement,
        ):
            raise PlanningError(
                "Invalid verification requirement"
            )

        if (
            verification.minimum_confidence is not None
            and not (
                0.0
                <= verification.minimum_confidence
                <= 1.0
            )
        ):
            raise PlanningError(
                "Verification minimum_confidence must be "
                "between 0.0 and 1.0"
            )

    # ========================================================================
    # PLAN ANALYSIS
    # ========================================================================

    def analyze_plan(
        self,
        plan: ExecutionPlan,
    ) -> Dict[str, Any]:
        """
        Analyze the structural characteristics of an execution plan.

        This is descriptive information for later scheduler/optimization
        components.

        No performance numbers are fabricated.
        """

        self._validate_plan(plan)

        graph = TaskDependencyGraph.from_plan(
            plan
        )

        ready_tasks = graph.root_tasks()
        leaf_tasks = graph.leaf_tasks()

        return {
            "plan_id": plan.plan_id,
            "request_id": plan.request_id,
            "task_count": graph.task_count(),
            "dependency_count": len(
                graph.dependencies()
            ),
            "root_task_count": len(
                ready_tasks
            ),
            "leaf_task_count": len(
                leaf_tasks
            ),
            "critical_path_length": (
                graph.critical_path_length()
            ),
            "contains_cycle": graph.contains_cycle(),
            "root_task_ids": [
                task.task_id
                for task in ready_tasks
            ],
            "leaf_task_ids": [
                task.task_id
                for task in leaf_tasks
            ],
        }

    # ========================================================================
    # PLAN RECONSTRUCTION
    # ========================================================================

    def clone_plan(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionPlan:
        """
        Create a new structural copy of a plan.

        This is useful later for safe replanning/speculative planning.

        The cloned plan receives a new plan ID through ExecutionPlan's
        default factory.

        Task objects are reconstructed with new task IDs.

        This method does not execute anything.
        """

        self._validate_plan(plan)

        cloned_plan = ExecutionPlan(
            request_id=plan.request_id,
            metadata={
                **plan.metadata,
                "cloned_from_plan_id": plan.plan_id,
            },
        )

        old_to_new_task_ids: Dict[str, str] = {}

        for original_task in plan.tasks.values():
            cloned_task = ExecutionTask(
                name=original_task.name,
                task_kind=original_task.task_kind,
                description=original_task.description,
                target=original_task.target,
                capability=original_task.capability,
                priority=original_task.priority,
                resource_requirement=original_task.resource_requirement,
                constraints=original_task.constraints,
                input_data=dict(
                    original_task.input_data
                ),
                metadata=dict(
                    original_task.metadata
                ),
            )

            old_to_new_task_ids[
                original_task.task_id
            ] = cloned_task.task_id

            cloned_plan.add_task(cloned_task)

        for dependency in plan.dependencies:
            cloned_dependency = TaskDependency(
                dependent_task_id=old_to_new_task_ids[
                    dependency.dependent_task_id
                ],
                prerequisite_task_id=old_to_new_task_ids[
                    dependency.prerequisite_task_id
                ],
                dependency_type=dependency.dependency_type,
                required=dependency.required,
                description=dependency.description,
            )

            cloned_plan.add_dependency(
                cloned_dependency
            )

        self._validate_plan(cloned_plan)

        return cloned_plan

    # ========================================================================
    # HELPERS
    # ========================================================================

    @staticmethod
    def _normalize_task_name(
        name: str,
    ) -> str:
        """
        Normalize a task name for blueprint dependency matching.
        """

        return " ".join(
            name.strip().lower().split()
        )

    def _validate_configuration(self) -> None:
        """
        Validate planner configuration.
        """

        if not isinstance(
            self.default_priority,
            TaskPriority,
        ):
            raise PlanningConfigurationError(
                "default_priority must be a TaskPriority"
            )

        if not isinstance(
            self.default_resource_class,
            ResourceClass,
        ):
            raise PlanningConfigurationError(
                "default_resource_class must be a ResourceClass"
            )


# ============================================================================
# PUBLIC EXPORTS
# ============================================================================


__all__ = [
    "ExecutionPlanner",
    "PlanningBlueprint",
    "TaskSpecification",
    "DependencySpecification",
    "PlanningError",
    "InvalidExecutionRequestError",
    "PlanningConfigurationError",
      ]
