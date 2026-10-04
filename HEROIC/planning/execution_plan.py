from future import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class HeroicExecutionPlan:
"""
Execution-oriented representation of a HEROIC plan.

HEROIC determines what must be accomplished and in what dependency-safe
structure. This object represents that structure for downstream execution
systems such as ALPHA.

It does not execute tasks itself.
"""

plan_id: str
mission_id: Optional[str] = None
objective_id: Optional[str] = None
goal_id: Optional[str] = None

ordered_task_ids: List[str] = field(default_factory=list)

parallel_task_groups: List[List[str]] = field(
    default_factory=list
)

dependency_map: Dict[str, List[str]] = field(
    default_factory=dict
)

required_capabilities: List[str] = field(
    default_factory=list
)

required_brains: List[str] = field(
    default_factory=list
)

inputs: Dict[str, Any] = field(
    default_factory=dict
)

expected_outputs: List[str] = field(
    default_factory=list
)

success_criteria: List[str] = field(
    default_factory=list
)

constraints: List[str] = field(
    default_factory=list
)

verification_required: bool = True

metadata: Dict[str, Any] = field(
    default_factory=dict
)

def add_task(self, task_id: str) -> None:
    """Add a task to the execution order if it is not already present."""
    if task_id not in self.ordered_task_ids:
        self.ordered_task_ids.append(task_id)

def add_parallel_group(
    self,
    task_ids: List[str],
) -> None:
    """
    Add a parallel execution group.

    Empty groups and duplicate groups are ignored.
    """
    if not task_ids:
        return

    normalized = list(dict.fromkeys(task_ids))

    if normalized not in self.parallel_task_groups:
        self.parallel_task_groups.append(normalized)

def add_dependency(
    self,
    task_id: str,
    dependency_task_id: str,
) -> None:
    """Register a dependency for a task."""
    dependencies = self.dependency_map.setdefault(
        task_id,
        [],
    )

    if dependency_task_id not in dependencies:
        dependencies.append(dependency_task_id)

def add_required_capability(
    self,
    capability: str,
) -> None:
    """Register a required capability."""
    if capability and capability not in self.required_capabilities:
        self.required_capabilities.append(capability)

def add_required_brain(
    self,
    brain: str,
) -> None:
    """Register a required brain."""
    if brain and brain not in self.required_brains:
        self.required_brains.append(brain)

def add_expected_output(
    self,
    output: str,
) -> None:
    """Register an expected execution output."""
    if output and output not in self.expected_outputs:
        self.expected_outputs.append(output)

def add_success_criterion(
    self,
    criterion: str,
) -> None:
    """Register a success criterion."""
    if criterion and criterion not in self.success_criteria:
        self.success_criteria.append(criterion)

def add_constraint(
    self,
    constraint: str,
) -> None:
    """Register an execution constraint."""
    if constraint and constraint not in self.constraints:
        self.constraints.append(constraint)

def is_empty(self) -> bool:
    """Return True when the execution plan contains no tasks."""
    return not self.ordered_task_ids

def task_count(self) -> int:
    """Return the number of unique ordered tasks."""
    return len(self.ordered_task_ids)

def parallel_stage_count(self) -> int:
    """Return the number of parallel execution stages."""
    return len(self.parallel_task_groups)

def to_dict(self) -> Dict[str, Any]:
    """Serialize the execution plan."""
    return {
        "plan_id": self.plan_id,
        "mission_id": self.mission_id,
        "objective_id": self.objective_id,
        "goal_id": self.goal_id,
        "ordered_task_ids": list(self.ordered_task_ids),
        "parallel_task_groups": [
            list(group)
            for group in self.parallel_task_groups
        ],
        "dependency_map": {
            task_id: list(dependencies)
            for task_id, dependencies in self.dependency_map.items()
        },
        "required_capabilities": list(
            self.required_capabilities
        ),
        "required_brains": list(
            self.required_brains
        ),
        "inputs": dict(self.inputs),
        "expected_outputs": list(
            self.expected_outputs
        ),
        "success_criteria": list(
            self.success_criteria
        ),
        "constraints": list(
            self.constraints
        ),
        "verification_required": self.verification_required,
        "metadata": dict(self.metadata),
    }

@classmethod
def from_plan_state(
    cls,
    plan: Any,
) -> "HeroicExecutionPlan":
    """
    Create an execution plan from HeroicPlanState.

    The method intentionally uses duck typing so this representation
    remains decoupled from the planning-state implementation.
    """
    execution_plan = cls(
        plan_id=plan.plan_id,
        mission_id=getattr(plan, "mission_id", None),
        objective_id=getattr(plan, "objective_id", None),
        goal_id=getattr(plan, "goal_id", None),
        ordered_task_ids=list(
            getattr(plan, "ordered_task_ids", [])
        ),
        parallel_task_groups=[
            list(group)
            for group in getattr(
                plan,
                "parallel_task_groups",
                [],
            )
        ],
        dependency_map={
            task_id: list(dependencies)
            for task_id, dependencies in getattr(
                plan,
                "dependency_map",
                {},
            ).items()
        },
        required_capabilities=list(
            getattr(
                plan,
                "required_capabilities",
                [],
            )
        ),
        required_brains=list(
            getattr(
                plan,
                "required_brains",
                [],
            )
        ),
        inputs=dict(
            getattr(
                plan,
                "inputs",
                {},
            )
        ),
        expected_outputs=list(
            getattr(
                plan,
                "expected_outputs",
                [],
            )
        ),
        success_criteria=list(
            getattr(
                plan,
                "success_criteria",
                [],
            )
        ),
        constraints=list(
            getattr(
                plan,
                "constraints",
                [],
            )
        ),
        verification_required=getattr(
            plan,
            "verification_required",
            True,
        ),
        metadata=dict(
            getattr(
                plan,
                "metadata",
                {},
            )
        ),
    )

    return execution_plan
