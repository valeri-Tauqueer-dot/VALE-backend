from future import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

class InformationRequirementStatus(str, Enum):
"""
State of an information requirement.
"""

UNKNOWN = "unknown"
IDENTIFIED = "identified"
AVAILABLE = "available"
PARTIAL = "partial"
MISSING = "missing"
STALE = "stale"
AMBIGUOUS = "ambiguous"
CONTRADICTED = "contradicted"
VERIFIED = "verified"
REJECTED = "rejected"

class InformationSourceType(str, Enum):
"""
Classification of an information source.
"""

USER = "user"
MEMORY = "memory"
KNOWLEDGE = "knowledge"
COGNITIVE_STATE = "cognitive_state"
BRAIN = "brain"
EXTERNAL = "external"
INFERRED = "inferred"
UNKNOWN = "unknown"

@dataclass
class HeroicInformationState:
"""
Represents one piece of information required by HEROIC.

This state deliberately separates availability from verification.
Information being present does not automatically make it trustworthy.
"""

information_id: str
description: str

status: InformationRequirementStatus = (
    InformationRequirementStatus.UNKNOWN
)

source_type: InformationSourceType = (
    InformationSourceType.UNKNOWN
)

value: Any = None

required: bool = True
critical: bool = False

confidence: float = 0.0

freshness_seconds: float | None = None
maximum_age_seconds: float | None = None

evidence_required: bool = False
verification_required: bool = False

ambiguity_reasons: List[str] = field(default_factory=list)
contradiction_reasons: List[str] = field(default_factory=list)

dependencies: List[str] = field(default_factory=list)

metadata: Dict[str, Any] = field(default_factory=dict)

def set_value(
    self,
    value: Any,
    source_type: InformationSourceType = (
        InformationSourceType.UNKNOWN
    ),
    confidence: float = 1.0,
) -> None:
    """Register information as available."""
    self.value = value
    self.source_type = source_type
    self.confidence = self._clamp(confidence)

    if value is None:
        self.status = InformationRequirementStatus.MISSING
    else:
        self.status = InformationRequirementStatus.AVAILABLE

def mark_identified(self) -> None:
    """Mark the requirement as identified."""
    self.status = InformationRequirementStatus.IDENTIFIED

def mark_missing(
    self,
    reason: str = "",
) -> None:
    """Mark required information as missing."""
    self.status = InformationRequirementStatus.MISSING

    if reason:
        self.metadata["missing_reason"] = reason

def mark_partial(
    self,
    reason: str = "",
) -> None:
    """Mark information as only partially available."""
    self.status = InformationRequirementStatus.PARTIAL

    if reason:
        self.metadata["partial_reason"] = reason

def mark_stale(
    self,
    age_seconds: float | None = None,
) -> None:
    """Mark information as stale."""
    self.status = InformationRequirementStatus.STALE

    if age_seconds is not None:
        self.freshness_seconds = age_seconds

def mark_ambiguous(
    self,
    reason: str,
) -> None:
    """Register an ambiguity affecting the information."""
    self.status = InformationRequirementStatus.AMBIGUOUS

    if reason and reason not in self.ambiguity_reasons:
        self.ambiguity_reasons.append(reason)

def mark_contradicted(
    self,
    reason: str,
) -> None:
    """Register a contradiction affecting the information."""
    self.status = InformationRequirementStatus.CONTRADICTED

    if reason and reason not in self.contradiction_reasons:
        self.contradiction_reasons.append(reason)

def mark_verified(self) -> None:
    """Mark the information as verified."""
    self.status = InformationRequirementStatus.VERIFIED

def mark_rejected(
    self,
    reason: str = "",
) -> None:
    """Reject the information for mission use."""
    self.status = InformationRequirementStatus.REJECTED

    if reason:
        self.metadata["rejection_reason"] = reason

def add_dependency(
    self,
    information_id: str,
) -> None:
    """Register another information requirement as a dependency."""
    if (
        information_id
        and information_id != self.information_id
        and information_id not in self.dependencies
    ):
        self.dependencies.append(information_id)

def is_available(self) -> bool:
    """Return whether information is available for consideration."""
    return self.status in {
        InformationRequirementStatus.AVAILABLE,
        InformationRequirementStatus.VERIFIED,
    }

def is_sufficient(self) -> bool:
    """
    Return whether this information requirement is sufficiently
    resolved for mission planning.
    """
    if self.status == InformationRequirementStatus.VERIFIED:
        return True

    if self.status != InformationRequirementStatus.AVAILABLE:
        return False

    if self.critical and self.confidence <= 0.0:
        return False

    if self.evidence_required and not self.verification_required:
        return False

    return True

def requires_attention(self) -> bool:
    """Return whether HEROIC should address this requirement."""
    return self.status in {
        InformationRequirementStatus.UNKNOWN,
        InformationRequirementStatus.MISSING,
        InformationRequirementStatus.PARTIAL,
        InformationRequirementStatus.STALE,
        InformationRequirementStatus.AMBIGUOUS,
        InformationRequirementStatus.CONTRADICTED,
    }

def to_dict(self) -> Dict[str, Any]:
    """Serialize information state."""
    return {
        "information_id": self.information_id,
        "description": self.description,
        "status": self.status.value,
        "source_type": self.source_type.value,
        "value": self.value,
        "required": self.required,
        "critical": self.critical,
        "confidence": self.confidence,
        "freshness_seconds": self.freshness_seconds,
        "maximum_age_seconds": self.maximum_age_seconds,
        "evidence_required": self.evidence_required,
        "verification_required": self.verification_required,
        "ambiguity_reasons": list(self.ambiguity_reasons),
        "contradiction_reasons": list(
            self.contradiction_reasons
        ),
        "dependencies": list(self.dependencies),
        "metadata": dict(self.metadata),
    }

@staticmethod
def _clamp(
    value: float,
) -> float:
    """Clamp confidence to the normalized 0.0–1.0 range."""
    return max(0.0, min(1.0, float(value)))
