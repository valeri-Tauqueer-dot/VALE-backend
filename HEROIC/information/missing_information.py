from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .information_state import (
    HeroicInformationState,
    InformationImportance,
    InformationStatus,
)


@dataclass
class HeroicMissingInformation:
    """
    Records information that is absent, stale, conflicting,
    or otherwise unusable for a HEROIC mission.
    """

    information_id: str
    name: str
    description: str = ""

    importance: InformationImportance = (
        InformationImportance.MEDIUM
    )

    reason: str = ""
    blocking: bool = False
    resolved: bool = False

    resolution_value: Any = None
    resolution_source: str = ""

    related_information_ids: List[str] = field(
        default_factory=list
    )
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_information(
        cls,
        information: HeroicInformationState,
        reason: str = "",
    ) -> "HeroicMissingInformation":
        if not isinstance(
            information,
            HeroicInformationState,
        ):
            raise TypeError(
                "information must be a "
                "HeroicInformationState instance."
            )

        if not reason:
            reason_by_status = {
                InformationStatus.UNKNOWN:
                    "Information status is unknown.",
                InformationStatus.MISSING:
                    "Required information is missing.",
                InformationStatus.STALE:
                    "Information may be outdated.",
                InformationStatus.CONFLICTING:
                    "Information contains unresolved conflicts.",
            }

            reason = reason_by_status.get(
                information.status,
                "Information is not currently usable.",
            )

        return cls(
            information_id=information.information_id,
            name=information.name,
            description=information.description,
            importance=information.importance,
            reason=reason,
            blocking=information.is_blocking(),
            related_information_ids=list(
                information.related_information_ids
            ),
            metadata=dict(information.metadata),
        )

    def resolve(
        self,
        value: Any,
        source: str = "",
    ) -> None:
        self.resolved = True
        self.resolution_value = value
        self.resolution_source = source
        self.blocking = False

    def reopen(
        self,
        reason: str = "",
    ) -> None:
        self.resolved = False
        self.resolution_value = None
        self.resolution_source = ""

        if reason:
            self.reason = reason

    def is_resolved(self) -> bool:
        return self.resolved

    def is_blocking(self) -> bool:
        return self.blocking and not self.resolved

    def to_dict(self) -> Dict[str, Any]:
        return {
            "information_id": self.information_id,
            "name": self.name,
            "description": self.description,
            "importance": self.importance.value,
            "reason": self.reason,
            "blocking": self.blocking,
            "resolved": self.resolved,
            "resolution_value": self.resolution_value,
            "resolution_source": self.resolution_source,
            "related_information_ids": list(
                self.related_information_ids
            ),
            "metadata": dict(self.metadata),
        }
