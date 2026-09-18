"""
VALE FEELING Brain
Emotional Appraisal Engine

Purpose:
    Model how a situation may be appraised in ways that are
    compatible with different emotional responses.

Core principle:

    EVENT
       ↓
    APPRAISAL
       ↓
    POSSIBLE EMOTIONAL RESPONSE

The engine does NOT claim direct access to a person's mind.

An appraisal is therefore represented as:
    - an interpretation
    - supported by available evidence
    - with confidence
    - with alternative explanations
    - with uncertainty

This module does not diagnose psychological conditions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from FEEL.core.models import (
    EmotionalSignal,
    EmotionalSignalType,
    EvidenceReference,
    EvidenceStrength,
)


@dataclass
class AppraisalDimension:
    """
    One dimension through which a situation may be appraised.
    """

    name: str

    value: float = 0.0

    interpretation: str = ""

    confidence: float = 0.0

    evidence: List[EvidenceReference] = field(
        default_factory=list
    )

    uncertainty: List[str] = field(
        default_factory=list
    )

    alternative_explanations: List[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "interpretation": self.interpretation,
            "confidence": self.confidence,
            "evidence": [
                item.to_dict()
                if hasattr(item, "to_dict")
                else item
                for item in self.evidence
            ],
            "uncertainty": list(self.uncertainty),
            "alternative_explanations": list(
                self.alternative_explanations
            ),
        }


@dataclass
class EmotionalAppraisal:
    """
    Complete appraisal of a situation.

    Dimensions:
        goal_relevance
        goal_congruence
        perceived_control
        certainty
        responsibility
        threat
        loss
        gain
        novelty
        fairness
        social_significance
        effort
        reversibility
    """

    situation: str = ""

    dimensions: List[AppraisalDimension] = field(
        default_factory=list
    )

    possible_emotions: List[EmotionalSignal] = field(
        default_factory=list
    )

    primary_interpretation: str = ""

    alternative_interpretations: List[str] = field(
        default_factory=list
    )

    confidence: float = 0.0

    uncertainty: List[str] = field(
        default_factory=list
    )

    evidence: List[EvidenceReference] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "situation": self.situation,
            "dimensions": [
                item.to_dict()
                for item in self.dimensions
            ],
            "possible_emotions": [
                item.to_dict()
                if hasattr(item, "to_dict")
                else item
                for item in self.possible_emotions
            ],
            "primary_interpretation": self.primary_interpretation,
            "alternative_interpretations": list(
                self.alternative_interpretations
            ),
            "confidence": self.confidence,
            "uncertainty": list(self.uncertainty),
            "evidence": [
                item.to_dict()
                if hasattr(item, "to_dict")
                else item
                for item in self.evidence
            ],
        }


class EmotionalAppraisalEngine:
    """
    Models situation appraisal and its possible emotional implications.

    This is an important bridge between:

        Human Experience
              ↓
        Psychological Intelligence
              ↓
        Emotional Context

    The engine evaluates questions such as:

        - Does this appear relevant to a goal?
        - Is the situation interpreted as positive or negative?
        - Does the person appear to have control?
        - Is there uncertainty?
        - Is there possible threat or loss?
        - Is there possible gain?
        - Does fairness appear relevant?
        - Is the situation socially significant?
        - Does the situation appear reversible?

    These are computational interpretations, not direct observations
    of someone's internal psychological state.
    """

    VERSION = "0.1.0"
    ENGINE_NAME = "emotional_appraisal"

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(
        self,
        minimum_confidence: float = 0.25,
    ) -> None:

        self.minimum_confidence = self._clamp(
            minimum_confidence
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        text: str,
        detected_signals: Optional[
            Sequence[EmotionalSignal]
        ] = None,
        context: Optional[Any] = None,
    ) -> EmotionalAppraisal:
        """
        Build an appraisal model from available communication
        and contextual evidence.
        """

        text = self._normalize(text)

        dimensions = self._evaluate_dimensions(
            text=text,
            context=context,
        )

        interpretation = self._build_primary_interpretation(
            dimensions
        )

        alternatives = self._build_alternative_interpretations(
            dimensions
        )

        uncertainty = self._build_uncertainty(
            dimensions=dimensions,
            text=text,
        )

        evidence = self._collect_evidence(
            dimensions
        )

        confidence = self._calculate_confidence(
            dimensions=dimensions,
            uncertainty=uncertainty,
        )

        possible_emotions = (
            list(detected_signals)
            if detected_signals
            else self._derive_emotional_implications(
                dimensions
            )
        )

        return EmotionalAppraisal(
            situation=text,
            dimensions=dimensions,
            possible_emotions=possible_emotions,
            primary_interpretation=interpretation,
            alternative_interpretations=alternatives,
            confidence=confidence,
            uncertainty=uncertainty,
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Appraisal dimensions
    # ------------------------------------------------------------------

    def _evaluate_dimensions(
        self,
        text: str,
        context: Optional[Any],
    ) -> List[AppraisalDimension]:

        dimensions = [
            self._goal_relevance(text),
            self._goal_congruence(text),
            self._perceived_control(text),
            self._certainty(text),
            self._responsibility(text),
            self._threat(text),
            self._loss(text),
            self._gain(text),
            self._novelty(text),
            self._fairness(text),
            self._social_significance(text),
            self._effort(text),
            self._reversibility(text),
        ]

        return [
            item
            for item in dimensions
            if item is not None
        ]

    # ------------------------------------------------------------------
    # Goal relevance
    # ------------------------------------------------------------------

    def _goal_relevance(
        self,
        text: str,
    ) -> AppraisalDimension:

        patterns = (
            "need to",
            "want to",
            "trying to",
            "goal",
            "important",
            "matters",
            "i need",
            "i want",
            "my plan",
            "my project",
            "my work",
            "deadline",
        )

        matches = self._matches(
            text,
            patterns,
        )

        value = self._score_matches(
            matches,
            base=0.15,
            increment=0.10,
            maximum=0.90,
        )

        return self._dimension(
            name="goal_relevance",
            value=value,
            interpretation=(
                "The situation may be relevant to a goal, "
                "priority, need, or desired outcome."
                if matches
                else
                "Goal relevance is not strongly established "
                "from the available information."
            ),
            matches=matches,
        )

    # ------------------------------------------------------------------
    # Goal congruence
    # ------------------------------------------------------------------

    def _goal_congruence(
        self,
        text: str,
    ) -> AppraisalDimension:

        positive = self._matches(
            text,
            (
                "working",
                "success",
                "successful",
                "fixed",
                "solved",
                "good",
                "great",
                "better",
                "improved",
                "progress",
                "achieved",
                "win",
            ),
        )

        negative = self._matches(
            text,
            (
                "failed",
                "failure",
                "broken",
                "blocked",
                "worse",
                "problem",
                "lost",
                "loss",
                "not working",
                "doesn't work",
                "can't",
                "cannot",
            ),
        )

        score = 0.0

        if positive:
            score += min(
                0.90,
                len(positive) * 0.15,
            )

        if negative:
            score -= min(
                0.90,
                len(negative) * 0.15,
            )

        score = max(
            -1.0,
            min(1.0, score),
        )

        matches = positive + negative

        return self._dimension(
            name="goal_congruence",
            value=score,
            interpretation=self._interpret_goal_congruence(
                score
            ),
            matches=matches,
        )

    @staticmethod
    def _interpret_goal_congruence(
        score: float,
    ) -> str:

        if score > 0.20:
            return (
                "The available language is compatible with "
                "a positive appraisal of progress or outcome."
            )

        if score < -0.20:
            return (
                "The available language is compatible with "
                "a negative appraisal of progress or outcome."
            )

        return (
            "Goal congruence is unclear or mixed."
        )

    # ------------------------------------------------------------------
    # Perceived control
    # ------------------------------------------------------------------

    def _perceived_control(
        self,
        text: str,
    ) -> AppraisalDimension:

        high_control = self._matches(
            text,
            (
                "i can",
                "i will",
                "i'll",
                "i can fix",
                "i can change",
                "i control",
                "my choice",
                "i decided",
            ),
        )

        low_control = self._matches(
            text,
            (
                "can't",
                "cannot",
                "nothing i can do",
                "out of my control",
                "no control",
                "stuck",
                "blocked",
                "depends on them",
                "depends on someone else",
            ),
        )

        score = 0.0

        score += min(
            0.90,
            len(high_control) * 0.18,
        )

        score -= min(
            0.90,
            len(low_control) * 0.18,
        )

        score = max(
            -1.0,
            min(1.0, score),
        )

        matches = high_control + low_control

        return self._dimension(
            name="perceived_control",
            value=score,
            interpretation=self._interpret_control(
                score
            ),
            matches=matches,
        )

    @staticmethod
    def _interpret_control(
        score: float,
    ) -> str:

        if score > 0.20:
            return (
                "The language suggests some perceived ability "
                "to influence the situation."
            )

        if score < -0.20:
            return (
                "The language suggests reduced or externally "
                constrained perceived control."
            )

        return (
            "Perceived control is uncertain."
        )

    # ------------------------------------------------------------------
    # Certainty
    # ------------------------------------------------------------------

    def _certainty(
        self,
        text: str,
    ) -> AppraisalDimension:

        certainty_patterns = self._matches(
            text,
            (
                "definitely",
                "certainly",
                "sure",
                "confirmed",
                "known",
                "obviously",
                "will happen",
            ),
        )

        uncertainty_patterns = self._matches(
            text,
            (
                "maybe",
                "perhaps",
                "possibly",
                "probably",
                "not sure",
                "uncertain",
                "i don't know",
                "what if",
                "could",
                "might",
                "unclear",
            ),
        )

        score = 0.0

        score += min(
            0.90,
            len(certainty_patterns) * 0.15,
        )

        score -= min(
            0.90,
            len(uncertainty_patterns) * 0.15,
        )

        score = max(
            -1.0,
            min(1.0, score),
        )

        return self._dimension(
            name="certainty",
            value=score,
            interpretation=(
                "The situation is described with relatively "
                "high certainty."
                if score > 0.20
                else
                "The situation contains meaningful uncertainty."
                if score < -0.20
                else
                "The available evidence does not establish "
                "a clear certainty level."
            ),
            matches=(
                certainty_patterns
                + uncertainty_patterns
            ),
        )

    # ------------------------------------------------------------------
    # Responsibility
    # ------------------------------------------------------------------

    def _responsibility(
        self,
        text: str,
    ) -> AppraisalDimension:

        self_patterns = self._matches(
            text,
            (
                "my fault",
                "i caused",
                "i did",
                "i made",
                "i should have",
                "i shouldn't have",
                "my mistake",
            ),
        )

        external_patterns = self._matches(
            text,
            (
                "their fault",
                "they caused",
                "they did",
                "the system",
                "the company",
                "the server",
                "someone else",
            ),
        )

        score = 0.0

        score += min(
            0.90,
            len(self_patterns) * 0.18,
        )

        score -= min(
            0.90,
            len(external_patterns) * 0.18,
        )

        return self._dimension(
            name="responsibility",
            value=max(
                -1.0,
                min(1.0, score),
            ),
            interpretation=(
                "Responsibility appears to be attributed "
                "toward the self."
                if score > 0.20
                else
                "Responsibility appears to be attributed "
                "toward external actors or circumstances."
                if score < -0.20
                else
                "Responsibility attribution is unclear."
            ),
            matches=(
                self_patterns
                + external_patterns
            ),
        )

    # ------------------------------------------------------------------
    # Threat
    # ------------------------------------------------------------------

    def _threat(
        self,
        text: str,
    ) -> AppraisalDimension:

        matches = self._matches(
            text,
            (
                "danger",
                "dangerous",
                "risk",
                "threat",
                "lose",
                "loss",
                "harm",
                "damage",
                "security",
                "unsafe",
                "problem",
                "failure",
                "fail",
                "deadline",
                "urgent",
            ),
        )

        value = self._score_matches(
            matches,
            base=0.10,
            increment=0.12,
            maximum=0.95,
        )

        return self._dimension(
            name="threat",
            value=value,
            interpretation=(
                "The situation contains language compatible "
                "with possible threat, risk, or negative consequence."
                if matches
                else
                "No strong threat signal was identified."
            ),
            matches=matches,
        )

    # ------------------------------------------------------------------
    # Loss
    # ------------------------------------------------------------------

    def _loss(
        self,
        text: str,
    ) -> AppraisalDimension:

        matches = self._matches(
            text,
            (
                "lost",
                "loss",
                "missed",
                "missing",
                "gone",
                "failed",
                "failure",
                "disappointed",
                "wasted",
                "cost me",
                "cost",
            ),
        )

        value = self._score_matches(
            matches,
            base=0.10,
            increment=0.12,
            maximum=0.90,
        )

        return self._dimension(
            name="loss",
            value=value,
            interpretation=(
                "The language is compatible with a possible "
                "loss or unwanted outcome."
                if matches
                else
                "No strong loss appraisal was identified."
            ),
            matches=matches,
        )

    # ------------------------------------------------------------------
    # Gain
    # ------------------------------------------------------------------

    def _gain(
        self,
        text: str,
    ) -> AppraisalDimension:

        matches = self._matches(
            text,
            (
                "gain",
                "gained",
                "success",
                "successful",
                "win",
                "won",
                "benefit",
                "improved",
                "better",
                "progress",
                "achieved",
                "opportunity",
                "reward",
            ),
        )

        value = self._score_matches(
            matches,
            base=0.10,
            increment=0.12,
            maximum=0.90,
        )

        return self._dimension(
            name="gain",
            value=value,
            interpretation=(
                "The language is compatible with a possible "
                "positive outcome, gain, or opportunity."
                if matches
                else
                "No strong gain appraisal was identified."
            ),
            matches=matches,
        )

    # ------------------------------------------------------------------
    # Novelty
    # ------------------------------------------------------------------

    def _novelty(
        self,
        text: str,
    ) -> AppraisalDimension:

        matches = self._matches(
            text,
            (
                "new",
                "first time",
                "never",
                "unfamiliar",
                "different",
                "unexpected",
                "surprise",
                "surprised",
                "new situation",
            ),
        )

        value = self._score_matches(
            matches,
            base=0.10,
            increment=0.12,
            maximum=0.90,
        )

        return self._dimension(
            name="novelty",
            value=value,
            interpretation=(
                "The situation contains indicators of novelty "
                "or unexpected change."
                if matches
                else
                "Novelty is not strongly established."
            ),
            matches=matches,
        )

    # ------------------------------------------------------------------
    # Fairness
    # ------------------------------------------------------------------

    def _fairness(
        self,
        text: str,
    ) -> AppraisalDimension:

        matches = self._matches(
            text,
            (
                "fair",
                "unfair",
                "fairness",
                "equal",
                "unequal",
                "deserve",
                "deserved",
                "rights",
                "treated badly",
                "treated unfairly",
            ),
        )

        value = self._score_matches(
            matches,
            base=0.10,
            increment=0.13,
            maximum=0.90,
        )

        return self._dimension(
            name="fairness",
            value=value,
            interpretation=(
                "Fairness or justice appears relevant "
                "to the situation."
                if matches
                else
                "Fairness is not explicitly established "
                "as a major appraisal dimension."
            ),
            matches=matches,
        )

    # ------------------------------------------------------------------
    # Social significance
    # ------------------------------------------------------------------

    def _social_significance(
        self,
        text: str,
    ) -> AppraisalDimension:

        matches = self._matches(
            text,
            (
                "friend",
                "family",
                "partner",
                "team",
                "boss",
                "manager",
                "customer",
                "client",
                "people",
                "everyone",
                "they think",
                "what will they think",
                "relationship",
                "reputation",
            ),
        )

        value = self._score_matches(
            matches,
            base=0.10,
            increment=0.11,
            maximum=0.90,
        )

        return self._dimension(
            name="social_significance",
            value=value,
            interpretation=(
                "The situation appears to contain a social "
                "or relational component."
                if matches
                else
                "No strong social component was identified."
            ),
            matches=matches,
        )

    # ------------------------------------------------------------------
    # Effort
    # ------------------------------------------------------------------

    def _effort(
        self,
        text: str,
    ) -> AppraisalDimension:

        matches = self._matches(
            text,
            (
                "hard",
                "difficult",
                "effort",
                "working hard",
                "long time",
                "spent hours",
                "took hours",
                "struggling",
                "trying",
                "kept trying",
            ),
        )

        value = self._score_matches(
            matches,
            base=0.10,
            increment=0.11,
            maximum=0.90,
        )

        return self._dimension(
            name="effort",
            value=value,
            interpretation=(
                "The situation appears to involve meaningful "
                "effort, difficulty, or persistence."
                if matches
                else
                "Effort level is not strongly established."
            ),
            matches=matches,
        )

    # ------------------------------------------------------------------
    # Reversibility
    # ------------------------------------------------------------------

    def _reversibility(
        self,
        text: str,
    ) -> AppraisalDimension:

        reversible = self._matches(
            text,
            (
                "can undo",
                "can reverse",
                "can change",
                "can fix",
                "temporary",
                "recover",
                "reversible",
            ),
        )

        irreversible = self._matches(
            text,
            (
                "permanent",
                "irreversible",
                "can't undo",
                "cannot undo",
                "too late",
                "gone forever",
                "cannot recover",
            ),
        )

        score = 0.0

        score += min(
            0.90,
            len(reversible) * 0.18,
        )

        score -= min(
            0.90,
            len(irreversible) * 0.18,
        )

        score = max(
            -1.0,
            min(1.0, score),
        )

        return self._dimension(
            name="reversibility",
            value=score,
            interpretation=(
                "The situation appears potentially reversible."
                if score > 0.20
                else
                "The situation may contain irreversible "
                "or difficult-to-reverse consequences."
                if score < -0.20
                else
                "Reversibility is uncertain."
            ),
            matches=(
                reversible
                + irreversible
            ),
        )

    # ------------------------------------------------------------------
    # Emotion implications
    # ------------------------------------------------------------------

    def _derive_emotional_implications(
        self,
        dimensions: Sequence[AppraisalDimension],
    ) -> List[EmotionalSignal]:

        lookup = {
            item.name: item
            for item in dimensions
        }

        results: List[EmotionalSignal] = []

        threat = self._value(
            lookup,
            "threat",
        )

        loss = self._value(
            lookup,
            "loss",
        )

        gain = self._value(
            lookup,
            "gain",
        )

        control = self._value(
            lookup,
            "perceived_control",
        )

        certainty = self._value(
            lookup,
            "certainty",
        )

        novelty = self._value(
            lookup,
            "novelty",
        )

        goal_congruence = self._value(
            lookup,
            "goal_congruence",
        )

        if threat > 0.45:
            results.append(
                self._emotion(
                    EmotionalSignalType.CONCERN,
                    intensity=threat,
                    confidence=0.45,
                )
            )

        if loss > 0.45:
            results.append(
                self._emotion(
                    EmotionalSignalType.SADNESS,
                    intensity=loss,
                    confidence=0.40,
                )
            )

        if gain > 0.45 and goal_congruence > 0.20:
            results.append(
                self._emotion(
                    EmotionalSignalType.EXCITEMENT,
                    intensity=min(
                        1.0,
                        gain,
                    ),
                    confidence=0.40,
                )
            )

        if (
            novelty > 0.45
            and certainty < -0.20
        ):
            results.append(
                self._emotion(
                    EmotionalSignalType.CURIOSITY,
                    intensity=novelty,
                    confidence=0.35,
                )
            )

        if (
            threat > 0.45
            and control < -0.20
        ):
            results.append(
                self._emotion(
                    EmotionalSignalType.URGENCY,
                    intensity=threat,
                    confidence=0.35,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Interpretation
    # ------------------------------------------------------------------

    @staticmethod
    def _build_primary_interpretation(
        dimensions: Sequence[AppraisalDimension],
    ) -> str:

        if not dimensions:
            return (
                "Insufficient information to construct a meaningful appraisal."
            )

        relevant = [
            item
            for item in dimensions
            if abs(item.value) >= 0.35
        ]

        if not relevant:
            return (
                "No single appraisal dimension is strongly dominant."
            )

        relevant.sort(
            key=lambda item: abs(item.value),
            reverse=True,
        )

        descriptions = [
            item.name.replace(
                "_",
                " ",
            )
            for item in relevant[:3]
        ]

        return (
            "The available information is most compatible with "
            + ", ".join(descriptions)
            + " being relevant to the situation."
        )

    @staticmethod
    def _build_alternative_interpretations(
        dimensions: Sequence[AppraisalDimension],
    ) -> List[str]:

        alternatives = [
            "The same observable event may be appraised differently depending on personal goals and prior experience.",
            "The detected appraisal may reflect communication framing rather than the person's actual internal evaluation.",
            "Missing contextual information may materially change the appraisal.",
        ]

        if any(
            item.name == "perceived_control"
            and item.value < -0.35
            for item in dimensions
        ):
            alternatives.append(
                "Reduced perceived control may reflect an external constraint rather than an emotional state."
            )

        if any(
            item.name == "threat"
            and item.value > 0.45
            for item in dimensions
        ):
            alternatives.append(
                "Risk language may represent rational risk assessment rather than fear."
            )

        return alternatives

    # ------------------------------------------------------------------
    # Uncertainty
    # ------------------------------------------------------------------

    @staticmethod
    def _build_uncertainty(
        dimensions: Sequence[AppraisalDimension],
        text: str,
    ) -> List[str]:

        uncertainty: List[str] = []

        if not text:
            uncertainty.append(
                "No textual situation description was available."
            )

        if not dimensions:
            uncertainty.append(
                "No appraisal dimensions could be evaluated."
            )

        if not any(
            abs(item.value) >= 0.30
            for item in dimensions
        ):
            uncertainty.append(
                "No appraisal dimension has strong supporting evidence."
            )

        uncertainty.extend(
            [
                "Appraisal depends on goals, context, beliefs, and prior experience that may not be observable.",
                "The model cannot directly observe the person's internal interpretation.",
            ]
        )

        return uncertainty

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        dimensions: Sequence[AppraisalDimension],
        uncertainty: Sequence[str],
    ) -> float:

        if not dimensions:
            return 0.0

        scores = [
            item.confidence
            for item in dimensions
            if item.confidence > 0
        ]

        if not scores:
            return 0.0

        confidence = sum(scores) / len(scores)

        penalty = min(
            0.25,
            len(uncertainty) * 0.025,
        )

        return self._clamp(
            confidence - penalty
        )

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_evidence(
        dimensions: Sequence[AppraisalDimension],
    ) -> List[EvidenceReference]:

        result: List[EvidenceReference] = []
        seen = set()

        for dimension in dimensions:
            for evidence in dimension.evidence:

                key = (
                    getattr(
                        evidence,
                        "source",
                        "",
                    ),
                    getattr(
                        evidence,
                        "content",
                        "",
                    ),
                )

                if key in seen:
                    continue

                seen.add(key)
                result.append(evidence)

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _dimension(
        self,
        name: str,
        value: float,
        interpretation: str,
        matches: Sequence[str],
    ) -> AppraisalDimension:

        confidence = self._dimension_confidence(
            matches
        )

        evidence = [
            EvidenceReference(
                source=f"{self.ENGINE_NAME}:text",
                content=(
                    f"Textual indicator '{match}' "
                    f"supports consideration of "
                    f"appraisal dimension '{name}'."
                ),
                evidence_type=EvidenceStrength.MODERATE,
            )
            for match in matches
        ]

        uncertainty = [
            (
                f"Dimension '{name}' is inferred from "
                "observable communication rather than "
                "direct access to internal appraisal."
            )
        ]

        alternatives = [
            (
                "The same wording may have a different meaning "
                "under different personal or situational contexts."
            )
        ]

        return AppraisalDimension(
            name=name,
            value=self._clamp(
                value,
                minimum=-1.0,
                maximum=1.0,
            ),
            interpretation=interpretation,
            confidence=confidence,
            evidence=evidence,
            uncertainty=uncertainty,
            alternative_explanations=alternatives,
        )

    @staticmethod
    def _dimension_confidence(
        matches: Sequence[str],
    ) -> float:

        if not matches:
            return 0.15

        return min(
            0.85,
            0.30 + len(matches) * 0.08,
        )

    @staticmethod
    def _matches(
        text: str,
        patterns: Sequence[str],
    ) -> List[str]:

        return [
            pattern
            for pattern in patterns
            if pattern.lower() in text
        ]

    @staticmethod
    def _score_matches(
        matches: Sequence[str],
        base: float,
        increment: float,
        maximum: float,
    ) -> float:

        if not matches:
            return 0.0

        return min(
            maximum,
            base + (
                len(matches) * increment
            ),
        )

    @staticmethod
    def _value(
        lookup: Dict[str, AppraisalDimension],
        name: str,
    ) -> float:

        item = lookup.get(name)

        if item is None:
            return 0.0

        return item.value

    @staticmethod
    def _emotion(
        signal_type: EmotionalSignalType,
        intensity: float,
        confidence: float,
    ) -> EmotionalSignal:

        return EmotionalSignal(
            signal_type=signal_type,
            intensity=max(
                0.0,
                min(1.0, intensity),
            ),
            confidence=max(
                0.0,
                min(1.0, confidence),
            ),
            evidence=[],
        )

    @staticmethod
    def _normalize(
        text: Optional[str],
    ) -> str:

        if text is None:
            return ""

        return " ".join(
            str(text)
            .strip()
            .lower()
            .split()
        )

    @staticmethod
    def _clamp(
        value: float,
        minimum: float = 0.0,
        maximum: float = 1.0,
    ) -> float:

        try:
            value = float(value)
        except (
            TypeError,
            ValueError,
        ):
            return minimum

        return max(
            minimum,
            min(maximum, value),
        )


__all__ = [
    "AppraisalDimension",
    "EmotionalAppraisal",
    "EmotionalAppraisalEngine",
  ]
