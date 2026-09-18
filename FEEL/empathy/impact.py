"""
VALE FEELINGS Brain
Empathy Impact Analyzer

File:
    FEEL/empathy/impact.py

Purpose:
    Estimate how a proposed communication or response may affect a
    person from a human-centered perspective.

Core model:

    RESPONSE / COMMUNICATION
              ↓
       HUMAN INTERPRETATION
              ↓
       POSSIBLE EXPERIENCE
              ↓
       POSSIBLE IMPACT
              ↓
       COMMUNICATION ADAPTATION

Important boundary:

    This module predicts possible communication effects.
    It does NOT claim to know the person's actual internal reaction.

    FACT != INFERENCE != HYPOTHESIS

This subsystem is not a replacement for:
    - VALE Safety systems
    - MCVL verification
    - HEROIC objective reasoning
    - ALPHA orchestration
    - psychological diagnosis
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from FEEL.core.models import (
    EvidenceReference,
    EpistemicClaim,
    EpistemicType,
)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(minimum, min(maximum, float(value)))


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _unique(values: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()

    for value in values:
        value = _safe_text(value)

        if not value:
            continue

        key = value.casefold()

        if key not in seen:
            seen.add(key)
            result.append(value)

    return result


# ---------------------------------------------------------------------------
# Impact model
# ---------------------------------------------------------------------------

@dataclass
class EmpathyImpactSignal:
    """
    One possible human impact of a response.

    Examples:
        - clarity improvement
        - possible confusion
        - reduced uncertainty
        - increased frustration
        - increased sense of autonomy
        - possible perceived harshness

    These are modeled possibilities, not guaranteed outcomes.
    """

    impact_type: str

    direction: str = "possible"

    intensity: float = 0.0

    confidence: float = 0.0

    rationale: str = ""

    evidence: List[EvidenceReference] = field(
        default_factory=list
    )

    alternative_explanations: List[str] = field(
        default_factory=list
    )

    uncertainties: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EmpathyImpactAssessment:
    """
    Complete human-impact assessment for a communication.
    """

    response_text: str = ""

    context_summary: str = ""

    signals: List[EmpathyImpactSignal] = field(
        default_factory=list
    )

    positive_possible_impacts: List[str] = field(
        default_factory=list
    )

    negative_possible_impacts: List[str] = field(
        default_factory=list
    )

    communication_risks: List[str] = field(
        default_factory=list
    )

    recommended_adaptations: List[str] = field(
        default_factory=list
    )

    autonomy_considerations: List[str] = field(
        default_factory=list
    )

    uncertainty_notes: List[str] = field(
        default_factory=list
    )

    alternative_explanations: List[str] = field(
        default_factory=list
    )

    confidence: float = 0.0

    evidence: List[EvidenceReference] = field(
        default_factory=list
    )

    epistemic_claims: List[EpistemicClaim] = field(
        default_factory=list
    )

    reasoning_notes: List[str] = field(
        default_factory=list
    )

    created_at: datetime = field(
        default_factory=_utc_now
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Main analyzer
# ---------------------------------------------------------------------------

class EmpathyImpactAnalyzer:
    """
    Analyze possible human impact of communication.

    The analyzer considers:

        clarity
        confusion
        emotional friction
        perceived harshness
        uncertainty reduction
        autonomy
        actionability
        cognitive load
        reassurance
        transparency
        trust implications

    It does not attempt to predict a person's exact emotional response.
    """

    ENGINE_NAME = "empathy_impact"
    VERSION = "0.1.0"

    # ------------------------------------------------------------------
    # Response-pattern definitions
    # ------------------------------------------------------------------

    CLARITY_PATTERNS = (
        "because",
        "therefore",
        "step",
        "first",
        "then",
        "example",
        "in simple terms",
        "specifically",
        "the reason",
    )

    UNCERTAINTY_PATTERNS = (
        "may",
        "might",
        "could",
        "uncertain",
        "not enough information",
        "unknown",
        "cannot confirm",
        "needs verification",
    )

    HARSH_PATTERNS = (
        "obviously",
        "stupid",
        "you should know",
        "that's wrong",
        "just do it",
        "you're wrong",
        "nonsense",
        "ridiculous",
    )

    DISMISSIVE_PATTERNS = (
        "whatever",
        "doesn't matter",
        "not important",
        "just trust me",
        "don't worry about it",
    )

    AUTONOMY_PATTERNS = (
        "you can choose",
        "option",
        "options",
        "your decision",
        "you decide",
        "one approach",
        "another approach",
        "alternative",
    )

    ACTION_PATTERNS = (
        "step 1",
        "step 2",
        "next",
        "do this",
        "you can",
        "try",
        "check",
        "verify",
    )

    HIGH_LOAD_PATTERNS = (
        "however",
        "additionally",
        "furthermore",
        "moreover",
        "in contrast",
        "on the other hand",
        "therefore",
        "consequently",
    )

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self.last_assessment: Optional[
            EmpathyImpactAssessment
        ] = None

    # ------------------------------------------------------------------
    # Input extraction
    # ------------------------------------------------------------------

    def _extract_response_text(
        self,
        response: Any,
    ) -> str:
        if response is None:
            return ""

        if isinstance(response, str):
            return response.strip()

        if isinstance(response, Mapping):
            for key in (
                "response",
                "response_text",
                "text",
                "content",
                "answer",
                "message",
            ):
                value = _safe_text(response.get(key))

                if value:
                    return value

            return ""

        for attribute in (
            "response",
            "response_text",
            "text",
            "content",
            "answer",
            "message",
        ):
            if hasattr(response, attribute):
                value = _safe_text(
                    getattr(response, attribute)
                )

                if value:
                    return value

        return ""

    def _extract_context_text(
        self,
        context: Any,
    ) -> str:
        if context is None:
            return ""

        if isinstance(context, str):
            return context.strip()

        if isinstance(context, Mapping):
            for key in (
                "text",
                "message",
                "user_message",
                "content",
                "query",
                "situation",
                "context",
            ):
                value = _safe_text(context.get(key))

                if value:
                    return value

            return ""

        for attribute in (
            "text",
            "message",
            "user_message",
            "content",
            "query",
            "situation",
        ):
            if hasattr(context, attribute):
                value = _safe_text(
                    getattr(context, attribute)
                )

                if value:
                    return value

        return ""

    # ------------------------------------------------------------------
    # Pattern helpers
    # ------------------------------------------------------------------

    def _contains_any(
        self,
        text: str,
        patterns: Sequence[str],
    ) -> bool:
        lowered = text.casefold()

        return any(
            pattern.casefold() in lowered
            for pattern in patterns
        )

    def _count_matches(
        self,
        text: str,
        patterns: Sequence[str],
    ) -> int:
        lowered = text.casefold()

        return sum(
            1
            for pattern in patterns
            if pattern.casefold() in lowered
        )

    # ------------------------------------------------------------------
    # Signal constructors
    # ------------------------------------------------------------------

    def _clarity_signal(
        self,
        response: str,
    ) -> Optional[EmpathyImpactSignal]:
        if not response:
            return None

        matches = self._count_matches(
            response,
            self.CLARITY_PATTERNS,
        )

        if matches == 0:
            return None

        intensity = _clamp(
            0.35 + (matches * 0.08)
        )

        return EmpathyImpactSignal(
            impact_type="clarity",
            direction="potentially_positive",
            intensity=intensity,
            confidence=0.62,
            rationale=(
                "The response contains structural or explanatory "
                "language that may improve understanding."
            ),
            alternative_explanations=[
                "Explanatory markers do not guarantee that the "
                "response will be understood."
            ],
        )

    def _uncertainty_signal(
        self,
        response: str,
    ) -> Optional[EmpathyImpactSignal]:
        if not response:
            return None

        matches = self._count_matches(
            response,
            self.UNCERTAINTY_PATTERNS,
        )

        if matches == 0:
            return None

        intensity = _clamp(
            0.3 + (matches * 0.1)
        )

        return EmpathyImpactSignal(
            impact_type="uncertainty_transparency",
            direction="potentially_positive",
            intensity=intensity,
            confidence=0.72,
            rationale=(
                "The response explicitly marks uncertainty or "
                "verification requirements."
            ),
            alternative_explanations=[
                "Too much uncertainty language may itself make "
                "the answer feel less decisive."
            ],
        )

    def _harshness_signal(
        self,
        response: str,
    ) -> Optional[EmpathyImpactSignal]:
        if not response:
            return None

        matches = self._count_matches(
            response,
            self.HARSH_PATTERNS,
        )

        if matches == 0:
            return None

        intensity = _clamp(
            0.5 + (matches * 0.12)
        )

        return EmpathyImpactSignal(
            impact_type="possible_perceived_harshness",
            direction="potentially_negative",
            intensity=intensity,
            confidence=0.7,
            rationale=(
                "Some wording may be interpreted as dismissive, "
                "judgmental, or unnecessarily forceful."
            ),
            alternative_explanations=[
                "The wording may be intended as concise emphasis "
                "rather than interpersonal criticism."
            ],
        )

    def _dismissive_signal(
        self,
        response: str,
    ) -> Optional[EmpathyImpactSignal]:
        if not response:
            return None

        matches = self._count_matches(
            response,
            self.DISMISSIVE_PATTERNS,
        )

        if matches == 0:
            return None

        return EmpathyImpactSignal(
            impact_type="possible_dismissiveness",
            direction="potentially_negative",
            intensity=_clamp(
                0.45 + (matches * 0.12)
            ),
            confidence=0.68,
            rationale=(
                "The response contains wording that may minimize "
                "the person's concern or uncertainty."
            ),
            alternative_explanations=[
                "Context may make the wording less dismissive "
                "than it appears in isolation."
            ],
        )

    def _autonomy_signal(
        self,
        response: str,
    ) -> Optional[EmpathyImpactSignal]:
        if not response:
            return None

        matches = self._count_matches(
            response,
            self.AUTONOMY_PATTERNS,
        )

        if matches == 0:
            return None

        return EmpathyImpactSignal(
            impact_type="autonomy_support",
            direction="potentially_positive",
            intensity=_clamp(
                0.4 + (matches * 0.1)
            ),
            confidence=0.63,
            rationale=(
                "The response appears to preserve or explicitly "
                "recognize the person's decision authority."
            ),
        )

    def _actionability_signal(
        self,
        response: str,
    ) -> Optional[EmpathyImpactSignal]:
        if not response:
            return None

        matches = self._count_matches(
            response,
            self.ACTION_PATTERNS,
        )

        if matches == 0:
            return None

        return EmpathyImpactSignal(
            impact_type="actionability",
            direction="potentially_positive",
            intensity=_clamp(
                0.35 + (matches * 0.08)
            ),
            confidence=0.64,
            rationale=(
                "The response contains actionable or sequential "
                "language that may help the person make progress."
            ),
        )

    def _cognitive_load_signal(
        self,
        response: str,
    ) -> Optional[EmpathyImpactSignal]:
        if not response:
            return None

        sentence_count = max(
            1,
            response.count(".")
            + response.count("!")
            + response.count("?"),
        )

        marker_count = self._count_matches(
            response,
            self.HIGH_LOAD_PATTERNS,
        )

        long_response = len(response.split()) > 350

        if not long_response and marker_count < 3:
            return None

        intensity = 0.45

        if long_response:
            intensity += 0.2

        intensity += min(
            0.2,
            marker_count * 0.04,
        )

        return EmpathyImpactSignal(
            impact_type="possible_cognitive_load",
            direction="potentially_negative",
            intensity=_clamp(intensity),
            confidence=0.5,
            rationale=(
                "The response may contain enough length or "
                "structural complexity to increase cognitive load."
            ),
            alternative_explanations=[
                "A detailed response may be appropriate when the "
                "person explicitly needs depth."
            ],
            uncertainties=[
                "Optimal response length depends on the person's "
                "knowledge, attention, and task requirements."
            ],
        )

    # ------------------------------------------------------------------
    # Context-aware signals
    # ------------------------------------------------------------------

    def _context_risks(
        self,
        context_text: str,
        response: str,
    ) -> List[str]:
        risks: List[str] = []

        lowered = context_text.casefold()

        if any(
            word in lowered
            for word in (
                "confused",
                "don't understand",
                "not understand",
                "explain",
                "what does this mean",
            )
        ):
            if not self._contains_any(
                response,
                self.CLARITY_PATTERNS,
            ):
                risks.append(
                    "The response may not sufficiently address a "
                    "possible need for clarification."
                )

        if any(
            word in lowered
            for word in (
                "urgent",
                "asap",
                "deadline",
                "quickly",
            )
        ):
            if len(response.split()) > 500:
                risks.append(
                    "The response may impose unnecessary cognitive "
                    "or time cost in a potentially urgent context."
                )

        if any(
            word in lowered
            for word in (
                "mistake",
                "wrong",
                "accuracy",
                "verify",
            )
        ):
            if not self._contains_any(
                response,
                self.UNCERTAINTY_PATTERNS,
            ):
                risks.append(
                    "The response may benefit from clearer distinction "
                    "between confirmed information and uncertainty."
                )

        if any(
            word in lowered
            for word in (
                "frustrated",
                "frustrating",
                "again",
                "already told",
                "still doesn't work",
            )
        ):
            if self._contains_any(
                response,
                self.HARSH_PATTERNS
                + self.DISMISSIVE_PATTERNS,
            ):
                risks.append(
                    "Potentially dismissive wording may compound "
                    "existing communication friction."
                )

        return _unique(risks)

    # ------------------------------------------------------------------
    # Adaptation recommendations
    # ------------------------------------------------------------------

    def _recommend_adaptations(
        self,
        signals: Sequence[EmpathyImpactSignal],
        context_text: str,
    ) -> List[str]:
        recommendations: List[str] = []

        signal_types = {
            signal.impact_type
            for signal in signals
        }

        if "possible_perceived_harshness" in signal_types:
            recommendations.append(
                "Replace unnecessarily judgmental wording with "
                "neutral, direct language."
            )

        if "possible_dismissiveness" in signal_types:
            recommendations.append(
                "Acknowledge the person's concern before moving "
                "to the solution."
            )

        if "possible_cognitive_load" in signal_types:
            recommendations.append(
                "Reduce unnecessary detail or organize the response "
                "into clear sections or steps."
            )

        if "clarity" not in signal_types:
            recommendations.append(
                "Make the main answer explicit and structure "
                "supporting explanation around it."
            )

        if "uncertainty_transparency" not in signal_types:
            recommendations.append(
                "Explicitly distinguish confirmed information from "
                "inference when uncertainty is material."
            )

        if (
            "autonomy_support" not in signal_types
            and any(
                word in context_text.casefold()
                for word in (
                    "choose",
                    "decision",
                    "option",
                    "should i",
                )
            )
        ):
            recommendations.append(
                "Preserve the person's decision authority by "
                "presenting relevant options and trade-offs."
            )

        return _unique(recommendations)

    # ------------------------------------------------------------------
    # Positive / negative impacts
    # ------------------------------------------------------------------

    def _positive_impacts(
        self,
        signals: Sequence[EmpathyImpactSignal],
    ) -> List[str]:
        positive: List[str] = []

        for signal in signals:
            if signal.direction != "potentially_positive":
                continue

            mapping = {
                "clarity": (
                    "may improve understanding"
                ),
                "uncertainty_transparency": (
                    "may provide a more honest understanding "
                    "of what is and is not known"
                ),
                "autonomy_support": (
                    "may preserve the person's sense of choice"
                ),
                "actionability": (
                    "may make the next step easier to identify"
                ),
            }

            description = mapping.get(
                signal.impact_type
            )

            if description:
                positive.append(description)

        return _unique(positive)

    def _negative_impacts(
        self,
        signals: Sequence[EmpathyImpactSignal],
    ) -> List[str]:
        negative: List[str] = []

        for signal in signals:
            if signal.direction != "potentially_negative":
                continue

            mapping = {
                "possible_perceived_harshness": (
                    "may be perceived as unnecessarily harsh"
                ),
                "possible_dismissiveness": (
                    "may make the person's concern feel minimized"
                ),
                "possible_cognitive_load": (
                    "may increase cognitive load"
                ),
            }

            description = mapping.get(
                signal.impact_type
            )

            if description:
                negative.append(description)

        return _unique(negative)

   
    # ------------------------------------------------------------------
    # Autonomy analysis
    # ------------------------------------------------------------------

    def _autonomy_considerations(
        self,
        response: str,
        context_text: str,
    ) -> List[str]:
        considerations: List[str] = []

        context_lower = context_text.casefold()
        response_lower = response.casefold()

        decision_context = any(
            word in context_lower
            for word in (
                "should i",
                "choose",
                "decision",
                "option",
                "which one",
                "what should",
            )
        )

        if decision_context:
            if self._contains_any(
                response,
                self.AUTONOMY_PATTERNS,
            ):
                considerations.append(
                    "The response contains language supporting "
                    "user decision authority."
                )
            else:
                considerations.append(
                    "Decision-related context may benefit from explicit "
                    "options and trade-offs rather than an unexplained "
                    "directive."
                )

        if any(
            phrase in response_lower
            for phrase in (
                "you must",
                "you have to",
                "there is only one",
            )
        ):
            considerations.append(
                "Directive wording may reduce perceived autonomy "
                "unless the constraint is genuinely mandatory."
            )

        if not considerations:
            considerations.append(
                "No strong autonomy-related communication issue "
                "was detected from the available text."
            )

        return _unique(considerations)

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    def _build_evidence(
        self,
        response: str,
        signals: Sequence[EmpathyImpactSignal],
    ) -> List[EvidenceReference]:
        evidence: List[EvidenceReference] = []

        if response:
            evidence.append(
                EvidenceReference(
                    source="response_text",
                    evidence_type="observable_communication",
                    content=response[:1200],
                    strength=0.65,
                )
            )

        for signal in signals:
            evidence.append(
                EvidenceReference(
                    source="empathy_impact_analyzer",
                    evidence_type="communication_pattern",
                    content=(
                        f"{signal.impact_type}: "
                        f"{signal.rationale}"
                    ),
                    strength=_clamp(
                        signal.confidence
                    ),
                )
            )

        return evidence

  
    # ------------------------------------------------------------------
    # Epistemic claims
    # ------------------------------------------------------------------

    def _build_epistemic_claims(
        self,
        signals: Sequence[EmpathyImpactSignal],
        confidence: float,
    ) -> List[EpistemicClaim]:
        claims: List[EpistemicClaim] = []

        if signals:
            claims.append(
                EpistemicClaim(
                    statement=(
                        "The response contains communication patterns "
                        "associated with possible human impacts."
                    ),
                    epistemic_type=EpistemicType.INFERENCE,
                    confidence=_clamp(confidence),
                    evidence=[
                        "response text",
                        "communication pattern analysis",
                    ],
                )
            )

        claims.append(
            EpistemicClaim(
                statement=(
                    "Predicted communication effects are possibilities "
                    "and do not establish the person's actual reaction."
                ),
                epistemic_type=EpistemicType.HYPOTHESIS,
                confidence=1.0,
                evidence=[
                    "FEELING empathy epistemic boundary"
                ],
            )
        )

        claims.append(
            EpistemicClaim(
                statement=(
                    "The analyzer does not directly observe another "
                    "person's internal emotional state."
                ),
                epistemic_type=EpistemicType.FACT,
                confidence=1.0,
                evidence=[
                    "FEELING epistemic boundary"
                ],
            )
        )

        return claims

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        signals: Sequence[EmpathyImpactSignal],
        context_text: str,
    ) -> float:
        if not signals:
            return 0.0

        signal_confidence = sum(
            signal.confidence
            for signal in signals
        ) / len(signals)

        context_factor = (
            0.75
            if context_text
            else 0.5
        )

        return _clamp(
            signal_confidence * context_factor
        )

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------

    def analyze(
        self,
        response: Any,
        context: Any = None,
    ) -> EmpathyImpactAssessment:
        """
        Analyze possible human impact of a response.

        Parameters:
            response:
                Proposed VALE response.

            context:
                Optional user/context information.

        Returns:
            EmpathyImpactAssessment
        """

        response_text = self._extract_response_text(
            response
        )

        context_text = self._extract_context_text(
            context
        )

        signals: List[EmpathyImpactSignal] = []

        signal_builders = (
            self._clarity_signal,
            self._uncertainty_signal,
            self._harshness_signal,
            self._dismissive_signal,
            self._autonomy_signal,
            self._actionability_signal,
            self._cognitive_load_signal,
        )

        for builder in signal_builders:
            signal = builder(response_text)

            if signal is not None:
                signals.append(signal)

        communication_risks = self._context_risks(
            context_text,
            response_text,
        )

        recommendations = self._recommend_adaptations(
            signals,
            context_text,
        )

        autonomy = self._autonomy_considerations(
            response_text,
            context_text,
        )

        positive_impacts = self._positive_impacts(
            signals
        )

        negative_impacts = self._negative_impacts(
            signals
        )

        confidence = self._calculate_confidence(
            signals,
            context_text,
        )

        uncertainty_notes = _unique(
            [
                "Communication impact depends on the person's "
                "individual context and interpretation.",
                "The same wording can affect different people "
                "differently.",
                "Text-based analysis cannot directly observe "
                "the recipient's internal reaction.",
                *[
                    uncertainty
                    for signal in signals
                    for uncertainty in signal.uncertainties
                ],
            ]
        )

        alternative_explanations = _unique(
            [
                alternative
                for signal in signals
                for alternative in (
                    signal.alternative_explanations
                )
            ]
        )

        if not alternative_explanations:
            alternative_explanations.append(
                "Observed communication patterns may not produce "
                "the predicted human impact in the actual context."
            )

        evidence = self._build_evidence(
            response_text,
            signals,
        )

        epistemic_claims = self._build_epistemic_claims(
            signals,
            confidence,
        )

        reasoning_notes = [
            "Analyzed observable response language.",
            "Mapped communication patterns to possible human impacts.",
            "Considered context where available.",
            "Separated possible communication effects from actual "
            "internal reactions.",
            "Preserved user autonomy in decision-related contexts.",
            "Recorded uncertainty and alternative explanations.",
        ]

        assessment = EmpathyImpactAssessment(
            response_text=response_text,
            context_summary=context_text,
            signals=signals,
            positive_possible_impacts=positive_impacts,
            negative_possible_impacts=negative_impacts,
            communication_risks=communication_risks,
            recommended_adaptations=recommendations,
            autonomy_considerations=autonomy,
            uncertainty_notes=uncertainty_notes,
            alternative_explanations=alternative_explanations,
            confidence=confidence,
            evidence=evidence,
            epistemic_claims=epistemic_claims,
            reasoning_notes=reasoning_notes,
            metadata={
                "engine": self.ENGINE_NAME,
                "version": self.VERSION,
                "signal_count": len(signals),
                "response_available": bool(response_text),
                "context_available": bool(context_text),
                "epistemic_boundary": (
                    "possible communication-impact inference; "
                    "not direct observation of internal reaction"
                ),
            },
        )

        self.last_assessment = assessment

        return assessment

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def evaluate(
        self,
        response: str,
        context: Any = None,
    ) -> EmpathyImpactAssessment:
        """
        Alias for analyze().
        """

        return self.analyze(
            response,
            context,
        )

    def risks(
        self,
        response: str,
        context: Any = None,
    ) -> List[str]:
        """
        Return possible communication risks.
        """

        assessment = self.analyze(
            response,
            context,
        )

        return assessment.communication_risks

    def recommendations(
        self,
        response: str,
        context: Any = None,
    ) -> List[str]:
        """
        Return possible communication adaptations.
        """

        assessment = self.analyze(
            response,
            context,
        )

        return assessment.recommended_adaptations

    def reset(self) -> None:
        """
        Clear the last assessment.
        """

        self.last_assessment = None

    def export_state(self) -> Dict[str, Any]:
        """
        Export analyzer state for observability and future integration
        with the Cognitive Fabric.
        """

        return {
            "engine": self.ENGINE_NAME,
            "version": self.VERSION,
            "last_assessment": (
                self.last_assessment.to_dict()
                if self.last_assessment is not None
                else None
            ),
        }


__all__ = [
    "EmpathyImpactSignal",
    "EmpathyImpactAssessment",
    "EmpathyImpactAnalyzer",
          ]
