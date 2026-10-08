from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class ConstraintType(str, Enum):
    SAFETY = "safety"
    RESOURCE = "resource"
    TIME = "time"
    CAPABILITY = "capability"
    DEPENDENCY = "dependency"
    INFORMATION = "information"
    EVIDENCE = "evidence"
    AUTHORIZATION = "authorization"
    SYSTEM = "system"
    USER = "user"
    OTHER = "other"


class ConstraintSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HeroicConstraintState:
    constraint_id: str
    name: str
    constraint_type: ConstraintType = ConstraintType.OTHER
    description: str = ""
    severity: ConstraintSeverity = ConstraintSeverity.MEDIUM
    enabled: bool = True
    satisfied: bool = True

    source: str = ""
    reason: str = ""

    required_capabilities: List[str] = field(
        default_factory=list
    )
    blocked_capabilities: List[str] = field(
        default_factory=list
    )
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def add_required_capability(
        self,
        capability_id: str,
    ) -> None:
        if (
            capability_id
            and capability_id
            not in self.required_capabilities
        ):
            self.required_capabilities.append(
                capability_id
            )

    def add_blocked_capability(
        self,
        capability_id: str,
    ) -> None:
        if (
            capability_id
            and capability_id
            not in self.blocked_capabilities
        ):
            self.blocked_capabilities.append(
                capability_id
            )

    def activate(self) -> None:
        self.enabled = True

    def deactivate(self) -> None:
        self.enabled = False

    def satisfy(self) -> None:
        self.satisfied = True

    def violate(self, reason: str = "") -> None:
        self.satisfied = False

        if reason:
            self.reason = reason

    def is_active(self) -> bool:
        return self.enabled

    def is_satisfied(self) -> bool:
        return self.satisfied

    def is_blocking(self) -> bool:
        return (
            self.enabled
            and not self.satisfied
            and self.severity
            in {
                ConstraintSeverity.HIGH,
                ConstraintSeverity.CRITICAL,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "name": self.name,
            "constraint_type": self.constraint_type.value,
            "description": self.description,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "satisfied": self.satisfied,
            "source": self.source,
            "reason": self.reason,
            "required_capabilities": list(
                self.required_capabilities
            ),
            "blocked_capabilities": list(
                self.blocked_capabilities
            ),
            "metadata": dict(self.metadata),
        }
