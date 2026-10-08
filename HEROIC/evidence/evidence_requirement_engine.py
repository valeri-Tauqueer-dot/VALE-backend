from __future__ import annotations

from typing import Iterable, List, Optional

from .evidence_state import (
    EvidenceStatus,
    HeroicEvidenceState,
)


class HeroicEvidenceRequirementEngine:
    """
    Determines whether HEROIC has sufficient evidence
    for a requested objective or decision.

    This engine does not create evidence and does not
    fabricate missing information.
    """

    def __init__(
        self,
        evidence: Optional[
            Iterable[HeroicEvidenceState]
        ] = None,
    ) -> None:
        self._evidence: List[
            HeroicEvidenceState
        ] = []

        if evidence:
            for item in evidence:
                self.add_evidence(item)

    def add_evidence(
        self,
        evidence: HeroicEvidenceState,
    ) -> HeroicEvidenceState:
        if not isinstance(
            evidence,
            HeroicEvidenceState,
        ):
            raise TypeError(
                "evidence must be a "
                "HeroicEvidenceState instance."
            )

        existing = self.get_evidence(
            evidence.evidence_id
        )

        if existing is not None:
            index = self._evidence.index(
                existing
            )
            self._evidence[index] = evidence
        else:
            self._evidence.append(evidence)

        return evidence

    def remove_evidence(
        self,
        evidence_id: str,
    ) -> Optional[HeroicEvidenceState]:
        evidence = self.get_evidence(
            evidence_id
        )

        if evidence is None:
            return None

        self._evidence.remove(evidence)

        return evidence

    def get_evidence(
        self,
        evidence_id: str,
    ) -> Optional[HeroicEvidenceState]:
        for evidence in self._evidence:
            if evidence.evidence_id == evidence_id:
                return evidence

        return None

    def list_all(
        self,
    ) -> List[HeroicEvidenceState]:
        return list(self._evidence)

    def available(
        self,
    ) -> List[HeroicEvidenceState]:
        return [
            evidence
            for evidence in self._evidence
            if evidence.is_available()
        ]

    def verified(
        self,
    ) -> List[HeroicEvidenceState]:
        return [
            evidence
            for evidence in self._evidence
            if evidence.is_verified()
        ]

    def missing(
        self,
    ) -> List[HeroicEvidenceState]:
        return [
            evidence
            for evidence in self._evidence
            if evidence.status
            == EvidenceStatus.MISSING
        ]

    def stale(
        self,
    ) -> List[HeroicEvidenceState]:
        return [
            evidence
            for evidence in self._evidence
            if evidence.status
            == EvidenceStatus.STALE
        ]

    def invalid(
        self,
    ) -> List[HeroicEvidenceState]:
        return [
            evidence
            for evidence in self._evidence
            if evidence.status
            == EvidenceStatus.INVALID
        ]

    def required(
        self,
    ) -> List[HeroicEvidenceState]:
        return [
            evidence
            for evidence in self._evidence
            if evidence.required
        ]

    def required_missing(
        self,
    ) -> List[HeroicEvidenceState]:
        return [
            evidence
            for evidence in self.required()
            if not evidence.is_usable()
        ]

    def is_sufficient(
        self,
    ) -> bool:
        return len(
            self.required_missing()
        ) == 0

    def has_verified_evidence(
        self,
    ) -> bool:
        return any(
            evidence.is_verified()
            for evidence in self._evidence
        )

    def mark_verified(
        self,
        evidence_id: str,
    ) -> HeroicEvidenceState:
        evidence = self._require(
            evidence_id
        )

        evidence.mark_verified()

        return evidence

    def mark_stale(
        self,
        evidence_id: str,
    ) -> HeroicEvidenceState:
        evidence = self._require(
            evidence_id
        )

        evidence.mark_stale()

        return evidence

    def mark_missing(
        self,
        evidence_id: str,
    ) -> HeroicEvidenceState:
        evidence = self._require(
            evidence_id
        )

        evidence.mark_missing()

        return evidence

    def _require(
        self,
        evidence_id: str,
    ) -> HeroicEvidenceState:
        evidence = self.get_evidence(
            evidence_id
        )

        if evidence is None:
            raise KeyError(
                f"Unknown HEROIC evidence: "
                f"{evidence_id}"
            )

        return evidence

    def clear(self) -> None:
        self._evidence.clear()

    def to_dict(self) -> List[dict]:
        return [
            evidence.to_dict()
            for evidence in self._evidence
    ]
