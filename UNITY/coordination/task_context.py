"""
VALE UNITY — Task Context

Represents the shared identity and lifecycle context of one cognitive task.

TaskContext is the common task-level reference used by UNITY coordination.

It does NOT:
- determine the user's objective
- replace HEROIC
- decide execution strategy
- perform routing
- perform verification
- generate the final answer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_TASK_CONTEXT_FOUNDATION"


def _utc_now() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TaskContext:
    """
    Shared context describing one VALE cognitive task.

    The purpose is continuity.

    Every participating component should be able to understand that
    information belongs to the same task rather than treating each
    communication as an isolated request.
    """

    user_message: str

    task_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    correlation_id: Optional[str] = None

    status: str = "CREATED"

    objective: Optional[str] = None

    active_brains: List[str] = field(
        default_factory=list
    )

    required_capabilities: List[str] = field(
        default_factory=list
    )

    completed_capabilities: List[str] = field(
        default_factory=list
    )

    pending_capabilities: List[str] = field(
        default_factory=list
    )

    shared_facts: Dict[str, Any] = field(
        default_factory=dict
    )

    assumptions: Dict[str, Any] = field(
        default_factory=dict
    )

    constraints: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    created_at: str = field(
        default_factory=_utc_now
    )

    updated_at: str = field(
        default_factory=_utc_now
    )

    def __post_init__(self) -> None:

        self.user_message = str(
            self.user_message
        ).strip()

        if self.correlation_id is None:
            self.correlation_id = self.task_id

        self.active_brains = self._normalize_list(
            self.active_brains
        )

        self.required_capabilities = self._normalize_list(
            self.required_capabilities
        )

        self.completed_capabilities = self._normalize_list(
            self.completed_capabilities
        )

        self.pending_capabilities = self._normalize_list(
            self.pending_capabilities
        )

        self.constraints = self._normalize_list(
            self.constraints
        )

        self.shared_facts = dict(
            self.shared_facts or {}
        )

        self.assumptions = dict(
            self.assumptions or {}
        )

        self.metadata = dict(
            self.metadata or {}
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Mark the task as active."""
        self.status = "ACTIVE"
        self._touch()

    def pause(self) -> None:
        """Pause the task."""
        self.status = "PAUSED"
        self._touch()

    def complete(self) -> None:
        """Mark the task as completed."""
        self.status = "COMPLETED"
        self._touch()

    def fail(
        self,
        reason: Optional[str] = None,
    ) -> None:
        """Mark the task as failed."""

        self.status = "FAILED"

        if reason:
            self.metadata["failure_reason"] = str(
                reason
            )

        self._touch()

    def cancel(
        self,
        reason: Optional[str] = None,
    ) -> None:
        """Cancel the task."""

        self.status = "CANCELLED"

        if reason:
            self.metadata["cancellation_reason"] = str(
                reason
            )

        self._touch()

    # ------------------------------------------------------------------
    # Objective
    # ------------------------------------------------------------------

    def set_objective(
        self,
        objective: Optional[str],
    ) -> None:
        """Store the currently recognized task objective."""

        self.objective = (
            None
            if objective is None
            else str(objective).strip()
        )

        self._touch()

    # ------------------------------------------------------------------
    # Brain participation
    # ------------------------------------------------------------------

    def add_brain(
        self,
        brain_name: str,
    ) -> None:
        """Register a brain as active for this task."""

        normalized = self._normalize_brain(
            brain_name
        )

        if normalized and normalized not in self.active_brains:
            self.active_brains.append(
                normalized
            )
            self._touch()

    def remove_brain(
        self,
        brain_name: str,
    ) -> None:
        """Remove a brain from active task participation."""

        normalized = self._normalize_brain(
            brain_name
        )

        if normalized in self.active_brains:
            self.active_brains.remove(
                normalized
            )
            self._touch()

    # ------------------------------------------------------------------
    # Capability tracking
    # ------------------------------------------------------------------

    def require_capability(
        self,
        capability: str,
    ) -> None:
        """Add a required capability."""

        capability = str(
            capability
        ).strip()

        if not capability:
            return

        if capability not in self.required_capabilities:
            self.required_capabilities.append(
                capability
            )

        if (
            capability not in self.completed_capabilities
            and capability not in self.pending_capabilities
        ):
            self.pending_capabilities.append(
                capability
            )

        self._touch()

    def complete_capability(
        self,
        capability: str,
    ) -> None:
        """Mark a capability as completed."""

        capability = str(
            capability
        ).strip()

        if not capability:
            return

        if capability not in self.completed_capabilities:
            self.completed_capabilities.append(
                capability
            )

        if capability in self.pending_capabilities:
            self.pending_capabilities.remove(
                capability
            )

        self._touch()

    def has_pending_capabilities(self) -> bool:
        """Return whether capabilities remain unfinished."""
        return bool(
            self.pending_capabilities
        )

    # ------------------------------------------------------------------
    # Shared information
    # ------------------------------------------------------------------

    def set_fact(
        self,
        key: str,
        value: Any,
    ) -> None:
        """Store a shared task fact."""

        self.shared_facts[str(key)] = value
        self._touch()

    def get_fact(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Retrieve a shared task fact."""

        return self.shared_facts.get(
            str(key),
            default,
        )

    def set_assumption(
        self,
        key: str,
        value: Any,
    ) -> None:
        """
        Store an assumption separately from shared facts.

        This distinction is important for evidence-aware cognition.
        """

        self.assumptions[str(key)] = value
        self._touch()

    def get_assumption(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Retrieve a task assumption."""

        return self.assumptions.get(
            str(key),
            default,
        )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    def add_constraint(
        self,
        constraint: str,
    ) -> None:
        """Add a task constraint."""

        constraint = str(
            constraint
        ).strip()

        if (
            constraint
            and constraint not in self.constraints
        ):
            self.constraints.append(
                constraint
            )
            self._touch()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def set_metadata(
        self,
        key: str,
        value: Any,
    ) -> None:
        """Set task metadata."""

        self.metadata[str(key)] = value
        self._touch()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        """Validate the structural task context."""

        errors: List[str] = []

        if not self.task_id:
            errors.append(
                "task_id is required."
            )

        if not self.user_message:
            errors.append(
                "user_message is required."
            )

        if self.status not in {
            "CREATED",
            "ACTIVE",
            "PAUSED",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        }:
            errors.append(
                f"Invalid task status: {self.status}"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "task_id": self.task_id,
            "status": self.status,
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task context."""

        return {
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,

            "user_message": self.user_message,
            "objective": self.objective,

            "status": self.status,

            "active_brains": list(
                self.active_brains
            ),

            "required_capabilities": list(
                self.required_capabilities
            ),

            "completed_capabilities": list(
                self.completed_capabilities
            ),

            "pending_capabilities": list(
                self.pending_capabilities
            ),

            "shared_facts": dict(
                self.shared_facts
            ),

            "assumptions": dict(
                self.assumptions
            ),

            "constraints": list(
                self.constraints
            ),

            "metadata": dict(
                self.metadata
            ),

            "created_at": self.created_at,
            "updated_at": self.updated_at,

            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _touch(self) -> None:
        self.updated_at = _utc_now()

    @staticmethod
    def _normalize_brain(
        value: Any,
    ) -> str:
        return str(value).strip().upper()

    @staticmethod
    def _normalize_list(
        values: Optional[List[Any]],
    ) -> List[str]:

        if not values:
            return []

        result: List[str] = []

        for value in values:
            normalized = str(value).strip()

            if normalized and normalized not in result:
                result.append(normalized)

        return result


__all__ = [
    "VERSION",
    "ARCHITECTURE_STAGE",
    "TaskContext",
  ]
