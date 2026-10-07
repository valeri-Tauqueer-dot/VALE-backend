from future import annotations

from typing import Dict, Iterable, List, Optional

from HEROIC.information.information_state import (
InformationRequirementStatus,
HeroicInformationState,
)

class HeroicInformationSufficiencyEngine:
"""
Evaluates whether HEROIC has enough information to proceed.

This engine is deliberately conservative:
missing, stale, ambiguous, contradicted, or unresolved critical
information can prevent a mission from being considered sufficient.

It does not retrieve missing information itself.
"""

def __init__(
    self,
    *,
    minimum_confidence: float = 0.5,
) -> None:
    self.minimum_confidence = self._clamp(
        minimum_confidence
    )

def evaluate(
    self,
    requirements: Iterable[HeroicInformationState],
) -> Dict[str, object]:
    """
    Evaluate a collection of information requirements.
    """
    items = list(requirements)

    missing: List[str] = []
    partial: List[str] = []
    stale: List[str] = []
    ambiguous: List[str] = []
    contradicted: List[str] = []
    insufficient: List[str] = []
    critical_missing: List[str] = []

    for requirement in items:
        status = requirement.status

        if status in {
            InformationRequirementStatus.UNKNOWN,
            InformationRequirementStatus.MISSING,
        }:
            missing.append(requirement.information_id)

        elif status == InformationRequirementStatus.PARTIAL:
            partial.append(requirement.information_id)

        elif status == InformationRequirementStatus.STALE:
            stale.append(requirement.information_id)

        elif status == InformationRequirementStatus.AMBIGUOUS:
            ambiguous.append(requirement.information_id)

        elif status == InformationRequirementStatus.CONTRADICTED:
            contradicted.append(requirement.information_id)

        if not self._is_sufficient(requirement):
            insufficient.append(requirement.information_id)

        if (
            requirement.critical
            and not self._is_sufficient(requirement)
        ):
            critical_missing.append(
                requirement.information_id
            )

    sufficient = (
        bool(items)
        and not insufficient
    )

    critical_blocked = bool(critical_missing)

    return {
        "sufficient": sufficient,
        "critical_blocked": critical_blocked,
        "total_requirements": len(items),
        "missing": missing,
        "partial": partial,
        "stale": stale,
        "ambiguous": ambiguous,
        "contradicted": contradicted,
        "insufficient": insufficient,
        "critical_missing": critical_missing,
    }

def is_sufficient(
    self,
    requirements: Iterable[HeroicInformationState],
) -> bool:
    """Return whether all supplied requirements are sufficient."""
    result = self.evaluate(requirements)
    return bool(result["sufficient"])

def is_critically_blocked(
    self,
    requirements: Iterable[HeroicInformationState],
) -> bool:
    """Return whether unresolved critical information blocks progress."""
    result = self.evaluate(requirements)
    return bool(result["critical_blocked"])

def critical_missing(
    self,
    requirements: Iterable[HeroicInformationState],
) -> List[HeroicInformationState]:
    """Return unresolved critical requirements."""
    return [
        requirement
        for requirement in requirements
        if (
            requirement.critical
            and not self._is_sufficient(requirement)
        )
    ]

def unresolved(
    self,
    requirements: Iterable[HeroicInformationState],
) -> List[HeroicInformationState]:
    """Return requirements that are not sufficiently resolved."""
    return [
        requirement
        for requirement in requirements
        if not self._is_sufficient(requirement)
    ]

def _is_sufficient(
    self,
    requirement: HeroicInformationState,
) -> bool:
    """
    Apply conservative sufficiency rules to one requirement.
    """
    if not requirement.required:
        return True

    if requirement.status in {
        InformationRequirementStatus.UNKNOWN,
        InformationRequirementStatus.MISSING,
        InformationRequirementStatus.PARTIAL,
        InformationRequirementStatus.STALE,
        InformationRequirementStatus.AMBIGUOUS,
        InformationRequirementStatus.CONTRADICTED,
        InformationRequirementStatus.REJECTED,
    }:
        return False

    if requirement.status == InformationRequirementStatus.VERIFIED:
        return True

    if requirement.status != InformationRequirementStatus.AVAILABLE:
        return False

    if (
        requirement.confidence
        < self.minimum_confidence
    ):
        return False

    if (
        requirement.evidence_required
        and not requirement.verification_required
    ):
        return False

    return True

@staticmethod
def _clamp(
    value: float,
) -> float:
    """Clamp a threshold to the normalized 0.0–1.0 range."""
    return max(0.0, min(1.0, float(value)))
