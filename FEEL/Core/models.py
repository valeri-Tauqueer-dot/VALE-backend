"""
VALE FEELING Brain
Core Models

Foundational data contracts for FEELING's human, emotional,
psychological, imaginative, creative, and communication intelligence.

Critical epistemic boundary:

    FACT != INFERENCE != HYPOTHESIS != IMAGINATION

These models represent computational interpretations.
They do not claim biological emotion, consciousness,
mind-reading, or psychological diagnosis.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


# ============================================================================
# UTILITIES
# ============================================================================

def _utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _clamp(value: float) -> float:
    """Keep a numeric confidence/intensity value inside [0.0, 1.0]."""
    return max(0.0, min(1.0, float(value)))


# ============================================================================
# EPISTEMIC TYPES
# ============================================================================

class EpistemicType(str, Enum):
    """
    Defines the epistemic status of information.

    FEELING must never silently convert one category into another.
    """

    FACT = "FACT"
    INFERENCE = "INFERENCE"
    HYPOTHESIS = "HYPOTHESIS"
    IMAGINATION = "IMAGINATION"
    UNKNOWN = "UNKNOWN"


class ConfidenceLevel(str, Enum):
    """Human-readable confidence bands."""

    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class EvidenceStrength(str, Enum):
    """Strength of evidence supporting an observation or interpretation."""

    NONE = "NONE"
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    DIRECT = "DIRECT"


# ============================================================================
# EMOTIONAL CONTEXT
# ============================================================================

class EmotionalSignalType(str, Enum):
    """
    Broad emotional/contextual signals.

    These are computational signals inferred from available context.
    They are NOT declarations of a person's literal internal state.
    """

    CALM = "CALM"
    HAPPY = "HAPPY"
    EXCITED = "EXCITED"
    CURIOUS = "CURIOUS"
    CONFUSED = "CONFUSED"
    FRUSTRATED = "FRUSTRATED"
    WORRIED = "WORRIED"
    ANGRY = "ANGRY"
    SAD = "SAD"
    DISCOURAGED = "DISCOURAGED"
    URGENT = "URGENT"
    UNCERTAIN = "UNCERTAIN"
    ENGAGED = "ENGAGED"
    DISENGAGED = "DISENGAGED"
    RELIEVED = "RELIEVED"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# CREATIVE / IDEA STATE
# ============================================================================

class IdeaStatus(str, Enum):
    """Lifecycle state of a FEELING-generated idea."""

    GENERATED = "GENERATED"
    COMBINED = "COMBINED"
    EVALUATING = "EVALUATING"
    PROMISING = "PROMISING"
    REJECTED = "REJECTED"
    RETAINED = "RETAINED"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# EVIDENCE
# ============================================================================

@dataclass
class EvidenceReference:
    """
    Traceable evidence supporting an observation or interpretation.

    Examples of sources:
        - current_user_message
        - conversation_context
        - explicit_user_statement
        - shared_state
        - memory
        - another_vaIe_brain
        - external_source

    FEELING should retain evidence provenance whenever possible.
    """

    source: str
    content: str

    strength: EvidenceStrength = EvidenceStrength.MODERATE

    source_id: Optional[str] = None

    timestamp: str = field(
        default_factory=_utc_now
    )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["strength"] = self.strength.value
        return data


# ============================================================================
# EPISTEMIC CLAIM
# ============================================================================

@dataclass
class EpistemicClaim:
    """
    A statement with explicit epistemic classification.

    Example:

        content="The user may be frustrated"
        epistemic_type=INFERENCE
        confidence=0.68

    This prevents psychological interpretations from being represented
    as established facts.
    """

    content: str

    epistemic_type: EpistemicType

    confidence: float = 0.0

    evidence: List[EvidenceReference] = field(
        default_factory=list
    )

    rationale: Optional[str] = None

    source: Optional[str] = None

    claim_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    timestamp: str = field(
        default_factory=_utc_now
    )

    def __post_init__(self) -> None:
        self.confidence = _clamp(self.confidence)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Convert numeric confidence into a readable confidence band."""

        if self.confidence < 0.20:
            return ConfidenceLevel.VERY_LOW

        if self.confidence < 0.40:
            return ConfidenceLevel.LOW

        if self.confidence < 0.65:
            return ConfidenceLevel.MODERATE

        if self.confidence < 0.85:
            return ConfidenceLevel.HIGH

        return ConfidenceLevel.VERY_HIGH

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)

        data["epistemic_type"] = self.epistemic_type.value
        data["confidence_level"] = self.confidence_level.value

        data["evidence"] = [
            evidence.to_dict()
            for evidence in self.evidence
        ]

        return data


