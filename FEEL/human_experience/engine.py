"""
VALE FEELING Brain
Human Experience Engine

Purpose:
    Integrate contextual understanding, human needs, and possible consequences
    into a structured model of the human side of a situation.

Important epistemic boundary:
    - Observations are not automatically facts about a person's inner state.
    - Psychological and human-context interpretations are hypotheses/inferences.
    - The engine must never claim literal human experience.
    - Missing information remains explicitly represented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from FEEL.core.contracts import CognitiveContext, EngineResult
from FEEL.core.models import (
    EvidenceReference,
    EpistemicClaim,
    EpistemicType,
    HumanContext,
)
from FEEL.human_experience.context import (
    HumanExperienceContext,
    HumanExperienceContextEngine,
)
from FEEL.human_experience.consequences import (
    HumanConsequence,
    HumanConsequenceAnalyzer,
)
from FEEL.human_experience.needs import (
    HumanNeedSignal,
    HumanNeedsAnalyzer,
)


@dataclass
class HumanExperienceAssessment:
    """
    Integrated assessment of the human side of a situation.

    All fields describing internal human states are probabilistic or
    interpretive unless directly provided by the user.
    """

    situation_summary: str = ""

    observed_events: List[str] = field(default_factory=list)

    known_context: List[str] = field(default_factory=list)

    possible_significance: List[str] = field(default_factory=list)

    possible_concerns: List[str] = field(default_factory=list)

    possible_priorities: List[str] = field(default_factory=list)

    possible_constraints: List[str] = field(default_factory=list)

    possible_consequences: List[HumanConsequence] = field(default_factory=list)

    possible_needs: List[HumanNeedSignal] = field(default_factory=list)

    missing_context: List[str] = field(default_factory=list)

    uncertainties: List[str] = field(default_factory=list)

    evidence: List[EvidenceReference] = field(default_factory=list)

    epistemic_claims: List[EpistemicClaim] = field(default_factory=list)

    confidence: float = 0.0

    reasoning_notes: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "situation_summary": self.situation_summary,
            "observed_events": list(self.observed_events),
            "known_context": list(self.known_context),
            "possible_significance": list(self.possible_significance),
            "possible_concerns": list(self.possible_concerns),
            "possible_priorities": list(self.possible_priorities),
            "possible_constraints": list(self.possible_constraints),
            "possible_consequences": [
                item.to_dict() if hasattr(item, "to_dict") else item
                for item in self.possible_consequences
            ],
            "possible_needs": [
                item.to_dict() if hasattr(item, "to_dict") else item
                for item in self.possible_needs
            ],
            "missing_context": list(self.missing_context),
            "uncertainties": list(self.uncertainties),
            "evidence": [
                item.to_dict() if hasattr(item, "to_dict") else item
                for item in self.evidence
            ],
            "epistemic_claims": [
                item.to_dict() if hasattr(item, "to_dict") else item
                for item in self.epistemic_claims
            ],
            "confidence": self.confidence,
            "reasoning_notes": list(self.reasoning_notes),
            "metadata": dict(self.metadata),
        }


class HumanExperienceEngine:
    """
    Main Human Experience subsystem.

    Responsibilities:
        1. Understand the human-relevant context of a situation.
        2. Separate observed information from interpretation.
        3. Identify possible human significance and concerns.
        4. Identify possible human needs.
        5. Identify possible consequences.
        6. Track missing information and uncertainty.
        7. Produce structured information for the wider FEELING Brain.

    Non-responsibilities:
        - Diagnosing psychological disorders.
        - Claiming mind-reading.
        - Making final system-wide decisions.
        - Replacing HEROIC.
        - Replacing MCVL.
        - Executing actions.
    """

    VERSION = "0.1.0"
    ENGINE_NAME = "human_experience"

    def __init__(
        self,
        context_engine: Optional[HumanExperienceContextEngine] = None,
        consequence_analyzer: Optional[HumanConsequenceAnalyzer] = None,
        needs_analyzer: Optional[HumanNeedsAnalyzer] = None,
    ) -> None:
        self.context_engine = (
            context_engine or HumanExperienceContextEngine()
        )
        self.consequence_analyzer = (
            consequence_analyzer or HumanConsequenceAnalyzer()
        )
        self.needs_analyzer = (
            needs_analyzer or HumanNeedsAnalyzer()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        context: CognitiveContext,
    ) -> HumanExperienceAssessment:
        """
        Analyze the human side of the supplied cognitive context.
        """

        experience_context = self.context_engine.analyze(context)

        consequences = self.consequence_analyzer.analyze(
            context=context,
            human_context=experience_context,
        )

        needs = self.needs_analyzer.analyze(
            context=context,
            human_context=experience_context,
        )

        assessment = self._build_assessment(
            context=context,
            experience_context=experience_context,
            consequences=consequences,
            needs=needs,
        )

        return assessment

    def run(
        self,
        context: CognitiveContext,
    ) -> EngineResult:
        """
        Engine-compatible execution method.

        Returns an EngineResult while keeping the detailed assessment
        available inside the result payload.
        """

        assessment = self.analyze(context)

        confidence = max(
            0.0,
            min(1.0, float(assessment.confidence)),
        )

        return EngineResult(
            engine_name=self.ENGINE_NAME,
            success=True,
            confidence=confidence,
            output=assessment.to_dict(),
            evidence=assessment.evidence,
            uncertainties=assessment.uncertainties,
            metadata={
                "version": self.VERSION,
                "engine": self.ENGINE_NAME,
                "epistemic_boundary": (
                    "human experience is modeled computationally; "
                    "internal states are not treated as directly observed"
                ),
            },
        )

    # ------------------------------------------------------------------
    # Assessment construction
    # ------------------------------------------------------------------

    def _build_assessment(
        self,
        context: CognitiveContext,
        experience_context: HumanExperienceContext,
        consequences: List[HumanConsequence],
        needs: List[HumanNeedSignal],
    ) -> HumanExperienceAssessment:

        evidence = self._collect_evidence(
            experience_context=experience_context,
            consequences=consequences,
            needs=needs,
        )

        missing_context = list(
            dict.fromkeys(
                getattr(
                    experience_context,
                    "missing_context",
                    [],
                )
            )
        )

        uncertainties = list(
            dict.fromkeys(
                getattr(
                    experience_context,
                    "contextual_uncertainties",
                    [],
                )
            )
        )

        uncertainties.extend(
            self._derive_uncertainties(
                context=context,
                consequences=consequences,
                needs=needs,
            )
        )

        uncertainties = list(dict.fromkeys(uncertainties))

        claims = self._build_epistemic_claims(
            experience_context=experience_context,
            consequences=consequences,
            needs=needs,
        )

        confidence = self._calculate_confidence(
            experience_context=experience_context,
            consequences=consequences,
            needs=needs,
            missing_context=missing_context,
        )

        reasoning_notes = self._build_reasoning_notes(
            experience_context=experience_context,
            consequences=consequences,
            needs=needs,
            missing_context=missing_context,
        )

        return HumanExperienceAssessment(
            situation_summary=self._get_situation_summary(
                context,
                experience_context,
            ),
            observed_events=list(
                getattr(
                    experience_context,
                    "observed_events",
                    [],
                )
            ),
            known_context=list(
                getattr(
                    experience_context,
                    "known_context",
                    [],
                )
            ),
            possible_significance=list(
                getattr(
                    experience_context,
                    "possible_personal_significance",
                    [],
                )
            ),
            possible_concerns=list(
                getattr(
                    experience_context,
                    "possible_concerns",
                    [],
                )
            ),
            possible_priorities=list(
                getattr(
                    experience_context,
                    "possible_priorities",
                    [],
                )
            ),
            possible_constraints=list(
                getattr(
                    experience_context,
                    "possible_constraints",
                    [],
                )
            ),
            possible_consequences=consequences,
            possible_needs=needs,
            missing_context=missing_context,
            uncertainties=uncertainties,
            evidence=evidence,
            epistemic_claims=claims,
            confidence=confidence,
            reasoning_notes=reasoning_notes,
            metadata={
                "engine": self.ENGINE_NAME,
                "version": self.VERSION,
                "analysis_mode": "evidence_weighted_human_context",
            },
        )

    # ------------------------------------------------------------------
    # Epistemic handling
    # ------------------------------------------------------------------

    def _build_epistemic_claims(
        self,
        experience_context: HumanExperienceContext,
        consequences: List[HumanConsequence],
        needs: List[HumanNeedSignal],
    ) -> List[EpistemicClaim]:

        claims: List[EpistemicClaim] = []

        for item in getattr(
            experience_context,
            "observed_events",
            [],
        ):
            claims.append(
                EpistemicClaim(
                    statement=str(item),
                    epistemic_type=EpistemicType.FACT,
                    confidence=1.0,
                    evidence_ids=[],
                )
            )

        for item in getattr(
            experience_context,
            "possible_personal_significance",
            [],
        ):
            claims.append(
                EpistemicClaim(
                    statement=str(item),
                    epistemic_type=EpistemicType.INFERENCE,
                    confidence=0.5,
                    evidence_ids=[],
                )
            )

        for item in consequences:
            summary = getattr(
                item,
                "description",
                None,
            )

            if not summary:
                summary = getattr(
                    item,
                    "summary",
                    None,
                )

            if summary:
                claims.append(
                    EpistemicClaim(
                        statement=str(summary),
                        epistemic_type=EpistemicType.INFERENCE,
                        confidence=self._safe_confidence(
                            getattr(item, "confidence", 0.5)
                        ),
                        evidence_ids=[],
                    )
                )

        for item in needs:
            category = getattr(
                item,
                "category",
                "unknown",
            )

            claims.append(
                EpistemicClaim(
                    statement=(
                        f"Possible human need category: {category}"
                    ),
                    epistemic_type=EpistemicType.HYPOTHESIS,
                    confidence=self._safe_confidence(
                        getattr(item, "confidence", 0.5)
                    ),
                    evidence_ids=[],
                )
            )

        return claims

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    def _collect_evidence(
        self,
        experience_context: HumanExperienceContext,
        consequences: List[HumanConsequence],
        needs: List[HumanNeedSignal],
    ) -> List[EvidenceReference]:

        evidence: List[EvidenceReference] = []

        context_evidence = getattr(
            experience_context,
            "evidence",
            [],
        )

        for item in context_evidence:
            if isinstance(item, EvidenceReference):
                evidence.append(item)
                continue

            if isinstance(item, dict):
                try:
                    evidence.append(
                        EvidenceReference(**item)
                    )
                except TypeError:
                    continue

        for analyzer_result in [*consequences, *needs]:
            result_evidence = getattr(
                analyzer_result,
                "evidence",
                [],
            )

            for item in result_evidence:
                if isinstance(item, EvidenceReference):
                    evidence.append(item)
                elif isinstance(item, dict):
                    try:
                        evidence.append(
                            EvidenceReference(**item)
                        )
                    except TypeError:
                        continue

        return self._deduplicate_evidence(evidence)

    @staticmethod
    def _deduplicate_evidence(
        evidence: List[EvidenceReference],
    ) -> List[EvidenceReference]:

        result: List[EvidenceReference] = []
        seen = set()

        for item in evidence:
            key = (
                getattr(item, "source", ""),
                getattr(item, "content", ""),
                getattr(item, "evidence_type", ""),
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(item)

        return result

    # ------------------------------------------------------------------
    # Uncertainty
    # ------------------------------------------------------------------

    def _derive_uncertainties(
        self,
        context: CognitiveContext,
        consequences: List[HumanConsequence],
        needs: List[HumanNeedSignal],
    ) -> List[str]:

        uncertainties: List[str] = []

        text = self._context_text(context)

        if not text.strip():
            uncertainties.append(
                "No sufficiently detailed human-context input was provided."
            )

        if not self._has_explicit_personal_context(context):
            uncertainties.append(
                "Personal significance is not directly established."
            )

        if not consequences:
            uncertainties.append(
                "No concrete human consequence was confidently identified."
            )

        if not needs:
            uncertainties.append(
                "No human need signal was sufficiently supported."
            )

        return uncertainties

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        experience_context: HumanExperienceContext,
        consequences: List[HumanConsequence],
        needs: List[HumanNeedSignal],
        missing_context: List[str],
    ) -> float:

        context_confidence = self._safe_confidence(
            getattr(
                experience_context,
                "confidence",
                0.0,
            )
        )

        component_scores: List[float] = [
            context_confidence,
        ]

        for item in consequences:
            component_scores.append(
                self._safe_confidence(
                    getattr(item, "confidence", 0.0)
                )
            )

        for item in needs:
            component_scores.append(
                self._safe_confidence(
                    getattr(item, "confidence", 0.0)
                )
            )

        if not component_scores:
            return 0.0

        average = sum(component_scores) / len(component_scores)

        uncertainty_penalty = min(
            0.35,
            len(missing_context) * 0.05,
        )

        return max(
            0.0,
            min(1.0, average - uncertainty_penalty),
        )

    # ------------------------------------------------------------------
    # Reasoning notes
    # ------------------------------------------------------------------

    def _build_reasoning_notes(
        self,
        experience_context: HumanExperienceContext,
        consequences: List[HumanConsequence],
        needs: List[HumanNeedSignal],
        missing_context: List[str],
    ) -> List[str]:

        notes = [
            "Human experience is modeled rather than literally experienced.",
            "Internal human states are not directly observable unless explicitly provided.",
            "Possible significance, needs, and consequences are treated as interpretations.",
        ]

        if consequences:
            notes.append(
                f"Identified {len(consequences)} possible human consequence(s)."
            )

        if needs:
            notes.append(
                f"Identified {len(needs)} possible human need signal(s)."
            )

        if missing_context:
            notes.append(
                "Additional context could materially change the interpretation."
            )

        return notes

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _context_text(
        context: CognitiveContext,
    ) -> str:

        values: List[str] = []

        for attribute in (
            "user_input",
            "message",
            "query",
            "task",
            "situation",
            "conversation_text",
        ):
            value = getattr(context, attribute, None)

            if value:
                values.append(str(value))

        return " ".join(values)

    @classmethod
    def _get_situation_summary(
        cls,
        context: CognitiveContext,
        experience_context: HumanExperienceContext,
    ) -> str:

        situation = getattr(
            experience_context,
            "situation",
            "",
        )

        if situation:
            return str(situation)

        text = cls._context_text(context)

        if text:
            return text[:1000]

        return "Human-relevant situation not sufficiently specified."

    @classmethod
    def _has_explicit_personal_context(
        cls,
        context: CognitiveContext,
    ) -> bool:

        for attribute in (
            "user_input",
            "message",
            "query",
            "conversation_text",
            "personal_context",
        ):
            value = getattr(context, attribute, None)

            if value:
                text = str(value).lower()

                personal_markers = (
                    "i ",
                    "i'm",
                    "i am",
                    "my ",
                    "me ",
                    "we ",
                    "our ",
                    "us ",
                )

                if any(marker in text for marker in personal_markers):
                    return True

        return bool(
            getattr(
                context,
                "personal_context",
                None,
            )
        )

    @staticmethod
    def _safe_confidence(value: Any) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0

        return max(0.0, min(1.0, value))


__all__ = [
    "HumanExperienceAssessment",
    "HumanExperienceEngine",
      ]
