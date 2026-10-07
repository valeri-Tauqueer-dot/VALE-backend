from future import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

class MissingInformationPriority(str, Enum):
"""
Priority of resolving missing information.
"""

LOW = "low"
MEDIUM = "medium"
HIGH = "high"
CRITICAL = "critical"

class MissingInformationStatus(str, Enum):
"""
Lifecycle state of a missing-information requirement.
"""

IDENTIFIED = "identified"
REQUESTED = "requested"
RETRIEVING = "retrieving"
AVAILABLE = "available"
RESOLVED = "resolved"
BLOCKED = "blocked"
REJECTED = "rejected"

@dataclass
class HeroicMissingInformation:
"""
Represents information that HEROIC has determined is missing.

This object describes the gap and its importance. It does not
retrieve the information itself.
"""

information_id: str
description: str

priority: MissingInformationPriority = (
    MissingInformationPriority.MEDIUM
)

status: MissingInformationStatus = (
    MissingInformationStatus.IDENTIFIED
)

reason: str = ""

required_for: List[str] = field(default_factory=list)

acceptable_sources: List[str] = field(default_factory=list)

constraints: List[str] = field(default_factory=list)

dependencies: List[str] = field(default_factory=list)

resolution_attempts: int = 0

resolved_value: Any = None

blockers: List[str] = field(default_factory=list)

metadata: Dict[str, Any] = field(default_factory=dict)

def add_required_for(
    self,
    requirement_id: str,
) -> None:
    """Register a mission element requiring this information."""
    if requirement_id and requirement_id not in self.required_for:
        self.required_for.append(requirement_id)

def add_acceptable_source(
    self,
    source: str,
) -> None:
    """Register an acceptable information source."""
    if source and source not in self.acceptable_sources:
        self.acceptable_sources.append(source)

def add_constraint(
    self,
    constraint: str,
) -> None:
    """Register a retrieval constraint."""
    if constraint and constraint not in self.constraints:
        self.constraints.append(constraint)

def add_dependency(
    self,
    information_id: str,
) -> None:
    """Register another missing-information dependency."""
    if (
        information_id
        and information_id != self.information_id
        and information_id not in self.dependencies
    ):
        self.dependencies.append(information_id)

def add_blocker(
    self,
    blocker: str,
) -> None:
    """Register a blocker preventing resolution."""
    if blocker and blocker not in self.blockers:
        self.blockers.append(blocker)

def mark_requested(self) -> None:
    """Mark the information as requested."""
    self.status = MissingInformationStatus.REQUESTED

def mark_retrieving(self) -> None:
    """Mark retrieval as in progress."""
    self.status = MissingInformationStatus.RETRIEVING
    self.resolution_attempts += 1

def mark_available(
    self,
    value: Any,
) -> None:
    """Record information that has become available."""
    self.resolved_value = value
    self.status = MissingInformationStatus.AVAILABLE

def mark_resolved(
    self,
    value: Optional[Any] = None,
) -> None:
    """Mark the missing-information requirement as resolved."""
    if value is not None:
        self.resolved_value = value

    self.status = MissingInformationStatus.RESOLVED

def mark_blocked(
    self,
    blocker: str = "",
) -> None:
    """Mark resolution as blocked."""
    self.status = MissingInformationStatus.BLOCKED

    if blocker:
        self.add_blocker(blocker)

def mark_rejected(
    self,
    reason: str = "",
) -> None:
    """Mark the requested information as rejected."""
    self.status = MissingInformationStatus.REJECTED

    if reason:
        self.metadata["rejection_reason"] = reason

def is_critical(self) -> bool:
    """Return whether this gap requires critical attention."""
    return (
        self.priority
        == MissingInformationPriority.CRITICAL
    )

def is_resolved(self) -> bool:
    """Return whether the information gap has been resolved."""
    return self.status == MissingInformationStatus.RESOLVED

def is_blocked(self) -> bool:
    """Return whether resolution is currently blocked."""
    return (
        self.status == MissingInformationStatus.BLOCKED
        or bool(self.blockers)
    )

def requires_action(self) -> bool:
    """Return whether the information gap still requires work."""
    return self.status in {
        MissingInformationStatus.IDENTIFIED,
        MissingInformationStatus.REQUESTED,
        MissingInformationStatus.RETRIEVING,
    }

def to_dict(self) -> Dict[str, Any]:
    """Serialize the missing-information state."""
    return {
        "information_id": self.information_id,
        "description": self.description,
        "priority": self.priority.value,
        "status": self.status.value,
        "reason": self.reason,
        "required_for": list(self.required_for),
        "acceptable_sources": list(
            self.acceptable_sources
        ),
        "constraints": list(self.constraints),
        "dependencies": list(self.dependencies),
        "resolution_attempts": self.resolution_attempts,
        "resolved_value": self.resolved_value,
        "blockers": list(self.blockers),
        "metadata": dict(self.metadata),
  }