# ============================================================================
# EMOTIONAL SIGNAL
# ============================================================================

@dataclass
class EmotionalSignal:
    """
    Represents a possible emotional/contextual signal.

    Important:
        This is an interpretation of available communication/context.
        It is not mind-reading and is not a clinical assessment.
    """

    signal: EmotionalSignalType

    confidence: float = 0.0

    intensity: float = 0.0

    evidence: List[EvidenceReference] = field(
        default_factory=list
    )

    alternative_signals: List[EmotionalSignalType] = field(
        default_factory=list
    )

    reasoning: Optional[str] = None

    signal_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    def __post_init__(self) -> None:
        self.confidence = _clamp(self.confidence)
        self.intensity = _clamp(self.intensity)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)

        data["signal"] = self.signal.value

        data["alternative_signals"] = [
            signal.value
            for signal in self.alternative_signals
        ]

        data["evidence"] = [
            evidence.to_dict()
            for evidence in self.evidence
        ]

        return data


# ============================================================================
# HUMAN CONTEXT
# ============================================================================

@dataclass
class HumanContext:
    """
    Structured human-context representation.

    Explicit information is deliberately separated from inferred
    psychological/emotional information.
    """

    explicit_facts: List[str] = field(
        default_factory=list
    )

    inferred_needs: List[EpistemicClaim] = field(
        default_factory=list
    )

    possible_concerns: List[EpistemicClaim] = field(
        default_factory=list
    )

    possible_goals: List[EpistemicClaim] = field(
        default_factory=list
    )

    emotional_signals: List[EmotionalSignal] = field(
        default_factory=list
    )

    preferences: Dict[str, Any] = field(
        default_factory=dict
    )

    constraints: List[str] = field(
        default_factory=list
    )

    social_context: Dict[str, Any] = field(
        default_factory=dict
    )

    communication_context: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "explicit_facts": list(self.explicit_facts),

            "inferred_needs": [
                item.to_dict()
                for item in self.inferred_needs
            ],

            "possible_concerns": [
                item.to_dict()
                for item in self.possible_concerns
            ],

            "possible_goals": [
                item.to_dict()
                for item in self.possible_goals
            ],

            "emotional_signals": [
                item.to_dict()
                for item in self.emotional_signals
            ],

            "preferences": dict(self.preferences),

            "constraints": list(self.constraints),

            "social_context": dict(self.social_context),

            "communication_context": dict(
                self.communication_context
            ),
        }


# ============================================================================
# PSYCHOLOGICAL SIGNAL
# ============================================================================

@dataclass
class PsychologicalSignal:
    """
    Represents a possible psychological-process signal.

    Categories can include:

        perception
        attention
        appraisal
        belief
        expectation
        need
        motivation
        bias
        decision
        uncertainty
        threat
        coping
        social_cognition
        self_concept
        behavior

    This is a computational interpretation, not a diagnosis.
    """

    category: str

    signal: str

    confidence: float = 0.0

    evidence: List[EvidenceReference] = field(
        default_factory=list
    )

    alternatives: List[str] = field(
        default_factory=list
    )

    assumptions: List[str] = field(
        default_factory=list
    )

    reasoning: Optional[str] = None

    signal_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    def __post_init__(self) -> None:
        self.confidence = _clamp(self.confidence)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)

        data["evidence"] = [
            evidence.to_dict()
            for evidence in self.evidence
        ]

        return data


# ============================================================================
# PSYCHOLOGICAL STATE
# ============================================================================

