from future import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

class EvidenceType(str, Enum):
"""
Defines the type of evidence required or supplied to HEROIC.
"""

FACT = "fact"
OBSERVATION = "observation"
USER_PROVIDED = "user_provided"
MEMORY = "memory"
KNOWLEDGE = "knowledge"
BRAIN_RESULT = "brain_result"
EXTERNAL_SOURCE = "external_source"
COMPUTED = "computed"
VERIFICATION = "verification"
OTHER = "other"

class EvidenceStatus(str, Enum):
"""
Lifecycle state of an evidence requirement.
"""

UNKNOWN = "unknown"
REQUIRED = "required"
AVAILABLE = "available"
PARTIAL = "partial"
VERIFIED = "verified"
UNVERIFIED = "unverified"
CONTRADICTED = "contradicted"
REJECTED = "rejected"
STALE = "stale"

@dataclass
class HeroicEvidenceState:
"""
Represents an evidence item or evidence requirement used by HEROIC.

Evidence is treated as something that must be identified,
evaluated, and, where required, verified before it supports
a consequential conclusion.
"""

evidence_id: str

description: str

evidence_type: EvidenceType = EvidenceType.OTHER

status: EvidenceStatus = EvidenceStatus.UNKNOWN

value: Any = None

source: str = ""

source_id: str = ""

confidence: float = 0.0

freshness_seconds: float | None = None

maximum_age_seconds: float | None = None

required: bool = True

critical: bool = False

verification_required: bool = False

contradiction_reasons: List[str] = field(
    default_factory=list
)

dependencies: List[str] = field(
    default_factory=list
)

metadata: Dict[str, Any] = field(
    default_factory=dict
)

def set_value(
    self,
    value: Any,
) -> None:
    """Attach evidence content to this evidence state."""
    self.value = value
    self.status = EvidenceStatus.AVAILABLE

def add_contradiction(
    self,
    reason: str,
) -> None:
    """Register a contradiction affecting the evidence."""
    if reason and reason not in self.contradiction_reasons:
        self.contradiction_reasons.append(reason)

    self.status = EvidenceStatus.CONTRADICTED

def add_dependency(
    self,
    evidence_id: str,
) -> None:
    """Register another evidence item as a dependency."""
    if (
        evidence_id
        and evidence_id != self.evidence_id
        and evidence_id not in self.dependencies
    ):
        self.dependencies.append(evidence_id)

def mark_required(self) -> None:
    """Mark this evidence as required."""
    self.required = True
    self.status = EvidenceStatus.REQUIRED

def mark_available(self) -> None:
    """Mark evidence as available without asserting verification."""
    self.status = EvidenceStatus.AVAILABLE

def mark_verified(self) -> None:
    """Mark evidence as verified."""
    self.status = EvidenceStatus.VERIFIED

def mark_unverified(self) -> None:
    """Explicitly mark evidence as unverified."""
    self.status = EvidenceStatus.UNVERIFIED

def mark_rejected(
    self,
    reason: str = "",
) -> None:
    """Reject evidence from supporting the mission."""
    self.status = EvidenceStatus.REJECTED

    if reason:
        self.metadata["rejection_reason"] = reason

def mark_stale(self) -> None:
    """Mark evidence as stale."""
    self.status = EvidenceStatus.STALE

def is_available(self) -> bool:
    """Return whether evidence is available for consideration."""
    return self.status in {
        EvidenceStatus.AVAILABLE,
        EvidenceStatus.VERIFIED,
    }

def is_verified(self) -> bool:
    """Return whether evidence is explicitly verified."""
    return self.status == EvidenceStatus.VERIFIED

def is_sufficient(
    self,
    minimum_confidence: float = 0.5,
) -> bool:
    """
    Determine whether this evidence can currently support
    a requirement.
    """
    if self.status in {
        EvidenceStatus.UNKNOWN,
        EvidenceStatus.REQUIRED,
        EvidenceStatus.PARTIAL,
        EvidenceStatus.UNVERIFIED,
        EvidenceStatus.CONTRADICTED,
        EvidenceStatus.REJECTED,
        EvidenceStatus.STALE,
    }:
        return False

    if self.verification_required and not self.is_verified():
        return False

    return self._clamp(
        self.confidence,
        0.0,
        1.0,
    ) >= self._clamp(
        minimum_confidence,
        0.0,
        1.0,
    )

def requires_attention(self) -> bool:
    """Return whether the evidence needs further evaluation."""
    return self.status in {
        EvidenceStatus.UNKNOWN,
        EvidenceStatus.REQUIRED,
        EvidenceStatus.PARTIAL,
        EvidenceStatus.UNVERIFIED,
        EvidenceStatus.CONTRADICTED,
        EvidenceStatus.REJECTED,
        EvidenceStatus.STALE,
    }

def to_dict(self) -> Dict[str, Any]:
    """Serialize the evidence state."""
    return {
        "evidence_id": self.evidence_id,
        "description": self.description,
        "evidence_type": self.evidence_type.value,
        "status": self.status.value,
        "value": self.value,
        "source": self.source,
        "source_id": self.source_id,
        "confidence": self.confidence,
        "freshness_seconds": self.freshness_seconds,
        "maximum_age_seconds": self.maximum_age_seconds,
        "required": self.required,
        "critical": self.critical,
        "verification_required": self.verification_required,
        "contradiction_reasons": list(
            self.contradiction_reasons
        ),
        "dependencies": list(self.dependencies),
        "metadata": dict(self.metadata),
    }

@staticmethod
def _clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            float(value),
        ),
)
