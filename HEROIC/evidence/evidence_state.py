from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class EvidenceType(str, Enum):
    FACT = "fact"
    OBSERVATION = "observation"
    SOURCE = "source"
    TEST = "test"
    VERIFICATION = "verification"
    USER_INPUT = "user_input"
    SYSTEM_STATE = "system_state"
    EXTERNAL_DATA = "external_data"
    OTHER = "other"


class EvidenceStatus(str, Enum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    VERIFIED = "verified"
    STALE = "stale"
    INVALID = "invalid"
    MISSING = "missing"


@dataclass
class HeroicEvidenceState:
    evidence_id: str
    name: str

    evidence_type: EvidenceType = EvidenceType.OTHER
    description: str = ""

    status: EvidenceStatus = EvidenceStatus.UNKNOWN

    source: str = ""
    value: Any = None

    confidence: float = 0.0
    freshness: float = 1.0

    required: bool = True

    supports: List[str] = field(
        default_factory=list
    )

    contradicts: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def add_support(
        self,
        target_id: str,
    ) -> None:
        if target_id and target_id not in self.supports:
            self.supports.append(target_id)

    def add_contradiction(
        self,
        target_id: str,
    ) -> None:
        if (
            target_id
            and target_id not in self.contradicts
        ):
            self.contradicts.append(target_id)

    def mark_available(self) -> None:
        self.status = EvidenceStatus.AVAILABLE

    def mark_verified(self) -> None:
        self.status = EvidenceStatus.VERIFIED

    def mark_stale(self) -> None:
        self.status = EvidenceStatus.STALE

    def mark_invalid(self) -> None:
        self.status = EvidenceStatus.INVALID

    def mark_missing(self) -> None:
        self.status = EvidenceStatus.MISSING

    def is_available(self) -> bool:
        return self.status in {
            EvidenceStatus.AVAILABLE,
            EvidenceStatus.VERIFIED,
        }

    def is_verified(self) -> bool:
        return (
            self.status
            == EvidenceStatus.VERIFIED
        )

    def is_usable(self) -> bool:
        return (
            self.is_available()
            and self.status
            not in {
                EvidenceStatus.STALE,
                EvidenceStatus.INVALID,
                EvidenceStatus.MISSING,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "name": self.name,
            "evidence_type": self.evidence_type.value,
            "description": self.description,
            "status": self.status.value,
            "source": self.source,
            "value": self.value,
            "confidence": self.confidence,
            "freshness": self.freshness,
            "required": self.required,
            "supports": list(self.supports),
            "contradicts": list(self.contradicts),
            "metadata": dict(self.metadata),
        }