@dataclass
class PsychologicalState:
    """
    Snapshot of FEELING's current psychological-context model.

    This is NOT a clinical psychological profile.

    It models potentially relevant processes such as:

        Observation
            ↓
        Perception
            ↓
        Appraisal
            ↓
        Beliefs / Expectations / Needs
            ↓
        Emotion / Motivation
            ↓
        Decision pressure
            ↓
        Possible behavior
            ↓
        Consequence
            ↓
        Updated interpretation
    """

    attention: List[PsychologicalSignal] = field(
        default_factory=list
    )

    appraisals: List[PsychologicalSignal] = field(
        default_factory=list
    )

    beliefs: List[EpistemicClaim] = field(
        default_factory=list
    )

    expectations: List[EpistemicClaim] = field(
        default_factory=list
    )

    needs: List[EpistemicClaim] = field(
        default_factory=list
    )

    motivations: List[PsychologicalSignal] = field(
        default_factory=list
    )

    biases: List[PsychologicalSignal] = field(
        default_factory=list
    )

    uncertainty_signals: List[PsychologicalSignal] = field(
        default_factory=list
    )

    coping_patterns: List[PsychologicalSignal] = field(
        default_factory=list
    )

    behavioral_tendencies: List[PsychologicalSignal] = field(
        default_factory=list
    )

    social_signals: List[PsychologicalSignal] = field(
        default_factory=list
    )

    contradictions: List[str] = field(
        default_factory=list
    )

    uncertainties: List[str] = field(
        default_factory=list
    )

    state_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    created_at: str = field(
        default_factory=_utc_now
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "created_at": self.created_at,

            "attention": [
                item.to_dict()
                for item in self.attention
            ],

            "appraisals": [
                item.to_dict()
                for item in self.appraisals
            ],

            "beliefs": [
                item.to_dict()
                for item in self.beliefs
            ],

            "expectations": [
                item.to_dict()
                for item in self.expectations
            ],

            "needs": [
                item.to_dict()
                for item in self.needs
            ],

            "motivations": [
                item.to_dict()
                for item in self.motivations
            ],

            "biases": [
                item.to_dict()
                for item in self.biases
            ],

            "uncertainty_signals": [
                item.to_dict()
                for item in self.uncertainty_signals
            ],

            "coping_patterns": [
                item.to_dict()
                for item in self.coping_patterns
            ],

            "behavioral_tendencies": [
                item.to_dict()
                for item in self.behavioral_tendencies
            ],

            "social_signals": [
                item.to_dict()
                for item in self.social_signals
            ],

            "contradictions": list(self.contradictions),

            "uncertainties": list(self.uncertainties),
        }


# ============================================================================
# IMAGINATION
# ============================================================================

@dataclass
class ImaginationCandidate:
    """
    A deliberately generated possibility.

    It is ALWAYS classified as IMAGINATION.

    It must never be silently promoted to factual reality.
    """

    description: str

    confidence: float = 0.0

    assumptions: List[str] = field(
        default_factory=list
    )

    constraints_used: List[str] = field(
        default_factory=list
    )

    possible_benefits: List[str] = field(
        default_factory=list
    )

    possible_risks: List[str] = field(
        default_factory=list
    )

    evaluation_notes: List[str] = field(
        default_factory=list
    )

    candidate_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    epistemic_type: EpistemicType = field(
        default=EpistemicType.IMAGINATION,
        init=False,
    )

    def __post_init__(self) -> None:
        self.confidence = _clamp(self.confidence)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)

        data["epistemic_type"] = self.epistemic_type.value

        return data


# ============================================================================
# CREATIVE IDEA
# ============================================================================

@dataclass
class Idea:
    """
    Creative idea generated by FEELING.

    An idea is not automatically a recommendation,
    validated solution, or factual conclusion.
    """

    title: str

    description: str

    status: IdeaStatus = IdeaStatus.GENERATED

    novelty_score: float = 0.0

    usefulness_score: float = 0.0

    feasibility_score: float = 0.0

    human_value_score: float = 0.0

    risks: List[str] = field(
        default_factory=list
    )

    assumptions: List[str] = field(
        default_factory=list
    )

    source_concepts: List[str] = field(
        default_factory=list
    )

    evaluation_notes: List[str] = field(
        default_factory=list
    )

    idea_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    def __post_init__(self) -> None:
        self.novelty_score = _clamp(self.novelty_score)
        self.usefulness_score = _clamp(self.usefulness_score)
        self.feasibility_score = _clamp(self.feasibility_score)
        self.human_value_score = _clamp(self.human_value_score)

    @property
    def overall_score(self) -> float:
        """
        Internal heuristic used to compare generated ideas.

        This is not proof that an idea is useful or feasible.
        """

        return (
            (self.novelty_score * 0.20)
            + (self.usefulness_score * 0.30)
            + (self.feasibility_score * 0.25)
            + (self.human_value_score * 0.25)
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)

        data["status"] = self.status.value
        data["overall_score"] = self.overall_score

        return data


