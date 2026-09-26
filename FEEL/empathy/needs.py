"""
VALE FEELINGS Brain
Empathy Needs Analyzer

File:
    FEEL/empathy/needs.py

Purpose:
    Model possible human needs that may be relevant to a situation
    or interaction.

Important epistemic boundary:

    FACT != INFERENCE != HYPOTHESIS

This module does not claim to know what a person truly needs.
It identifies possible needs from explicit statements, goals,
constraints, context, and communication signals.

This is not psychological diagnosis and does not perform mind-reading.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ..Core.models import (
    EvidenceReference,
    EpistemicClaim,
    EpistemicType,
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
    """Clamp a numeric value into the requested range."""
    return max(minimum, min(maximum, float(value)))


def _safe_text(value: Any) -> str:
    """Convert a value to clean text."""
    if value is None:
        return ""

    return str(value).strip()


def _unique(values: Iterable[str]) -> List[str]:
    """Return non-empty strings while preserving order."""
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
# NEED SIGNAL
# ============================================================================

@dataclass
class EmpathyNeedSignal:
    """
    Represents one possible human need.

    Example:

        need_type="clarity"
        confidence=0.72

    This means clarity may be relevant. It does NOT mean the person
    definitely has that need.
    """

    need_type: str

    confidence: float = 0.0

    intensity: float = 0.0

    source: str = "inference"

    rationale: str = ""

    evidence: List[EvidenceReference] = field(
        default_factory=list
    )

    alternative_explanations: List[str] = field(
        default_factory=list
    )

    uncertainties: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    created_at: datetime = field(
        default_factory=_utc_now
    )

    def __post_init__(self) -> None:
        self.confidence = _clamp(self.confidence)
        self.intensity = _clamp(self.intensity)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()

        data["evidence"] = [
            evidence.to_dict()
            for evidence in self.evidence
        ]

        return data


# ============================================================================
# NEED ASSESSMENT
# ============================================================================

@dataclass
class EmpathyNeedsAssessment:
    """
    Complete assessment of possible human needs.
    """

    input_text: str = ""

    signals: List[EmpathyNeedSignal] = field(
        default_factory=list
    )

    possible_needs: List[str] = field(
        default_factory=list
    )

    explicit_needs: List[str] = field(
        default_factory=list
    )

    inferred_needs: List[str] = field(
        default_factory=list
    )

    possible_priorities: List[str] = field(
        default_factory=list
    )

    communication_implications: List[str] = field(
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

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    created_at: datetime = field(
        default_factory=_utc_now
    )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)

        data["created_at"] = self.created_at.isoformat()

        data["signals"] = [
            signal.to_dict()
            for signal in self.signals
        ]

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
# MAIN ANALYZER
# ============================================================================

class EmpathyNeedsAnalyzer:
    """
    Identify possible human needs from communication and context.

    The analyzer considers needs such as:

        clarity
        understanding
        safety
        certainty
        control
        autonomy
        accuracy
        efficiency
        stability
        predictability
        competence
        achievement
        connection
        recognition
        fairness
        exploration
        novelty
        self-expression
        resource preservation

    The result is probabilistic/contextual rather than a claim about
    the person's actual internal state.
    """

    ENGINE_NAME = "empathy_needs"
    VERSION = "0.1.0"

    NEED_PATTERNS: Mapping[str, Sequence[str]] = {
        "clarity": (
            "explain",
            "clear",
            "clarify",
            "what does this mean",
            "meaning",
            "i don't understand",
            "don't understand",
        ),
        "understanding": (
            "understand",
            "why",
            "how",
            "what does",
            "teach me",
            "help me understand",
        ),
        "safety": (
            "safe",
            "danger",
            "risk",
            "protect",
            "harm",
            "unsafe",
        ),
        "certainty": (
            "certain",
            "sure",
            "confirm",
            "confirmation",
            "definitely",
            "know for sure",
        ),
        "accuracy": (
            "correct",
            "accurate",
            "mistake",
            "wrong",
            "verify",
            "evidence",
            "proof",
        ),
        "control": (
            "control",
            "manage",
            "handle",
            "what should i do",
            "how do i deal",
        ),
        "autonomy": (
            "my choice",
            "my decision",
            "i decide",
            "choose",
            "option",
            "options",
        ),
        "efficiency": (
            "faster",
            "quick",
            "efficient",
            "save time",
            "waste time",
            "simpler",
        ),
        "stability": (
            "stable",
            "stability",
            "consistent",
            "reliable",
            "keep it working",
        ),
        "predictability": (
            "what will happen",
            "what happens next",
            "predict",
            "expected",
            "expect",
            "uncertain",
        ),
        "competence": (
            "learn",
            "improve",
            "better at",
            "skill",
            "understand how",
        ),
        "achievement": (
            "achieve",
            "finish",
            "complete",
            "success",
            "goal",
            "accomplish",
        ),
        "connection": (
            "connect",
            "relationship",
            "together",
            "with me",
            "support",
        ),
        "recognition": (
            "recognize",
            "appreciate",
            "acknowledge",
            "credit",
        ),
        "fairness": (
            "fair",
            "unfair",
            "equal",
            "justice",
            "reasonable",
        ),
        "exploration": (
            "explore",
            "discover",
            "investigate",
            "find out",
            "learn more",
        ),
        "novelty": (
            "new",
            "different",
            "creative",
            "novel",
            "fresh idea",
        ),
        "self_expression": (
            "express",
            "creative",
            "my idea",
            "my way",
            "design",
        ),
        "resource_preservation": (
            "save money",
            "save time",
            "avoid wasting",
            "preserve",
            "protect resources",
        ),
    }

    # ------------------------------------------------------------------
    # Explicit need patterns
    # ------------------------------------------------------------------

    EXPLICIT_NEED_PATTERNS: Sequence[str] = (
        "i need",
        "i want",
        "i require",
        "i'm looking for",
        "i am looking for",
        "i really need",
        "what i need is",
    )

    # ------------------------------------------------------------------
    # Analyze
    # ------------------------------------------------------------------

    def analyze(
        self,
        text: str = "",
        context: Optional[Any] = None,
        evidence: Optional[Sequence[EvidenceReference]] = None,
    ) -> EmpathyNeedsAssessment:
        """
        Analyze possible human needs.

        Parameters
        ----------
        text:
            Primary communication text.

        context:
            Optional contextual object. It may expose fields such as:
                user_input
                conversation_context
                known_facts
                active_constraints
                metadata

        evidence:
            Optional pre-existing evidence references.
        """

        combined_text = self._build_context_text(
            text=text,
            context=context,
        )

        normalized = combined_text.casefold()

        evidence_items: List[EvidenceReference] = list(
            evidence or []
        )

        if combined_text:
            evidence_items.append(
                EvidenceReference(
                    source="empathy_needs_input",
                    content=combined_text,
                )
            )

        signals: List[EmpathyNeedSignal] = []

        explicit_needs = self._extract_explicit_needs(
            combined_text
        )

        # --------------------------------------------------------------
        # Pattern-based need detection
        # --------------------------------------------------------------

        for need_type, patterns in self.NEED_PATTERNS.items():

            matched_patterns = [
                pattern
                for pattern in patterns
                if pattern.casefold() in normalized
            ]

            if not matched_patterns:
                continue

            confidence = self._calculate_confidence(
                matched_count=len(matched_patterns),
                explicit=need_type in explicit_needs,
                context_available=context is not None,
            )

            intensity = self._calculate_intensity(
                matched_count=len(matched_patterns),
                explicit=need_type in explicit_needs,
            )

            rationale = (
                f"Detected language associated with possible "
                f"{need_type} need: "
                f"{', '.join(matched_patterns)}."
            )

            signals.append(
                EmpathyNeedSignal(
                    need_type=need_type,
                    confidence=confidence,
                    intensity=intensity,
                    source=(
                        "explicit"
                        if need_type in explicit_needs
                        else "inference"
                    ),
                    rationale=rationale,
                    evidence=list(evidence_items),
                    alternative_explanations=[
                        "The wording may reflect the task itself "
                        "rather than a stable personal need.",
                        "The detected signal may be situational.",
                    ],
                    uncertainties=[
                        "The person's actual internal need cannot "
                        "be directly observed from text alone."
                    ],
                )
            )

        # --------------------------------------------------------------
        # Explicitly stated needs
        # --------------------------------------------------------------

        explicit_needs = _unique(explicit_needs)

        # --------------------------------------------------------------
        # Possible needs
        # --------------------------------------------------------------

        possible_needs = _unique(
            [
                signal.need_type
                for signal in sorted(
                    signals,
                    key=lambda item: item.confidence,
                    reverse=True,
                )
            ]
        )

        inferred_needs = _unique(
            [
                signal.need_type
                for signal in signals
                if signal.source != "explicit"
            ]
        )

        possible_priorities = self._derive_priorities(
            signals=signals,
            normalized_text=normalized,
        )

        communication_implications = (
            self._derive_communication_implications(
                possible_needs=possible_needs
            )
        )

        uncertainties = [
            "Need inference is based on available language and "
            "context, not direct access to internal mental state."
        ]

        if not context:
            uncertainties.append(
                "No structured cognitive context was supplied."
            )

        if not signals:
            uncertainties.append(
                "No strong need-related linguistic signal was detected."
            )

        alternative_explanations = [
            "The wording may describe a task requirement rather "
            "than a personal psychological need.",
            "A detected need signal may be temporary or "
            "context-specific.",
            "Multiple needs may explain the same language."
        ]

        confidence = self._overall_confidence(
            signals=signals,
            context_available=context is not None,
        )

        epistemic_claims = self._build_claims(
            signals=signals,
            evidence=evidence_items,
        )

        reasoning_notes = [
            "Needs are modeled as possible contextual signals.",
            "Explicitly stated needs receive stronger epistemic "
            "status than inferred needs.",
            "Inferred needs remain uncertain and should be "
            "challenged when consequential.",
        ]

        return EmpathyNeedsAssessment(
            input_text=combined_text,
            signals=signals,
            possible_needs=possible_needs,
            explicit_needs=explicit_needs,
            inferred_needs=inferred_needs,
            possible_priorities=possible_priorities,
            communication_implications=communication_implications,
            uncertainties=_unique(uncertainties),
            alternative_explanations=_unique(
                alternative_explanations
            ),
            evidence=evidence_items,
            epistemic_claims=epistemic_claims,
            confidence=confidence,
            reasoning_notes=reasoning_notes,
            metadata={
                "engine": self.ENGINE_NAME,
                "version": self.VERSION,
                "signal_count": len(signals),
            },
        )

    # ------------------------------------------------------------------
    # Context handling
    # ------------------------------------------------------------------

    def _build_context_text(
        self,
        text: str,
        context: Optional[Any],
    ) -> str:
        parts: List[str] = []

        text = _safe_text(text)

        if text:
            parts.append(text)

        if context is None:
            return "\n".join(parts)

        user_input = _safe_text(
            getattr(context, "user_input", "")
        )

        if user_input and user_input not in parts:
            parts.append(user_input)

        conversation_context = getattr(
            context,
            "conversation_context",
            [],
        )

        if conversation_context:
            parts.extend(
                _safe_text(item)
                for item in conversation_context
                if _safe_text(item)
            )

        known_facts = getattr(
            context,
            "known_facts",
            [],
        )

        if known_facts:
            parts.extend(
                _safe_text(item)
                for item in known_facts
                if _safe_text(item)
            )

        active_constraints = getattr(
            context,
            "active_constraints",
            [],
        )

        if active_constraints:
            parts.extend(
                _safe_text(item)
                for item in active_constraints
                if _safe_text(item)
            )

        return "\n".join(
            _unique(parts)
        )

    # ------------------------------------------------------------------
    # Explicit needs
    # ------------------------------------------------------------------

    def _extract_explicit_needs(
        self,
        text: str,
    ) -> List[str]:
        normalized = text.casefold()

        explicit: List[str] = []

        for need_type, patterns in self.NEED_PATTERNS.items():

            if any(
                explicit_pattern in normalized
                for explicit_pattern in self.EXPLICIT_NEED_PATTERNS
            ):
                if any(
                    pattern.casefold() in normalized
                    for pattern in patterns
                ):
                    explicit.append(need_type)

        return _unique(explicit)

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        matched_count: int,
        explicit: bool,
        context_available: bool,
    ) -> float:
        confidence = 0.35

        confidence += min(
            0.20,
            matched_count * 0.07,
        )

        if explicit:
            confidence += 0.20

        if context_available:
            confidence += 0.10

        return _clamp(confidence)

    # ------------------------------------------------------------------
    # Intensity
    # ------------------------------------------------------------------

    def _calculate_intensity(
        self,
        matched_count: int,
        explicit: bool,
    ) -> float:
        intensity = 0.25

        intensity += min(
            0.35,
            matched_count * 0.08,
        )

        if explicit:
            intensity += 0.20

        return _clamp(intensity)

    # ------------------------------------------------------------------
    # Priority derivation
    # ------------------------------------------------------------------

    def _derive_priorities(
        self,
        signals: Sequence[EmpathyNeedSignal],
        normalized_text: str,
    ) -> List[str]:

        priorities: List[str] = []

        priority_mapping = {
            "clarity": "clear understanding",
            "understanding": "understanding",
            "safety": "safety",
            "certainty": "certainty",
            "accuracy": "accuracy and verification",
            "control": "control and actionable direction",
            "autonomy": "autonomy and choice",
            "efficiency": "efficiency",
            "stability": "reliability and stability",
            "predictability": "predictability",
            "competence": "learning and competence",
            "achievement": "goal completion",
            "connection": "connection and support",
            "recognition": "recognition",
            "fairness": "fairness",
            "exploration": "exploration",
            "novelty": "novelty",
            "self_expression": "self-expression",
            "resource_preservation": "resource preservation",
        }

        ranked = sorted(
            signals,
            key=lambda signal: (
                signal.confidence * signal.intensity
            ),
            reverse=True,
        )

        for signal in ranked:
            priority = priority_mapping.get(
                signal.need_type
            )

            if priority:
                priorities.append(priority)

        # Direct urgency should raise attention to actionable
        # communication, but does not prove a psychological need.
        if any(
            phrase in normalized_text
            for phrase in (
                "urgent",
                "asap",
                "right now",
                "quickly",
            )
        ):
            priorities.append(
                "timely and actionable communication"
            )

        return _unique(priorities)

    # ------------------------------------------------------------------
    # Communication implications
    # ------------------------------------------------------------------

    def _derive_communication_implications(
        self,
        possible_needs: Sequence[str],
    ) -> List[str]:

        implications: List[str] = []

        mapping = {
            "clarity": (
                "Use clear language and make the main point explicit."
            ),
            "understanding": (
                "Explain reasoning and avoid unnecessary unexplained jargon."
            ),
            "safety": (
                "State important risks and safety constraints clearly."
            ),
            "certainty": (
                "Separate confirmed information from uncertainty."
            ),
            "accuracy": (
                "Show evidence or verification where it materially matters."
            ),
            "control": (
                "Provide concrete next steps or actionable options."
            ),
            "autonomy": (
                "Present meaningful options rather than unnecessarily "
                "removing the person's choice."
            ),
            "efficiency": (
                "Keep the response focused and avoid unnecessary steps."
            ),
            "stability": (
                "Emphasize reliable behavior, constraints, and recovery "
                "when relevant."
            ),
            "predictability": (
                "Explain expected next steps and important conditions."
            ),
            "competence": (
                "Teach the reasoning when learning appears relevant."
            ),
            "achievement": (
                "Connect the response to the stated objective."
            ),
            "connection": (
                "Use respectful and supportive communication."
            ),
            "recognition": (
                "Acknowledge relevant effort or explicitly stated concerns."
            ),
            "fairness": (
                "Explain relevant trade-offs and criteria transparently."
            ),
            "exploration": (
                "Offer useful alternatives or avenues for investigation."
            ),
            "novelty": (
                "Allow creative alternatives when they remain relevant."
            ),
            "self_expression": (
                "Preserve room for the person's stated preferences "
                "and creative direction."
            ),
            "resource_preservation": (
                "Avoid unnecessary use of time, money, attention, "
                "or other resources."
            ),
        }

        for need in possible_needs:
            implication = mapping.get(need)

            if implication:
                implications.append(implication)

        return _unique(implications)

    # ------------------------------------------------------------------
    # Overall confidence
    # ------------------------------------------------------------------

    def _overall_confidence(
        self,
        signals: Sequence[EmpathyNeedSignal],
        context_available: bool,
    ) -> float:

        if not signals:
            return 0.10

        values = [
            signal.confidence
            for signal in signals
        ]

        confidence = sum(values) / len(values)

        if context_available:
            confidence += 0.05

        return _clamp(confidence)

    # ------------------------------------------------------------------
    # Epistemic claims
    # ------------------------------------------------------------------

    def _build_claims(
        self,
        signals: Sequence[EmpathyNeedSignal],
        evidence: Sequence[EvidenceReference],
    ) -> List[EpistemicClaim]:

        claims: List[EpistemicClaim] = []

        for signal in signals:

            if signal.source == "explicit":
                epistemic_type = EpistemicType.FACT
                content = (
                    f"The available text explicitly indicates "
                    f"a possible {signal.need_type} need."
                )
            else:
                epistemic_type = EpistemicType.INFERENCE
                content = (
                    f"The available context may indicate a "
                    f"{signal.need_type} need."
                )

            claims.append(
                EpistemicClaim(
                    content=content,
                    epistemic_type=epistemic_type,
                    confidence=signal.confidence,
                    evidence=list(evidence),
                    rationale=signal.rationale,
                    source=self.ENGINE_NAME,
                )
            )

        return claims

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def infer(
        self,
        text: str = "",
        context: Optional[Any] = None,
    ) -> List[EmpathyNeedSignal]:
        """Return only detected need signals."""
        return self.analyze(
            text=text,
            context=context,
        ).signals

    def possible_needs(
        self,
        text: str = "",
        context: Optional[Any] = None,
    ) -> List[str]:
        """Return possible need categories."""
        return self.analyze(
            text=text,
            context=context,
        ).possible_needs

    def priorities(
        self,
        text: str = "",
        context: Optional[Any] = None,
    ) -> List[str]:
        """Return possible human-centered communication priorities."""
        return self.analyze(
            text=text,
            context=context,
        ).possible_priorities

    def reset(self) -> None:
        """
        Reset hook for interface compatibility.

        The current analyzer is stateless, so there is nothing
        persistent to clear.
        """
        return None

    def export_state(self) -> Dict[str, Any]:
        """
        Export analyzer metadata.

        The analyzer currently has no mutable state.
        """
        return {
            "engine": self.ENGINE_NAME,
            "version": self.VERSION,
            "stateful": False,
        }


__all__ = [
    "EmpathyNeedSignal",
    "EmpathyNeedsAssessment",
    "EmpathyNeedsAnalyzer",
      ]
