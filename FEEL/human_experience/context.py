"""
VALE FEELING Brain
Human Experience Context

File:
    FEEL/human_experience/context.py

Purpose:
    Builds a structured representation of the human context surrounding
    an event, request, conversation, or situation.

This module does NOT claim to know what a person is actually thinking
or feeling.

It separates:
    OBSERVATION
        ↓
    CONTEXTUAL INTERPRETATION
        ↓
    POSSIBLE HUMAN SIGNIFICANCE
        ↓
    UNCERTAINTY

The output can be consumed by the other FEELING subsystems and by
the wider VALE Cognitive Fabric.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.contracts import (
    CognitiveContext,
    EngineResult,
    EvidenceItem,
)
from ..core.models import (
    HumanContext,
    EpistemicType,
)


@dataclass
class HumanExperienceContext:
    """
    Structured contextual representation of a human situation.

    This is a computational model, not a claim that FEELING literally
    experiences the situation.
    """

    situation: str = ""

    observed_events: List[str] = field(
        default_factory=list
    )

    known_context: List[str] = field(
        default_factory=list
    )

    possible_personal_significance: List[str] = field(
        default_factory=list
    )

    possible_concerns: List[str] = field(
        default_factory=list
    )

    possible_priorities: List[str] = field(
        default_factory=list
    )

    possible_constraints: List[str] = field(
        default_factory=list
    )

    possible_consequences: List[str] = field(
        default_factory=list
    )

    contextual_uncertainties: List[str] = field(
        default_factory=list
    )

    missing_context: List[str] = field(
        default_factory=list
    )

    evidence: List[EvidenceItem] = field(
        default_factory=list
    )

    confidence: float = 0.0

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.confidence = max(
            0.0,
            min(1.0, self.confidence),
        )

    def add_observation(self, value: str) -> None:
        if value and value not in self.observed_events:
            self.observed_events.append(value)

    def add_context(self, value: str) -> None:
        if value and value not in self.known_context:
            self.known_context.append(value)

    def add_significance(self, value: str) -> None:
        if (
            value
            and value not in self.possible_personal_significance
        ):
            self.possible_personal_significance.append(value)

    def add_concern(self, value: str) -> None:
        if value and value not in self.possible_concerns:
            self.possible_concerns.append(value)

    def add_priority(self, value: str) -> None:
        if value and value not in self.possible_priorities:
            self.possible_priorities.append(value)

    def add_constraint(self, value: str) -> None:
        if value and value not in self.possible_constraints:
            self.possible_constraints.append(value)

    def add_consequence(self, value: str) -> None:
        if value and value not in self.possible_consequences:
            self.possible_consequences.append(value)

    def add_uncertainty(self, value: str) -> None:
        if (
            value
            and value not in self.contextual_uncertainties
        ):
            self.contextual_uncertainties.append(value)

    def add_missing_context(self, value: str) -> None:
        if value and value not in self.missing_context:
            self.missing_context.append(value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "situation": self.situation,
            "observed_events": list(
                self.observed_events
            ),
            "known_context": list(
                self.known_context
            ),
            "possible_personal_significance": list(
                self.possible_personal_significance
            ),
            "possible_concerns": list(
                self.possible_concerns
            ),
            "possible_priorities": list(
                self.possible_priorities
            ),
            "possible_constraints": list(
                self.possible_constraints
            ),
            "possible_consequences": list(
                self.possible_consequences
            ),
            "contextual_uncertainties": list(
                self.contextual_uncertainties
            ),
            "missing_context": list(
                self.missing_context
            ),
            "evidence": [
                evidence.to_dict()
                for evidence in self.evidence
            ],
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }


class HumanExperienceContextEngine:
    """
    Context builder for the Human Experience Engine.

    Responsibilities:
        - identify explicit human context
        - organize observed events
        - identify potentially relevant concerns
        - identify possible significance
        - identify missing information
        - preserve uncertainty
        - avoid unsupported psychological claims

    It does not:
        - diagnose
        - mind-read
        - assert hidden emotions as facts
        - determine the user's ultimate intent
        - override HEROIC
        - make decisions for UNITY
    """

    NAME = "human_experience_context"

    def analyze(
        self,
        context: CognitiveContext,
    ) -> EngineResult:
        """
        Analyze the human context contained in a cognitive request.
        """

        result = EngineResult(
            engine=self.NAME,
            success=True,
        )

        user_input = (context.user_input or "").strip()

        if not user_input:
            result.summary = (
                "No user input was supplied for human-context analysis."
            )

            result.add_uncertainty(
                "Human context cannot be meaningfully modeled "
                "without relevant input."
            )

            result.confidence = 0.0
            return result

        model = self.build_context(context)

        result.summary = self._build_summary(model)

        for observation in model.observed_events:
            result.add_observation(observation)

        for contextual_item in model.known_context:
            result.add_observation(
                f"Known context: {contextual_item}"
            )

        for significance in model.possible_personal_significance:
            result.add_inference(
                f"Possible significance: {significance}"
            )

        for concern in model.possible_concerns:
            result.add_inference(
                f"Possible concern: {concern}"
            )

        for priority in model.possible_priorities:
            result.add_inference(
                f"Possible priority: {priority}"
            )

        for uncertainty in model.contextual_uncertainties:
            result.add_uncertainty(uncertainty)

        for missing in model.missing_context:
            result.add_uncertainty(
                f"Missing context: {missing}"
            )

        result.evidence.extend(model.evidence)

        result.outputs["human_experience_context"] = (
            model.to_dict()
        )

        result.confidence = model.confidence

        result.metadata["epistemic_boundary"] = (
            "Contextual interpretations are hypotheses or "
            "inferences unless explicitly supported by evidence."
        )

        return result

    def build_context(
        self,
        context: CognitiveContext,
    ) -> HumanExperienceContext:
        """
        Construct the contextual model.

        This method intentionally uses conservative heuristics. Deeper
        psychological reasoning belongs to the Psychological Intelligence
        subsystem, which will be implemented separately.
        """

        user_input = (context.user_input or "").strip()

        model = HumanExperienceContext(
            situation=user_input
        )

        # --------------------------------------------------------------
        # Explicit information supplied by the system/user
        # --------------------------------------------------------------

        for fact in context.known_facts:
            if fact:
                model.add_context(fact)

        for constraint in context.active_constraints:
            if constraint:
                model.add_constraint(constraint)

        for evidence in context.evidence:
            model.evidence.append(evidence)

            if evidence.content:
                model.add_observation(
                    evidence.content
                )

        # --------------------------------------------------------------
        # Conversation context
        # --------------------------------------------------------------

        for item in context.conversation_context:
            if item:
                model.add_context(item)

        # --------------------------------------------------------------
        # Basic contextual interpretation
        # --------------------------------------------------------------

        self._identify_contextual_signals(
            user_input=user_input,
            model=model,
        )

        self._identify_missing_context(
            user_input=user_input,
            model=model,
        )

        self._calculate_confidence(model)

        return model

    def _identify_contextual_signals(
        self,
        user_input: str,
        model: HumanExperienceContext,
    ) -> None:
        """
        Identify explicit contextual signals.

        These are deliberately conservative. The presence of a word
        does not prove an emotional or psychological state.
        """

        text = user_input.lower()

        # ----------------------------------------------------------
        # Problem / difficulty
        # ----------------------------------------------------------

        difficulty_terms = (
            "problem",
            "issue",
            "error",
            "failed",
            "failure",
            "broken",
            "can't",
            "cannot",
            "unable",
            "not working",
        )

        if any(term in text for term in difficulty_terms):
            model.add_significance(
                "The situation may involve solving or resolving "
                "a perceived problem."
            )

        # ----------------------------------------------------------
        # Urgency
        # ----------------------------------------------------------

        urgency_terms = (
            "urgent",
            "asap",
            "immediately",
            "right now",
            "quickly",
            "deadline",
            "emergency",
        )

        if any(term in text for term in urgency_terms):
            model.add_priority(
                "There may be a time-sensitive requirement."
            )

        # ----------------------------------------------------------
        # Learning / understanding
        # ----------------------------------------------------------

        learning_terms = (
            "explain",
            "understand",
            "learn",
            "how do",
            "what does",
            "why",
        )

        if any(term in text for term in learning_terms):
            model.add_priority(
                "Understanding or learning may be an important "
                "part of the user's objective."
            )

        # ----------------------------------------------------------
        # Decision / comparison
        # ----------------------------------------------------------

        decision_terms = (
            "should i",
            "which",
            "choose",
            "decision",
            "decide",
            "compare",
            "better",
            "option",
        )

        if any(term in text for term in decision_terms):
            model.add_significance(
                "The user may be dealing with a choice or "
                "decision context."
            )

        # ----------------------------------------------------------
        # Creative context
        # ----------------------------------------------------------

        creative_terms = (
            "idea",
            "create",
            "design",
            "imagine",
            "creative",
            "invent",
            "brainstorm",
        )

        if any(term in text for term in creative_terms):
            model.add_priority(
                "Creative generation or exploration may be relevant."
            )

        # ----------------------------------------------------------
        # Explicit personal context
        # ----------------------------------------------------------

        personal_terms = (
            "i feel",
            "i'm feeling",
            "my situation",
            "my problem",
            "for me",
            "personally",
            "i am",
            "i'm",
        )

        if any(term in text for term in personal_terms):
            model.add_significance(
                "The request contains explicit first-person "
                "personal context."
            )

    def _identify_missing_context(
        self,
        user_input: str,
        model: HumanExperienceContext,
    ) -> None:
        """
        Identify context that may materially change interpretation.

        This does not assume the missing information; it records that
        additional information may be needed.
        """

        if len(user_input) < 10:
            model.add_missing_context(
                "The available statement is very brief."
            )

        if not model.known_context:
            model.add_missing_context(
                "Relevant situational background may be unavailable."
            )

        if not model.evidence:
            model.add_missing_context(
                "No independently structured evidence was supplied."
            )

        # Human significance should remain uncertain when context is thin.
        if not model.possible_personal_significance:
            model.add_uncertainty(
                "The personal meaning of the situation is unknown."
            )

    def _calculate_confidence(
        self,
        model: HumanExperienceContext,
    ) -> None:
        """
        Calculate a conservative confidence estimate.

        This confidence measures confidence in the contextual model,
        not confidence about a person's hidden internal state.
        """

        score = 0.0

        if model.observed_events:
            score += 0.20

        if model.known_context:
            score += 0.20

        if model.evidence:
            score += 0.25

        if model.possible_priorities:
            score += 0.10

        if model.possible_constraints:
            score += 0.10

        if model.missing_context:
            score -= 0.10 * min(
                len(model.missing_context),
                3,
            )

        if model.contextual_uncertainties:
            score -= 0.05 * min(
                len(model.contextual_uncertainties),
                3,
            )

        model.confidence = max(
            0.0,
            min(1.0, score),
        )

    def _build_summary(
        self,
        model: HumanExperienceContext,
    ) -> str:
        """
        Generate a concise human-readable summary.
        """

        if not model.observed_events and not model.known_context:
            return (
                "Insufficient explicit context for a strong "
                "human-experience interpretation."
            )

        parts: List[str] = []

        if model.possible_priorities:
            parts.append(
                "Possible priorities were identified."
            )

        if model.possible_concerns:
            parts.append(
                "Possible concerns were identified."
            )

        if model.possible_personal_significance:
            parts.append(
                "Possible personal significance was identified."
            )

        if model.missing_context:
            parts.append(
                "Additional context may be required."
            )

        if not parts:
            parts.append(
                "Human context was organized without making "
                "strong psychological assumptions."
            )

        return " ".join(parts)


__all__ = [
    "HumanExperienceContext",
    "HumanExperienceContextEngine",
  ]
