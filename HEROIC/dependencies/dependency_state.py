from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class DependencyType(str, Enum):
    TASK = "task"
    CAPABILITY = "capability"
    INFORMATION = "information"
    EVIDENCE = "evidence"
    RESOURCE = "resource"
    BRAIN = "brain"
    SYSTEM = "system"
    OTHER = "other"


class DependencyStatus(str, Enum):
    UNKNOWN = "unknown"
    PENDING = "pending"
    SATISFIED = "satisfied"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class HeroicDependencyState:
    dependency_id: str
    name: str
    dependency_type: DependencyType = DependencyType.OTHER
    description: str = ""

    status: DependencyStatus = DependencyStatus.UNKNOWN

    source_id: str = ""
    target_id: str = ""

    required: bool = True
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    related_dependency_ids: List[str] = field(
        default_factory=list
    )

    def add_related_dependency(
        self,
        dependency_id: str,
    ) -> None:
        if (
            dependency_id
            and dependency_id not in self.related_dependency_ids
        ):
            self.related_dependency_ids.append(
                dependency_id
            )

    def mark_pending(self) -> None:
        self.status = DependencyStatus.PENDING

    def satisfy(self) -> None:
        self.status = DependencyStatus.SATISFIED

    def block(self) -> None:
        self.status = DependencyStatus.BLOCKED

    def fail(self) -> None:
        self.status = DependencyStatus.FAILED

    def is_satisfied(self) -> bool:
        return (
            self.status
            == DependencyStatus.SATISFIED
        )

    def is_blocked(self) -> bool:
        return (
            self.status
            in {
                DependencyStatus.BLOCKED,
                DependencyStatus.FAILED,
            }
        )

    def is_pending(self) -> bool:
        return (
            self.status
            == DependencyStatus.PENDING
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dependency_id": self.dependency_id,
            "name": self.name,
            "dependency_type": self.dependency_type.value,
            "description": self.description,
            "status": self.status.value,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "required": self.required,
            "metadata": dict(self.metadata),
            "related_dependency_ids": list(
                self.related_dependency_ids
            ),
        }
