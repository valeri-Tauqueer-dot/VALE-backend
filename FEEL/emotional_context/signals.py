"""
VALE FEELING Brain
Emotional Signal Detection

Purpose:
    Detect possible emotional signals from observable input.

Epistemic rule:
    Observable language/context -> possible emotional signal.

    It must NOT become:
    observable language/context -> guaranteed internal emotion.

The detector therefore returns:
    - signal type
    - intensity estimate
    - confidence
    - evidence
    - alternative explanations
    - uncertainty

This module does not diagnose mental-health conditions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from FEEL.core.models import (
    EmotionalSignal,
    EmotionalSignalType,
    EvidenceReference,
    EvidenceStrength,
)


@dataclass
class DetectedEmotionalSignal:
    """
    Structured result for one possible emotional signal.
    """

    signal_type: EmotionalSignalType
    intensity: float = 0.0
    confidence: float = 0.0

    evidence: List[EvidenceReference] = field(
        default_factory=list
    )

    textual_indicators: List[str] = field(
        default_factory=list
    )

    alternative_explanations: List[str] = field(
        default_factory=list
    )

    uncertainty: List[str] = field(
        default_factory=list
    )

    source: str = "communication_input"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_type": (
                self.signal_type.value
                if hasattr(self.signal_type, "value")
                else str(self.signal_type)
            ),
            "intensity": self.intensity,
            "confidence": self.confidence,
            "evidence": [
                item.to_dict()
                if hasattr(item, "to_dict")
                else item
                for item in self.evidence
            ],
            "textual_indicators": list(
                self.textual_indicators
            ),
            "alternative_explanations": list(
                self.alternative_explanations
            ),
            "uncertainty": list(self.uncertainty),
            "source": self.source,
        }


class EmotionalSignalDetector:
    """
    Detects possible emotional signals from text and context.

    This is deliberately a signal detector, not a mind-reading engine.

    Supported broad signal categories include:
        - frustration
        - concern
        - excitement
        - calm
        - sadness
        - anger
        - confusion
        - urgency
        - disappointment
        - curiosity
        - relief
        - enthusiasm

    A detected signal means:

        "The available evidence is compatible with this
         emotional state."

    It does NOT mean:

        "The person definitely feels this emotion."
    """

    VERSION = "0.1.0"
    DETECTOR_NAME = "emotional_signal_detector"

    # ------------------------------------------------------------------
    # Signal vocabulary
    # ------------------------------------------------------------------

    SIGNAL_PATTERNS: Dict[
        EmotionalSignalType,
        Tuple[str, ...],
    ] = {
        EmotionalSignalType.FRUSTRATION: (
            "frustrated",
            "frustrating",
            "annoying",
            "annoyed",
            "this isn't working",
            "not working",
            "doesn't work",
            "still doesn't work",
            "again",
            "why isn't",
            "why is this",
            "fed up",
            "tired of",
            "waste of time",
            "you keep",
            "keeps failing",
        ),

        EmotionalSignalType.CONCERN: (
            "worried",
            "worry",
            "concerned",
            "concern",
            "afraid",
            "fear",
            "scared",
            "nervous",
            "risk",
            "danger",
            "uncertain",
            "what if",
            "i'm not sure",
            "not sure",
        ),

        EmotionalSignalType.EXCITEMENT: (
            "excited",
            "exciting",
            "can't wait",
            "amazing",
            "awesome",
            "incredible",
            "finally",
            "yes!",
            "let's go",
        ),

        EmotionalSignalType.ANGER: (
            "angry",
            "mad",
            "furious",
            "rage",
            "ridiculous",
            "unacceptable",
            "hate this",
            "this is terrible",
        ),

        EmotionalSignalType.SADNESS: (
            "sad",
            "upset",
            "hurt",
            "disappointed",
            "disappointing",
            "heartbroken",
            "unhappy",
            "lost",
        ),

        EmotionalSignalType.CONFUSION: (
            "confused",
            "confusing",
            "i don't understand",
            "don't understand",
            "what does this mean",
            "what do you mean",
            "i'm lost",
            "unclear",
            "not clear",
        ),

        EmotionalSignalType.URGENCY: (
            "urgent",
            "urgently",
            "asap",
            "right now",
            "immediately",
            "quickly",
            "hurry",
            "need this now",
            "deadline",
        ),

        EmotionalSignalType.CURIOSITY: (
            "curious",
            "wonder",
            "wondering",
            "how does",
            "why does",
            "why is",
            "what if",
            "tell me",
            "i want to know",
            "interested",
        ),

        EmotionalSignalType.RELIEF: (
            "relieved",
            "thank god",
            "finally fixed",
            "glad",
            "good to know",
            "that's a relief",
            "relief",
        ),

        EmotionalSignalType.ENTHUSIASM: (
            "love this",
            "love it",
            "great idea",
            "brilliant",
            "perfect",
            "let's do it",
            "i'm in",
            "sounds great",
        ),

        EmotionalSignalType.CALM: (
            "calm",
            "fine",
            "okay",
            "no problem",
            "all good",
            "i'm comfortable",
            "comfortable",
            "no worries",
        ),
    }

    # Signals where intensity may increase with punctuation/repetition.
    HIGH_INTENSITY_MARKERS = (
        "!!!",
        "???",
        "!!!!",
        "????",
        "wtf",
        "omg",
        "again again",
    )

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(
        self,
        minimum_confidence: float = 0.25,
        maximum_signals: int = 8,
    ) -> None:

        self.minimum_confidence = self._clamp(
            minimum_confidence
        )

        self.maximum_signals = max(
            1,
            int(maximum_signals),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(
        self,
        text: str,
        context: Optional[Any] = None,
    ) -> List[DetectedEmotionalSignal]:
        """
        Detect possible emotional signals from text.

        Args:
            text:
                Observable communication text.

            context:
                Optional broader context. It is used only as
                supporting information and never treated as
                direct access to internal emotion.
        """

        normalized = self._normalize(text)

        if not normalized:
            return []

        results: List[DetectedEmotionalSignal] = []

        for signal_type, patterns in self.SIGNAL_PATTERNS.items():

            matched_patterns = self._find_matches(
                normalized,
                patterns,
            )

            if not matched_patterns:
                continue

            intensity = self._estimate_intensity(
                normalized,
                matched_patterns,
            )

            confidence = self._estimate_confidence(
                normalized,
                matched_patterns,
                context,
            )

            if confidence < self.minimum_confidence:
                continue

            alternatives = self._alternative_explanations(
                signal_type,
                matched_patterns,
            )

            uncertainty = self._uncertainty_notes(
                signal_type,
                normalized,
                matched_patterns,
            )

            evidence = self._build_evidence(
                signal_type,
                matched_patterns,
                normalized,
            )

            results.append(
                DetectedEmotionalSignal(
                    signal_type=signal_type,
                    intensity=intensity,
                    confidence=confidence,
                    evidence=evidence,
                    textual_indicators=matched_patterns,
                    alternative_explanations=alternatives,
                    uncertainty=uncertainty,
                )
            )

        results.sort(
            key=lambda item: (
                item.confidence * item.intensity
            ),
            reverse=True,
        )

        return results[: self.maximum_signals]

    def detect_as_models(
        self,
        text: str,
        context: Optional[Any] = None,
    ) -> List[EmotionalSignal]:
        """
        Convert detector results into the shared FEELING
        EmotionalSignal model.

        This keeps the detector compatible with the central
        FEELING data model.
        """

        detected = self.detect(
            text=text,
            context=context,
        )

        models: List[EmotionalSignal] = []

        for item in detected:

            try:
                model = EmotionalSignal(
                    signal_type=item.signal_type,
                    intensity=item.intensity,
                    confidence=item.confidence,
                    evidence=item.evidence,
                )

            except TypeError:
                # Defensive compatibility path in case the
                # central model evolves while this subsystem
                # remains independently usable.
                model = self._build_compatible_model(
                    item
                )

            models.append(model)

        return models

    def analyze(
        self,
        text: str,
        context: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Return a complete detector-level analysis.
        """

        signals = self.detect(
            text=text,
            context=context,
        )

        return {
            "detector": self.DETECTOR_NAME,
            "version": self.VERSION,
            "signals": [
                item.to_dict()
                for item in signals
            ],
            "signal_count": len(signals),
            "epistemic_boundary": (
                "Signals represent evidence-supported possibilities, "
                "not confirmed internal emotional states."
            ),
        }

    # ------------------------------------------------------------------
    # Pattern matching
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(text: Optional[str]) -> str:

        if text is None:
            return ""

        value = str(text).strip().lower()

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value

    @staticmethod
    def _find_matches(
        text: str,
        patterns: Sequence[str],
    ) -> List[str]:

        matches: List[str] = []

        for pattern in patterns:

            normalized_pattern = pattern.lower().strip()

            if not normalized_pattern:
                continue

            if normalized_pattern in text:
                matches.append(
                    normalized_pattern
                )

        return matches

    # ------------------------------------------------------------------
    # Intensity and confidence
    # ------------------------------------------------------------------

    def _estimate_intensity(
        self,
        text: str,
        matches: Sequence[str],
    ) -> float:

        if not matches:
            return 0.0

        base = min(
            0.8,
            0.30 + (len(matches) * 0.10),
        )

        marker_bonus = 0.0

        for marker in self.HIGH_INTENSITY_MARKERS:
            if marker in text:
                marker_bonus += 0.05

        uppercase_ratio = self._uppercase_ratio(text)

        if uppercase_ratio > 0.30:
            marker_bonus += 0.08

        return self._clamp(
            base + marker_bonus
        )

    def _estimate_confidence(
        self,
        text: str,
        matches: Sequence[str],
        context: Optional[Any],
    ) -> float:

        if not matches:
            return 0.0

        confidence = 0.30

        # Multiple independent textual indicators increase
        # evidence strength, but never make the inference certain.
        confidence += min(
            0.30,
            len(matches) * 0.08,
        )

        # Longer expressions provide more contextual evidence.
        if len(text.split()) >= 12:
            confidence += 0.08

        # Explicit first-person emotional language is somewhat
        # stronger evidence than generic wording.
        if self._contains_first_person_signal(
            text,
            matches,
        ):
            confidence += 0.15

        # Context can increase evidence if it contains relevant
        # information, but it does not provide certainty.
        if context is not None:
            confidence += 0.05

        return min(
            0.90,
            confidence,
        )

    @staticmethod
    def _contains_first_person_signal(
        text: str,
        matches: Sequence[str],
    ) -> bool:

        first_person = (
            "i ",
            "i'm ",
            "i am ",
            "i feel ",
            "i'm feeling ",
            "i was ",
            "i've ",
        )

        has_first_person = any(
            marker in text
            for marker in first_person
        )

        if not has_first_person:
            return False

        return any(
            match in text
            for match in matches
        )

    @staticmethod
    def _uppercase_ratio(text: str) -> float:

        letters = [
            char
            for char in text
            if char.isalpha()
        ]

        if not letters:
            return 0.0

        uppercase = sum(
            char.isupper()
            for char in letters
        )

        return uppercase / len(letters)

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    def _build_evidence(
        self,
        signal_type: EmotionalSignalType,
        matches: Sequence[str],
        source_text: str,
    ) -> List[EvidenceReference]:

        evidence: List[EvidenceReference] = []

        signal_name = (
            signal_type.value
            if hasattr(signal_type, "value")
            else str(signal_type)
        )

        for match in matches:

            evidence.append(
                EvidenceReference(
                    source=(
                        f"{self.DETECTOR_NAME}:text"
                    ),
                    content=(
                        f"Textual indicator '{match}' "
                        f"is compatible with possible "
                        f"{signal_name}."
                    ),
                    evidence_type=(
                        EvidenceStrength.MODERATE
                    ),
                )
            )

        return evidence

    # ------------------------------------------------------------------
    # Alternative explanations
    # ------------------------------------------------------------------

    @staticmethod
    def _alternative_explanations(
        signal_type: EmotionalSignalType,
        matches: Sequence[str],
    ) -> List[str]:

        signal = (
            signal_type.value
            if hasattr(signal_type, "value")
            else str(signal_type)
        )

        alternatives: List[str] = [
            "The wording may reflect communication style rather than emotion.",
            "The signal may be situational rather than a persistent emotional state.",
        ]

        if signal == "frustration":
            alternatives.append(
                "Repeated wording may reflect emphasis or a technical failure."
            )

        elif signal == "concern":
            alternatives.append(
                "Risk language may reflect rational caution rather than fear."
            )

        elif signal == "excitement":
            alternatives.append(
                "Positive language may reflect politeness or enthusiasm about an idea rather than strong emotion."
            )

        elif signal == "anger":
            alternatives.append(
                "Strong wording may be rhetorical emphasis rather than anger."
            )

        elif signal == "confusion":
            alternatives.append(
                "A request for clarification does not necessarily indicate emotional distress."
            )

        elif signal == "urgency":
            alternatives.append(
                "Urgency may be caused by an external deadline rather than emotional pressure."
            )

        elif signal == "curiosity":
            alternatives.append(
                "Questioning may simply reflect information-seeking behavior."
            )

        return alternatives

    # ------------------------------------------------------------------
    # Uncertainty
    # ------------------------------------------------------------------

    @staticmethod
    def _uncertainty_notes(
        signal_type: EmotionalSignalType,
        text: str,
        matches: Sequence[str],
    ) -> List[str]:

        notes = [
            "Internal emotional state is not directly observable.",
            "The detected signal is inferred from available communication evidence.",
        ]

        if len(matches) == 1:
            notes.append(
                "Only one primary textual indicator was detected."
            )

        if "?" in text:
            notes.append(
                "Questioning language can have multiple interpretations."
            )

        if "!" in text:
            notes.append(
                "Exclamation marks may indicate emphasis rather than emotion."
            )

        return notes

    # ------------------------------------------------------------------
    # Compatibility
    # ------------------------------------------------------------------

    @staticmethod
    def _build_compatible_model(
        item: DetectedEmotionalSignal,
    ) -> EmotionalSignal:

        """
        Defensive fallback for small schema changes in the
        central EmotionalSignal model.
        """

        model = EmotionalSignal()

        if hasattr(model, "signal_type"):
            model.signal_type = item.signal_type

        if hasattr(model, "intensity"):
            model.intensity = item.intensity

        if hasattr(model, "confidence"):
            model.confidence = item.confidence

        if hasattr(model, "evidence"):
            model.evidence = item.evidence

        return model

     # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp(
        value: float,
        minimum: float = 0.0,
        maximum: float = 1.0,
    ) -> float:

        try:
            value = float(value)
        except (TypeError, ValueError):
            return minimum

        return max(
            minimum,
            min(maximum, value),
        )


__all__ = [
    "DetectedEmotionalSignal",
    "EmotionalSignalDetector",
      ]
