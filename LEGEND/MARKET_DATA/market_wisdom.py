"""
LEGEND Stage 13 — Market Wisdom Engine
=======================================

Builds reusable, evidence-weighted market wisdom from LEGEND's accumulated
observations.

Pipeline position:

    Market Data
        ↓
    Market State
        ↓
    Market DNA
        ↓
    Market Regime
        ↓
    Regime Memory
        ↓
    Historical Intelligence
        ↓
    Hypothesis Generator
        ↓
    Missing Information
        ↓
    Market Understanding
        ↓
    Market Influence Map
        ↓
    Participant Behavior
        ↓
    Market Wisdom

Core principle:
    A pattern is not automatically wisdom.

Wisdom becomes stronger only when a market lesson has:
    - clearly defined conditions
    - supporting evidence
    - opposing evidence considered
    - uncertainty explicitly represented
    - repeated historical/contextual support
    - known limitations
    - outcome feedback where available

This module does NOT:
    - fetch market data
    - fabricate evidence
    - guarantee future outcomes
    - convert historical behavior into certainty
    - generate BUY/SELL instructions
    - claim hidden participant intent
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


WISDOM_STATES = {
    "PROVISIONAL",
    "SUPPORTED",
    "CONTESTED",
    "WEAKENED",
    "INVALIDATED",
    "INSUFFICIENT_EVIDENCE",
}

EVIDENCE_TYPES = {
    "MARKET_STATE",
    "MARKET_DNA",
    "MARKET_REGIME",
    "HISTORICAL",
    "PARTICIPANT_BEHAVIOR",
    "INFLUENCE_MAP",
    "MARKET_UNDERSTANDING",
    "OUTCOME",
    "OTHER",
}


@dataclass
class WisdomEvidence:
    """
    One piece of evidence supporting or opposing a market lesson.
    """

    evidence_id: str
    evidence_type: str
    statement: str
    supports: bool = True
    strength: float = 0.0
    uncertainty: float = 1.0
    source: Optional[str] = None
    observed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MarketWisdom:
    """
    A reusable market lesson.

    'lesson' is deliberately descriptive rather than predictive.
    """

    wisdom_id: str
    title: str
    lesson: str

    conditions: List[str] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
    opposing_evidence: List[str] = field(default_factory=list)

    evidence_count: int = 0
    support_count: int = 0
    opposition_count: int = 0

    confidence: float = 0.0
    uncertainty: float = 1.0

    state: str = "PROVISIONAL"

    historical_support: int = 0
    historical_counterexamples: int = 0

    outcome_count: int = 0
    successful_outcome_count: int = 0
    unsuccessful_outcome_count: int = 0

    applicable_regimes: List[str] = field(default_factory=list)
    applicable_market_states: List[str] = field(default_factory=list)

    limitations: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketWisdomEngine:
    """
    LEGEND Stage 13.

    Converts accumulated market knowledge into explicit, reusable lessons.

    This is a knowledge layer, not a prediction layer.

    Example of acceptable wisdom:

        "During observed volatility-expansion regimes, breakout attempts
        have historically shown greater dispersion in outcomes than the
        same setup during stable-volatility regimes."

    Example of unacceptable logic:

        "Volatility expansion means price will rise."

    The first preserves conditions and uncertainty.
    The second makes an unsupported future claim.
    """

    VERSION = "0.1.0"
    COMPONENT = "LEGEND_MARKET_WISDOM"

    def __init__(
        self,
        max_wisdom_items: int = 1000,
        max_evidence_per_item: int = 200,
    ) -> None:
        self.max_wisdom_items = max(1, int(max_wisdom_items))
        self.max_evidence_per_item = max(1, int(max_evidence_per_item))

        self.wisdom: Dict[str, MarketWisdom] = {}
        self.evidence: Dict[str, List[WisdomEvidence]] = {}

        self.last_assessment: Dict[str, Any] = {}

    # ================================================================
    # Helpers
    # ================================================================

    @staticmethod
    def _clamp(
        value: Any,
        low: float = 0.0,
        high: float = 1.0,
    ) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return low

        return max(low, min(high, number))

    @staticmethod
    def _slug(value: str) -> str:
        return (
            str(value)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("/", "_")
        )

    @staticmethod
    def _dict(
        context: Dict[str, Any],
        *keys: str,
    ) -> Dict[str, Any]:
        for key in keys:
            value = context.get(key)

            if isinstance(value, dict):
                return value

        return {}

    @staticmethod
    def _list(
        context: Dict[str, Any],
        *keys: str,
    ) -> List[Any]:
        for key in keys:
            value = context.get(key)

            if isinstance(value, list):
                return value

        return []

    @staticmethod
    def _first_nonempty(*values: Any) -> Any:
        for value in values:
            if value not in (None, "", [], {}):
                return value

        return None

    # ================================================================
    # Wisdom creation
    # ================================================================

    def create_wisdom(
        self,
        title: str,
        lesson: str,
        conditions: Optional[Iterable[str]] = None,
        applicable_regimes: Optional[Iterable[str]] = None,
        applicable_market_states: Optional[Iterable[str]] = None,
        limitations: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        wisdom_id: Optional[str] = None,
    ) -> MarketWisdom:

        if not str(title).strip():
            raise ValueError("Wisdom title cannot be empty.")

        if not str(lesson).strip():
            raise ValueError("Wisdom lesson cannot be empty.")

        wisdom_id = wisdom_id or (
            f"wisdom:{self._slug(title)}"
        )

        item = MarketWisdom(
            wisdom_id=wisdom_id,
            title=str(title).strip(),
            lesson=str(lesson).strip(),
            conditions=list(conditions or []),
            applicable_regimes=list(
                applicable_regimes or []
            ),
            applicable_market_states=list(
                applicable_market_states or []
            ),
            limitations=list(limitations or []),
            metadata=dict(metadata or {}),
        )

        if not item.limitations:
            item.limitations = [
                "This lesson is contextual, not universally applicable.",
                "Historical support does not guarantee future behavior.",
                "Conflicting evidence must remain visible.",
                "Wisdom confidence depends on evidence quality.",
            ]

        self.wisdom[wisdom_id] = item

        if wisdom_id not in self.evidence:
            self.evidence[wisdom_id] = []

        self._enforce_limits()

        return item

    # ================================================================
    # Evidence
    # ================================================================

    def add_evidence(
        self,
        wisdom_id: str,
        evidence_type: str,
        statement: str,
        supports: bool = True,
        strength: float = 0.0,
        uncertainty: float = 1.0,
        source: Optional[str] = None,
        observed_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        evidence_id: Optional[str] = None,
    ) -> WisdomEvidence:

        if wisdom_id not in self.wisdom:
            raise KeyError(
                f"Wisdom item '{wisdom_id}' does not exist."
            )

        evidence_type = str(evidence_type).upper().strip()

        if evidence_type not in EVIDENCE_TYPES:
            evidence_type = "OTHER"

        if not str(statement).strip():
            raise ValueError(
                "Evidence statement cannot be empty."
            )

        evidence_id = evidence_id or (
            f"{wisdom_id}:evidence:"
            f"{len(self.evidence.get(wisdom_id, [])) + 1}"
        )

        item = WisdomEvidence(
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            statement=str(statement).strip(),
            supports=bool(supports),
            strength=self._clamp(strength),
            uncertainty=self._clamp(uncertainty),
            source=source,
            observed_at=observed_at or utc_now(),
            metadata=dict(metadata or {}),
        )

        self.evidence.setdefault(wisdom_id, []).append(item)

        if len(self.evidence[wisdom_id]) > self.max_evidence_per_item:
            self.evidence[wisdom_id] = (
                self.evidence[wisdom_id]
                [-self.max_evidence_per_item:]
            )

        self._recalculate(wisdom_id)

        return item

    # ================================================================
    # Recalculation
    # ================================================================

    def _recalculate(
        self,
        wisdom_id: str,
    ) -> None:

        item = self.wisdom.get(wisdom_id)

        if item is None:
            return

        evidence = self.evidence.get(wisdom_id, [])

        item.evidence_count = len(evidence)

        supporting = [
            x for x in evidence
            if x.supports
        ]

        opposing = [
            x for x in evidence
            if not x.supports
        ]

        item.support_count = len(supporting)
        item.opposition_count = len(opposing)

        item.supporting_evidence = [
            x.evidence_id
            for x in supporting
        ]

        item.opposing_evidence = [
            x.evidence_id
            for x in opposing
        ]

        if not evidence:
            item.confidence = 0.0
            item.uncertainty = 1.0
            item.state = "INSUFFICIENT_EVIDENCE"
            item.updated_at = utc_now()
            return

        support_strength = sum(
            x.strength
            for x in supporting
        )

        opposition_strength = sum(
            x.strength
            for x in opposing
        )

        total_strength = (
            support_strength +
            opposition_strength
        )

        if total_strength <= 0:
            evidence_balance = 0.0
        else:
            evidence_balance = (
                support_strength -
                opposition_strength
            ) / total_strength

        support_ratio = (
            len(supporting) / len(evidence)
        )

        uncertainty = sum(
            x.uncertainty
            for x in evidence
        ) / len(evidence)

        # Confidence reflects evidence quantity, strength and balance.
        # It deliberately cannot become certainty.
        confidence = (
            (self._clamp(support_ratio) * 0.35)
            + (self._clamp(
                (evidence_balance + 1.0) / 2.0
            ) * 0.35)
            + (self._clamp(
                min(len(evidence), 10) / 10.0
            ) * 0.30)
        )

        confidence *= (
            1.0 - (0.5 * uncertainty)
        )

        item.confidence = round(
            self._clamp(confidence),
            4,
        )

        item.uncertainty = round(
            self._clamp(uncertainty),
            4,
        )

        if (
            item.opposition_count > 0
            and opposition_strength >= support_strength
        ):
            item.state = "CONTESTED"

        elif item.confidence < 0.25:
            item.state = "INSUFFICIENT_EVIDENCE"

        elif item.confidence < 0.50:
            item.state = "PROVISIONAL"

        else:
            item.state = "SUPPORTED"

        if (
            item.historical_counterexamples >
            item.historical_support
            and item.historical_support > 0
        ):
            item.state = "CONTESTED"

        item.updated_at = utc_now()

    # ================================================================
    # Historical feedback
    # ================================================================

    def record_historical_support(
        self,
        wisdom_id: str,
        supported: bool,
        evidence_statement: str,
        strength: float = 0.5,
        uncertainty: float = 0.5,
        source: str = "historical_intelligence",
    ) -> None:

        item = self.wisdom.get(wisdom_id)

        if item is None:
            raise KeyError(
                f"Wisdom item '{wisdom_id}' does not exist."
            )

        if supported:
            item.historical_support += 1
        else:
            item.historical_counterexamples += 1

        self.add_evidence(
            wisdom_id=wisdom_id,
            evidence_type="HISTORICAL",
            statement=evidence_statement,
            supports=supported,
            strength=strength,
            uncertainty=uncertainty,
            source=source,
        )

    # ================================================================
    # Outcome feedback
    # ================================================================

    def record_outcome(
        self,
        wisdom_id: str,
        outcome_supported: bool,
        outcome_statement: str,
        strength: float = 0.5,
        uncertainty: float = 0.5,
        source: str = "outcome_learning",
    ) -> None:

        item = self.wisdom.get(wisdom_id)

        if item is None:
            raise KeyError(
                f"Wisdom item '{wisdom_id}' does not exist."
            )

        item.outcome_count += 1

        if outcome_supported:
            item.successful_outcome_count += 1
        else:
            item.unsuccessful_outcome_count += 1

        self.add_evidence(
            wisdom_id=wisdom_id,
            evidence_type="OUTCOME",
            statement=outcome_statement,
            supports=outcome_supported,
            strength=strength,
            uncertainty=uncertainty,
            source=source,
        )

    # ================================================================
    # Build wisdom from existing LEGEND context
    # ================================================================

    def derive_context_wisdom(
        self,
        context: Dict[str, Any],
    ) -> List[MarketWisdom]:

        created: List[MarketWisdom] = []

        state = self._dict(
            context,
            "market_state",
        )

        dna = self._dict(
            context,
            "market_dna",
        )

        regime = self._dict(
            context,
            "market_regime",
        )

        understanding = self._dict(
            context,
            "market_understanding",
        )

        participant = self._dict(
            context,
            "participant_behavior",
        )

        direction = self._first_nonempty(
            state.get("direction"),
            state.get("trend_direction"),
        )

        volatility = self._first_nonempty(
            state.get("volatility"),
            dna.get("volatility_behavior"),
        )

        regime_label = self._first_nonempty(
            regime.get("regime"),
            regime.get("regime_label"),
        )

        trend_persistence = dna.get(
            "trend_persistence"
        )

        # ------------------------------------------------------------
        # Direction + regime lesson
        # ------------------------------------------------------------

        if direction is not None and regime_label is not None:

            title = (
                f"{regime_label} directional context"
            )

            lesson = (
                f"Within the supplied evidence, directional behavior "
                f"of '{direction}' is occurring in a '{regime_label}' "
                f"regime context."
            )

            item = self.create_wisdom(
                title=title,
                lesson=lesson,
                conditions=[
                    f"direction={direction}",
                    f"regime={regime_label}",
                ],
                applicable_regimes=[
                    str(regime_label)
                ],
                limitations=[
                    "This describes the observed combination.",
                    "The relationship does not establish future direction.",
                    "The regime itself may transition.",
                ],
                metadata={
                    "derived_from": [
                        "market_state",
                        "market_regime",
                    ]
                },
            )

            self.add_evidence(
                item.wisdom_id,
                "MARKET_STATE",
                f"Observed direction: {direction}.",
                supports=True,
                strength=self._clamp(
                    state.get("confidence", 0.5)
                ),
                uncertainty=self._clamp(
                    state.get("uncertainty", 0.5)
                ),
                source="market_state",
            )

            self.add_evidence(
                item.wisdom_id,
                "MARKET_REGIME",
                f"Observed regime: {regime_label}.",
                supports=True,
                strength=self._clamp(
                    regime.get("confidence", 0.5)
                ),
                uncertainty=self._clamp(
                    regime.get("uncertainty", 0.5)
                ),
                source="market_regime",
            )

            created.append(item)

        # ------------------------------------------------------------
        # Volatility lesson
        # ------------------------------------------------------------

        if volatility is not None:

            title = (
                f"Observed volatility behavior: {volatility}"
            )

            lesson = (
                f"The supplied market context contains "
                f"'{volatility}' volatility behavior. Volatility "
                f"conditions should therefore be treated as part of "
                f"the market environment rather than ignored."
            )

            item = self.create_wisdom(
                title=title,
                lesson=lesson,
                conditions=[
                    f"volatility={volatility}"
                ],
                limitations=[
                    "Volatility alone does not establish price direction.",
                    "Volatility can change rapidly.",
                    "The meaning of volatility depends on market regime.",
                ],
                metadata={
                    "derived_from": [
                        "market_state",
                        "market_dna",
                    ]
                },
            )

            self.add_evidence(
                item.wisdom_id,
                "MARKET_STATE",
                f"Observed volatility: {volatility}.",
                supports=True,
                strength=self._clamp(
                    state.get("confidence", 0.5)
                ),
                uncertainty=self._clamp(
                    state.get("uncertainty", 0.5)
                ),
                source="market_state",
            )

            if dna.get("volatility_behavior") is not None:

                self.add_evidence(
                    item.wisdom_id,
                    "MARKET_DNA",
                    (
                        "Market DNA also records volatility behavior: "
                        f"{dna.get('volatility_behavior')}."
                    ),
                    supports=True,
                    strength=self._clamp(
                        dna.get("confidence", 0.5)
                    ),
                    uncertainty=self._clamp(
                        dna.get("uncertainty", 0.5)
                    ),
                    source="market_dna",
                )

            created.append(item)

        # ------------------------------------------------------------
        # Trend persistence lesson
        # ------------------------------------------------------------

        if trend_persistence is not None:

            item = self.create_wisdom(
                title="Trend persistence observation",
                lesson=(
                    "The supplied Market DNA contains measurable trend "
                    "persistence. This can be used as contextual evidence "
                    "when comparing current market behavior with historical "
                    "conditions."
                ),
                conditions=[
                    f"trend_persistence={trend_persistence}"
                ],
                limitations=[
                    "Persistence does not guarantee continuation.",
                    "Persistence may weaken during regime transitions.",
                    "Historical persistence must be evaluated against "
                    "counterexamples.",
                ],
                metadata={
                    "trend_persistence": trend_persistence,
                    "derived_from": ["market_dna"],
                },
            )

            self.add_evidence(
                item.wisdom_id,
                "MARKET_DNA",
                (
                    f"Observed trend persistence: "
                    f"{trend_persistence}."
                ),
                supports=True,
                strength=self._clamp(
                    dna.get("confidence", 0.5)
                ),
                uncertainty=self._clamp(
                    dna.get("uncertainty", 0.5)
                ),
                source="market_dna",
            )

            created.append(item)

        # ------------------------------------------------------------
        # Participant context lesson
        # ------------------------------------------------------------

        if participant:

            observation_count = participant.get(
                "observation_count",
                0,
            )

            if observation_count:

                item = self.create_wisdom(
                    title="Participant behavior requires evidence",
                    lesson=(
                        "Participant behavior can be incorporated into "
                        "market understanding only when the behavioral "
                        "claim is explicitly supported by observable "
                        "evidence."
                    ),
                    conditions=[
                        f"participant_observations={observation_count}"
                    ],
                    limitations=[
                        "Hidden positions are not directly observable.",
                        "Observed volume does not identify a participant.",
                        "Participant intent remains uncertain.",
                    ],
                    metadata={
                        "derived_from": [
                            "participant_behavior"
                        ]
                    },
                )

                self.add_evidence(
                    item.wisdom_id,
                    "PARTICIPANT_BEHAVIOR",
                    (
                        f"Participant behavior subsystem supplied "
                        f"{observation_count} observations."
                    ),
                    supports=True,
                    strength=0.5,
                    uncertainty=0.5,
                    source="participant_behavior",
                )

                created.append(item)

        return created

    # ================================================================
    # Queries
    # ================================================================

    def get_wisdom(
        self,
        wisdom_id: str,
    ) -> Optional[Dict[str, Any]]:

        item = self.wisdom.get(wisdom_id)

        if item is None:
            return None

        result = item.to_dict()

        result["evidence"] = [
            x.to_dict()
            for x in self.evidence.get(wisdom_id, [])
        ]

        return result

    def list_wisdom(
        self,
        state: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        results = []

        for item in self.wisdom.values():

            if state is not None:
                if item.state != str(state).upper():
                    continue

            results.append(item.to_dict())

        return results

    def strongest_wisdom(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:

        limit = max(1, int(limit))

        items = sorted(
            self.wisdom.values(),
            key=lambda x: (
                x.confidence,
                x.evidence_count,
                -x.uncertainty,
            ),
            reverse=True,
        )

        return [
            item.to_dict()
            for item in items[:limit]
        ]

    def contested_wisdom(self) -> List[Dict[str, Any]]:

        return [
            item.to_dict()
            for item in self.wisdom.values()
            if item.state == "CONTESTED"
        ]

    # ================================================================
    # Lifecycle
    # ================================================================

    def remove_wisdom(
        self,
        wisdom_id: str,
    ) -> bool:

        removed = self.wisdom.pop(
            wisdom_id,
            None,
        )

        self.evidence.pop(
            wisdom_id,
            None,
        )

        return removed is not None

    def clear(self) -> None:
        self.wisdom.clear()
        self.evidence.clear()
        self.last_assessment = {}

    def _enforce_limits(self) -> None:

        if len(self.wisdom) <= self.max_wisdom_items:
            return

        ordered = sorted(
            self.wisdom.values(),
            key=lambda x: x.updated_at,
        )

        remove_count = (
            len(self.wisdom) -
            self.max_wisdom_items
        )

        for item in ordered[:remove_count]:
            self.wisdom.pop(
                item.wisdom_id,
                None,
            )

            self.evidence.pop(
                item.wisdom_id,
                None,
            )

    # ================================================================
    # Shared context
    # ================================================================

    def analyze_into_context(
        self,
        context: Dict[str, Any],
        context_key: str = "market_wisdom",
        derive_from_context: bool = True,
    ) -> Dict[str, Any]:

        if not isinstance(context, dict):
            raise TypeError(
                "context must be a dictionary."
            )

        if derive_from_context:
            self.derive_context_wisdom(context)

        result = self.assess()

        context[context_key] = result
        context["market_wisdom_status"] = result[
            "status"
        ]

        return result

    # ================================================================
    # Overall assessment
    # ================================================================

    def assess(self) -> Dict[str, Any]:

        for wisdom_id in list(self.wisdom):
            self._recalculate(wisdom_id)

        items = list(self.wisdom.values())

        if not items:
            status = "INSUFFICIENT_EVIDENCE"
        elif any(
            x.state == "CONTESTED"
            for x in items
        ):
            status = "READY_WITH_CONTESTED_WISDOM"
        elif any(
            x.state == "SUPPORTED"
            for x in items
        ):
            status = "READY"
        else:
            status = "PROVISIONAL"

        confidence_values = [
            x.confidence
            for x in items
        ]

        uncertainty_values = [
            x.uncertainty
            for x in items
        ]

        overall_confidence = (
            sum(confidence_values) /
            len(confidence_values)
            if confidence_values
            else 0.0
        )

        overall_uncertainty = (
            sum(uncertainty_values) /
            len(uncertainty_values)
            if uncertainty_values
            else 1.0
        )

        result = {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "assessed_at": utc_now(),
            "status": status,
            "wisdom_count": len(items),
            "supported_count": sum(
                1
                for x in items
                if x.state == "SUPPORTED"
            ),
            "provisional_count": sum(
                1
                for x in items
                if x.state == "PROVISIONAL"
            ),
            "contested_count": sum(
                1
                for x in items
                if x.state == "CONTESTED"
            ),
            "insufficient_count": sum(
                1
                for x in items
                if x.state == "INSUFFICIENT_EVIDENCE"
            ),
            "overall_confidence": round(
                overall_confidence,
                4,
            ),
            "overall_uncertainty": round(
                overall_uncertainty,
                4,
            ),
            "wisdom": [
                x.to_dict()
                for x in items
            ],
            "principles": [
                "wisdom_is_not_prediction",
                "historical_support_is_not_guarantee",
                "counterexamples_must_remain_visible",
                "uncertainty_is_preserved",
                "context_matters",
                "participant_intent_is_not_assumed",
                "evidence_quality_controls_confidence",
            ],
        }

        self.last_assessment = result

        return result

    def status(self) -> Dict[str, Any]:

        return {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "status": "READY",
            "wisdom_count": len(self.wisdom),
            "evidence_count": sum(
                len(items)
                for items in self.evidence.values()
            ),
            "last_assessment_available": bool(
                self.last_assessment
            ),
            "last_status": self.last_assessment.get(
                "status"
            ),
            "checked_at": utc_now(),
        }


__all__ = [
    "WisdomEvidence",
    "MarketWisdom",
    "MarketWisdomEngine",
    "WISDOM_STATES",
    "EVIDENCE_TYPES",
          ]
