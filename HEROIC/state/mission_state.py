"""
HEROIC MISSION STATE

The foundational state container for a HEROIC mission.

This is HEROIC's structured representation of the mission,
not a replacement for VALE's shared cognitive state.

This module records mission state. It does not execute tasks,
select specialist brains, or independently verify outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MissionStatus(str, Enum):
    NEW = "NEW"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    REPLANNING = "REPLANNING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"


class InformationState(str, Enum):
    UNKNOWN = "UNKNOWN"
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"
    CRITICAL_MISSING = "CRITICAL_MISSING"


class EpistemicStatus(str, Enum):
    KNOWN = "KNOWN"
    SUPPORTED = "SUPPORTED"
    INFERRED = "INFERRED"
    LIKELY = "LIKELY"
    UNCERTAIN = "UNCERTAIN"
    CONTESTED = "CONTESTED"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    UNKNOWN = "UNKNOWN"


@dataclass
class HeroicMissionState:
    """Structured state for one HEROIC mission."""

    mission_id: str
    user_request: str = ""
    objective: Optional[str] = None
    status: MissionStatus = MissionStatus.NEW
    information_state: InformationState = InformationState.UNKNOWN
    intent: Optional[str] = None
    intent_status: EpistemicStatus = EpistemicStatus.UNKNOWN

    constraints: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)
    activated_capabilities: List[str] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    missing_information: List[str] = field(default_factory=list)
    critical_missing_information: List[str] = field(default_factory=list)
    relevant_context: Dict[str, Any] = field(default_factory=dict)
    evidence_requirements: List[str] = field(default_factory=list)
    active_brains: List[str] = field(default_factory=list)
    dormant_brains: List[str] = field(default_factory=list)

    priority: str = "NORMAL"
    task_drift_detected: bool = False
    replanning_required: bool = False
    verification_required: bool = False
    completion_requested: bool = False
    completion_confirmed: bool = False
    escalation_required: bool = False

    blockers: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize enum inputs and validate mission identity."""

        if not isinstance(self.mission_id, str) or not self.mission_id.strip():
            raise ValueError("mission_id must be a non-empty string.")

        self.mission_id = self.mission_id.strip()

        self.status = self._normalize_enum(
            self.status, MissionStatus, "status"
        )
        self.information_state = self._normalize_enum(
            self.information_state, InformationState, "information_state"
        )
        self.intent_status = self._normalize_enum(
            self.intent_status, EpistemicStatus, "intent_status"
        )

        self.active_brains = self._normalize_names(
            self.active_brains, uppercase=True
        )
        self.dormant_brains = self._normalize_names(
            self.dormant_brains, uppercase=True
        )
        self.required_capabilities = self._normalize_names(
            self.required_capabilities
        )
        self.activated_capabilities = self._normalize_names(
            self.activated_capabilities
        )
        self.missing_information = self._normalize_names(
            self.missing_information
        )
        self.critical_missing_information = self._normalize_names(
            self.critical_missing_information
        )
        self.blockers = self._normalize_names(self.blockers)

        # Critical missing information must never be omitted from
        # the general missing-information collection.
        for item in self.critical_missing_information:
            if item not in self.missing_information:
                self.missing_information.append(item)

        if self.critical_missing_information:
            self.information_state = InformationState.CRITICAL_MISSING

        if self.blockers and self.status != MissionStatus.COMPLETED:
            self.status = MissionStatus.BLOCKED

    @staticmethod
    def _normalize_enum(value: Any, enum_type: Any, field_name: str) -> Any:
        if isinstance(value, enum_type):
            return value

        try:
            return enum_type(value)
        except (ValueError, TypeError):
            try:
                return enum_type[str(value).strip().upper()]
            except (KeyError, ValueError, TypeError):
                raise ValueError(
                    f"Invalid {field_name}: {value!r}"
                ) from None

    @staticmethod
    def _normalize_names(
        values: List[str],
        uppercase: bool = False,
    ) -> List[str]:
        normalized: List[str] = []

        for value in values:
            item = str(value).strip()
            if uppercase:
                item = item.upper()

            if item and item not in normalized:
                normalized.append(item)

        return normalized

    def add_required_capability(self, capability: str) -> None:
        capability = str(capability).strip()
        if capability and capability not in self.required_capabilities:
            self.required_capabilities.append(capability)

    def add_active_brain(self, brain_name: str) -> None:
        brain_name = str(brain_name).upper().strip()
        if not brain_name:
            return

        if brain_name not in self.active_brains:
            self.active_brains.append(brain_name)

        if brain_name in self.dormant_brains:
            self.dormant_brains.remove(brain_name)

    def add_dormant_brain(self, brain_name: str) -> None:
        brain_name = str(brain_name).upper().strip()
        if not brain_name or brain_name in self.active_brains:
            return

        if brain_name not in self.dormant_brains:
            self.dormant_brains.append(brain_name)

    def add_missing_information(
        self,
        information: str,
        critical: bool = False,
    ) -> None:
        information = str(information).strip()
        if not information:
            return

        if information not in self.missing_information:
            self.missing_information.append(information)

        if critical and information not in self.critical_missing_information:
            self.critical_missing_information.append(information)

        if self.critical_missing_information:
            self.information_state = InformationState.CRITICAL_MISSING
        else:
            self.information_state = InformationState.INSUFFICIENT

        if critical and self.status not in (
            MissionStatus.COMPLETED,
            MissionStatus.ESCALATED,
        ):
            self.status = MissionStatus.BLOCKED

    def resolve_missing_information(self, information: str) -> None:
        """Remove an item once it has actually been resolved."""

        information = str(information).strip()
        if not information:
            return

        if information in self.missing_information:
            self.missing_information.remove(information)

        if information in self.critical_missing_information:
            self.critical_missing_information.remove(information)

        if self.critical_missing_information:
            self.information_state = InformationState.CRITICAL_MISSING
        elif self.missing_information:
            self.information_state = InformationState.INSUFFICIENT
        elif self.information_state in (
            InformationState.CRITICAL_MISSING,
            InformationState.INSUFFICIENT,
        ):
            self.information_state = InformationState.UNKNOWN

        self._refresh_blocked_status()

    def add_blocker(self, blocker: str) -> None:
        blocker = str(blocker).strip()
        if not blocker:
            return

        if blocker not in self.blockers:
            self.blockers.append(blocker)

        if self.status not in (
            MissionStatus.COMPLETED,
            MissionStatus.ESCALATED,
        ):
            self.status = MissionStatus.BLOCKED

    def remove_blocker(self, blocker: str) -> None:
        blocker = str(blocker).strip()
        if blocker in self.blockers:
            self.blockers.remove(blocker)

        self._refresh_blocked_status()

    def _refresh_blocked_status(self) -> None:
        """Reassess blocking without silently advancing the mission."""

        if self.status in (
            MissionStatus.COMPLETED,
            MissionStatus.ESCALATED,
        ):
            return

        if self.blockers or self.critical_missing_information:
            self.status = MissionStatus.BLOCKED
        elif self.status == MissionStatus.BLOCKED:
            self.status = MissionStatus.PLANNING

    def is_blocked(self) -> bool:
        return bool(
            self.blockers
            or self.critical_missing_information
            or self.status == MissionStatus.BLOCKED
        )

    def mark_for_replanning(self, reason: Optional[str] = None) -> None:
        if self.status == MissionStatus.COMPLETED:
            raise ValueError("A completed mission cannot be replanned.")

        self.replanning_required = True
        if reason:
            self.notes.append(str(reason))

        if not self.is_blocked():
            self.status = MissionStatus.REPLANNING

    def mark_verification_required(self) -> None:
        if self.status == MissionStatus.COMPLETED:
            raise ValueError("A completed mission cannot enter verification.")

        self.verification_required = True
        if not self.is_blocked():
            self.status = MissionStatus.VERIFYING

    def mark_completed(self) -> None:
        """
        Confirm completion only when explicit blockers and critical
        missing information are absent.

        Actual outcome verification must be performed by the caller.
        """

        if self.is_blocked():
            raise ValueError(
                "Cannot complete a blocked mission. Resolve blockers first."
            )

        if self.verification_required and not self.completion_requested:
            raise ValueError(
                "Verification is required before mission completion."
            )

        self.completion_confirmed = True
        self.status = MissionStatus.COMPLETED

    def mark_escalated(self, reason: Optional[str] = None) -> None:
        if self.status == MissionStatus.COMPLETED:
            raise ValueError("A completed mission cannot be escalated.")

        self.escalation_required = True
        self.status = MissionStatus.ESCALATED

        if reason:
            self.notes.append(str(reason))

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialization-safe representation."""

        return {
            "mission_id": self.mission_id,
            "user_request": self.user_request,
            "objective": self.objective,
            "status": self.status.value,
            "information_state": self.information_state.value,
            "intent": self.intent,
            "intent_status": self.intent_status.value,
            "constraints": dict(self.constraints),
            "required_capabilities": list(self.required_capabilities),
            "activated_capabilities": list(self.activated_capabilities),
            "dependencies": {
                key: list(value)
                for key, value in self.dependencies.items()
            },
            "missing_information": list(self.missing_information),
            "critical_missing_information": list(
                self.critical_missing_information
            ),
            "relevant_context": dict(self.relevant_context),
            "evidence_requirements": list(self.evidence_requirements),
            "active_brains": list(self.active_brains),
            "dormant_brains": list(self.dormant_brains),
            "priority": self.priority,
            "task_drift_detected": self.task_drift_detected,
            "replanning_required": self.replanning_required,
            "verification_required": self.verification_required,
            "completion_requested": self.completion_requested,
            "completion_confirmed": self.completion_confirmed,
            "escalation_required": self.escalation_required,
            "blockers": list(self.blockers),
            "notes": list(self.notes),
            "metadata": dict(self.metadata),
        }


__all__ = [
    "HeroicMissionState",
    "MissionStatus",
    "InformationState",
    "EpistemicStatus",
]