# ============================================================================
# HUMAN PERSPECTIVE
# ============================================================================

@dataclass
class Perspective:
    """A possible human interpretation or perspective."""

    perspective: str

    reasoning: Optional[str] = None

    confidence: float = 0.0

    assumptions: List[str] = field(
        default_factory=list
    )

    evidence: List[EvidenceReference] = field(
        default_factory=list
    )

    perspective_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    def __post_init__(self) -> None:
        self.confidence = _clamp(self.confidence)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)

        data["evidence"] = [
            evidence.to_dict()
            for evidence in self.evidence
        ]

        return data


# ============================================================================
# COMMUNICATION INTELLIGENCE
# ============================================================================

@dataclass
class CommunicationProfile:
    """
    Human-context guidance for communication.

    This does not produce the final VALE response.
    It provides contextual guidance to the wider system.
    """

    detail_level: str = "adaptive"

    tone: str = "neutral"

    directness: str = "balanced"

    structure: str = "clear"

    step_by_step: bool = False

    supportive_language: bool = False

    urgency: float = 0.0

    confidence: float = 0.0

    reasons: List[str] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.urgency = _clamp(self.urgency)
        self.confidence = _clamp(self.confidence)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# COMPLETE FEELING ASSESSMENT
# ============================================================================

@dataclass
class FeelingAssessment:
    """
    Complete FEELING assessment envelope.

    It deliberately keeps separate:

        human context
        psychological state
        emotional signals
        perspectives
        imagination
        creative ideas
        communication guidance
        uncertainty
        contradictions
        missing information

    This allows UNITY and MCVL to reason about FEELING's output
    without losing epistemic boundaries.
    """

    context: HumanContext = field(
        default_factory=HumanContext
    )

    psychological_state: PsychologicalState = field(
        default_factory=PsychologicalState
    )

    perspectives: List[Perspective] = field(
        default_factory=list
    )

    imagination_candidates: List[ImaginationCandidate] = field(
        default_factory=list
    )

    ideas: List[Idea] = field(
        default_factory=list
    )

    communication_profile: CommunicationProfile = field(
        default_factory=CommunicationProfile
    )

    uncertainties: List[str] = field(
        default_factory=list
    )

    contradictions: List[str] = field(
        default_factory=list
    )

    missing_information: List[str] = field(
        default_factory=list
    )

    reasoning_notes: List[str] = field(
        default_factory=list
    )

    assessment_confidence: float = 0.0

    assessment_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    created_at: str = field(
        default_factory=_utc_now
    )

    def __post_init__(self) -> None:
        self.assessment_confidence = _clamp(
            self.assessment_confidence
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "created_at": self.created_at,

            "context": self.context.to_dict(),

            "psychological_state": (
                self.psychological_state.to_dict()
            ),

            "perspectives": [
                item.to_dict()
                for item in self.perspectives
            ],

            "imagination_candidates": [
                item.to_dict()
                for item in self.imagination_candidates
            ],

            "ideas": [
                item.to_dict()
                for item in self.ideas
            ],

            "communication_profile": (
                self.communication_profile.to_dict()
            ),

            "uncertainties": list(self.uncertainties),

            "contradictions": list(self.contradictions),

            "missing_information": list(
                self.missing_information
            ),

            "reasoning_notes": list(
                self.reasoning_notes
            ),

            "assessment_confidence": (
                self.assessment_confidence
            ),
        }


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    "EpistemicType",
    "ConfidenceLevel",
    "EvidenceStrength",
    "EmotionalSignalType",
    "IdeaStatus",
    "EvidenceReference",
    "EpistemicClaim",
    "EmotionalSignal",
    "HumanContext",
    "PsychologicalSignal",
    "PsychologicalState",
    "ImaginationCandidate",
    "Idea",
    "Perspective",
    "CommunicationProfile",
    "FeelingAssessment",
  ]
