"""
VALE FEELING Brain
Human Needs Analyzer

File:
    FEEL/human_experience/needs.py

Purpose:
    Models possible human needs, goals, priorities, and drives that may
    be relevant to a situation.

Important epistemic boundary:

    A detected word or behavior does NOT prove that a person has a
    particular psychological need.

    This module therefore produces:
        - explicit needs
        - possible needs
        - supporting evidence
        - alternative explanations
        - uncertainty

It does not diagnose, mind-read, or claim certainty about internal
psychological states.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.contracts import (
    CognitiveContext,
    EngineResult,
    EvidenceItem,
)


@dataclass
class HumanNeedSignal:
    """
    Represents a possible human need or goal relevant to a situation.

    `confidence` represents confidence in the interpretation, not proof
    that the person internally possesses this need.
    """

    need: str

    category: str

    description: str

    source: str = "inference"

    confidence: float = 0.0

    evidence: List[str] = field(
        default_factory=list
    )

    alternative_explanations: List[str] = field(
        default_factory=list
    )

    uncertainties: List[str] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.confidence = max(
            0.0,
            min(1.0, self.confidence),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "need": self.need,
            "category": self.category,
            "description": self.description,
            "source": self.source,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "alternative_explanations": list(
                self.alternative_explanations
            ),
            "uncertainties": list(
                self.uncertainties
            ),
        }


class HumanNeedsAnalyzer:
    """
    Models possible needs and goal pressures from available context.

    Core categories include:

        - autonomy
        - competence
        - security
        - belonging
        - connection
        - achievement
        - recognition
        - fairness
        - predictability
        - control
        - understanding
        - exploration
        - novelty
        - efficiency
        - stability
        - self-expression
        - progress
        - resource preservation

    These categories are computational abstractions. They should not be
    interpreted as a clinical psychological assessment.
    """

    NAME = "human_needs_analyzer"

    # ------------------------------------------------------------------
    # Explicit language patterns
    # ------------------------------------------------------------------

    NEED_PATTERNS = {
        "autonomy": (
            "my choice",
            "choose for myself",
            "independent",
            "independence",
            "freedom",
            "control my",
            "my decision",
        ),
        "security": (
            "safe",
            "safety",
            "secure",
            "protect",
            "protection",
            "risk",
            "danger",
            "afraid of losing",
        ),
        "understanding": (
            "understand",
            "explain",
            "clarify",
            "make sense",
            "confused",
            "know why",
            "learn",
        ),
        "competence": (
            "improve",
            "better at",
            "skill",
            "learn how",
            "master",
            "capable",
            "ability",
        ),
        "achievement": (
            "achieve",
            "accomplish",
            "success",
            "goal",
            "finish",
            "complete",
            "win",
            "progress",
        ),
        "belonging": (
            "belong",
            "fit in",
            "included",
            "accepted",
            "alone",
            "left out",
            "part of",
        ),
        "connection": (
            "relationship",
            "friend",
            "family",
            "partner",
            "connect",
            "talk to",
            "communicate",
        ),
        "recognition": (
            "respect",
            "recognized",
            "appreciated",
            "credit",
            "acknowledge",
            "recognition",
        ),
        "fairness": (
            "fair",
            "unfair",
            "equal",
            "justice",
            "treated",
            "bias",
            "double standard",
        ),
        "predictability": (
            "know what will happen",
            "predict",
            "uncertain",
            "uncertainty",
            "stable",
            "consistent",
            "reliable",
        ),
        "control": (
            "control",
            "manage",
            "handle",
            "can't control",
            "cannot control",
            "out of control",
        ),
        "exploration": (
            "explore",
            "discover",
            "curious",
            "find out",
            "investigate",
            "research",
        ),
        "novelty": (
            "new",
            "different",
            "novel",
            "fresh",
            "change",
            "something else",
        ),
        "efficiency": (
            "faster",
            "efficient",
            "save time",
            "simplify",
            "streamline",
            "quick",
        ),
        "stability": (
            "stable",
            "consistent",
            "routine",
            "steady",
            "reliable",
            "maintain",
        ),
        "self_expression": (
            "create",
            "express",
            "design",
            "my style",
            "creative",
            "idea",
        ),
        "resource_preservation": (
            "save money",
            "save time",
            "avoid loss",
            "preserve",
            "protect resources",
            "waste",
        ),
    }

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------

    def analyze(
        self,
        context: CognitiveContext,
    ) -> EngineResult:
        """
        Analyze possible needs and goal pressures.
        """

        result = EngineResult(
            engine=self.NAME,
            success=True,
        )

        text = (context.user_input or "").strip()

        if not text:
            result.summary = (
                "No input was supplied for human-needs analysis."
            )

            result.add_uncertainty(
                "Human needs cannot be meaningfully inferred "
                "without relevant context."
            )

            result.confidence = 0.0
            return result

        signals = self.identify_needs(
            context
        )

        for signal in signals:
            result.add_inference(
                f"Possible need: {signal.need} — "
                f"{signal.description}"
            )

            for uncertainty in signal.uncertainties:
                result.add_uncertainty(
                    uncertainty
                )

            for alternative in signal.alternative_explanations:
                result.add_alternative(
                    alternative
                )

        result.outputs["needs"] = [
            signal.to_dict()
            for signal in signals
        ]

        result.confidence = self._overall_confidence(
            signals
        )

        result.summary = self._build_summary(
            signals
        )

        result.metadata["epistemic_boundary"] = (
            "Needs are contextual hypotheses unless explicitly "
            "stated or strongly supported by evidence."
        )

        return result

    # ------------------------------------------------------------------
    # Need identification
    # ------------------------------------------------------------------

    def identify_needs(
        self,
        context: CognitiveContext,
    ) -> List[HumanNeedSignal]:
        """
        Identify explicit and possible needs from the context.
        """

        text = (context.user_input or "").strip()

        if not text:
            return []

        normalized = text.lower()

        signals: List[HumanNeedSignal] = []

        for category, patterns in self.NEED_PATTERNS.items():
            matched = [
                pattern
                for pattern in patterns
                if pattern in normalized
            ]

            if not matched:
                continue

            signal = self._build_need_signal(
                category=category,
                matched_patterns=matched,
                context=context,
            )

            if signal is not None:
                signals.append(signal)

        # Explicit goals can indicate a need for progress or achievement,
        # but the underlying psychological need remains an inference.
        goal_signal = self._detect_goal_context(
            context
        )

        if goal_signal is not None:
            signals.append(goal_signal)

        # Explicit constraints can indicate a practical need to preserve
        # resources or reduce uncertainty.
        constraint_signal = self._detect_constraint_context(
            context
        )

        if constraint_signal is not None:
            signals.append(constraint_signal)

        return self._deduplicate(
            signals
        )

    # ------------------------------------------------------------------
    # Signal construction
    # ------------------------------------------------------------------

    def _build_need_signal(
        self,
        category: str,
        matched_patterns: List[str],
        context: CognitiveContext,
    ) -> Optional[HumanNeedSignal]:
        definitions = {
            "autonomy": (
                "The person may place importance on having meaningful "
                "choice or control over their own decisions."
            ),
            "security": (
                "The person may be concerned with safety, protection, "
                "or reducing exposure to harmful outcomes."
            ),
            "understanding": (
                "The person may be seeking clarity, explanation, "
                "or a more accurate mental model."
            ),
            "competence": (
                "The person may be seeking greater capability, "
                "skill, or confidence in performing a task."
            ),
            "achievement": (
                "The person may be focused on reaching a goal, "
                "completing something, or making measurable progress."
            ),
            "belonging": (
                "The person may place importance on inclusion, "
                "acceptance, or social belonging."
            ),
            "connection": (
                "The person may be seeking communication, "
                "relationship, or interpersonal connection."
            ),
            "recognition": (
                "The person may value acknowledgment, respect, "
                "or recognition of their contribution."
            ),
            "fairness": (
                "The person may be concerned with equitable treatment "
                "or consistency in how people are treated."
            ),
            "predictability": (
                "The person may be seeking greater predictability "
                "or consistency in uncertain circumstances."
            ),
            "control": (
                "The person may be trying to increase their ability "
                "to influence or manage the situation."
            ),
            "exploration": (
                "The person may be motivated to discover, investigate, "
                "or understand something unknown."
            ),
            "novelty": (
                "The person may be seeking change, novelty, or a "
                "different experience."
            ),
            "efficiency": (
                "The person may value reduced effort, faster execution, "
                "or a simpler process."
            ),
            "stability": (
                "The person may value consistency, reliability, "
                "or preservation of an existing state."
            ),
            "self_expression": (
                "The person may be seeking an opportunity to express "
                "ideas, identity, preferences, or creativity."
            ),
            "resource_preservation": (
                "The person may be trying to preserve time, money, "
                "effort, or another limited resource."
            ),
        }

        description = definitions.get(
            category,
            "A potentially relevant human need was detected."
        )

        # Explicit language receives higher confidence than indirect
        # contextual interpretation, but confidence remains below certainty.
        confidence = min(
            0.80,
            0.35 + (0.10 * len(matched_patterns)),
        )

        evidence = [
            f"Matched explicit contextual signal: '{pattern}'"
            for pattern in matched_patterns
        ]

        alternatives = [
            (
                "The wording may reflect the immediate task rather "
                "than a stable underlying need."
            ),
            (
                "The signal may have another contextual explanation "
                "not represented by the current model."
            ),
        ]

        uncertainties = [
            (
                f"The presence of '{category}' language does not prove "
                "that this is the person's underlying psychological need."
            )
        ]

        return HumanNeedSignal(
            need=category,
            category=category,
            description=description,
            source="contextual_inference",
            confidence=confidence,
            evidence=evidence,
            alternative_explanations=alternatives,
            uncertainties=uncertainties,
        )

    # ------------------------------------------------------------------
    # Goal detection
    # ------------------------------------------------------------------

    def _detect_goal_context(
        self,
        context: CognitiveContext,
    ) -> Optional[HumanNeedSignal]:
        text = (context.user_input or "").lower()

        goal_patterns = (
            "i want",
            "i need to",
            "i'm trying to",
            "i am trying to",
            "my goal",
            "i would like",
            "i hope to",
            "i plan to",
        )

        matched = [
            pattern
            for pattern in goal_patterns
            if pattern in text
        ]

        if not matched:
            return None

        return HumanNeedSignal(
            need="goal_progress",
            category="goal",
            description=(
                "The person has expressed a goal or desired outcome; "
                "the underlying motivation should remain open for "
                "further analysis."
            ),
            source="explicit_user_goal",
            confidence=0.75,
            evidence=[
                f"Explicit goal-language detected: '{pattern}'"
                for pattern in matched
            ],
            alternative_explanations=[
                (
                    "The stated goal may be situational rather than "
                    "a broader motivational pattern."
                )
            ],
            uncertainties=[
                (
                    "The reason the goal matters to the person "
                    "has not necessarily been stated."
                )
            ],
        )

    # ------------------------------------------------------------------
    # Constraint detection
    # ------------------------------------------------------------------

    def _detect_constraint_context(
        self,
        context: CognitiveContext,
    ) -> Optional[HumanNeedSignal]:
        if not context.active_constraints:
            return None

        return HumanNeedSignal(
            need="constraint_management",
            category="practical",
            description=(
                "The person may need to work within explicit "
                "practical constraints."
            ),
            source="explicit_constraint",
            confidence=0.70,
            evidence=[
                str(constraint)
                for constraint in context.active_constraints
                if constraint
            ],
            alternative_explanations=[
                (
                    "A constraint may be imposed externally and "
                    "not represent a personal psychological need."
                )
            ],
            uncertainties=[
                (
                    "The relative importance of each constraint "
                    "has not necessarily been established."
                )
            ],
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _deduplicate(
        self,
        signals: List[HumanNeedSignal],
    ) -> List[HumanNeedSignal]:
        seen = set()
        unique: List[HumanNeedSignal] = []

        for signal in signals:
            key = signal.need.strip().lower()

            if not key or key in seen:
                continue

            seen.add(key)
            unique.append(signal)

        return unique

    def _overall_confidence(
        self,
        signals: List[HumanNeedSignal],
    ) -> float:
        if not signals:
            return 0.0

        return max(
            0.0,
            min(
                1.0,
                sum(
                    signal.confidence
                    for signal in signals
                ) / len(signals),
            ),
        )

    def _build_summary(
        self,
        signals: List[HumanNeedSignal],
    ) -> str:
        if not signals:
            return (
                "No meaningful human-need signals were identified "
                "from the available context."
            )

        explicit = sum(
            1
            for signal in signals
            if signal.source.startswith("explicit")
        )

        return (
            f"Identified {len(signals)} possible human need or "
            f"goal signal(s), including {explicit} directly "
            "supported by explicit language. Underlying motivation "
            "remains uncertain unless separately established."
        )


__all__ = [
    "HumanNeedSignal",
    "HumanNeedsAnalyzer",
  ]
