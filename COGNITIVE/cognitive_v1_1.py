# ============================================================
# VALE SUPPORTING COGNITIVE SYSTEM
# V1.1 — EPISTEMIC STATE FOUNDATION
#
# File:
#     COGNITIVE/cognitive_v1_1.py
#
# ADDITIVE VERSION
# ----------------
# This file extends cognitive_v1_0.py.
# Existing files are intentionally left unchanged.
#
# V1.1 introduces:
#   - explicit epistemic states
#   - propositions
#   - evidence records
#   - belief revision history
#   - contradiction representation
#   - reality/information gaps
#   - epistemic inspection and diagnostics
#
# It does NOT:
#   - replace CognitiveBrain
#   - create a second VALE state system
#   - make final decisions
#   - trade
#   - supervise main brains
#   - automatically modify its own code
# ============================================================

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from .cognitive_v1_0 import (
    CognitiveBrainV1_0,
    CognitiveV1Architecture,
    CognitiveV1VerificationEngine,
    CognitiveV1VerificationResult,
    CognitiveV1_SYSTEM_NAME,
)


# ============================================================
# 1. VERSION IDENTITY
# ============================================================

CognitiveV11_SYSTEM_NAME = CognitiveV1_SYSTEM_NAME
CognitiveV11_VERSION = "1.1.0"
CognitiveV11_STAGE = "EPISTEMIC_STATE_FOUNDATION"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def clamp(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = default
    return max(0.0, min(1.0, value))


# ============================================================
# 2. EPISTEMIC VOCABULARY
# ============================================================

class EpistemicStatus:
    OBSERVED = "OBSERVED"
    SUPPORTED = "SUPPORTED"
    INFERRED = "INFERRED"
    HYPOTHESIS = "HYPOTHESIS"
    UNCERTAIN = "UNCERTAIN"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"


class EvidencePolarity:
    SUPPORTS = "SUPPORTS"
    CHALLENGES = "CHALLENGES"
    NEUTRAL = "NEUTRAL"


class RealityGapType:
    MISSING_INFORMATION = "MISSING_INFORMATION"
    STALE_INFORMATION = "STALE_INFORMATION"
    CONFLICTING_INFORMATION = "CONFLICTING_INFORMATION"
    LOW_QUALITY_EVIDENCE = "LOW_QUALITY_EVIDENCE"
    UNVERIFIED_INFERENCE = "UNVERIFIED_INFERENCE"


# ============================================================
# 3. DATA MODELS
# ============================================================

@dataclass
class CognitiveEvidenceV11:
    evidence_id: str
    proposition_id: str
    content: Any
    source: Optional[str] = None
    source_type: str = "unknown"
    reliability: float = 0.0
    freshness: float = 1.0
    relevance: float = 1.0
    polarity: str = EvidencePolarity.NEUTRAL
    observed_at: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def quality(self) -> float:
        return (
            clamp(self.reliability)
            + clamp(self.freshness, 1.0)
            + clamp(self.relevance, 1.0)
        ) / 3.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CognitivePropositionV11:
    proposition_id: str
    statement: str
    status: str = EpistemicStatus.UNKNOWN
    confidence: float = 0.0
    uncertainty: float = 1.0
    evidence_ids: List[str] = field(default_factory=list)
    supporting_evidence_ids: List[str] = field(default_factory=list)
    challenging_evidence_ids: List[str] = field(default_factory=list)
    source_refs: List[str] = field(default_factory=list)
    domain: Optional[str] = None
    revision: int = 0
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CognitiveBeliefRevisionV11:
    revision_id: str
    proposition_id: str
    previous_status: str
    new_status: str
    previous_confidence: float
    new_confidence: float
    previous_uncertainty: float
    new_uncertainty: float
    reason: str
    evidence_ids: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CognitiveRealityGapV11:
    gap_id: str
    proposition_id: Optional[str]
    gap_type: str
    severity: float
    description: str
    required_information: List[str] = field(default_factory=list)
    resolved: bool = False
    detected_at: str = field(default_factory=utc_now)
    resolved_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# 4. EPISTEMIC STATE MANAGER
# ============================================================

class CognitiveEpistemicStateManagerV11:
    """
    Maintains the explicit state of what the cognitive system
    currently has reason to believe.

    Confidence is evidence-weighted support, not objective truth.
    """

    VALID_STATUSES = {
        EpistemicStatus.OBSERVED,
        EpistemicStatus.SUPPORTED,
        EpistemicStatus.INFERRED,
        EpistemicStatus.HYPOTHESIS,
        EpistemicStatus.UNCERTAIN,
        EpistemicStatus.CONTRADICTED,
        EpistemicStatus.UNKNOWN,
        EpistemicStatus.STALE,
    }

    def __init__(self) -> None:
        self.propositions: Dict[str, CognitivePropositionV11] = {}
        self.evidence: Dict[str, CognitiveEvidenceV11] = {}
        self.revisions: List[CognitiveBeliefRevisionV11] = []
        self.reality_gaps: Dict[str, CognitiveRealityGapV11] = {}

    # --------------------------------------------------------
    # Propositions
    # --------------------------------------------------------

    def create_proposition(
        self,
        statement: str,
        *,
        proposition_id: Optional[str] = None,
        domain: Optional[str] = None,
        status: str = EpistemicStatus.UNKNOWN,
        confidence: float = 0.0,
        uncertainty: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CognitivePropositionV11:

        if status not in self.VALID_STATUSES:
            status = EpistemicStatus.UNKNOWN

        item = CognitivePropositionV11(
            proposition_id=proposition_id or make_id("prop"),
            statement=str(statement),
            status=status,
            confidence=clamp(confidence),
            uncertainty=clamp(uncertainty, 1.0),
            domain=domain,
            metadata=deepcopy(metadata or {}),
        )
        self.propositions[item.proposition_id] = item
        return deepcopy(item)

    register_proposition = create_proposition

    def get_proposition(
        self,
        proposition_id: str,
    ) -> Optional[CognitivePropositionV11]:
        item = self.propositions.get(proposition_id)
        return deepcopy(item) if item else None

    get_belief = get_proposition

    # --------------------------------------------------------
    # Evidence
    # --------------------------------------------------------

    def add_evidence(
        self,
        proposition_id: str,
        content: Any,
        *,
        source: Optional[str] = None,
        source_type: str = "unknown",
        reliability: float = 0.0,
        freshness: float = 1.0,
        relevance: float = 1.0,
        polarity: str = EvidencePolarity.NEUTRAL,
        supports: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        proposition = self.propositions.get(proposition_id)
        if proposition is None:
            return {
                "accepted": False,
                "reason": "UNKNOWN_PROPOSITION",
                "proposition_id": proposition_id,
            }

        if supports is True:
            polarity = EvidencePolarity.SUPPORTS
        elif supports is False:
            polarity = EvidencePolarity.CHALLENGES

        if polarity not in {
            EvidencePolarity.SUPPORTS,
            EvidencePolarity.CHALLENGES,
            EvidencePolarity.NEUTRAL,
        }:
            polarity = EvidencePolarity.NEUTRAL

        evidence = CognitiveEvidenceV11(
            evidence_id=make_id("evidence"),
            proposition_id=proposition_id,
            content=deepcopy(content),
            source=source,
            source_type=str(source_type),
            reliability=clamp(reliability),
            freshness=clamp(freshness, 1.0),
            relevance=clamp(relevance, 1.0),
            polarity=polarity,
            metadata=deepcopy(metadata or {}),
        )

        self.evidence[evidence.evidence_id] = evidence
        proposition.evidence_ids.append(evidence.evidence_id)

        if polarity == EvidencePolarity.SUPPORTS:
            proposition.supporting_evidence_ids.append(
                evidence.evidence_id
            )
        elif polarity == EvidencePolarity.CHALLENGES:
            proposition.challenging_evidence_ids.append(
                evidence.evidence_id
            )

        if source and source not in proposition.source_refs:
            proposition.source_refs.append(source)

        self._recalculate(proposition_id)

        return {
            "accepted": True,
            "evidence_id": evidence.evidence_id,
            "belief": deepcopy(proposition),
        }

    # --------------------------------------------------------
    # Belief calculation
    # --------------------------------------------------------

    def _recalculate(self, proposition_id: str) -> None:
        proposition = self.propositions[proposition_id]

        supporting = [
            self.evidence[eid]
            for eid in proposition.supporting_evidence_ids
            if eid in self.evidence
        ]
        challenging = [
            self.evidence[eid]
            for eid in proposition.challenging_evidence_ids
            if eid in self.evidence
        ]

        support_weight = sum(item.quality() for item in supporting)
        challenge_weight = sum(item.quality() for item in challenging)
        total = support_weight + challenge_weight

        old_status = proposition.status
        old_confidence = proposition.confidence
        old_uncertainty = proposition.uncertainty

        if total <= 0:
            new_confidence = 0.0
            new_uncertainty = 1.0
            new_status = EpistemicStatus.UNKNOWN
        else:
            new_confidence = support_weight / total
            contradiction_ratio = challenge_weight / total

            avg_quality = (
                sum(item.quality() for item in supporting + challenging)
                / len(supporting + challenging)
            )

            # Contradiction and weak evidence increase uncertainty.
            new_uncertainty = clamp(
                0.20
                + (0.55 * contradiction_ratio)
                + (0.25 * (1.0 - avg_quality)),
                1.0,
            )

            if supporting and challenging:
                new_status = EpistemicStatus.CONTRADICTED
            elif new_confidence >= 0.80:
                new_status = EpistemicStatus.SUPPORTED
            elif new_confidence >= 0.50:
                new_status = EpistemicStatus.INFERRED
            else:
                new_status = EpistemicStatus.UNCERTAIN

        proposition.status = new_status
        proposition.confidence = clamp(new_confidence)
        proposition.uncertainty = clamp(new_uncertainty, 1.0)
        proposition.revision += 1
        proposition.updated_at = utc_now()

        self.revisions.append(
            CognitiveBeliefRevisionV11(
                revision_id=make_id("beliefrev"),
                proposition_id=proposition_id,
                previous_status=old_status,
                new_status=new_status,
                previous_confidence=old_confidence,
                new_confidence=proposition.confidence,
                previous_uncertainty=old_uncertainty,
                new_uncertainty=proposition.uncertainty,
                reason="evidence_recalculation",
                evidence_ids=list(proposition.evidence_ids),
            )
        )

    def update_belief(
        self,
        proposition_id: str,
        *,
        confidence: Optional[float] = None,
        uncertainty: Optional[float] = None,
        status: Optional[str] = None,
        reason: str = "explicit_update",
    ) -> Dict[str, Any]:

        proposition = self.propositions.get(proposition_id)
        if proposition is None:
            return {
                "updated": False,
                "reason": "UNKNOWN_PROPOSITION",
            }

        old = deepcopy(proposition)

        if confidence is not None:
            proposition.confidence = clamp(confidence)
        if uncertainty is not None:
            proposition.uncertainty = clamp(uncertainty, 1.0)
        if status in self.VALID_STATUSES:
            proposition.status = status

        proposition.revision += 1
        proposition.updated_at = utc_now()

        self.revisions.append(
            CognitiveBeliefRevisionV11(
                revision_id=make_id("beliefrev"),
                proposition_id=proposition_id,
                previous_status=old.status,
                new_status=proposition.status,
                previous_confidence=old.confidence,
                new_confidence=proposition.confidence,
                previous_uncertainty=old.uncertainty,
                new_uncertainty=proposition.uncertainty,
                reason=str(reason),
                evidence_ids=list(proposition.evidence_ids),
            )
        )

        return {
            "updated": True,
            "belief": deepcopy(proposition),
        }

    # --------------------------------------------------------
    # Reality / information gaps
    # --------------------------------------------------------

    def register_reality_gap(
        self,
        gap_type: str,
        description: str,
        *,
        proposition_id: Optional[str] = None,
        severity: float = 1.0,
        required_information: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if (
            proposition_id is not None
            and proposition_id not in self.propositions
        ):
            return {
                "accepted": False,
                "reason": "UNKNOWN_PROPOSITION",
            }

        gap = CognitiveRealityGapV11(
            gap_id=make_id("gap"),
            proposition_id=proposition_id,
            gap_type=str(gap_type),
            severity=clamp(severity),
            description=str(description),
            required_information=list(required_information or []),
            metadata=deepcopy(metadata or {}),
        )

        self.reality_gaps[gap.gap_id] = gap
        return {
            "accepted": True,
            "gap": deepcopy(gap),
        }

    def resolve_reality_gap(self, gap_id: str) -> bool:
        gap = self.reality_gaps.get(gap_id)
        if gap is None:
            return False
        gap.resolved = True
        gap.resolved_at = utc_now()
        return True

    def unresolved_gaps(
        self,
        minimum_severity: float = 0.0,
    ) -> List[CognitiveRealityGapV11]:
        threshold = clamp(minimum_severity)
        return [
            deepcopy(item)
            for item in self.reality_gaps.values()
            if not item.resolved and item.severity >= threshold
        ]

    # --------------------------------------------------------
    # Reports
    # --------------------------------------------------------

    def contradiction_report(self) -> List[Dict[str, Any]]:
        return [
            {
                "proposition_id": item.proposition_id,
                "statement": item.statement,
                "confidence": item.confidence,
                "uncertainty": item.uncertainty,
                "supporting_evidence": list(
                    item.supporting_evidence_ids
                ),
                "challenging_evidence": list(
                    item.challenging_evidence_ids
                ),
            }
            for item in self.propositions.values()
            if item.status == EpistemicStatus.CONTRADICTED
        ]

    def snapshot(self) -> Dict[str, Any]:
        return {
            "version": CognitiveV11_VERSION,
            "timestamp": utc_now(),
            "propositions": {
                key: value.to_dict()
                for key, value in self.propositions.items()
            },
            "evidence": {
                key: value.to_dict()
                for key, value in self.evidence.items()
            },
            "revisions": [
                item.to_dict() for item in self.revisions
            ],
            "reality_gaps": {
                key: value.to_dict()
                for key, value in self.reality_gaps.items()
            },
        }

    def diagnostics(self) -> Dict[str, Any]:
        status_counts: Dict[str, int] = {}

        for item in self.propositions.values():
            status_counts[item.status] = (
                status_counts.get(item.status, 0) + 1
            )

        return {
            "proposition_count": len(self.propositions),
            "evidence_count": len(self.evidence),
            "revision_count": len(self.revisions),
            "reality_gap_count": len(self.reality_gaps),
            "unresolved_gap_count": len(
                self.unresolved_gaps()
            ),
            "status_counts": status_counts,
        }


# ============================================================
# 5. REALITY-BELIEF GAP DETECTOR
# ============================================================

class CognitiveRealityBeliefGapDetectorV11:
    """
    Detects conditions where a proposition should not be treated
    as sufficiently established.

    It detects epistemic risk; it does not claim to prove reality.
    """

    def __init__(
        self,
        epistemic_state: CognitiveEpistemicStateManagerV11,
    ) -> None:
        self.epistemic_state = epistemic_state

    def analyze(
        self,
        proposition_id: str,
    ) -> Dict[str, Any]:

        proposition = self.epistemic_state.get_proposition(
            proposition_id
        )

        if proposition is None:
            return {
                "analyzed": False,
                "reason": "UNKNOWN_PROPOSITION",
            }

        issues: List[str] = []

        if not proposition.evidence_ids:
            issues.append("NO_EVIDENCE")
        if proposition.uncertainty >= 0.70:
            issues.append("HIGH_UNCERTAINTY")
        if proposition.status == EpistemicStatus.CONTRADICTED:
            issues.append("CONTRADICTORY_EVIDENCE")
        if proposition.status == EpistemicStatus.HYPOTHESIS:
            issues.append("UNVERIFIED_HYPOTHESIS")
        if proposition.status == EpistemicStatus.STALE:
            issues.append("STALE_INFORMATION")

        return {
            "analyzed": True,
            "proposition_id": proposition_id,
            "status": proposition.status,
            "confidence": proposition.confidence,
            "uncertainty": proposition.uncertainty,
            "issues": issues,
            "gap_present": bool(issues),
        }

    analyze_proposition = analyze

    def scan(self) -> Dict[str, Any]:
        results = [
            self.analyze(pid)
            for pid in self.epistemic_state.propositions
        ]
        return {
            "version": CognitiveV11_VERSION,
            "propositions_scanned": len(results),
            "gaps_detected": sum(
                1 for item in results if item["gap_present"]
            ),
            "results": results,
        }


# ============================================================
# 6. V1.1 VERIFICATION ENGINE
# ============================================================

class CognitiveV11VerificationEngine(CognitiveV1VerificationEngine):
    """V1.0 verification plus deterministic V1.1 checks."""

    def verify_v11_components(
        self,
    ) -> CognitiveV1VerificationResult:

        required = [
            "epistemic_state",
            "reality_belief_gap_detector",
        ]

        missing = [
            name
            for name in required
            if not hasattr(self.brain, name)
        ]

        if missing:
            return self._record(
                "V1_1_COMPONENTS_001",
                "v1_1",
                "FAIL",
                "Required V1.1 components are missing.",
                {"missing": missing},
            )

        return self._record(
            "V1_1_COMPONENTS_001",
            "v1_1",
            "PASS",
            "Required V1.1 components are available.",
            {"checked": required},
        )

    def verify_epistemic_round_trip(
        self,
    ) -> CognitiveV1VerificationResult:

        manager = self.brain.epistemic_state

        proposition = manager.create_proposition(
            "V1.1 verification proposition"
        )

        result = manager.add_evidence(
            proposition.proposition_id,
            {"verification": True},
            source="v1_1_internal_verifier",
            source_type="internal_test",
            reliability=1.0,
            freshness=1.0,
            relevance=1.0,
            polarity=EvidencePolarity.SUPPORTS,
        )

        if not result.get("accepted"):
            return self._record(
                "V1_1_EPISTEMIC_001",
                "epistemic",
                "FAIL",
                "Epistemic proposition/evidence round-trip failed.",
                result,
            )

        recovered = manager.get_proposition(
            proposition.proposition_id
        )

        if recovered is None or not recovered.evidence_ids:
            return self._record(
                "V1_1_EPISTEMIC_001",
                "epistemic",
                "FAIL",
                "Evidence could not be recovered from the proposition.",
            )

        return self._record(
            "V1_1_EPISTEMIC_001",
            "epistemic",
            "PASS",
            "Epistemic proposition/evidence round-trip succeeded.",
            {
                "proposition_id": proposition.proposition_id,
                "status": recovered.status,
            },
        )

    def verify_gap_detector(
        self,
    ) -> CognitiveV1VerificationResult:

        manager = self.brain.epistemic_state

        proposition = manager.create_proposition(
            "V1.1 gap detector proposition"
        )

        result = self.brain.reality_belief_gap_detector.analyze(
            proposition.proposition_id
        )

        if not result.get("analyzed"):
            return self._record(
                "V1_1_GAP_001",
                "epistemic",
                "FAIL",
                "Reality-belief gap detector failed.",
                result,
            )

        if "NO_EVIDENCE" not in result.get("issues", []):
            return self._record(
                "V1_1_GAP_001",
                "epistemic",
                "FAIL",
                "Gap detector did not identify missing evidence.",
                result,
            )

        return self._record(
            "V1_1_GAP_001",
            "epistemic",
            "PASS",
            "Reality-belief gap detector identified missing evidence.",
            result,
        )

    def verify_safety_boundary(
        self,
    ) -> CognitiveV1VerificationResult:

        identity = self.brain.identity()

        if identity.get("decision_authority") is True:
            return self._record(
                "V1_1_SAFETY_001",
                "safety",
                "FAIL",
                "V1.1 exposes decision authority.",
            )

        if identity.get("automatic_self_modification") is True:
            return self._record(
                "V1_1_SAFETY_001",
                "safety",
                "FAIL",
                "V1.1 exposes automatic self-modification.",
            )

        return self._record(
            "V1_1_SAFETY_001",
            "safety",
            "PASS",
            "V1.1 safety boundaries are preserved.",
        )

    def run_all(self, state: Any) -> Dict[str, Any]:
        # The V1.0 suite is the compatibility baseline.
        super().run_all(state)

        self.verify_v11_components()
        self.verify_epistemic_round_trip()
        self.verify_gap_detector()
        self.verify_safety_boundary()

        counts = {
            "PASS": 0,
            "FAIL": 0,
            "PARTIAL": 0,
            "NOT_RUN": 0,
        }

        for result in self.results:
            counts[result.status] += 1

        if counts["FAIL"]:
            overall = "FAIL"
        elif counts["PARTIAL"]:
            overall = "PARTIAL"
        elif counts["PASS"] == len(self.results) and self.results:
            overall = "PASS"
        else:
            overall = "NOT_RUN"

        return {
            "verification_id": make_id("v11_verification"),
            "system": CognitiveV11_SYSTEM_NAME,
            "version": CognitiveV11_VERSION,
            "stage": CognitiveV11_STAGE,
            "overall": overall,
            "counts": counts,
            "total_checks": len(self.results),
            "results": [
                result.to_dict()
                for result in self.results
            ],
            "timestamp": utc_now(),
        }


# ============================================================
# 7. COGNITIVE BRAIN V1.1
# ============================================================

class CognitiveBrainV1_1(CognitiveBrainV1_0):
    """
    V1.1 additive Cognitive Brain.

    Inheritance:
        V0.x/V0.9 CognitiveBrain
                    ↓
        CognitiveBrainV1_0
                    ↓
        CognitiveBrainV1_1

    V1.0 remains the compatibility baseline.
    """

    def __init__(self, connector):
        super().__init__(connector)

        self.system_name = CognitiveV11_SYSTEM_NAME
        self.system_version = CognitiveV11_VERSION
        self.cognitive_stage = CognitiveV11_STAGE

        self.epistemic_state = (
            CognitiveEpistemicStateManagerV11()
        )

        self.reality_belief_gap_detector = (
            CognitiveRealityBeliefGapDetectorV11(
                self.epistemic_state
            )
        )

        self.verification = CognitiveV11VerificationEngine(
            self
        )

        self.last_v11_verification_report: Optional[
            Dict[str, Any]
        ] = None

    # --------------------------------------------------------
    # Identity
    # --------------------------------------------------------

    def identity(self) -> Dict[str, Any]:
        identity = super().identity()

        identity.update(
            {
                "system": CognitiveV11_SYSTEM_NAME,
                "version": CognitiveV11_VERSION,
                "stage": CognitiveV11_STAGE,
                "role": "SUPPORTING_COGNITIVE_SYSTEM",
                "base_version": "1.0.0",
                "epistemic_state_enabled": True,
                "reality_belief_gap_detection": True,
                "decision_authority": False,
                "automatic_self_modification": False,
                "replaces_unity": False,
                "replaces_heroic": False,
                "replaces_supervisor": False,
                "replaces_alpha": False,
                "replaces_legend": False,
            }
        )

        return identity

    # --------------------------------------------------------
    # Think
    # --------------------------------------------------------

    def think(self, state: Any) -> Dict[str, Any]:
        result = super().think(state)

        # Use the existing VALE task state rather than creating
        # another global state object.
        state.set(
            "cognitive_v1_1_version",
            CognitiveV11_VERSION,
        )
        state.set(
            "cognitive_v1_1_stage",
            CognitiveV11_STAGE,
        )
        state.set(
            "cognitive_epistemic_state_enabled",
            True,
        )

        state.event(
            "cognitive_v1_1_initialized",
            "COGNITIVE",
            payload={
                "version": CognitiveV11_VERSION,
                "stage": CognitiveV11_STAGE,
                "task_id": state.task_id,
            },
        )

        result = deepcopy(result)
        result.update(
            {
                "version": CognitiveV11_VERSION,
                "stage": CognitiveV11_STAGE,
                "status": "V1_1_EPISTEMIC_READY",
                "epistemic": (
                    self.epistemic_state.diagnostics()
                ),
                "reality_belief_gaps": len(
                    self.epistemic_state.unresolved_gaps()
                ),
            }
        )
        return result

    # --------------------------------------------------------
    # Explicit verification
    # --------------------------------------------------------

    def verify(self, state: Any) -> Dict[str, Any]:
        report = self.verification.run_all(state)

        self.last_v11_verification_report = deepcopy(report)
        self.last_verification_report = deepcopy(report)

        state.set(
            "cognitive_v1_1_verification",
            deepcopy(report),
        )

        state.event(
            "cognitive_v1_1_verification_completed",
            "COGNITIVE",
            payload={
                "verification_id": report.get(
                    "verification_id"
                ),
                "overall": report.get("overall"),
                "counts": report.get("counts"),
            },
        )

        return report

    # --------------------------------------------------------
    # Epistemic API
    # --------------------------------------------------------

    def create_proposition(
        self,
        statement: str,
        **kwargs: Any,
    ) -> CognitivePropositionV11:
        return self.epistemic_state.create_proposition(
            statement,
            **kwargs,
        )

    def add_evidence(
        self,
        proposition_id: str,
        content: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return self.epistemic_state.add_evidence(
            proposition_id,
            content,
            **kwargs,
        )

    def update_belief(
        self,
        proposition_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return self.epistemic_state.update_belief(
            proposition_id,
            **kwargs,
        )

    def register_reality_gap(
        self,
        gap_type: str,
        description: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return self.epistemic_state.register_reality_gap(
            gap_type,
            description,
            **kwargs,
        )

    def scan_reality_belief_gaps(self) -> Dict[str, Any]:
        return self.reality_belief_gap_detector.scan()

    def epistemic_snapshot(self) -> Dict[str, Any]:
        return self.epistemic_state.snapshot()

    # --------------------------------------------------------
    # Diagnostics
    # --------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        diagnostics = super().diagnostics()

        diagnostics.update(
            {
                "system": CognitiveV11_SYSTEM_NAME,
                "version": CognitiveV11_VERSION,
                "stage": CognitiveV11_STAGE,
                "epistemic": (
                    self.epistemic_state.diagnostics()
                ),
                "reality_belief_gap_detector": {
                    "enabled": True,
                    "unresolved_gaps": len(
                        self.epistemic_state.unresolved_gaps()
                    ),
                },
                "safety": {
                    "decision_authority": False,
                    "automatic_self_modification": False,
                },
                "verification": {
                    "available": True,
                    "last_overall": (
                        self.last_v11_verification_report.get(
                            "overall"
                        )
                        if self.last_v11_verification_report
                        else None
                    ),
                },
            }
        )

        return diagnostics

    # --------------------------------------------------------
    # Architecture status
    # --------------------------------------------------------

    def architecture_status(self) -> Dict[str, Any]:
        return {
            "manifest": {
                "system": CognitiveV11_SYSTEM_NAME,
                "version": CognitiveV11_VERSION,
                "stage": CognitiveV11_STAGE,
                "base": "COGNITIVE.cognitive_v1_0",
                "additive": True,
                "decision_authority": False,
                "automatic_self_modification": False,
            },
            "identity": self.identity(),
            "v1_0_architecture": (
                CognitiveV1Architecture.manifest()
            ),
            "v1_1_components": {
                "epistemic_state": True,
                "belief_revision_history": True,
                "reality_belief_gap_detection": True,
            },
            "diagnostics": self.diagnostics(),
            "verification": deepcopy(
                self.last_v11_verification_report
            ),
        }


# ============================================================
# 8. FACTORY
# ============================================================

def create_cognitive_v1_1(
    connector: Any,
) -> CognitiveBrainV1_1:
    """
    Explicit V1.1 factory.

    The existence of this file does not silently change the
    current production CognitiveBrain path.
    """
    return CognitiveBrainV1_1(connector)


# ============================================================
# 9. PUBLIC EXPORTS
# ============================================================

__all__ = [
    "CognitiveV11_SYSTEM_NAME",
    "CognitiveV11_VERSION",
    "CognitiveV11_STAGE",
    "EpistemicStatus",
    "EvidencePolarity",
    "RealityGapType",
    "CognitiveEvidenceV11",
    "CognitivePropositionV11",
    "CognitiveBeliefRevisionV11",
    "CognitiveRealityGapV11",
    "CognitiveEpistemicStateManagerV11",
    "CognitiveRealityBeliefGapDetectorV11",
    "CognitiveV11VerificationEngine",
    "CognitiveBrainV1_1",
    "create_cognitive_v1_1",
]
