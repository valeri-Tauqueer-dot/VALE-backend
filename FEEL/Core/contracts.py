"""
VALE FEELING Brain
Core Contracts

File:
    FEEL/core/contracts.py

Purpose:
    Defines the internal contracts used by FEELING subsystems.

These contracts keep the architecture modular. Individual engines should
communicate through structured cognitive results rather than depending
directly on each other's internal implementation.

Core epistemic rule:

    FACT
    INFERENCE
    HYPOTHESIS
    IMAGINATION

must remain distinguishable.

FEELING does not perform mind-reading or clinical diagnosis.
Psychological outputs are computational interpretations with evidence,
confidence, uncertainty, and alternative explanations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from .models import (
    EpistemicClaim,
    FeelingAssessment,
    HumanContext,
    ImaginationCandidate,
    Idea,
    Perspective,
    PsychologicalSignal,
    PsychologicalState,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class EvidenceItem:
    """
    Evidence supplied to a FEELING subsystem.

    Evidence may originate from:
        - user statements
        - conversation context
        - explicitly supplied information
        - trusted memory
        - another VALE brain
        - external knowledge
        - system observations

    The source should be recorded whenever possible.
    """

    content: str

    source: str = "unknown"

    evidence_type: str = "observation"

    reliability: float = 0.5

    timestamp: datetime = field(default_factory=_utc_now)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.reliability = max(0.0, min(1.0, self.reliability))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source": self.source,
            "evidence_type": self.evidence_type,
            "reliability": self.reliability,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class CognitiveContext:
    """
    Shared input context supplied to a FEELING subsystem.

    This is intentionally generic so that FEELING can receive information
    from the wider VALE Cognitive Fabric without becoming tightly coupled
    to one particular brain.
    """

    task_id: str

    user_input: str = ""

    conversation_context: List[str] = field(default_factory=list)

    evidence: List[EvidenceItem] = field(default_factory=list)

    known_facts: List[str] = field(default_factory=list)

    active_constraints: List[str] = field(default_factory=list)

    relevant_memory: List[Dict[str, Any]] = field(
        default_factory=list
    )

    other_brain_context: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=_utc_now)

    def add_evidence(
        self,
        content: str,
        source: str = "unknown",
        evidence_type: str = "observation",
        reliability: float = 0.5,
    ) -> None:
        """Add structured evidence to the context."""

        if not content:
            return

        self.evidence.append(
            EvidenceItem(
                content=content,
                source=source,
                evidence_type=evidence_type,
                reliability=reliability,
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "user_input": self.user_input,
            "conversation_context": list(
                self.conversation_context
            ),
            "evidence": [
                item.to_dict()
                for item in self.evidence
            ],
            "known_facts": list(self.known_facts),
            "active_constraints": list(self.active_constraints),
            "relevant_memory": list(self.relevant_memory),
            "other_brain_context": dict(
                self.other_brain_context
            ),
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class EngineResult:
    """
    Standard result returned by any FEELING subsystem.

    This is the main internal contract between engines.

    An engine should not simply return a raw string such as:

        "The user is frustrated."

    Instead it should return structured information containing:
        - what was observed
        - what was inferred
        - confidence
        - uncertainty
        - alternatives
        - evidence
        - provenance
    """

    engine: str

    success: bool = True

    summary: str = ""

    observations: List[str] = field(
        default_factory=list
    )

    inferences: List[str] = field(
        default_factory=list
    )

    hypotheses: List[str] = field(
        default_factory=list
    )

    uncertainties: List[str] = field(
        default_factory=list
    )

    alternative_explanations: List[str] = field(
        default_factory=list
    )

    evidence: List[EvidenceItem] = field(
        default_factory=list
    )

    confidence: float = 0.0

    outputs: Dict[str, Any] = field(
        default_factory=dict
    )

    warnings: List[str] = field(
        default_factory=list
    )

    errors: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    created_at: datetime = field(
        default_factory=_utc_now
    )

    def __post_init__(self) -> None:
        self.confidence = max(
            0.0,
            min(1.0, self.confidence),
        )

    def add_observation(self, value: str) -> None:
        if value and value not in self.observations:
            self.observations.append(value)

    def add_inference(self, value: str) -> None:
        if value and value not in self.inferences:
            self.inferences.append(value)

    def add_hypothesis(self, value: str) -> None:
        if value and value not in self.hypotheses:
            self.hypotheses.append(value)

    def add_uncertainty(self, value: str) -> None:
        if value and value not in self.uncertainties:
            self.uncertainties.append(value)

    def add_alternative(self, value: str) -> None:
        if (
            value
            and value not in self.alternative_explanations
        ):
            self.alternative_explanations.append(value)

    def add_warning(self, value: str) -> None:
        if value and value not in self.warnings:
            self.warnings.append(value)

    def add_error(self, value: str) -> None:
        if value and value not in self.errors:
            self.errors.append(value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "success": self.success,
            "summary": self.summary,
            "observations": list(self.observations),
            "inferences": list(self.inferences),
            "hypotheses": list(self.hypotheses),
            "uncertainties": list(self.uncertainties),
            "alternative_explanations": list(
                self.alternative_explanations
            ),
            "evidence": [
                item.to_dict()
                for item in self.evidence
            ],
            "confidence": self.confidence,
            "outputs": dict(self.outputs),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PsychologicalResult(EngineResult):
    """
    Specialized result for psychological intelligence.

    The psychological model must remain explicitly probabilistic and
    contextual. It does not claim direct access to another person's mind.
    """

    psychological_signals: List[PsychologicalSignal] = field(
        default_factory=list
    )

    psychological_state: Optional[PsychologicalState] = None

    possible_emotions: List[str] = field(
        default_factory=list
    )

    possible_motivations: List[str] = field(
        default_factory=list
    )

    possible_behaviors: List[str] = field(
        default_factory=list
    )

    cognitive_biases: List[str] = field(
        default_factory=list
    )

    needs_or_drives: List[str] = field(
        default_factory=list
    )

    threat_or_uncertainty_signals: List[str] = field(
        default_factory=list
    )

    social_signals: List[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()

        result.update(
            {
                "psychological_signals": [
                    signal.to_dict()
                    for signal in self.psychological_signals
                ],
                "psychological_state": (
                    self.psychological_state.to_dict()
                    if self.psychological_state is not None
                    else None
                ),
                "possible_emotions": list(
                    self.possible_emotions
                ),
                "possible_motivations": list(
                    self.possible_motivations
                ),
                "possible_behaviors": list(
                    self.possible_behaviors
                ),
                "cognitive_biases": list(
                    self.cognitive_biases
                ),
                "needs_or_drives": list(
                    self.needs_or_drives
                ),
                "threat_or_uncertainty_signals": list(
                    self.threat_or_uncertainty_signals
                ),
                "social_signals": list(
                    self.social_signals
                ),
            }
        )

        return result


@dataclass
class HumanUnderstandingResult(EngineResult):
    """
    Result of FEELING's broader human-understanding layer.
    """

    human_context: Optional[HumanContext] = None

    emotional_assessment: Optional[FeelingAssessment] = None

    perspectives: List[Perspective] = field(
        default_factory=list
    )

    communication_recommendations: Dict[str, Any] = field(
        default_factory=dict
    )

    intent_context: Dict[str, Any] = field(
        default_factory=dict
    )

    social_context: Dict[str, Any] = field(
        default_factory=dict
    )

    values_and_preferences: Dict[str, Any] = field(
        default_factory=dict
    )

    human_impact: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()

        result.update(
            {
                "human_context": (
                    self.human_context.to_dict()
                    if self.human_context is not None
                    else None
                ),
                "emotional_assessment": (
                    self.emotional_assessment.to_dict()
                    if self.emotional_assessment is not None
                    else None
                ),
                "perspectives": [
                    perspective.to_dict()
                    for perspective in self.perspectives
                ],
                "communication_recommendations": dict(
                    self.communication_recommendations
                ),
                "intent_context": dict(
                    self.intent_context
                ),
                "social_context": dict(
                    self.social_context
                ),
                "values_and_preferences": dict(
                    self.values_and_preferences
                ),
                "human_impact": dict(
                    self.human_impact
                ),
            }
        )

        return result


@dataclass
class CreativityResult(EngineResult):
    """
    Result produced by imagination and idea-generation systems.
    """

    imagination_candidates: List[
        ImaginationCandidate
    ] = field(default_factory=list)

    ideas: List[Idea] = field(
        default_factory=list
    )

    combinations_considered: List[str] = field(
        default_factory=list
    )

    novelty_notes: List[str] = field(
        default_factory=list
    )

    validation_requirements: List[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()

        result.update(
            {
                "imagination_candidates": [
                    candidate.to_dict()
                    for candidate in self.imagination_candidates
                ],
                "ideas": [
                    idea.to_dict()
                    for idea in self.ideas
                ],
                "combinations_considered": list(
                    self.combinations_considered
                ),
                "novelty_notes": list(
                    self.novelty_notes
                ),
                "validation_requirements": list(
                    self.validation_requirements
                ),
            }
        )

        return result


@dataclass
class MCVLChallenge:
    """
    Structured challenge request sent from FEELING toward MCVL.

    MCVL should challenge:
        - unsupported psychological assumptions
        - excessive confidence
        - missing evidence
        - alternative explanations
        - fact/inference confusion
        - imagination/reality confusion
        - contradictions
    """

    challenge_id: str

    source_engine: str

    claim: str

    claim_type: str

    evidence: List[EvidenceItem] = field(
        default_factory=list
    )

    confidence: float = 0.0

    uncertainty: List[str] = field(
        default_factory=list
    )

    alternatives: List[str] = field(
        default_factory=list
    )

    requested_checks: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    created_at: datetime = field(
        default_factory=_utc_now
    )

    def __post_init__(self) -> None:
        self.confidence = max(
            0.0,
            min(1.0, self.confidence),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "source_engine": self.source_engine,
            "claim": self.claim,
            "claim_type": self.claim_type,
            "evidence": [
                item.to_dict()
                for item in self.evidence
            ],
            "confidence": self.confidence,
            "uncertainty": list(self.uncertainty),
            "alternatives": list(self.alternatives),
            "requested_checks": list(
                self.requested_checks
            ),
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class MCVLChallengeResult:
    """
    Structured response from MCVL.

    FEELING should consume this result before treating a psychological,
    emotional, human-contextual, or imaginative interpretation as stronger
    than its evidence supports.
    """

    challenge_id: str

    accepted: bool = False

    revised_confidence: float = 0.0

    verified_claims: List[str] = field(
        default_factory=list
    )

    rejected_claims: List[str] = field(
        default_factory=list
    )

    uncertain_claims: List[str] = field(
        default_factory=list
    )

    missing_evidence: List[str] = field(
        default_factory=list
    )

    alternative_explanations: List[str] = field(
        default_factory=list
    )

    contradictions: List[str] = field(
        default_factory=list
    )

    reasoning_notes: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    created_at: datetime = field(
        default_factory=_utc_now
    )

    def __post_init__(self) -> None:
        self.revised_confidence = max(
            0.0,
            min(1.0, self.revised_confidence),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "accepted": self.accepted,
            "revised_confidence": self.revised_confidence,
            "verified_claims": list(
                self.verified_claims
            ),
            "rejected_claims": list(
                self.rejected_claims
            ),
            "uncertain_claims": list(
                self.uncertain_claims
            ),
            "missing_evidence": list(
                self.missing_evidence
            ),
            "alternative_explanations": list(
                self.alternative_explanations
            ),
            "contradictions": list(
                self.contradictions
            ),
            "reasoning_notes": list(
                self.reasoning_notes
            ),
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class InterBrainContext:
    """
    Contract for information FEELING receives from or sends to another
    VALE brain.

    FEELING contributes human-context intelligence but does not take over
    another brain's responsibility.
    """

    source_brain: str

    target_brain: str

    task_id: str

    purpose: str

    payload: Dict[str, Any] = field(
        default_factory=dict
    )

    confidence: float = 0.0

    uncertainties: List[str] = field(
        default_factory=list
    )

    evidence_refs: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    created_at: datetime = field(
        default_factory=_utc_now
    )

    def __post_init__(self) -> None:
        self.confidence = max(
            0.0,
            min(1.0, self.confidence),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_brain": self.source_brain,
            "target_brain": self.target_brain,
            "task_id": self.task_id,
            "purpose": self.purpose,
            "payload": dict(self.payload),
            "confidence": self.confidence,
            "uncertainties": list(
                self.uncertainties
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FeelingEngineRequest:
    """
    Standard request passed into a FEELING subsystem.
    """

    engine: str

    context: CognitiveContext

    state_version: int = 0

    requested_depth: str = "normal"

    require_evidence: bool = True

    allow_hypotheses: bool = True

    allow_imagination: bool = False

    require_mcvl_review: bool = False

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class FeelingEngineResponse:
    """
    Standard response returned from a FEELING subsystem.
    """

    engine: str

    result: EngineResult

    state_version: int

    requires_mcvl: bool = False

    mcvl_challenges: List[MCVLChallenge] = field(
        default_factory=list
    )

    interbrain_context: List[InterBrainContext] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    created_at: datetime = field(
        default_factory=_utc_now
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "result": self.result.to_dict(),
            "state_version": self.state_version,
            "requires_mcvl": self.requires_mcvl,
            "mcvl_challenges": [
                challenge.to_dict()
                for challenge in self.mcvl_challenges
            ],
            "interbrain_context": [
                context.to_dict()
                for context in self.interbrain_context
            ],
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
        }


__all__ = [
    "EvidenceItem",
    "CognitiveContext",
    "EngineResult",
    "PsychologicalResult",
    "HumanUnderstandingResult",
    "CreativityResult",
    "MCVLChallenge",
    "MCVLChallengeResult",
    "InterBrainContext",
    "FeelingEngineRequest",
    "FeelingEngineResponse",
]
             
