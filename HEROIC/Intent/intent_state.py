"""
HEROIC INTENT STATE

Foundational representation of what HEROIC believes the user
is trying to accomplish.

Important:
Intent interpretation is not the same as certainty.

HEROIC must preserve the distinction between:
- what the user explicitly said
- what HEROIC inferred
- how confident that inference is

This module does not perform intent detection itself.
It only defines the state used by future intent intelligence.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class IntentType(str, Enum):
    """
    High-level categories of user intent.
    """

    DIRECT_REQUEST = "direct_request"
    INFORMATION_REQUEST = "information_request"
    DECISION_REQUEST = "decision_request"
    ACTION_REQUEST = "action_request"
    EXPLORATION = "exploration"
    CLARIFICATION = "clarification"
    CORRECTION = "correction"
    FOLLOW_UP = "follow_up"
    CONTINUATION = "continuation"
    COMPARISON = "comparison"
    ANALYSIS = "analysis"
    UNKNOWN = "unknown"


@dataclass
class HeroicIntentState:
    """
    Structured state representing interpreted user intent.
    """

    intent_type: IntentType = IntentType.UNKNOWN

    explicit_request: str = ""

    inferred_objective: Optional[str] = None

    confidence: float = 0.0

    ambiguity_detected: bool = False

    ambiguity_reasons: List[str] = field(default_factory=list)

    assumptions: List[str] = field(default_factory=list)

    required_clarifications: List[str] = field(default_factory=list)

    signals: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_ambiguity(self, reason: str) -> None:
        """
        Record an ambiguity discovered during intent interpretation.
        """

        if reason and reason not in self.ambiguity_reasons:
            self.ambiguity_reasons.append(reason)

        self.ambiguity_detected = True

    def add_assumption(self, assumption: str) -> None:
        """
        Record an assumption used during interpretation.
        """

        if assumption and assumption not in self.assumptions:
            self.assumptions.append(assumption)

    def add_clarification(self, clarification: str) -> None:
        """
        Record information that must be clarified.
        """

        if clarification and clarification not in self.required_clarifications:
            self.required_clarifications.append(clarification)

    def add_signal(self, signal: str) -> None:
        """
        Record an observable signal supporting the interpretation.
        """

        if signal and signal not in self.signals:
            self.signals.append(signal)

    def is_sufficient(self) -> bool:
        """
        Determine whether the current intent state is sufficiently
        understood for downstream planning.
        """

        return (
            self.intent_type != IntentType.UNKNOWN
            and self.confidence > 0.0
            and not self.required_clarifications
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert intent state into a serializable dictionary.
        """

        return {
            "intent_type": self.intent_type.value,
            "explicit_request": self.explicit_request,
            "inferred_objective": self.inferred_objective,
            "confidence": self.confidence,
            "ambiguity_detected": self.ambiguity_detected,
            "ambiguity_reasons": list(self.ambiguity_reasons),
            "assumptions": list(self.assumptions),
            "required_clarifications": list(
                self.required_clarifications
            ),
            "signals": list(self.signals),
            "metadata": dict(self.metadata),
      }
