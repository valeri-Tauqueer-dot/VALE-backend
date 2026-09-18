"""
VALE FEELING Brain
Emotional State Model

Purpose:
    Maintain a structured, uncertainty-aware representation of
    possible emotional state across observations.

Core model:

        OBSERVATION
             ↓
        SIGNALS
             ↓
        APPRAISAL
             ↓
        STATE UPDATE
             ↓
        STATE TRANSITION
             ↓
        NEW OBSERVATION
             ↺

Important:
    This is a computational model of possible emotional state.

    It does NOT:
        - read minds
        - claim certainty about internal emotion
        - diagnose mental-health conditions
        - treat inferred emotion as fact

Every state is therefore associated with:
    - confidence
    - evidence
    - uncertainty
    - alternative explanations
    - observation history
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

from FEEL.core.models import (
    EmotionalSignal,
    EmotionalSignalType,
    EvidenceReference,
)


def _utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    """Clamp a numeric value to a safe range."""

    try:
        value = float(value)
    except (TypeError, ValueError):
        return minimum

    return max(
        minimum,
        min(maximum, value),
    )


@dataclass
class EmotionalStateObservation:
    """
    One observation contributing to the current emotional model.
    """

    observation_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    timestamp: datetime = field(
        default_factory=_utc_now
    )

    signals: List[EmotionalSignal] = field(
        default_factory=list
    )

    source: str = "unknown"

    confidence: float = 0.0

    evidence: List[EvidenceReference] = field(
        default_factory=list
    )

    uncertainty: List[str] = field(
        default_factory=list
    )

    context_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "timestamp": self.timestamp.isoformat(),
            "signals": [
                signal.to_dict()
                if hasattr(signal, "to_dict")
                else signal
                for signal in self.signals
            ],
            "source": self.source,
            "confidence": self.confidence,
            "evidence": [
                item.to_dict()
                if hasattr(item, "to_dict")
                else item
                for item in self.evidence
            ],
            "uncertainty": list(self.uncertainty),
            "context_summary": self.context_summary,
        }


@dataclass
class EmotionalStateValue:
    """
    Current modeled value for one emotional category.
    """

    signal_type: EmotionalSignalType

    intensity: float = 0.0

    confidence: float = 0.0

    persistence: float = 0.0

    trend: float = 0.0

    observation_count: int = 0

    last_updated: datetime = field(
        default_factory=_utc_now
    )

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
            "signal_type": (
                self.signal_type.value
                if hasattr(
                    self.signal_type,
                    "value",
                )
                else str(self.signal_type)
            ),
            "intensity": self.intensity,
            "confidence": self.confidence,
            "persistence": self.persistence,
            "trend": self.trend,
            "observation_count": self.observation_count,
            "last_updated": self.last_updated.isoformat(),
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
class EmotionalStateTransition:
    """
    Records a change between modeled emotional states.
    """

    transition_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    timestamp: datetime = field(
        default_factory=_utc_now
    )

    from_signal: Optional[
        EmotionalSignalType
    ] = None

    to_signal: Optional[
        EmotionalSignalType
    ] = None

    previous_intensity: float = 0.0

    new_intensity: float = 0.0

    change: float = 0.0

    confidence: float = 0.0

    reason: str = ""

    uncertainty: List[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "timestamp": self.timestamp.isoformat(),
            "from_signal": (
                self.from_signal.value
                if hasattr(
                    self.from_signal,
                    "value",
                )
                else (
                    str(self.from_signal)
                    if self.from_signal is not None
                    else None
                )
            ),
            "to_signal": (
                self.to_signal.value
                if hasattr(
                    self.to_signal,
                    "value",
                )
                else (
                    str(self.to_signal)
                    if self.to_signal is not None
                    else None
                )
            ),
            "previous_intensity": self.previous_intensity,
            "new_intensity": self.new_intensity,
            "change": self.change,
            "confidence": self.confidence,
            "reason": self.reason,
            "uncertainty": list(self.uncertainty),
        }


@dataclass
class EmotionalStateSnapshot:
    """
    Immutable-style snapshot of the modeled emotional state.
    """

    snapshot_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    timestamp: datetime = field(
        default_factory=_utc_now
    )

    dominant_signal: Optional[
        EmotionalSignalType
    ] = None

    dominant_intensity: float = 0.0

    overall_confidence: float = 0.0

    states: Dict[
        str,
        EmotionalStateValue,
    ] = field(
        default_factory=dict
    )

    transitions: List[
        EmotionalStateTransition
    ] = field(
        default_factory=list
    )

    uncertainty: List[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "dominant_signal": (
                self.dominant_signal.value
                if hasattr(
                    self.dominant_signal,
                    "value",
                )
                else (
                    str(self.dominant_signal)
                    if self.dominant_signal is not None
                    else None
                )
            ),
            "dominant_intensity": self.dominant_intensity,
            "overall_confidence": self.overall_confidence,
            "states": {
                key: value.to_dict()
                for key, value in self.states.items()
            },
            "transitions": [
                item.to_dict()
                for item in self.transitions
            ],
            "uncertainty": list(self.uncertainty),
        }


class EmotionalStateModel:
    """
    Stateful model of possible emotional context.

    The model maintains:
        - current signal intensities
        - confidence
        - persistence
        - direction/trend
        - observation history
        - state transitions
        - uncertainty

    Example conceptual sequence:

        frustration 0.30
             ↓
        frustration 0.55
             ↓
        frustration 0.75
             ↓
        relief 0.40

    The model can therefore distinguish:
        "possible frustration detected"

    from:
        "frustration appears to be persisting or increasing."

    Neither statement is treated as certainty about the person's
    actual internal experience.
    """

    VERSION = "0.1.0"
    MODEL_NAME = "emotional_state_model"

    # How much a new observation affects the existing state.
    DEFAULT_UPDATE_RATE = 0.45

    # State below this value is treated as effectively inactive.
    ACTIVE_THRESHOLD = 0.15

    # A state transition requires a meaningful change.
    TRANSITION_THRESHOLD = 0.20

    def __init__(
        self,
        update_rate: float = DEFAULT_UPDATE_RATE,
        history_limit: int = 100,
    ) -> None:

        self.update_rate = _clamp(
            update_rate
        )

        self.history_limit = max(
            1,
            int(history_limit),
        )

        self._states: Dict[
            EmotionalSignalType,
            EmotionalStateValue,
        ] = {}

        self._observations: List[
            EmotionalStateObservation
        ] = []

        self._transitions: List[
            EmotionalStateTransition
        ] = []

        self._previous_dominant: Optional[
            EmotionalSignalType
        ] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        signals: Sequence[EmotionalSignal],
        source: str = "unknown",
        context_summary: str = "",
        evidence: Optional[
            Sequence[EvidenceReference]
        ] = None,
        uncertainty: Optional[
            Sequence[str]
        ] = None,
    ) -> EmotionalStateSnapshot:
        """
        Update the emotional state model using new signals.
        """

        signals = list(signals)

        observation = EmotionalStateObservation(
            signals=signals,
            source=source,
            confidence=self._observation_confidence(
                signals
            ),
            evidence=list(
                evidence or []
            ),
            uncertainty=list(
                uncertainty or []
            ),
            context_summary=context_summary,
        )

        self._observations.append(
            observation
        )

        self._trim_history()

        previous_states = {
            key: self._copy_state(value)
            for key, value in self._states.items()
        }

        self._apply_signals(
            signals
        )

        self._calculate_transitions(
            previous_states=previous_states
        )

        return self.snapshot()

    def snapshot(self) -> EmotionalStateSnapshot:
        """
        Return the current modeled emotional state.
        """

        states = {
            (
                key.value
                if hasattr(key, "value")
                else str(key)
            ): self._copy_state(value)
            for key, value in self._states.items()
            if value.intensity >= self.ACTIVE_THRESHOLD
        }

        dominant = self.dominant_state()

        uncertainty = self._global_uncertainty()

        return EmotionalStateSnapshot(
            dominant_signal=(
                dominant.signal_type
                if dominant
                else None
            ),
            dominant_intensity=(
                dominant.intensity
                if dominant
                else 0.0
            ),
            overall_confidence=(
                self.overall_confidence()
            ),
            states=states,
            transitions=list(
                self._transitions[-10:]
            ),
            uncertainty=uncertainty,
        )

    def dominant_state(
        self,
    ) -> Optional[EmotionalStateValue]:
        """
        Return the strongest currently modeled signal.
        """

        active = [
            state
            for state in self._states.values()
            if state.intensity >= self.ACTIVE_THRESHOLD
        ]

        if not active:
            return None

        return max(
            active,
            key=lambda item: (
                item.intensity
                * max(
                    item.confidence,
                    0.01,
                )
            ),
        )

    def get_state(
        self,
        signal_type: EmotionalSignalType,
    ) -> Optional[EmotionalStateValue]:

        return self._states.get(
            signal_type
        )

    def active_states(
        self,
    ) -> List[EmotionalStateValue]:

        states = [
            self._copy_state(state)
            for state in self._states.values()
            if state.intensity >= self.ACTIVE_THRESHOLD
        ]

        states.sort(
            key=lambda item: item.intensity,
            reverse=True,
        )

        return states

    def recent_observations(
        self,
        limit: int = 10,
    ) -> List[EmotionalStateObservation]:

        limit = max(
            1,
            int(limit),
        )

        return list(
            self._observations[-limit:]
        )

    def recent_transitions(
        self,
        limit: int = 10,
    ) -> List[EmotionalStateTransition]:

        limit = max(
            1,
            int(limit),
        )

        return list(
            self._transitions[-limit:]
        )

    def overall_confidence(self) -> float:
        """
        Estimate confidence in the current model.

        This is confidence in the MODEL based on evidence,
        not confidence that the person literally feels an emotion.
        """

        active = self.active_states()

        if not active:
            return 0.0

        weighted_sum = sum(
            state.confidence * state.intensity
            for state in active
        )

        total_weight = sum(
            state.intensity
            for state in active
        )

        if total_weight <= 0:
            return 0.0

        return _clamp(
            weighted_sum / total_weight
        )

    def reset(self) -> None:
        """
        Clear current state and observation history.
        """

        self._states.clear()
        self._observations.clear()
        self._transitions.clear()
        self._previous_dominant = None

    def export(self) -> Dict[str, Any]:
        """
        Export the complete model state.
        """

        return {
            "model": self.MODEL_NAME,
            "version": self.VERSION,
            "update_rate": self.update_rate,
            "history_limit": self.history_limit,
            "snapshot": self.snapshot().to_dict(),
            "observations": [
                item.to_dict()
                for item in self._observations
            ],
            "transitions": [
                item.to_dict()
                for item in self._transitions
            ],
            "epistemic_boundary": (
                "The model represents inferred emotional context, "
                "not direct access to internal human experience."
            ),
        }

    # ------------------------------------------------------------------
    # State update
    # ------------------------------------------------------------------

    def _apply_signals(
        self,
        signals: Sequence[EmotionalSignal],
    ) -> None:

        observed_types = set()

        for signal in signals:

            signal_type = getattr(
                signal,
                "signal_type",
                None,
            )

            if signal_type is None:
                continue

            observed_types.add(
                signal_type
            )

            intensity = _clamp(
                getattr(
                    signal,
                    "intensity",
                    0.0,
                )
            )

            confidence = _clamp(
                getattr(
                    signal,
                    "confidence",
                    0.0,
                )
            )

            existing = self._states.get(
                signal_type
            )

            if existing is None:
                existing = EmotionalStateValue(
                    signal_type=signal_type,
                    intensity=0.0,
                    confidence=0.0,
                )

                self._states[
                    signal_type
                ] = existing

            old_intensity = existing.intensity

            new_intensity = (
                old_intensity
                * (1.0 - self.update_rate)
                + intensity
                * self.update_rate
            )

            old_confidence = existing.confidence

            new_confidence = (
                old_confidence
                * (1.0 - self.update_rate)
                + confidence
                * self.update_rate
            )

            change = (
                new_intensity
                - old_intensity
            )

            existing.intensity = _clamp(
                new_intensity
            )

            existing.confidence = _clamp(
                new_confidence
            )

            existing.trend = max(
                -1.0,
                min(
                    1.0,
                    change,
                ),
            )

            existing.persistence = _clamp(
                existing.persistence
                + 0.10
            )

            existing.observation_count += 1
            existing.last_updated = _utc_now()

            signal_evidence = getattr(
                signal,
                "evidence",
                [],
            )

            existing.evidence.extend(
                signal_evidence
            )

            existing.uncertainty.extend(
                [
                    "The modeled state is inferred from available signals.",
                    "Signal intensity does not directly establish internal emotional intensity.",
                ]
            )

            existing.alternative_explanations.extend(
                [
                    "The communication pattern may reflect context, style, or emphasis rather than persistent emotion.",
                ]
            )

        # Decay signals that were not observed in this update.
        for signal_type, state in self._states.items():

            if signal_type in observed_types:
                continue

            state.intensity *= (
                1.0 - (
                    self.update_rate * 0.25
                )
            )

            state.trend = max(
                -1.0,
                min(
                    1.0,
                    state.trend - 0.05,
                ),
            )

     # ------------------------------------------------------------------
    # Transition detection
    # ------------------------------------------------------------------

    def _calculate_transitions(
        self,
        previous_states: Dict[
            EmotionalSignalType,
            EmotionalStateValue,
        ],
    ) -> None:

        previous_dominant = self._dominant_from_states(
            previous_states
        )

        current_dominant = self.dominant_state()

        previous_type = (
            previous_dominant.signal_type
            if previous_dominant
            else None
        )

        current_type = (
            current_dominant.signal_type
            if current_dominant
            else None
        )

        if (
            previous_type != current_type
            and current_dominant is not None
        ):

            previous_intensity = (
                previous_dominant.intensity
                if previous_dominant
                else 0.0
            )

            change = (
                current_dominant.intensity
                - previous_intensity
            )

            if (
                abs(change)
                >= self.TRANSITION_THRESHOLD
                or previous_type is None
            ):

                self._transitions.append(
                    EmotionalStateTransition(
                        from_signal=previous_type,
                        to_signal=current_type,
                        previous_intensity=(
                            previous_intensity
                        ),
                        new_intensity=(
                            current_dominant.intensity
                        ),
                        change=change,
                        confidence=min(
                            current_dominant.confidence,
                            0.85,
                        ),
                        reason=(
                            "The dominant modeled emotional "
                            "signal changed based on new evidence."
                        ),
                        uncertainty=[
                            "A change in detected communication signals does not necessarily mean the person's underlying emotional state changed.",
                        ],
                    )
                )

        self._transitions = self._transitions[
            -self.history_limit:
        ]

        self._previous_dominant = current_type

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dominant_from_states(
        states: Dict[
            EmotionalSignalType,
            EmotionalStateValue,
        ],
    ) -> Optional[EmotionalStateValue]:

        active = [
            state
            for state in states.values()
            if state.intensity
            >= EmotionalStateModel.ACTIVE_THRESHOLD
        ]

        if not active:
            return None

        return max(
            active,
            key=lambda item: (
                item.intensity
                * max(
                    item.confidence,
                    0.01,
                )
            ),
        )

    @staticmethod
    def _copy_state(
        state: EmotionalStateValue,
    ) -> EmotionalStateValue:

        return EmotionalStateValue(
            signal_type=state.signal_type,
            intensity=state.intensity,
            confidence=state.confidence,
            persistence=state.persistence,
            trend=state.trend,
            observation_count=state.observation_count,
            last_updated=state.last_updated,
            evidence=list(
                state.evidence
            ),
            uncertainty=list(
                state.uncertainty
            ),
            alternative_explanations=list(
                state.alternative_explanations
            ),
        )

    @staticmethod
    def _observation_confidence(
        signals: Sequence[EmotionalSignal],
    ) -> float:

        if not signals:
            return 0.0

        values = [
            _clamp(
                getattr(
                    signal,
                    "confidence",
                    0.0,
                )
            )
            for signal in signals
        ]

        return sum(values) / len(values)

    def _global_uncertainty(self) -> List[str]:

        uncertainty = [
            "Emotional state is modeled from observable evidence rather than directly observed.",
            "A detected emotional pattern may be situational, rhetorical, or communication-style related.",
            "Persistence in the model represents persistence of observed signals, not proof of persistent internal emotion.",
        ]

        if not self._observations:
            uncertainty.append(
                "No observations have yet been accumulated."
            )

        if len(self._observations) < 2:
            uncertainty.append(
                "Limited temporal observations are available for detecting meaningful state change."
            )

        return uncertainty

    def _trim_history(self) -> None:

        if len(self._observations) > self.history_limit:
            self._observations = self._observations[
                -self.history_limit:
            ]


__all__ = [
    "EmotionalStateObservation",
    "EmotionalStateValue",
    "EmotionalStateTransition",
    "EmotionalStateSnapshot",
    "EmotionalStateModel",
]
