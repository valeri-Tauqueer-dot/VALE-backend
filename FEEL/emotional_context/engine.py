"""
VALE FEELINGS Brain
Emotional Context Engine

File:
    FEEL/emotional_context/engine.py

Purpose:
    Integrate emotional signal detection, cognitive appraisal, and
    emotional-state tracking into one coherent FEELING subsystem.

Important epistemic boundary:
    FEELING does not directly observe another person's internal emotions.
    Emotional states produced here are computational inferences based on
    available language/contextual evidence.

    FACT != INFERENCE != HYPOTHESIS != IMAGINATION

This engine therefore:
    - detects possible emotional signals
    - evaluates contextual/appraisal factors
    - maintains a bounded emotional-state model
    - records evidence and uncertainty
    - identifies alternative explanations
    - avoids claiming mind-reading
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from FEEL.core.contracts import CognitiveContext, EngineResult
from FEEL.core.models import (
    EmotionalSignal,
    EvidenceReference,
    EpistemicClaim,
    EpistemicType,
)

from .appraisal import (
    EmotionalAppraisal,
    EmotionalAppraisalEngine,
)
from .signals import (
    DetectedEmotionalSignal,
    EmotionalSignalDetector,
)
from .state import (
    EmotionalStateModel,
    EmotionalStateSnapshot,
)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _unique(values: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []

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
# Result model
# ---------------------------------------------------------------------------

@dataclass
class EmotionalContextAssessment:
    """
    Unified output of the Emotional Context Engine.

    This is an interpretation model, not a claim about a person's literal
    internal emotional state.
    """

    detected_signals: List[DetectedEmotionalSignal] = field(default_factory=list)

    emotional_signals: List[EmotionalSignal] = field(default_factory=list)

    appraisal: Optional[EmotionalAppraisal] = None

    state_snapshot: Optional[EmotionalStateSnapshot] = None

    dominant_possible_state: Optional[str] = None

    possible_states: List[str] = field(default_factory=list)

    emotional_intensity: float = 0.0

    confidence: float = 0.0

    evidence: List[EvidenceReference] = field(default_factory=list)

    uncertainties: List[str] = field(default_factory=list)

    alternative_explanations: List[str] = field(default_factory=list)

    epistemic_claims: List[EpistemicClaim] = field(default_factory=list)

    reasoning_notes: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class EmotionalContextEngine:
    """
    Main FEELING Emotional Context Engine.

    Processing model:

        INPUT
          ↓
        SIGNAL DETECTION
          ↓
        CONTEXTUAL APPRAISAL
          ↓
        EMOTIONAL STATE UPDATE
          ↓
        CONFIDENCE / UNCERTAINTY
          ↓
        ALTERNATIVE EXPLANATIONS
          ↓
        EPISTEMIC OUTPUT

    The engine does not diagnose psychological conditions and does not
    claim direct access to a person's internal emotional state.
    """

    ENGINE_NAME = "emotional_context"
    VERSION = "0.1.0"

    def __init__(
        self,
        signal_detector: Optional[EmotionalSignalDetector] = None,
        appraisal_engine: Optional[EmotionalAppraisalEngine] = None,
        state_model: Optional[EmotionalStateModel] = None,
    ) -> None:
        self.signal_detector = (
            signal_detector
            if signal_detector is not None
            else EmotionalSignalDetector()
        )

        self.appraisal_engine = (
            appraisal_engine
            if appraisal_engine is not None
            else EmotionalAppraisalEngine()
        )

        self.state_model = (
            state_model
            if state_model is not None
            else EmotionalStateModel()
        )

        self.last_assessment: Optional[EmotionalContextAssessment] = None

    # ------------------------------------------------------------------
    # Input normalization
    # ------------------------------------------------------------------

    def _extract_text(self, context: Any) -> str:
        """
        Extract usable text from supported context structures.
        """

        if context is None:
            return ""

        if isinstance(context, str):
            return context.strip()

        if isinstance(context, Mapping):
            candidates = [
                context.get("text"),
                context.get("message"),
                context.get("user_message"),
                context.get("content"),
                context.get("query"),
                context.get("situation"),
            ]

            parts = [_safe_text(item) for item in candidates if item]

            if parts:
                return " ".join(parts)

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
                value = _safe_text(getattr(context, attribute))

                if value:
                    return value

        return ""

    def _extract_context_mapping(self, context: Any) -> Dict[str, Any]:
        """
        Convert a supported CognitiveContext-like object into a simple
        dictionary for subsystem consumption.
        """

        if context is None:
            return {}

        if isinstance(context, Mapping):
            return dict(context)

        try:
            return asdict(context)
        except (TypeError, ValueError):
            pass

        result: Dict[str, Any] = {}

        for attribute in (
            "text",
            "message",
            "user_message",
            "content",
            "query",
            "situation",
            "goal",
            "constraints",
            "metadata",
        ):
            if hasattr(context, attribute):
                result[attribute] = getattr(context, attribute)

        return result

    # ------------------------------------------------------------------
    # Signal conversion
    # ------------------------------------------------------------------

    def _convert_detected_signal(
        self,
        signal: DetectedEmotionalSignal,
    ) -> EmotionalSignal:
        """
        Convert detector-level output into the shared FEELING model.
        """

        signal_type = getattr(signal, "signal_type", None)

        if signal_type is None:
            signal_type = getattr(signal, "category", "unknown")

        intensity = _clamp(
            getattr(signal, "intensity", 0.0)
        )

        confidence = _clamp(
            getattr(signal, "confidence", 0.0)
        )

        evidence_value = getattr(signal, "evidence", None)

        evidence_text = ""

        if isinstance(evidence_value, Sequence) and not isinstance(
            evidence_value, (str, bytes)
        ):
            evidence_text = "; ".join(
                _safe_text(item) for item in evidence_value if item
            )
        else:
            evidence_text = _safe_text(evidence_value)

        return EmotionalSignal(
            signal_type=signal_type,
            intensity=intensity,
            confidence=confidence,
            evidence=evidence_text,
        )

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    def _build_evidence(
        self,
        text: str,
        detected_signals: Sequence[DetectedEmotionalSignal],
    ) -> List[EvidenceReference]:
        """
        Build evidence references for emotional interpretation.

        Evidence describes observable input, not a person's hidden state.
        """

        evidence: List[EvidenceReference] = []

        if text:
            evidence.append(
                EvidenceReference(
                    source="conversation_input",
                    evidence_type="observed_text",
                    content=text[:1000],
                    strength=0.65,
                )
            )

        for signal in detected_signals:
            signal_type = _safe_text(
                getattr(signal, "signal_type", None)
                or getattr(signal, "category", None)
            )

            signal_evidence = getattr(signal, "evidence", None)

            if isinstance(signal_evidence, Sequence) and not isinstance(
                signal_evidence, (str, bytes)
            ):
                signal_evidence = "; ".join(
                    _safe_text(item)
                    for item in signal_evidence
                    if item
                )

            signal_evidence = _safe_text(signal_evidence)

            if signal_type or signal_evidence:
                evidence.append(
                    EvidenceReference(
                        source="emotional_signal_detector",
                        evidence_type="detected_signal",
                        content=(
                            f"Possible signal: {signal_type}. "
                            f"Observed evidence: {signal_evidence}"
                        ),
                        strength=_clamp(
                            getattr(signal, "confidence", 0.0)
                        ),
                    )
                )

        return evidence

    # ------------------------------------------------------------------
    # Uncertainty
    # ------------------------------------------------------------------

    def _build_uncertainties(
        self,
        text: str,
        detected_signals: Sequence[DetectedEmotionalSignal],
        confidence: float,
    ) -> List[str]:
        uncertainties: List[str] = []

        if not text:
            uncertainties.append(
                "No meaningful conversational text was available."
            )

        if not detected_signals:
            uncertainties.append(
                "No strong emotional signals were detected."
            )

        if confidence < 0.4:
            uncertainties.append(
                "Emotional interpretation has low confidence."
            )
        elif confidence < 0.7:
            uncertainties.append(
                "Emotional interpretation has moderate uncertainty."
            )

        uncertainties.extend(
            [
                "Emotional signals may have explanations unrelated to "
                "the inferred emotional state.",
                "Text alone does not provide direct access to internal "
                "emotional experience.",
            ]
        )

        return _unique(uncertainties)

    # ------------------------------------------------------------------
    # Alternative explanations
    # ------------------------------------------------------------------

    def _build_alternative_explanations(
        self,
        detected_signals: Sequence[DetectedEmotionalSignal],
    ) -> List[str]:
        alternatives: List[str] = []

        signal_names = {
            _safe_text(
                getattr(signal, "signal_type", None)
                or getattr(signal, "category", None)
            ).casefold()
            for signal in detected_signals
        }

        if "frustration" in signal_names:
            alternatives.extend(
                [
                    "The wording may reflect a request for correction "
                    "rather than emotional frustration.",
                    "Repeated wording may result from communication "
                    "difficulty rather than frustration.",
                ]
            )

        if "urgency" in signal_names:
            alternatives.append(
                "Urgent wording may reflect a genuine deadline rather "
                "than heightened emotional arousal."
            )

        if "anger" in signal_names:
            alternatives.append(
                "Strong wording may reflect emphasis, communication "
                "style, or disagreement rather than anger."
            )

        if "sadness" in signal_names:
            alternatives.append(
                "Negative wording may describe an external situation "
                "without indicating the speaker's current emotional state."
            )

        if "excitement" in signal_names or "enthusiasm" in signal_names:
            alternatives.append(
                "Positive or energetic wording may reflect writing style "
                "rather than elevated emotional intensity."
            )

        if "confusion" in signal_names:
            alternatives.append(
                "A question may represent information seeking rather "
                "than confusion."
            )

        if "curiosity" in signal_names:
            alternatives.append(
                "Questioning behavior may be task-driven rather than "
                "emotionally motivated."
            )

        if not alternatives:
            alternatives.append(
                "The available signals may have multiple contextual "
                "interpretations."
            )

        return _unique(alternatives)

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        detected_signals: Sequence[DetectedEmotionalSignal],
        appraisal: Optional[EmotionalAppraisal],
        state_snapshot: Optional[EmotionalStateSnapshot],
    ) -> float:
        """
        Calculate confidence in the interpretation.

        This is confidence in the MODEL OUTPUT, not confidence that the
        inferred emotion is objectively true.
        """

        signal_confidences = [
            _clamp(getattr(signal, "confidence", 0.0))
            for signal in detected_signals
        ]

        signal_confidence = (
            sum(signal_confidences) / len(signal_confidences)
            if signal_confidences
            else 0.0
        )

        appraisal_confidence = 0.0

        if appraisal is not None:
            appraisal_confidence = _clamp(
                getattr(appraisal, "confidence", 0.0)
            )

        state_confidence = 0.0

        if state_snapshot is not None:
            state_confidence = _clamp(
                getattr(state_snapshot, "overall_confidence", 0.0)
            )

        components = [
            value
            for value in (
                signal_confidence,
                appraisal_confidence,
                state_confidence,
            )
            if value > 0.0
        ]

        if not components:
            return 0.0

        return _clamp(sum(components) / len(components))

    # ------------------------------------------------------------------
    # Epistemic claims
    # ------------------------------------------------------------------

    def _build_epistemic_claims(
        self,
        detected_signals: Sequence[DetectedEmotionalSignal],
        dominant_state: Optional[str],
        confidence: float,
    ) -> List[EpistemicClaim]:
        claims: List[EpistemicClaim] = []

        if detected_signals:
            claims.append(
                EpistemicClaim(
                    statement=(
                        "The input contains observable linguistic signals "
                        "that may correspond to emotional states."
                    ),
                    epistemic_type=EpistemicType.INFERENCE,
                    confidence=_clamp(confidence),
                    evidence=[
                        "conversation input",
                        "emotional signal detection",
                    ],
                )
            )

        if dominant_state:
            claims.append(
                EpistemicClaim(
                    statement=(
                        f"'{dominant_state}' is the currently modeled "
                        "possible dominant emotional state."
                    ),
                    epistemic_type=EpistemicType.HYPOTHESIS,
                    confidence=_clamp(confidence),
                    evidence=[
                        "detected emotional signals",
                        "contextual appraisal",
                        "state model",
                    ],
                )
            )

        claims.append(
            EpistemicClaim(
                statement=(
                    "The modeled emotional state is not direct evidence "
                    "of a person's internal subjective experience."
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
    # Main analysis
    # ------------------------------------------------------------------

    def analyze(
        self,
        context: Any,
        *,
        reset_state: bool = False,
    ) -> EmotionalContextAssessment:
        """
        Analyze emotional context.

        Parameters:
            context:
                CognitiveContext, mapping, string, or compatible object.

            reset_state:
                If True, clear the persistent emotional state model before
                processing this input.

        Returns:
            EmotionalContextAssessment
        """

        if reset_state:
            self.state_model.reset()

        text = self._extract_text(context)
        context_mapping = self._extract_context_mapping(context)

        # --------------------------------------------------------------
        # 1. Detect possible emotional signals
        # --------------------------------------------------------------

        detected_signals: List[DetectedEmotionalSignal] = []

        if text:
            detected_signals = list(
                self.signal_detector.detect(text)
            )

        emotional_signals = [
            self._convert_detected_signal(signal)
            for signal in detected_signals
        ]

        # --------------------------------------------------------------
        # 2. Evaluate cognitive/contextual appraisal
        # --------------------------------------------------------------

        appraisal: Optional[EmotionalAppraisal] = None

        try:
            appraisal = self.appraisal_engine.evaluate(
                text=text,
                context=context_mapping,
                signals=detected_signals,
            )
        except TypeError:
            # Compatibility fallback for a simpler appraisal engine
            # signature.
            try:
                appraisal = self.appraisal_engine.analyze(
                    text=text,
                    context=context_mapping,
                )
            except (AttributeError, TypeError):
                appraisal = None

        # --------------------------------------------------------------
        # 3. Update emotional state model
        # --------------------------------------------------------------

        state_snapshot: Optional[EmotionalStateSnapshot] = None

        try:
            state_snapshot = self.state_model.update(
                detected_signals=detected_signals,
                appraisal=appraisal,
                evidence=self._build_evidence(
                    text,
                    detected_signals,
                ),
            )
        except TypeError:
            # Compatibility path for state-model implementations that
            # accept only the signal collection.
            try:
                state_snapshot = self.state_model.update(
                    detected_signals
                )
            except TypeError:
                state_snapshot = self.state_model.update(
                    signals=detected_signals
                )

        # --------------------------------------------------------------
        # 4. Determine current modeled states
        # --------------------------------------------------------------

        dominant_state: Optional[str] = None
        possible_states: List[str] = []

        if state_snapshot is not None:
            dominant_state = getattr(
                state_snapshot,
                "dominant_state",
                None,
            )

            active_states = getattr(
                state_snapshot,
                "active_states",
                None,
            )

            if active_states:
                possible_states.extend(
                    _safe_text(state)
                    for state in active_states
                    if _safe_text(state)
                )

        if not possible_states:
            possible_states.extend(
                _safe_text(
                    getattr(signal, "signal_type", None)
                    or getattr(signal, "category", None)
                )
                for signal in detected_signals
            )

        possible_states = _unique(possible_states)

        # --------------------------------------------------------------
        # 5. Calculate confidence
        # --------------------------------------------------------------

        confidence = self._calculate_confidence(
            detected_signals,
            appraisal,
            state_snapshot,
        )

        # --------------------------------------------------------------
        # 6. Determine emotional intensity
        # --------------------------------------------------------------

        intensities = [
            _clamp(
                getattr(signal, "intensity", 0.0)
            )
            for signal in detected_signals
        ]

        emotional_intensity = (
            max(intensities)
            if intensities
            else 0.0
        )

        # --------------------------------------------------------------
        # 7. Evidence / uncertainty / alternatives
        # --------------------------------------------------------------

        evidence = self._build_evidence(
            text,
            detected_signals,
        )

        uncertainties = self._build_uncertainties(
            text,
            detected_signals,
            confidence,
        )

        alternative_explanations = (
            self._build_alternative_explanations(
                detected_signals
            )
        )

        # --------------------------------------------------------------
        # 8. Reasoning trace
        # --------------------------------------------------------------

        reasoning_notes = [
            "Processed observable conversational/contextual input.",
            "Detected possible emotional linguistic signals.",
            "Evaluated contextual/appraisal dimensions where available.",
            "Updated the bounded emotional-state model.",
            "Represented emotional conclusions as inferences or hypotheses.",
            "Maintained uncertainty and alternative explanations.",
            "Did not assume direct access to internal subjective experience.",
        ]

        # --------------------------------------------------------------
        # 9. Epistemic claims
        # --------------------------------------------------------------

        epistemic_claims = self._build_epistemic_claims(
            detected_signals,
            dominant_state,
            confidence,
        )

        # --------------------------------------------------------------
        # 10. Unified assessment
        # --------------------------------------------------------------

        assessment = EmotionalContextAssessment(
            detected_signals=detected_signals,
            emotional_signals=emotional_signals,
            appraisal=appraisal,
            state_snapshot=state_snapshot,
            dominant_possible_state=dominant_state,
            possible_states=possible_states,
            emotional_intensity=emotional_intensity,
            confidence=confidence,
            evidence=evidence,
            uncertainties=uncertainties,
            alternative_explanations=alternative_explanations,
            epistemic_claims=epistemic_claims,
            reasoning_notes=reasoning_notes,
            metadata={
                "engine": self.ENGINE_NAME,
                "version": self.VERSION,
                "input_available": bool(text),
                "signal_count": len(detected_signals),
                "state_model_updated": state_snapshot is not None,
                "epistemic_boundary": (
                    "possible emotional state inference; "
                    "not direct internal-state observation"
                ),
            },
        )

        self.last_assessment = assessment

        return assessment

    # ------------------------------------------------------------------
    # Engine contract
    # ------------------------------------------------------------------

    def run(
        self,
        context: Any,
        *,
        reset_state: bool = False,
    ) -> EngineResult:
        """
        Run the engine using the shared VALE EngineResult contract.
        """

        assessment = self.analyze(
            context,
            reset_state=reset_state,
        )

        return EngineResult(
            engine_name=self.ENGINE_NAME,
            success=True,
            confidence=assessment.confidence,
            output=assessment.to_dict(),
            evidence=assessment.evidence,
            uncertainties=assessment.uncertainties,
            metadata={
                "version": self.VERSION,
                "dominant_possible_state": (
                    assessment.dominant_possible_state
                ),
                "possible_states": assessment.possible_states,
                "emotional_intensity": (
                    assessment.emotional_intensity
                ),
            },
        )

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def detect_signals(
        self,
        text: str,
    ) -> List[DetectedEmotionalSignal]:
        """
        Detect possible emotional signals without updating persistent state.
        """

        text = _safe_text(text)

        if not text:
            return []

        return list(
            self.signal_detector.detect(text)
        )

    def current_state(
        self,
    ) -> Optional[EmotionalStateSnapshot]:
        """
        Return the current modeled emotional-state snapshot.
        """

        try:
            return self.state_model.snapshot()
        except AttributeError:
            return None

    def dominant_state(
        self,
    ) -> Optional[str]:
        """
        Return the currently modeled dominant possible state.
        """

        snapshot = self.current_state()

        if snapshot is None:
            return None

        return getattr(
            snapshot,
            "dominant_state",
            None,
        )

    def reset(self) -> None:
        """
        Reset transient/persistent emotional-context state.
        """

        self.state_model.reset()
        self.last_assessment = None

    def export_state(self) -> Dict[str, Any]:
        """
        Export the engine's current state for debugging, observability,
        persistence, or future Cognitive Fabric integration.
        """

        state_data: Dict[str, Any] = {}

        try:
            exported = self.state_model.export()

            if isinstance(exported, Mapping):
                state_data = dict(exported)
        except AttributeError:
            snapshot = self.current_state()

            if snapshot is not None:
                try:
                    state_data = asdict(snapshot)
                except TypeError:
                    state_data = {
                        "snapshot": str(snapshot)
                    }

        return {
            "engine": self.ENGINE_NAME,
            "version": self.VERSION,
            "state": state_data,
            "last_assessment": (
                self.last_assessment.to_dict()
                if self.last_assessment is not None
                else None
            ),
        }


__all__ = [
    "EmotionalContextAssessment",
    "EmotionalContextEngine",
                  ]
