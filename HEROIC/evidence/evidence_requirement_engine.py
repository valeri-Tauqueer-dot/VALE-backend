from future import annotations

from typing import Dict, Iterable, List, Optional

from HEROIC.evidence.evidence_state import (
EvidenceStatus,
HeroicEvidenceState,
)

class HeroicEvidenceRequirementEngine:
"""
Evaluates whether HEROIC has sufficient evidence for the
requirements of a mission, objective, goal, or task.

The engine evaluates evidence; it does not fabricate, retrieve,
or strengthen evidence that has not been provided.
"""

def __init__(
    self,
    evidence: Optional[
        Iterable[HeroicEvidenceState]
    ] = None,
    minimum_confidence: float = 0.5,
) -> None:
    self._evidence: Dict[
        str,
        HeroicEvidenceState,
    ] = {}

    self.minimum_confidence = self._clamp(
        minimum_confidence,
        0.0,
        1.0,
    )

    if evidence:
        for item in evidence:
            self.register(item)

def register(
    self,
    evidence: HeroicEvidenceState,
    overwrite: bool = True,
) -> HeroicEvidenceState:
    """Register an evidence state."""
    if (
        evidence.evidence_id in self._evidence
        and not overwrite
    ):
        raise ValueError(
            f"Evidence already exists: "
            f"{evidence.evidence_id}"
        )

    self._evidence[evidence.evidence_id] = evidence

    return evidence

def get(
    self,
    evidence_id: str,
) -> Optional[HeroicEvidenceState]:
    """Return evidence by ID."""
    return self._evidence.get(evidence_id)

def require(
    self,
    evidence_id: str,
) -> HeroicEvidenceState:
    """Return evidence or raise an explicit error."""
    evidence = self.get(evidence_id)

    if evidence is None:
        raise KeyError(
            f"Unknown HEROIC evidence: {evidence_id}"
        )

    return evidence

def evaluate(
    self,
    evidence: HeroicEvidenceState,
) -> bool:
    """Evaluate whether one evidence item is sufficient."""
    return evidence.is_sufficient(
        self.minimum_confidence
    )

def evaluate_all(self) -> Dict[str, object]:
    """
    Evaluate all registered evidence.

    Returns a structured assessment instead of reducing the
    result to a single boolean so HEROIC can preserve uncertainty.
    """
    available: List[str] = []
    insufficient: List[str] = []
    critical_missing: List[str] = []
    contradicted: List[str] = []
    stale: List[str] = []
    unverified: List[str] = []

    required_count = 0

    for evidence in self._evidence.values():
        if evidence.required:
            required_count += 1

        if evidence.status == EvidenceStatus.CONTRADICTED:
            contradicted.append(evidence.evidence_id)

        if evidence.status == EvidenceStatus.STALE:
            stale.append(evidence.evidence_id)

        if evidence.status == EvidenceStatus.UNVERIFIED:
            unverified.append(evidence.evidence_id)

        if self.evaluate(evidence):
            available.append(evidence.evidence_id)
        elif evidence.required:
            insufficient.append(evidence.evidence_id)

        if (
            evidence.required
            and evidence.critical
            and not self.evaluate(evidence)
        ):
            critical_missing.append(evidence.evidence_id)

    sufficient = not insufficient
    critical_blocked = bool(critical_missing)

    return {
        "sufficient": sufficient,
        "critical_blocked": critical_blocked,
        "required_count": required_count,
        "available": available,
        "insufficient": insufficient,
        "critical_missing": critical_missing,
        "contradicted": contradicted,
        "stale": stale,
        "unverified": unverified,
    }

def is_sufficient(self) -> bool:
    """Return whether all required evidence is sufficient."""
    return bool(self.evaluate_all()["sufficient"])

def is_critically_blocked(self) -> bool:
    """Return whether critical evidence is insufficient."""
    return bool(
        self.evaluate_all()["critical_blocked"]
    )

def missing(
    self,
) -> List[HeroicEvidenceState]:
    """Return required evidence that is not sufficient."""
    return [
        evidence
        for evidence in self._evidence.values()
        if evidence.required
        and not self.evaluate(evidence)
    ]

def critical_missing(
    self,
) -> List[HeroicEvidenceState]:
    """Return critical required evidence that is insufficient."""
    return [
        evidence
        for evidence in self._evidence.values()
        if evidence.required
        and evidence.critical
        and not self.evaluate(evidence)
    ]

def verified(
    self,
) -> List[HeroicEvidenceState]:
    """Return explicitly verified evidence."""
    return [
        evidence
        for evidence in self._evidence.values()
        if evidence.is_verified()
    ]

def contradicted(
    self,
) -> List[HeroicEvidenceState]:
    """Return contradicted evidence."""
    return [
        evidence
        for evidence in self._evidence.values()
        if evidence.status == EvidenceStatus.CONTRADICTED
    ]

def clear(self) -> None:
    """Remove all registered evidence."""
    self._evidence.clear()

def __len__(self) -> int:
    return len(self._evidence)

def __contains__(
    self,
    evidence_id: str,
) -> bool:
    return evidence_id in self._evidence

def to_dict(self) -> Dict[str, Dict]:
    """Serialize all registered evidence."""
    return {
        evidence_id: evidence.to_dict()
        for evidence_id, evidence
        in self._evidence.items()
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
