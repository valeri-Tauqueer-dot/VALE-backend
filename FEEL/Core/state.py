"""
VALE FEELING Brain
Core State Management

File:
    FEEL/core/state.py

Purpose:
    Maintains the internal working state of the FEELING brain.

Design principles:
    - State is explicit and inspectable.
    - Facts, inferences, hypotheses, and imagination remain distinguishable.
    - Psychological interpretations carry uncertainty.
    - State can be updated incrementally.
    - Previous state is preserved through versioning.
    - No psychological inference is treated as mind-reading.
    - No clinical diagnosis is performed here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import copy
import uuid

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
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class FeelingStateSnapshot:
    """
    Immutable-style snapshot of FEELING state at a point in time.

    The snapshot is intentionally data-oriented so that it can later be
    connected to VALE's broader shared-state/versioning infrastructure.
    """

    state_id: str
    version: int
    created_at: datetime

    human_context: Optional[HumanContext] = None
    psychological_state: Optional[PsychologicalState] = None

    psychological_signals: List[PsychologicalSignal] = field(
        default_factory=list
    )

    emotional_assessment: Optional[FeelingAssessment] = None

    perspectives: List[Perspective] = field(default_factory=list)

    imagination_candidates: List[ImaginationCandidate] = field(
        default_factory=list
    )

    ideas: List[Idea] = field(default_factory=list)

    epistemic_claims: List[EpistemicClaim] = field(default_factory=list)

    active_hypotheses: List[str] = field(default_factory=list)

    uncertainties: List[str] = field(default_factory=list)

    contradictions: List[str] = field(default_factory=list)

    communication_context: Dict[str, Any] = field(default_factory=dict)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the snapshot into a JSON-friendly dictionary."""

        def serialize(value: Any) -> Any:
            if hasattr(value, "to_dict"):
                return value.to_dict()

            if isinstance(value, datetime):
                return value.isoformat()

            if isinstance(value, list):
                return [serialize(item) for item in value]

            if isinstance(value, dict):
                return {
                    str(key): serialize(item)
                    for key, item in value.items()
                }

            return value

        return {
            "state_id": self.state_id,
            "version": self.version,
            "created_at": serialize(self.created_at),
            "human_context": serialize(self.human_context),
            "psychological_state": serialize(self.psychological_state),
            "psychological_signals": serialize(self.psychological_signals),
            "emotional_assessment": serialize(self.emotional_assessment),
            "perspectives": serialize(self.perspectives),
            "imagination_candidates": serialize(
                self.imagination_candidates
            ),
            "ideas": serialize(self.ideas),
            "epistemic_claims": serialize(self.epistemic_claims),
            "active_hypotheses": serialize(self.active_hypotheses),
            "uncertainties": serialize(self.uncertainties),
            "contradictions": serialize(self.contradictions),
            "communication_context": serialize(self.communication_context),
            "metadata": serialize(self.metadata),
        }


