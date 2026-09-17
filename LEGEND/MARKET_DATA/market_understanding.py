"""
LEGEND Stage 10 — Market Understanding Engine

Transforms outputs from Market State, Market DNA, Market Regime, Historical
Intelligence, Hypotheses, and Missing Information into an auditable,
descriptive understanding of the market.

No market-data fetching, fabrication, prediction, or BUY/SELL instructions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvidenceItem:
    category: str
    statement: str
    source: Optional[str] = None
    strength: float = 0.0
    observed: bool = True
    uncertainty: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MarketInterpretation:
    interpretation_type: str
    statement: str
    supporting_evidence: List[str] = field(default_factory=list)
    opposing_evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    uncertainty: float = 1.0
    status: str = "UNRESOLVED"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketUnderstandingEngine:
    """
    Stage 10 of LEGEND.

    Produces descriptive market understanding from evidence already available
    in shared context. Observations, interpretations, uncertainty, missing
    information, and contradictions remain explicitly distinguishable.
    """

    VERSION = "0.1.0"
    COMPONENT = "LEGEND_MARKET_UNDERSTANDING"

    def __init__(self, max_history: int = 200) -> None:
        self.max_history = max(1, int(max_history))
        self.last_understanding: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []

    @staticmethod
    def _dict(context: Dict[str, Any], *keys: str) -> Dict[str, Any]:
        for key in keys:
            value = context.get(key)
            if isinstance(value, dict):
                return value
        return {}

    @staticmethod
    def _list(context: Dict[str, Any], *keys: str) -> List[Any]:
        for key in keys:
            value = context.get(key)
            if isinstance(value, list):
                return value
        return []

    @staticmethod
    def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return low
        return max(low, min(high, number))

    @staticmethod
    def _first_nonempty(*values: Any) -> Any:
        for value in values:
            if value not in (None, "", [], {}):
                return value
        return None

    @staticmethod
    def _summarize(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                "type": "dict",
                "keys": list(value.keys())[:20],
                "key_count": len(value),
            }
        if isinstance(value, (list, tuple)):
            return {"type": "sequence", "length": len(value)}
        if isinstance(value, str) and len(value) > 180:
            return value[:177] + "..."
        return value

    def collect_evidence(self, context: Dict[str, Any]) -> List[EvidenceItem]:
        evidence: List[EvidenceItem] = []

        state = self._dict(context, "market_state")
        for key in (
            "direction", "trend_direction", "price_structure", "momentum",
            "volatility", "volume_behavior", "range_behavior",
        ):
            if state.get(key) not in (None, "", [], {}):
                evidence.append(EvidenceItem(
                    "MARKET_STATE", f"{key}: {state[key]}",
                    "market_state",
                    self._clamp(state.get("confidence", 0.5)),
                    True,
                    self._clamp(state.get("uncertainty", 0.5)),
                ))

        dna = self._dict(context, "market_dna")
        for key in (
            "price_behavior", "trend_persistence", "volatility_behavior",
            "range_behavior", "volume_behavior", "return_distribution",
            "fingerprint",
        ):
            if dna.get(key) not in (None, "", [], {}):
                evidence.append(EvidenceItem(
                    "MARKET_DNA", f"{key}: {dna[key]}",
                    "market_dna",
                    self._clamp(dna.get("confidence", 0.5)),
                    True,
                    self._clamp(dna.get("uncertainty", 0.5)),
                ))

        regime = self._dict(context, "market_regime")
        for key in (
            "regime", "regime_label", "evidence", "data_sufficiency",
        ):
            if regime.get(key) not in (None, "", [], {}):
                evidence.append(EvidenceItem(
                    "REGIME", f"{key}: {regime[key]}",
                    "market_regime",
                    self._clamp(regime.get("confidence", 0.5)),
                    True,
                    self._clamp(regime.get("uncertainty", 0.5)),
                ))

        historical = self._dict(context, "historical_intelligence")
        for key in (
            "coverage", "sample_count", "comparable_conditions",
            "historical_regimes", "evidence_quality",
        ):
            if historical.get(key) not in (None, "", [], {}):
                evidence.append(EvidenceItem(
                    "HISTORICAL", f"{key}: {historical[key]}",
                    "historical_intelligence",
                    self._clamp(historical.get("evidence_quality", 0.5)),
                    True,
                    self._clamp(historical.get("uncertainty", 0.5)),
                ))

        hypotheses = self._list(context, "hypotheses")
        for index, hypothesis in enumerate(hypotheses[:50]):
            if not isinstance(hypothesis, dict):
                continue
            statement = self._first_nonempty(
                hypothesis.get("statement"),
                hypothesis.get("hypothesis"),
                hypothesis.get("description"),
            )
            if statement:
                evidence.append(EvidenceItem(
                    "HYPOTHESIS",
                    str(statement),
                    "hypothesis_generator",
                    self._clamp(hypothesis.get("confidence", 0.0)),
                    False,
                    self._clamp(hypothesis.get("uncertainty", 1.0)),
                    {"index": index},
                ))

        return evidence

    def _build_observations(
        self, evidence: Iterable[EvidenceItem]
    ) -> List[str]:
        observations: List[str] = []
        seen = set()
        for item in evidence:
            if not item.observed:
                continue
            text = item.statement.strip()
            if text and text not in seen:
                observations.append(text)
                seen.add(text)
        return observations

    def _build_interpretations(
        self, context: Dict[str, Any]
    ) -> List[MarketInterpretation]:
        state = self._dict(context, "market_state")
        dna = self._dict(context, "market_dna")
        regime = self._dict(context, "market_regime")

        confidence_values = [
            self._clamp(state.get("confidence", 0)),
            self._clamp(dna.get("confidence", 0)),
            self._clamp(regime.get("confidence", 0)),
        ]
        positive = [x for x in confidence_values if x > 0]
        confidence = sum(positive) / len(positive) if positive else 0.0

        uncertainty_values = [
            self._clamp(state.get("uncertainty", 1)),
            self._clamp(dna.get("uncertainty", 1)),
            self._clamp(regime.get("uncertainty", 1)),
        ]
        uncertainty = sum(uncertainty_values) / len(uncertainty_values)

        interpretations: List[MarketInterpretation] = []

        direction = self._first_nonempty(
            state.get("direction"), state.get("trend_direction")
        )
        regime_label = self._first_nonempty(
            regime.get("regime"), regime.get("regime_label")
        )
        volatility = self._first_nonempty(
            state.get("volatility"), dna.get("volatility_behavior")
        )
        structure = self._first_nonempty(
            state.get("range_behavior"), dna.get("range_behavior"),
            state.get("price_structure")
        )
        momentum = state.get("momentum")

        if direction is not None:
            interpretations.append(MarketInterpretation(
                "DIRECTIONAL_CONTEXT",
                f"Observed directional context: {direction}.",
                ["market_state.direction"],
                confidence=confidence,
                uncertainty=uncertainty,
                status="SUPPORTED",
            ))

        if regime_label is not None:
            interpretations.append(MarketInterpretation(
                "REGIME_CONTEXT",
                f"Observed market regime context: {regime_label}.",
                ["market_regime.regime"],
                confidence=self._clamp(regime.get("confidence", confidence)),
                uncertainty=self._clamp(regime.get("uncertainty", uncertainty)),
                status="SUPPORTED",
            ))

        if volatility is not None:
            interpretations.append(MarketInterpretation(
                "VOLATILITY_CONTEXT",
                f"Observed volatility behavior: {volatility}.",
                ["market_state.volatility", "market_dna.volatility_behavior"],
                confidence=confidence,
                uncertainty=uncertainty,
                status="SUPPORTED",
            ))

        if structure is not None:
            interpretations.append(MarketInterpretation(
                "STRUCTURAL_CONTEXT",
                f"Observed price/range structure: {structure}.",
                ["market_state", "market_dna"],
                confidence=confidence,
                uncertainty=uncertainty,
                status="SUPPORTED",
            ))

        if momentum is not None:
            interpretations.append(MarketInterpretation(
                "MOMENTUM_CONTEXT",
                f"Observed momentum context: {momentum}.",
                ["market_state.momentum"],
                confidence=confidence,
                uncertainty=uncertainty,
                status="SUPPORTED",
            ))

        if not interpretations:
            interpretations.append(MarketInterpretation(
                "EVIDENCE_LIMIT",
                "Insufficient structured evidence for a reliable descriptive "
                "market understanding.",
                confidence=0.0,
                uncertainty=1.0,
                status="INSUFFICIENT_EVIDENCE",
            ))

        return interpretations

    def _detect_conflicts(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        conflicts: List[Dict[str, Any]] = []
        state = self._dict(context, "market_state")
        regime = self._dict(context, "market_regime")

        direction = str(self._first_nonempty(
            state.get("direction"), state.get("trend_direction")
        ) or "").upper()
        regime_label = str(self._first_nonempty(
            regime.get("regime"), regime.get("regime_label")
        ) or "").upper()

        up = {"UP", "UPWARD", "BULLISH", "TRENDING_UP"}
        down = {"DOWN", "DOWNWARD", "BEARISH", "TRENDING_DOWN"}

        if direction in up and regime_label == "TRENDING_DOWN":
            conflicts.append({
                "type": "DIRECTION_REGIME_CONFLICT",
                "severity": "MATERIAL",
                "details": "Market State indicates upward direction while "
                           "Market Regime indicates TRENDING_DOWN.",
                "resolution": "UNRESOLVED",
            })
        elif direction in down and regime_label == "TRENDING_UP":
            conflicts.append({
                "type": "DIRECTION_REGIME_CONFLICT",
                "severity": "MATERIAL",
                "details": "Market State indicates downward direction while "
                           "Market Regime indicates TRENDING_UP.",
                "resolution": "UNRESOLVED",
            })

        upstream = context.get("contradictions")
        if isinstance(upstream, list):
            for item in upstream[:50]:
                if isinstance(item, dict):
                    conflicts.append({
                        "type": "UPSTREAM_CONTRADICTION",
                        "severity": item.get("severity", "UNKNOWN"),
                        "details": item.get(
                            "details",
                            item.get("description", "Unspecified contradiction.")
                        ),
                        "resolution": item.get("resolution", "UNRESOLVED"),
                    })
        return conflicts

    def understand(
        self,
        context: Optional[Dict[str, Any]] = None,
        analysis_type: str = "market_analysis",
    ) -> Dict[str, Any]:
        context = dict(context or {})
        evidence = self.collect_evidence(context)
        observations = self._build_observations(evidence)
        interpretations = self._build_interpretations(context)
        conflicts = self._detect_conflicts(context)

        readiness = self._dict(context, "information_readiness")
        missing = self._dict(context, "missing_information")

        if readiness:
            information_ready = readiness.get("ready_for_analysis")
            readiness_score = readiness.get("readiness_score")
        else:
            information_ready = missing.get("ready_for_analysis")
            readiness_score = missing.get("readiness_score")

        observed = [x for x in evidence if x.observed]
        uncertainty = (
            sum(x.uncertainty for x in observed) / len(observed)
            if observed else 1.0
        )
        strength = (
            sum(x.strength for x in observed) / len(observed)
            if observed else 0.0
        )

        result = {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "analysis_type": str(analysis_type).strip().lower(),
            "understood_at": utc_now(),
            "status": (
                "READY_WITH_CONFLICTS" if conflicts and observations
                else "READY" if observations
                else "INSUFFICIENT_EVIDENCE"
            ),
            "observations": observations,
            "interpretations": [x.to_dict() for x in interpretations],
            "conflicts": conflicts,
            "evidence": [x.to_dict() for x in evidence],
            "evidence_count": len(evidence),
            "observed_evidence_count": len(observed),
            "hypothesis_count": len(evidence) - len(observed),
            "evidence_strength": round(strength, 4),
            "overall_uncertainty": round(uncertainty, 4),
            "information_ready": information_ready,
            "information_readiness_score": readiness_score,
            "limits": [
                "descriptive_understanding_only",
                "future_direction_not_guaranteed",
                "historical_similarity_is_not_prediction",
                "unresolved_conflicts_remain_visible",
                "missing_information_remains_explicit",
            ],
        }

        self.last_understanding = result
        self._history.append(result)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]
        return result

    def analyze_into_context(
        self,
        context: Dict[str, Any],
        analysis_type: str = "market_analysis",
        context_key: str = "market_understanding",
    ) -> Dict[str, Any]:
        if not isinstance(context, dict):
            raise TypeError("context must be a dictionary.")
        result = self.understand(context, analysis_type)
        context[context_key] = result
        context["market_understanding_status"] = result["status"]
        context["market_understanding_uncertainty"] = result[
            "overall_uncertainty"
        ]
        return result

    def latest(self) -> Dict[str, Any]:
        return dict(self.last_understanding)

    def history(self, limit: int = 20) -> List[Dict[str, Any]]:
        limit = max(1, int(limit))
        return [dict(x) for x in self._history[-limit:]]

    def clear_history(self) -> None:
        self._history.clear()

    def status(self) -> Dict[str, Any]:
        return {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "status": "READY",
            "history_size": len(self._history),
            "last_status": self.last_understanding.get("status"),
            "last_evidence_count": self.last_understanding.get("evidence_count"),
            "last_uncertainty": self.last_understanding.get("overall_uncertainty"),
            "checked_at": utc_now(),
        }


__all__ = [
    "EvidenceItem",
    "MarketInterpretation",
    "MarketUnderstandingEngine",
]
