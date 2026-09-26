"""
HEROIC MISSION STATE

The mission state is the foundational state container for HEROIC.

HEROIC is responsible for understanding what VALE is trying to
accomplish. This state therefore represents the current mission
without performing the mission itself.

Important architectural rule:

HEROIC state is not a replacement for VALE's shared cognitive
state. It is HEROIC's structured view of the current mission.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MissionStatus(str, Enum):
    """
    Lifecycle state of a HEROIC mission.
    """

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
    """
    HEROIC's current assessment of information sufficiency.
    """

    UNKNOWN = "UNKNOWN"
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"
    CRITICAL_MISSING = "CRITICAL_MISSING"


class EpistemicStatus(str, Enum):
    """
    Basic epistemic states used by HEROIC when tracking
    mission-relevant conclusions or assumptions.

    These are descriptive states, not confidence scores.
    """

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
    """
    Structured representation of the current HEROIC mission.

    This class is intentionally conservative.

    It does not decide which brain should execute a task,
    does not perform specialist reasoning, and does not
    perform verification.

    Those responsibilities will be implemented by separate
    HEROIC components.
    """

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

    critical_missing_information: List[str] = field(
        default_factory=list
    )

    relevant_context: Dict[str, Any] = field(
        default_factory=dict
    )

    evidence_requirements: List[str] = field(
        default_factory=list
    )

    active_brains: List[str] = field(
        default_factory=list
    )

    dormant_brains: List[str] = field(
        default_factory=list
    )

    priority: str = "NORMAL"

    task_drift_detected: bool = False

    replanning_required: bool = False

    verification_required: bool = False

    completion_requested: bool = False

    completion_confirmed: bool = False

    escalation_required: bool = False

    blockers: List[str] = field(
        default_factory=list
    )

    notes: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def add_required_capability(
        self,
        capability: str,
    ) -> None:
        """
        Add a required capability without creating duplicates.
        """

        capability = str(capability).strip()

        if capability and capability not in self.required_capabilities:
            self.required_capabilities.append(
                capability
            )

    def add_active_brain(
        self,
        brain_name: str,
    ) -> None:
        """
        Mark a brain as active for this mission.
        """

        brain_name = str(brain_name).upper().strip()

        if brain_name and brain_name not in self.active_brains:
            self.active_brains.append(
                brain_name
            )

    def add_dormant_brain(
        self,
        brain_name: str,
    ) -> None:
        """
        Mark a brain as intentionally dormant for this mission.
        """

        brain_name = str(brain_name).upper().strip()

        if brain_name and brain_name not in self.dormant_brains:
            self.dormant_brains.append(
                brain_name
            )

    def add_missing_information(
        self,
        information: str,
        critical: bool = False,
    ) -> None:
        """
        Register missing information.

        Critical information is separately tracked because HEROIC
        may need to block progression rather than allowing the
        system to guess.
        """

        information = str(information).strip()

        if not information:
            return

        if information not in self.missing_information:
            self.missing_information.append(
                information
            )

        if critical and information not in self.critical_missing_information:
            self.critical_missing_information.append(
                information
            )

        if self.critical_missing_information:
            self.information_state = (
                InformationState.CRITICAL_MISSING
            )
        else:
            self.information_state = (
                InformationState.INSUFFICIENT
            )

    def add_blocker(
        self,
        blocker: str,
    ) -> None:
        """
        Register a reason preventing mission progression.
        """

        blocker = str(blocker).strip()

        if blocker and blocker not in self.blockers:
            self.blockers.append(
                blocker
            )

    def is_blocked(self) -> bool:
        """
        Return whether critical information or an explicit
        blocker currently prevents normal progression.
        """

        return bool(
            self.critical_missing_information
            or self.blockers
            or self.status == MissionStatus.BLOCKED
        )

    def mark_for_replanning(
        self,
        reason: Optional[str] = None,
    ) -> None:
        """
        Mark the current mission as requiring replanning.
        """

        self.replanning_required = True
        self.status = MissionStatus.REPLANNING

        if reason:
            self.notes.append(
                str(reason)
            )

    def mark_verification_required(self) -> None:
        """
        Mark the mission as requiring verification.
        """

        self.verification_required = True
        self.status = MissionStatus.VERIFYING

    def mark_completed(self) -> None:
        """
        Mark the mission as completed.

        Completion should only be called by later HEROIC
        completion logic after the required work has actually
        been assessed.
        """

        self.completion_confirmed = True
        self.status = MissionStatus.COMPLETED

    def mark_escalated(
        self,
        reason: Optional[str] = None,
    ) -> None:
        """
        Escalate the mission.
        """

        self.escalation_required = True
        self.status = MissionStatus.ESCALATED

        if reason:
            self.notes.append(
                str(reason)
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a serialization-safe representation of the
        current mission state.
        """

        return {
            "mission_id": self.mission_id,
            "user_request": self.user_request,
            "objective": self.objective,
            "status": self.status.value,
            "information_state": self.information_state.value,
            "intent": self.intent,
            "intent_status": self.intent_status.value,
            "constraints": dict(self.constraints),
            "required_capabilities": list(
                self.required_capabilities
            ),
            "activated_capabilities": list(
                self.activated_capabilities
            ),
            "dependencies": {
                key: list(value)
                for key, value in self.dependencies.items()
            },
            "missing_information": list(
                self.missing_information
            ),
            "critical_missing_information": list(
                self.critical_missing_information
            ),
            "relevant_context": dict(
                self.relevant_context
            ),
            "evidence_requirements": list(
                self.evidence_requirements
            ),
            "active_brains": list(
                self.active_brains
            ),
            "dormant_brains": list(
                self.dormant_brains
            ),
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
