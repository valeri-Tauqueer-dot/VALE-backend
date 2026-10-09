from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class InformationStatus(str, Enum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    MISSING = "missing"
    STALE = "stale"
    CONFLICTING = "conflicting"
    VERIFIED = "verified"


class InformationImportance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HeroicInformationState:
    """
    Tracks information required to understand and complete
    a HEROIC mission.
    """

    information_id: str
    name: str
    description: str = ""

    status: InformationStatus = InformationStatus.UNKNOWN
    importance: InformationImportance = (
        InformationImportance.MEDIUM
    )

    value: Any = None
    source: str = ""
    required: bool = True

    related_information_ids: List[str] = field(
        default_factory=list
    )
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def set_value(
        self,
        value: Any,
        source: str = "",
    ) -> None:
        self.value = value

        if source:
            self.source = source

        self.status = InformationStatus.AVAILABLE

    def mark_verified(self) -> None:
        self.status = InformationStatus.VERIFIED

    def mark_missing(self) -> None:
        self.status = InformationStatus.MISSING
        self.value = None

    def mark_stale(self) -> None:
        self.status = InformationStatus.STALE

    def mark_conflicting(self) -> None:
        self.status = InformationStatus.CONFLICTING

    def mark_unknown(self) -> None:
        self.status = InformationStatus.UNKNOWN

    def add_related_information(
        self,
        information_id: str,
    ) -> None:
        if (
            information_id
            and information_id not in self.related_information_ids
        ):
            self.related_information_ids.append(
                information_id
            )

    def is_available(self) -> bool:
        return self.status in {
            InformationStatus.AVAILABLE,
            InformationStatus.VERIFIED,
        }

    def is_verified(self) -> bool:
        return self.status == InformationStatus.VERIFIED

    def is_usable(self) -> bool:
        return self.is_available() and self.value is not None

    def is_blocking(self) -> bool:
        return (
            self.required
            and self.importance
            in {
                InformationImportance.HIGH,
                InformationImportance.CRITICAL,
            }
            and not self.is_usable()
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "information_id": self.information_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "importance": self.importance.value,
            "value": self.value,
            "source": self.source,
            "required": self.required,
            "related_information_ids": list(
                self.related_information_ids
            ),
            "metadata": dict(self.metadata),
        }