class FeelingState:
    """
    Working state of the FEELING brain.

    This class acts as the internal state container between FEELING
    subsystems.

    Example flow:

        input
          ↓
        human context
          ↓
        psychological signals
          ↓
        psychological state
          ↓
        emotional interpretation
          ↓
        perspective / intent / communication
          ↓
        imagination / ideas
          ↓
        MCVL challenge
          ↓
        updated state

    The state does not decide whether an inference is true.
    It stores the inference, its evidence/uncertainty, and its current
    status so that verification systems can evaluate it.
    """

    def __init__(self) -> None:
        self.state_id: str = str(uuid.uuid4())
        self.version: int = 0
        self.created_at: datetime = _utc_now()
        self.updated_at: datetime = self.created_at

        self.human_context: Optional[HumanContext] = None

        self.psychological_state: Optional[PsychologicalState] = None

        self.psychological_signals: List[PsychologicalSignal] = []

        self.emotional_assessment: Optional[FeelingAssessment] = None

        self.perspectives: List[Perspective] = []

        self.imagination_candidates: List[ImaginationCandidate] = []

        self.ideas: List[Idea] = []

        self.epistemic_claims: List[EpistemicClaim] = []

        self.active_hypotheses: List[str] = []

        self.uncertainties: List[str] = []

        self.contradictions: List[str] = []

        self.communication_context: Dict[str, Any] = {}

        self.metadata: Dict[str, Any] = {}

        # Internal history.
        self._history: List[FeelingStateSnapshot] = []

    # ------------------------------------------------------------------
    # State lifecycle
    # ------------------------------------------------------------------

    def touch(self) -> None:
        """
        Mark the state as changed.

        Every meaningful mutation should call this method.
        """

        self.version += 1
        self.updated_at = _utc_now()

    def snapshot(self) -> FeelingStateSnapshot:
        """
        Create a deep snapshot of the current state.
        """

        return FeelingStateSnapshot(
            state_id=self.state_id,
            version=self.version,
            created_at=self.updated_at,
            human_context=copy.deepcopy(self.human_context),
            psychological_state=copy.deepcopy(self.psychological_state),
            psychological_signals=copy.deepcopy(
                self.psychological_signals
            ),
            emotional_assessment=copy.deepcopy(
                self.emotional_assessment
            ),
            perspectives=copy.deepcopy(self.perspectives),
            imagination_candidates=copy.deepcopy(
                self.imagination_candidates
            ),
            ideas=copy.deepcopy(self.ideas),
            epistemic_claims=copy.deepcopy(self.epistemic_claims),
            active_hypotheses=copy.deepcopy(self.active_hypotheses),
            uncertainties=copy.deepcopy(self.uncertainties),
            contradictions=copy.deepcopy(self.contradictions),
            communication_context=copy.deepcopy(
                self.communication_context
            ),
            metadata=copy.deepcopy(self.metadata),
        )

    def checkpoint(self) -> FeelingStateSnapshot:
        """
        Save the current state into internal history and return it.
        """

        snapshot = self.snapshot()
        self._history.append(copy.deepcopy(snapshot))
        return snapshot

    # ------------------------------------------------------------------
    # Human context
    # ------------------------------------------------------------------

    def set_human_context(
        self,
        context: Optional[HumanContext],
    ) -> None:
        """Replace the current human-context model."""

        self.human_context = copy.deepcopy(context)
        self.touch()

    # ------------------------------------------------------------------
    # Psychological state
    # ------------------------------------------------------------------

    def set_psychological_state(
        self,
        state: Optional[PsychologicalState],
    ) -> None:
        """
        Replace the current psychological model.

        This represents FEELING's current computational hypothesis about
        relevant psychological processes. It is not a claim of direct
        access to another person's internal mental state.
        """

        self.psychological_state = copy.deepcopy(state)
        self.touch()

    def add_psychological_signal(
        self,
        signal: PsychologicalSignal,
    ) -> None:
        """Add a psychological signal to the working state."""

        self.psychological_signals.append(copy.deepcopy(signal))
        self.touch()

    def clear_psychological_signals(self) -> None:
        """Clear transient psychological signals."""

        self.psychological_signals.clear()
        self.touch()

    # ------------------------------------------------------------------
    # Emotional assessment
    # ------------------------------------------------------------------

    def set_emotional_assessment(
        self,
        assessment: Optional[FeelingAssessment],
    ) -> None:
        """Store the current emotional/human-context assessment."""

        self.emotional_assessment = copy.deepcopy(assessment)
        self.touch()

    # ------------------------------------------------------------------
    # Perspectives
    # ------------------------------------------------------------------

    def add_perspective(
        self,
        perspective: Perspective,
    ) -> None:
        """Add a possible human perspective."""

        self.perspectives.append(copy.deepcopy(perspective))
        self.touch()

    def clear_perspectives(self) -> None:
        """Clear current perspective candidates."""

        self.perspectives.clear()
        self.touch()

    # ------------------------------------------------------------------
    # Imagination
    # ------------------------------------------------------------------

    def add_imagination_candidate(
        self,
        candidate: ImaginationCandidate,
    ) -> None:
        """
        Store an imagined possibility.

        Imagination candidates are explicitly separated from factual
        state and must never silently become factual claims.
        """

        self.imagination_candidates.append(copy.deepcopy(candidate))
        self.touch()

    def clear_imagination(self) -> None:
        """Remove current imagination candidates."""

        self.imagination_candidates.clear()
        self.touch()

    # ------------------------------------------------------------------
    # Ideas
    # ------------------------------------------------------------------

    def add_idea(self, idea: Idea) -> None:
        """Store a generated idea."""

        self.ideas.append(copy.deepcopy(idea))
        self.touch()

    def clear_ideas(self) -> None:
        """Clear generated ideas from the working state."""

        self.ideas.clear()
        self.touch()

    # ------------------------------------------------------------------
    # Epistemic information
    # ------------------------------------------------------------------

    def add_epistemic_claim(
        self,
        claim: EpistemicClaim,
    ) -> None:
        """
        Add an epistemically classified claim.

        Claims can later be challenged or updated by MCVL.
        """

        self.epistemic_claims.append(copy.deepcopy(claim))
        self.touch()

    def add_hypothesis(self, hypothesis: str) -> None:
        """Register an active hypothesis."""

        if not hypothesis:
            return

        if hypothesis not in self.active_hypotheses:
            self.active_hypotheses.append(hypothesis)
            self.touch()

    def remove_hypothesis(self, hypothesis: str) -> None:
        """Remove an active hypothesis if present."""

        if hypothesis in self.active_hypotheses:
            self.active_hypotheses.remove(hypothesis)
            self.touch()

    # ------------------------------------------------------------------
    # Uncertainty
    # ------------------------------------------------------------------

    def add_uncertainty(self, uncertainty: str) -> None:
        """
        Register an uncertainty.

        FEELING should prefer explicit uncertainty over false certainty.
        """

        if not uncertainty:
            return

        if uncertainty not in self.uncertainties:
            self.uncertainties.append(uncertainty)
            self.touch()

    def clear_uncertainties(self) -> None:
        """Clear currently registered uncertainties."""

        self.uncertainties.clear()
        self.touch()

    # ------------------------------------------------------------------
    # Contradictions
    # ------------------------------------------------------------------

    def add_contradiction(self, contradiction: str) -> None:
        """
        Register a contradiction or interpretation mismatch.
        """

        if not contradiction:
            return

        if contradiction not in self.contradictions:
            self.contradictions.append(contradiction)
            self.touch()

    def clear_contradictions(self) -> None:
        """Clear current contradictions."""

        self.contradictions.clear()
        self.touch()

    # ------------------------------------------------------------------
    # Communication context
    # ------------------------------------------------------------------

    def update_communication_context(
        self,
        values: Dict[str, Any],
    ) -> None:
        """Merge communication-related context."""

        if not values:
            return

        self.communication_context.update(
            copy.deepcopy(values)
        )
        self.touch()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def update_metadata(
        self,
        values: Dict[str, Any],
    ) -> None:
        """Merge internal metadata."""

        if not values:
            return

        self.metadata.update(copy.deepcopy(values))
        self.touch()

    # ------------------------------------------------------------------
    # History / recovery
    # ------------------------------------------------------------------

    def history(self) -> List[FeelingStateSnapshot]:
        """
        Return a deep copy of state history.

        Callers cannot mutate the internal history accidentally.
        """

        return copy.deepcopy(self._history)

    def latest_checkpoint(
        self,
    ) -> Optional[FeelingStateSnapshot]:
        """Return the most recent checkpoint."""

        if not self._history:
            return None

        return copy.deepcopy(self._history[-1])

    # ------------------------------------------------------------------
    # State export
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return the current state as a dictionary."""

        return self.snapshot().to_dict()

    def reset_working_state(self) -> None:
        """
        Clear transient reasoning products while preserving identity,
        versioning, metadata, and history.

        This is useful when FEELING begins a new cognitive task.
        """

        self.human_context = None
        self.psychological_state = None
        self.psychological_signals.clear()
        self.emotional_assessment = None
        self.perspectives.clear()
        self.imagination_candidates.clear()
        self.ideas.clear()
        self.epistemic_claims.clear()
        self.active_hypotheses.clear()
        self.uncertainties.clear()
        self.contradictions.clear()
        self.communication_context.clear()

        self.touch()

    def __repr__(self) -> str:
        return (
            f"FeelingState("
            f"state_id={self.state_id!r}, "
            f"version={self.version}, "
            f"signals={len(self.psychological_signals)}, "
            f"hypotheses={len(self.active_hypotheses)}, "
            f"uncertainties={len(self.uncertainties)}, "
            f"contradictions={len(self.contradictions)}"
            f")"
        )


__all__ = [
    "FeelingState",
    "FeelingStateSnapshot",
      ]
