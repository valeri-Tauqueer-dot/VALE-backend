"""
VALE FEELINGS Brain
Empathy Engine

File:
    FEEL/empathy/engine.py

Purpose:
    Integrate FEELING's empathy perspective, human-needs, and
    communication-impact analysis into one coherent subsystem.

Pipeline:

    INPUT
      ↓
    POSSIBLE HUMAN PERSPECTIVE
      ↓
    POSSIBLE HUMAN NEEDS
      ↓
    POSSIBLE COMMUNICATION IMPACT
      ↓
    EMPATHY ASSESSMENT

Important epistemic boundary:

    FACT != INFERENCE != HYPOTHESIS

Empathy does not mean:
    - mind-reading
    - claiming literal emotional experience
    - psychological diagnosis
    - certainty about another person's internal state
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ..Core.contracts import (
    CognitiveContext,
    EngineResult,
)
from ..Core.models import (
    EvidenceReference,
    EpistemicClaim,
    EpistemicType,
)

from .impact import (
    EmpathyImpactAssessment,
    EmpathyImpactAnalyzer,
)
from .needs import (
    EmpathyNeedsAssessment,
    EmpathyNeedsAnalyzer,
)
from .perspective import (
    EmpathyPerspectiveEngine,
    EmpathyPerspectiveModel,
)


# ============================================================================
# UTILITIES
# ============================================================================

def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    """Clamp a numeric value."""
    return max(minimum, min(maximum, float(value)))


def _safe_text(value: Any) -> str:
    """Convert a value to clean text."""
    if value is None:
        return ""

    return str(value).strip()


def _unique(values: Iterable[str]) -> List[str]:
    """Return unique non-empty strings while preserving order."""
    result: List[str] = []
    seen = set()

    for value in values:
        value = _safe_text(value)

        if not value:
            continue

        key = value.casefold()

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


# ============================================================================
# EMPATHY ASSESSMENT
# ============================================================================

@dataclass
class EmpathyAssessment:
    """
    Integrated empathy assessment.

    The assessment combines:

        - perspective modeling
        - possible human needs
        - communication impact
        - uncertainty
        - alternative explanations
        - evidence
        - epistemic claims

    It remains explicitly probabilistic and contextual.
    """

    input_text: str = ""

    perspective: Optional[EmpathyPerspectiveModel] = None

    needs: Optional[EmpathyNeedsAssessment] = None

    impact: Optional[EmpathyImpactAssessment] = None

    possible_concerns: List[str] = field(
        default_factory=list
    )

    possible_priorities: List[str] = field(
        default_factory=list
    )

    possible_needs: List[str] = field(
        default_factory=list
    )

    communication_implications: List[str] = field(
        default_factory=list
    )

    communication_risks: List[str] = field(
        default_factory=list
    )

    recommended_adaptations: List[str] = field(
        default_factory=list
    )

    uncertainties: List[str] = field(
        default_factory=list
    )

    alternative_explanations: List[str] = field(
        default_factory=list
    )

    evidence: List[EvidenceReference] = field(
        default_factory=list
    )

    epistemic_claims: List[EpistemicClaim] = field(
        default_factory=list
    )

    confidence: float = 0.0

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
        data = asdict(self)

        data["created_at"] = self.created_at.isoformat()

        data["evidence"] = [
            evidence.to_dict()
            for evidence in self.evidence
        ]

        data["epistemic_claims"] = [
            claim.to_dict()
            for claim in self.epistemic_claims
        ]

        return data


# ============================================================================
# EMPATHY ENGINE
# ============================================================================

class EmpathyEngine:
    """
    Main FEELING Empathy subsystem.

    This engine is deliberately an internal FEELING component.

    It does not replace:

        HEROIC
        ALPHA
        UNITY
        MCVL
        Safety systems
        Psychological Intelligence
    """

    ENGINE_NAME = "empathy"
    VERSION = "0.1.0"

    def __init__(
        self,
        perspective_engine: Optional[
            EmpathyPerspectiveEngine
        ] = None,
        needs_analyzer: Optional[
            EmpathyNeedsAnalyzer
        ] = None,
        impact_analyzer: Optional[
            EmpathyImpactAnalyzer
        ] = None,
    ) -> None:

        self.perspective_engine = (
            perspective_engine
            or EmpathyPerspectiveEngine()
        )

        self.needs_analyzer = (
            needs_analyzer
            or EmpathyNeedsAnalyzer()
        )

        self.impact_analyzer = (
            impact_analyzer
            or EmpathyImpactAnalyzer()
        )

        self.last_assessment: Optional[
            EmpathyAssessment
        ] = None

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------

    def analyze(
        self,
        text: str = "",
        context: Optional[CognitiveContext] = None,
        response_text: str = "",
        evidence: Optional[
            Sequence[EvidenceReference]
        ] = None,
    ) -> EmpathyAssessment:
        """
        Run the complete empathy analysis pipeline.
        """

        input_text = self._resolve_input_text(
            text=text,
            context=context,
        )

        evidence_items = list(
            evidence or []
        )

        if input_text:
            evidence_items.append(
                EvidenceReference(
                    source="empathy_engine_input",
                    content=input_text,
                )
            )

        # --------------------------------------------------------------
        # 1. Perspective
        # --------------------------------------------------------------

        perspective = self._run_perspective(
            input_text=input_text,
            context=context,
        )

        # --------------------------------------------------------------
        # 2. Needs
        # --------------------------------------------------------------

        needs = self.needs_analyzer.analyze(
            text=input_text,
            context=context,
            evidence=evidence_items,
        )

        # --------------------------------------------------------------
        # 3. Communication impact
        # --------------------------------------------------------------

        impact = self._run_impact(
            response_text=response_text,
            input_text=input_text,
            context=context,
        )

        # --------------------------------------------------------------
        # Combine concerns
        # --------------------------------------------------------------

        possible_concerns = _unique(
            [
                *getattr(
                    perspective,
                    "possible_concerns",
                    [],
                ),
                *self._needs_to_concerns(needs),
                *self._impact_to_concerns(impact),
            ]
        )

        # --------------------------------------------------------------
        # Combine priorities
        # --------------------------------------------------------------

        possible_priorities = _unique(
            [
                *getattr(
                    perspective,
                    "possible_priorities",
                    [],
                ),
                *needs.possible_priorities,
                *self._impact_to_priorities(impact),
            ]
        )

        # --------------------------------------------------------------
        # Communication implications
        # --------------------------------------------------------------

        communication_implications = _unique(
            [
                *getattr(
                    perspective,
                    "communication_implications",
                    [],
                ),
                *needs.communication_implications,
            ]
        )

        # --------------------------------------------------------------
        # Communication risks
        # --------------------------------------------------------------

        communication_risks = _unique(
            impact.communication_risks
            if impact
            else []
        )

        # --------------------------------------------------------------
        # Recommended adaptations
        # --------------------------------------------------------------

        recommended_adaptations = _unique(
            impact.recommended_adaptations
            if impact
            else []
        )

        # --------------------------------------------------------------
        # Evidence
        # --------------------------------------------------------------

        combined_evidence = self._collect_evidence(
            perspective=perspective,
            needs=needs,
            impact=impact,
            fallback=evidence_items,
        )

        # --------------------------------------------------------------
        # Uncertainty
        # --------------------------------------------------------------

        uncertainties = _unique(
            [
                *getattr(
                    perspective,
                    "uncertainties",
                    [],
                ),
                *needs.uncertainties,
                *(
                    impact.uncertainty_notes
                    if impact
                    else []
                ),
                (
                    "Empathy outputs represent possible "
                    "human interpretations rather than "
                    "direct access to internal experience."
                ),
            ]
        )

        # --------------------------------------------------------------
        # Alternative explanations
        # --------------------------------------------------------------

        alternative_explanations = _unique(
            [
                *getattr(
                    perspective,
                    "alternative_explanations",
                    [],
                ),
                *needs.alternative_explanations,
                *(
                    impact.alternative_explanations
                    if impact
                    else []
                ),
            ]
        )

        # --------------------------------------------------------------
        # Epistemic claims
        # --------------------------------------------------------------

        epistemic_claims = self._collect_claims(
            perspective=perspective,
            needs=needs,
            impact=impact,
        )

        # --------------------------------------------------------------
        # Overall confidence
        # --------------------------------------------------------------

        confidence = self._calculate_confidence(
            perspective=perspective,
            needs=needs,
            impact=impact,
        )

        reasoning_notes = [
            "Empathy combines perspective, possible needs, "
            "and communication-impact analysis.",
            "The engine does not claim direct access to another "
            "person's internal mental state.",
            "Explicitly stated information is treated more "
            "strongly than inferred psychological interpretation.",
            "Alternative explanations and uncertainty are retained "
            "for downstream MCVL verification.",
        ]

        assessment = EmpathyAssessment(
            input_text=input_text,
            perspective=perspective,
            needs=needs,
            impact=impact,
            possible_concerns=possible_concerns,
            possible_priorities=possible_priorities,
            possible_needs=needs.possible_needs,
            communication_implications=communication_implications,
            communication_risks=communication_risks,
            recommended_adaptations=recommended_adaptations,
            uncertainties=uncertainties,
            alternative_explanations=alternative_explanations,
            evidence=combined_evidence,
            epistemic_claims=epistemic_claims,
            confidence=confidence,
            reasoning_notes=reasoning_notes,
            metadata={
                "engine": self.ENGINE_NAME,
                "version": self.VERSION,
                "has_response_text": bool(
                    _safe_text(response_text)
                ),
                "perspective_confidence": getattr(
                    perspective,
                    "confidence",
                    0.0,
                ),
                "needs_confidence": needs.confidence,
                "impact_confidence": (
                    impact.confidence
                    if impact
                    else 0.0
                ),
            },
        )

        self.last_assessment = assessment

        return assessment

    # ------------------------------------------------------------------
    # EngineResult wrapper
    # ------------------------------------------------------------------

    def run(
        self,
        context: CognitiveContext,
        response_text: str = "",
    ) -> EngineResult:
        """
        Run the empathy engine through the common FEELING EngineResult
        contract.
        """

        assessment = self.analyze(
            text=context.user_input,
            context=context,
            response_text=response_text,
        )

        return EngineResult(
            engine_name=self.ENGINE_NAME,
            success=True,
            confidence=assessment.confidence,
            output=assessment.to_dict(),
            evidence=[
                evidence.to_dict()
                for evidence in assessment.evidence
            ],
            uncertainties=assessment.uncertainties,
            metadata={
                "version": self.VERSION,
                "possible_needs": assessment.possible_needs,
                "possible_concerns": assessment.possible_concerns,
            },
        )

    # ------------------------------------------------------------------
    # Perspective
    # ------------------------------------------------------------------

    def _run_perspective(
        self,
        input_text: str,
        context: Optional[CognitiveContext],
    ) -> EmpathyPerspectiveModel:

        if context is not None:
            try:
                result = self.perspective_engine.analyze(
                    text=input_text,
                    context=context,
                )

                return result
            except TypeError:
                pass

        return self.perspective_engine.analyze(
            text=input_text
        )

    # ------------------------------------------------------------------
    # Impact
    # ------------------------------------------------------------------

    def _run_impact(
        self,
        response_text: str,
        input_text: str,
        context: Optional[CognitiveContext],
    ) -> EmpathyImpactAssessment:

        response_text = _safe_text(response_text)

        if not response_text:
            # There is no proposed response to evaluate.
            # Return a neutral assessment rather than inventing one.
            return EmpathyImpactAssessment(
                response_text="",
                context_summary=input_text,
                confidence=0.10,
                uncertainty_notes=[
                    "No proposed response text was supplied, "
                    "so communication impact could not be "
                    "meaningfully evaluated."
                ],
                reasoning_notes=[
                    "Impact analysis requires a response or "
                    "communication candidate."
                ],
                metadata={
                    "engine": "empathy_impact",
                    "status": "NO_RESPONSE_TO_EVALUATE",
                },
            )

        # The current impact analyzer is intentionally kept loosely
        # coupled because its public interface may evolve as FEELING
        # grows. Try the richer interface first.
        try:
            return self.impact_analyzer.analyze(
                response_text=response_text,
                context=input_text,
            )
        except TypeError:
            pass

        try:
            return self.impact_analyzer.evaluate(
                response_text=response_text,
                context=input_text,
            )
        except TypeError:
            pass

        # Safe fallback for future compatibility.
        return EmpathyImpactAssessment(
            response_text=response_text,
            context_summary=input_text,
            confidence=0.10,
            uncertainty_notes=[
                "The communication-impact analyzer does not "
                "currently expose a compatible analysis signature."
            ],
            reasoning_notes=[
                "Impact result was created as a compatibility "
                "fallback rather than inventing an unsupported result."
            ],
            metadata={
                "engine": "empathy_impact",
                "status": "INTERFACE_MISMATCH",
            },
        )

    # ------------------------------------------------------------------
    # Input resolution
    # ------------------------------------------------------------------

    def _resolve_input_text(
        self,
        text: str,
        context: Optional[CognitiveContext],
    ) -> str:

        text = _safe_text(text)

        if text:
            return text

        if context is not None:
            user_input = _safe_text(
                getattr(
                    context,
                    "user_input",
                    "",
                )
            )

            if user_input:
                return user_input

        return ""

    # ------------------------------------------------------------------
    # Concern extraction
    # ------------------------------------------------------------------

    def _needs_to_concerns(
        self,
        needs: EmpathyNeedsAssessment,
    ) -> List[str]:

        mapping = {
            "clarity": "Possible concern about unclear information.",
            "understanding": "Possible concern about understanding the situation.",
            "safety": "Possible concern about safety or harm.",
            "certainty": "Possible concern about uncertainty.",
            "accuracy": "Possible concern about correctness or verification.",
            "control": "Possible concern about maintaining control over the situation.",
            "autonomy": "Possible concern about preserving choice or autonomy.",
            "efficiency": "Possible concern about unnecessary time or effort.",
            "stability": "Possible concern about reliability or consistency.",
            "predictability": "Possible concern about what happens next.",
            "competence": "Possible concern about learning or capability.",
            "achievement": "Possible concern about reaching the intended goal.",
            "connection": "Possible concern about support or connection.",
            "recognition": "Possible concern about acknowledgment.",
            "fairness": "Possible concern about fairness.",
            "exploration": "Possible desire to investigate or understand further.",
            "novelty": "Possible interest in new or different possibilities.",
            "self_expression": "Possible need for self-expression or personal direction.",
            "resource_preservation": "Possible concern about preserving time, money, or other resources.",
        }

        return [
            mapping[need]
            for need in needs.possible_needs
            if need in mapping
        ]

    # ------------------------------------------------------------------
    # Impact concerns
    # ------------------------------------------------------------------

    def _impact_to_concerns(
        self,
        impact: EmpathyImpactAssessment,
    ) -> List[str]:

        return list(
            impact.communication_risks
        )

    # ------------------------------------------------------------------
    # Impact priorities
    # ------------------------------------------------------------------

    def _impact_to_priorities(
        self,
        impact: EmpathyImpactAssessment,
    ) -> List[str]:

        priorities: List[str] = []

        for recommendation in impact.recommended_adaptations:
            priorities.append(recommendation)

        return priorities

    # ------------------------------------------------------------------
    # Evidence aggregation
    # ------------------------------------------------------------------

    def _collect_evidence(
        self,
        perspective: EmpathyPerspectiveModel,
        needs: EmpathyNeedsAssessment,
        impact: EmpathyImpactAssessment,
        fallback: Sequence[EvidenceReference],
    ) -> List[EvidenceReference]:

        result: List[EvidenceReference] = []

        result.extend(
            getattr(
                perspective,
                "evidence",
                [],
            )
        )

        result.extend(
            needs.evidence
        )

        result.extend(
            impact.evidence
        )

        if not result:
            result.extend(fallback)

        # Deduplicate using source + content.
        unique: List[EvidenceReference] = []
        seen = set()

        for item in result:
            key = (
                item.source,
                item.content,
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(item)

        return unique

    # ------------------------------------------------------------------
    # Claim aggregation
    # ------------------------------------------------------------------

    def _collect_claims(
        self,
        perspective: EmpathyPerspectiveModel,
        needs: EmpathyNeedsAssessment,
        impact: EmpathyImpactAssessment,
    ) -> List[EpistemicClaim]:

        claims: List[EpistemicClaim] = []

        claims.extend(
            getattr(
                perspective,
                "epistemic_claims",
                [],
            )
        )

        claims.extend(
            needs.epistemic_claims
        )

        claims.extend(
            impact.epistemic_claims
        )

        # Add one explicit system-level epistemic boundary.
        claims.append(
            EpistemicClaim(
                content=(
                    "Empathy outputs represent possible human "
                    "interpretations and communication effects, "
                    "not direct observations of internal mental state."
                ),
                epistemic_type=EpistemicType.INFERENCE,
                confidence=0.99,
                evidence=[],
                rationale=(
                    "This is a system-level epistemic boundary "
                    "of the FEELING Empathy subsystem."
                ),
                source=self.ENGINE_NAME,
            )
        )

        return claims

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        perspective: EmpathyPerspectiveModel,
        needs: EmpathyNeedsAssessment,
        impact: EmpathyImpactAssessment,
    ) -> float:

        values = [
            getattr(
                perspective,
                "confidence",
                0.0,
            ),
            needs.confidence,
            impact.confidence,
        ]

        valid_values = [
            _clamp(value)
            for value in values
            if value is not None
        ]

        if not valid_values:
            return 0.0

        # The integrated confidence is intentionally conservative.
        # A weak component should reduce overall certainty rather
        # than allowing another component to hide it.
        average = sum(valid_values) / len(valid_values)
        minimum = min(valid_values)

        return _clamp(
            (average * 0.60) + (minimum * 0.40)
        )

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def possible_needs(
        self,
        text: str = "",
        context: Optional[CognitiveContext] = None,
    ) -> List[str]:
        """Return possible human needs."""
        return self.analyze(
            text=text,
            context=context,
        ).possible_needs

    def possible_concerns(
        self,
        text: str = "",
        context: Optional[CognitiveContext] = None,
    ) -> List[str]:
        """Return possible human concerns."""
        return self.analyze(
            text=text,
            context=context,
        ).possible_concerns

    def communication_guidance(
        self,
        text: str = "",
        context: Optional[CognitiveContext] = None,
    ) -> List[str]:
        """Return possible communication adaptations."""
        return self.analyze(
            text=text,
            context=context,
        ).recommended_adaptations

    # ------------------------------------------------------------------
    # State compatibility
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the internal last-assessment state."""
        self.last_assessment = None

        if hasattr(
            self.perspective_engine,
            "reset",
        ):
            self.perspective_engine.reset()

        if hasattr(
            self.needs_analyzer,
            "reset",
        ):
            self.needs_analyzer.reset()

        if hasattr(
            self.impact_analyzer,
            "reset",
        ):
            self.impact_analyzer.reset()

    def export_state(self) -> Dict[str, Any]:
        """Export current empathy subsystem state."""
        return {
            "engine": self.ENGINE_NAME,
            "version": self.VERSION,
            "last_assessment": (
                self.last_assessment.to_dict()
                if self.last_assessment
                else None
            ),
            "components": {
                "perspective": (
                    self.perspective_engine.export_state()
                    if hasattr(
                        self.perspective_engine,
                        "export_state",
                    )
                    else {}
                ),
                "needs": (
                    self.needs_analyzer.export_state()
                    if hasattr(
                        self.needs_analyzer,
                        "export_state",
                    )
                    else {}
                ),
                "impact": (
                    self.impact_analyzer.export_state()
                    if hasattr(
                        self.impact_analyzer,
                        "export_state",
                    )
                    else {}
                ),
            },
        }


__all__ = [
    "EmpathyAssessment",
    "EmpathyEngine",
      ]
