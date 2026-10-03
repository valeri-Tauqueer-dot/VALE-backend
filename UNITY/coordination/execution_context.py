"""
VALE UNITY — Execution Context

Represents the current execution state of a VALE task.

TaskContext answers:
    "What task are we working on?"

ExecutionContext answers:
    "What is currently happening while working on it?"

This module tracks execution state without becoming an ALPHA replacement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_EXECUTION_CONTEXT_FOUNDATION"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ExecutionContext:
    """
    Shared execution state for one active cognitive workflow.
    """

    task_id: str

    execution_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    status: str = "CREATED"

    current_stage: Optional[str] = None

    current_brain: Optional[str] = None

    active_routes: List[str] = field(
        default_factory=list
    )

    completed_routes: List[str] = field(
        default_factory=list
    )

    failed_routes: List[str] = field(
        default_factory=list
    )

    active_operations: List[str] = field(
        default_factory=list
    )

    completed_operations: List[str] = field(
        default_factory=list
    )

    events: List[Dict[str, Any]] = field(
        default_factory=list
    )

    outputs: Dict[str, Any] = field(
        default_factory=dict
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

        self.task_id = str(
            self.task_id
        ).strip()

        if self.current_brain:
            self.current_brain = (
                str(
                    self.current_brain
                )
                .strip()
                .upper()
            )

        self.active_routes = self._normalize_list(
            self.active_routes
        )

        self.completed_routes = self._normalize_list(
            self.completed_routes
        )

        self.failed_routes = self._normalize_list(
            self.failed_routes
        )

        self.active_operations = self._normalize_list(
            self.active_operations
        )

        self.completed_operations = self._normalize_list(
            self.completed_operations
        )

        self.events = list(
            self.events or []
        )

        self.outputs = dict(
            self.outputs or {}
        )

        self.metadata = dict(
            self.metadata or {}
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(
        self,
        stage: Optional[str] = None,
    ) -> None:

        self.status = "ACTIVE"

        if stage:
            self.current_stage = str(
                stage
            ).strip()

        self.record_event(
            "EXECUTION_STARTED"
        )

        self._touch()

    def pause(self) -> None:

        self.status = "PAUSED"

        self.record_event(
            "EXECUTION_PAUSED"
        )

        self._touch()

    def complete(self) -> None:

        self.status = "COMPLETED"

        self.record_event(
            "EXECUTION_COMPLETED"
        )

        self._touch()

    def fail(
        self,
        reason: Optional[str] = None,
    ) -> None:

        self.status = "FAILED"

        if reason:
            self.metadata["failure_reason"] = str(
                reason
            )

        self.record_event(
            "EXECUTION_FAILED",
            {
                "reason": reason
            },
        )

        self._touch()

    # ------------------------------------------------------------------
    # Stage / brain
    # ------------------------------------------------------------------

    def set_stage(
        self,
        stage: Optional[str],
    ) -> None:

        self.current_stage = (
            None
            if stage is None
            else str(stage).strip()
        )

        self.record_event(
            "STAGE_CHANGED",
            {
                "stage": self.current_stage
            },
        )

        self._touch()

    def set_current_brain(
        self,
        brain_name: Optional[str],
    ) -> None:

        self.current_brain = (
            None
            if brain_name is None
            else str(
                brain_name
            ).strip().upper()
        )

        self.record_event(
            "BRAIN_CHANGED",
            {
                "brain": self.current_brain
            },
        )

        self._touch()

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    def activate_route(
        self,
        route_id: str,
    ) -> None:

        route_id = str(
            route_id
        ).strip()

        if (
            route_id
            and route_id not in self.active_routes
        ):
            self.active_routes.append(
                route_id
            )

        self.record_event(
            "ROUTE_ACTIVATED",
            {
                "route_id": route_id
            },
        )

        self._touch()

    def complete_route(
        self,
        route_id: str,
    ) -> None:

        route_id = str(
            route_id
        ).strip()

        if route_id in self.active_routes:
            self.active_routes.remove(
                route_id
            )

        if (
            route_id
            and route_id not in self.completed_routes
        ):
            self.completed_routes.append(
                route_id
            )

        self.record_event(
            "ROUTE_COMPLETED",
            {
                "route_id": route_id
            },
        )

        self._touch()

    def fail_route(
        self,
        route_id: str,
        reason: Optional[str] = None,
    ) -> None:

        route_id = str(
            route_id
        ).strip()

        if route_id in self.active_routes:
            self.active_routes.remove(
                route_id
            )

        if (
            route_id
            and route_id not in self.failed_routes
        ):
            self.failed_routes.append(
                route_id
            )

        self.record_event(
            "ROUTE_FAILED",
            {
                "route_id": route_id,
                "reason": reason,
            },
        )

        self._touch()

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def activate_operation(
        self,
        operation: str,
    ) -> None:

        operation = str(
            operation
        ).strip()

        if (
            operation
            and operation not in self.active_operations
        ):
            self.active_operations.append(
                operation
            )

        self._touch()

    def complete_operation(
        self,
        operation: str,
    ) -> None:

        operation = str(
            operation
        ).strip()

        if operation in self.active_operations:
            self.active_operations.remove(
                operation
            )

        if (
            operation
            and operation not in self.completed_operations
        ):
            self.completed_operations.append(
                operation
            )

        self._touch()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def record_event(
        self,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:

        self.events.append(
            {
                "event_id": str(uuid4()),
                "event_type": str(
                    event_type
                ).strip().upper(),
                "timestamp": _utc_now(),
                "payload": dict(
                    payload or {}
                ),
            }
        )

        self._touch()

    # ------------------------------------------------------------------
    # Outputs
    # ------------------------------------------------------------------

    def set_output(
        self,
        key: str,
        value: Any,
    ) -> None:

        self.outputs[str(key)] = value
        self._touch()

    def get_output(
        self,
        key: str,
        default: Any = None,
    ) -> Any:

        return self.outputs.get(
            str(key),
            default,
        )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def active(self) -> bool:
        return self.status == "ACTIVE"

    def has_active_work(self) -> bool:
        return bool(
            self.active_routes
            or self.active_operations
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:

        errors: List[str] = []

        if not self.task_id:
            errors.append(
                "task_id is required."
            )

        if not self.execution_id:
            errors.append(
                "execution_id is required."
            )

        if self.status not in {
            "CREATED",
            "ACTIVE",
            "PAUSED",
            "COMPLETED",
            "FAILED",
        }:
            errors.append(
                f"Invalid execution status: {self.status}"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "status": self.status,
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:

        return {
            "execution_id": self.execution_id,
            "task_id": self.task_id,

            "status": self.status,
            "current_stage": self.current_stage,
            "current_brain": self.current_brain,

            "active_routes": list(
                self.active_routes
            ),

            "completed_routes": list(
                self.completed_routes
            ),

            "failed_routes": list(
                self.failed_routes
            ),

            "active_operations": list(
                self.active_operations
            ),

            "completed_operations": list(
                self.completed_operations
            ),

            "events": list(
                self.events
            ),

            "outputs": dict(
                self.outputs
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
    "ExecutionContext",
      ]
