"""
LEGEND Stage 8 — AI Hypothesis Generator

Purpose:
    Generate explicit, testable hypotheses from already supplied LEGEND market
    observations, market state, DNA, regime, and historical context.

Rules:
    - Never invent market observations.
    - Never treat a hypothesis as a fact.
    - Never produce BUY/SELL instructions.
    - Every hypothesis must identify supporting and missing evidence.
    - Competing hypotheses are preserved to reduce confirmation bias.
    - Historical similarity is context, not proof.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MarketHypothesis:
    hypothesis_id: str
    statement: str
    category: str
    status: str = "UNTESTED"
    evidence_for: List[str] = field(default_factory=list)
    evidence_against: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    uncertainty: float = 1.0
    source_observations: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HypothesisGenerator:
    """Evidence-aware generator of descriptive market hypotheses."""

    VERSION = "0.1.0"

    CATEGORIES = (
        "TREND_CONTINUATION",
        "TREND_EXHAUSTION",
        "RANGE_PERSISTENCE",
        "VOLATILITY_EXPANSION",
        "VOLATILITY_CONTRACTION",
        "REGIME_TRANSITION",
        "VOLUME_CONFIRMATION",
        "VOLUME_DIVERGENCE",
        "STRUCTURAL_CHANGE",
        "INSUFFICIENT_EVIDENCE",
    )

    def __init__(self, max_hypotheses: int = 100) -> None:
        self.max_hypotheses = max(10, int(max_hypotheses))
        self._hypotheses: List[MarketHypothesis] = []
        self._counter = 0
        self._lock = RLock()

    @staticmethod
    def _clamp(value: Any, default: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(1.0, number))

    @staticmethod
    def _list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        if isinstance(value, Iterable):
            result = []
            for item in value:
                text = str(item).strip()
                if text and text not in result:
                    result.append(text)
            return result
        return []

    def _new_id(self) -> str:
        with self._lock:
            self._counter += 1
            return f"HYP-{self._counter:06d}"

    def _create(
        self,
        statement: str,
        category: str,
        *,
        evidence_for: Optional[Iterable[str]] = None,
        evidence_against: Optional[Iterable[str]] = None,
        missing_evidence: Optional[Iterable[str]] = None,
        confidence: float = 0.0,
        uncertainty: float = 1.0,
        source_observations: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MarketHypothesis:
        return MarketHypothesis(
            hypothesis_id=self._new_id(),
            statement=statement,
            category=category,
            evidence_for=self._list(evidence_for),
            evidence_against=self._list(evidence_against),
            missing_evidence=self._list(missing_evidence),
            confidence=self._clamp(confidence, 0.0),
            uncertainty=self._clamp(uncertainty, 1.0),
            source_observations=self._list(source_observations),
            metadata=dict(metadata or {}),
        )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        *,
        market_state: Optional[Dict[str, Any]] = None,
        market_dna: Optional[Dict[str, Any]] = None,
        regime: Optional[Dict[str, Any]] = None,
        historical: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate multiple competing explanations from supplied evidence.

        The engine intentionally avoids forecasting language. Statements are
        framed as hypotheses about what the supplied observations may represent.
        """
        state = dict(market_state or {})
        dna = dict(market_dna or {})
        regime_data = dict(regime or {})
        historical_data = dict(historical or {})

        hypotheses: List[MarketHypothesis] = []

        direction = str(
            state.get("direction")
            or state.get("market_direction")
            or ""
        ).upper()
        momentum = str(state.get("momentum") or "").upper()
        volatility = str(state.get("volatility") or "").upper()
        range_behavior = str(
            state.get("range_behavior")
            or state.get("range")
            or ""
        ).upper()
        regime_name = str(
            regime_data.get("regime")
            or regime_data.get("current_regime")
            or state.get("regime")
            or ""
        ).upper()
        volume_behavior = str(
            state.get("volume_behavior")
            or state.get("volume")
            or ""
        ).upper()

        common_missing = [
            "higher-resolution price history",
            "reliable volume history",
            "validated multi-timeframe context",
        ]

        # Trend-related competing hypotheses.
        if direction in {"UP", "UPWARD", "BULLISH"}:
            hypotheses.append(
                self._create(
                    "The observed upward structure may represent persistent directional behavior.",
                    "TREND_CONTINUATION",
                    evidence_for=[
                        f"Observed direction: {direction}.",
                    ],
                    missing_evidence=common_missing,
                    confidence=0.35,
                    uncertainty=0.65,
                    source_observations=["market_state.direction"],
                )
            )
            hypotheses.append(
                self._create(
                    "The observed upward structure may be approaching exhaustion rather than representing durable continuation.",
                    "TREND_EXHAUSTION",
                    evidence_for=[
                        "An upward structure exists, so exhaustion remains a competing explanation.",
                    ],
                    missing_evidence=[
                        "momentum deterioration evidence",
                        "structural failure evidence",
                        "multi-timeframe confirmation",
                    ],
                    confidence=0.15,
                    uncertainty=0.85,
                    source_observations=["market_state.direction"],
                )
            )

        elif direction in {"DOWN", "DOWNWARD", "BEARISH"}:
            hypotheses.append(
                self._create(
                    "The observed downward structure may represent persistent directional behavior.",
                    "TREND_CONTINUATION",
                    evidence_for=[
                        f"Observed direction: {direction}.",
                    ],
                    missing_evidence=common_missing,
                    confidence=0.35,
                    uncertainty=0.65,
                    source_observations=["market_state.direction"],
                )
            )
            hypotheses.append(
                self._create(
                    "The observed downward structure may be approaching exhaustion rather than representing durable continuation.",
                    "TREND_EXHAUSTION",
                    evidence_for=[
                        "A downward structure exists, so exhaustion remains a competing explanation.",
                    ],
                    missing_evidence=[
                        "momentum deterioration evidence",
                        "structural failure evidence",
                        "multi-timeframe confirmation",
                    ],
                    confidence=0.15,
                    uncertainty=0.85,
                    source_observations=["market_state.direction"],
                )
            )

        if range_behavior in {"RANGE", "RANGING", "SIDEWAYS", "CONSOLIDATION"}:
            hypotheses.append(
                self._create(
                    "The observed market structure may be maintaining a range-bound state.",
                    "RANGE_PERSISTENCE",
                    evidence_for=[f"Observed range behavior: {range_behavior}."],
                    missing_evidence=[
                        "validated range boundaries",
                        "breakout/breakdown evidence",
                    ],
                    confidence=0.40,
                    uncertainty=0.60,
                    source_observations=["market_state.range_behavior"],
                )
            )

        if volatility in {"EXPANDING", "EXPANSION", "HIGH"}:
            hypotheses.append(
                self._create(
                    "The market may currently be undergoing a volatility-expansion state.",
                    "VOLATILITY_EXPANSION",
                    evidence_for=[f"Observed volatility state: {volatility}."],
                    missing_evidence=[
                        "duration of volatility expansion",
                        "cross-timeframe volatility confirmation",
                    ],
                    confidence=0.40,
                    uncertainty=0.60,
                    source_observations=["market_state.volatility"],
                )
            )

        if volatility in {"CONTRACTING", "CONTRACTION", "LOW"}:
            hypotheses.append(
                self._create(
                    "The market may currently be undergoing a volatility-contraction state.",
                    "VOLATILITY_CONTRACTION",
                    evidence_for=[f"Observed volatility state: {volatility}."],
                    missing_evidence=[
                        "duration of volatility contraction",
                        "cross-timeframe confirmation",
                    ],
                    confidence=0.40,
                    uncertainty=0.60,
                    source_observations=["market_state.volatility"],
                )
            )

        if volume_behavior:
            hypotheses.append(
                self._create(
                    f"Observed volume behavior ({volume_behavior}) may be confirming or challenging the current price structure.",
                    "VOLUME_CONFIRMATION" if "CONFIRM" in volume_behavior else "VOLUME_DIVERGENCE",
                    evidence_for=[f"Observed volume behavior: {volume_behavior}."],
                    missing_evidence=[
                        "normalized volume baseline",
                        "comparable historical volume context",
                    ],
                    confidence=0.30,
                    uncertainty=0.70,
                    source_observations=["market_state.volume_behavior"],
                )
            )

        if regime_name in {"TRANSITION", "UNKNOWN", "INSUFFICIENT_EVIDENCE"}:
            hypotheses.append(
                self._create(
                    "The available evidence may be insufficient to establish a stable market regime.",
                    "INSUFFICIENT_EVIDENCE",
                    evidence_for=[f"Observed regime state: {regime_name or 'UNKNOWN'}."],
                    missing_evidence=[
                        "additional validated observations",
                        "stable multi-timeframe structure",
                    ],
                    confidence=0.60,
                    uncertainty=0.40,
                    source_observations=["market_regime"],
                )
            )
        elif regime_name:
            hypotheses.append(
                self._create(
                    f"The market may currently be operating within the observed {regime_name} regime.",
                    "REGIME_TRANSITION" if "TRANS" in regime_name else "STRUCTURAL_CHANGE",
                    evidence_for=[f"Observed regime: {regime_name}."],
                    missing_evidence=[
                        "regime persistence confirmation",
                        "independent supporting evidence",
                    ],
                    confidence=0.35,
                    uncertainty=0.65,
                    source_observations=["market_regime"],
                )
            )

        if historical_data:
            hypotheses.append(
                self._create(
                    "Historical observations may contain comparable conditions that can be used to test the present interpretation.",
                    "STRUCTURAL_CHANGE",
                    evidence_for=["Historical intelligence is available for comparison."],
                    missing_evidence=[
                        "validated similarity across multiple independent features",
                        "evidence that historical conditions are structurally comparable",
                    ],
                    confidence=0.25,
                    uncertainty=0.75,
                    source_observations=["historical_intelligence"],
                    metadata={"historical_context_used": True},
                )
            )

        if not hypotheses:
            hypotheses.append(
                self._create(
                    "There is currently insufficient structured evidence to form a useful market hypothesis.",
                    "INSUFFICIENT_EVIDENCE",
                    missing_evidence=[
                        "validated market observations",
                        "market state",
                        "regime context",
                    ],
                    confidence=0.05,
                    uncertainty=0.95,
                )
            )

        # Preserve diversity while respecting the configured bound.
        hypotheses = hypotheses[: self.max_hypotheses]

        with self._lock:
            self._hypotheses.extend(hypotheses)
            if len(self._hypotheses) > self.max_hypotheses:
                self._hypotheses = self._hypotheses[-self.max_hypotheses :]

        return {
            "success": True,
            "version": self.VERSION,
            "hypotheses": [item.to_dict() for item in hypotheses],
            "count": len(hypotheses),
            "all_are_hypotheses": True,
            "prediction": False,
            "buy_sell_signal": False,
            "generated_at": utc_now(),
        }

    # ------------------------------------------------------------------
    # Evaluation / state
    # ------------------------------------------------------------------

    def update_evidence(
        self,
        hypothesis_id: str,
        *,
        evidence_for: Optional[Iterable[str]] = None,
        evidence_against: Optional[Iterable[str]] = None,
        missing_evidence: Optional[Iterable[str]] = None,
        confidence: Optional[float] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            for hypothesis in self._hypotheses:
                if hypothesis.hypothesis_id != hypothesis_id:
                    continue

                if evidence_for:
                    hypothesis.evidence_for.extend(
                        x for x in self._list(evidence_for)
                        if x not in hypothesis.evidence_for
                    )
                if evidence_against:
                    hypothesis.evidence_against.extend(
                        x for x in self._list(evidence_against)
                        if x not in hypothesis.evidence_against
                    )
                if missing_evidence:
                    hypothesis.missing_evidence = self._list(missing_evidence)
                if confidence is not None:
                    hypothesis.confidence = self._clamp(confidence, hypothesis.confidence)
                    hypothesis.uncertainty = 1.0 - hypothesis.confidence
                if status:
                    hypothesis.status = str(status).strip().upper()

                return {"success": True, "hypothesis": hypothesis.to_dict()}

        return {"success": False, "error": "Hypothesis not found."}

    def all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [item.to_dict() for item in self._hypotheses]

    def latest(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [item.to_dict() for item in self._hypotheses[-max(1, int(limit)) :]]

    def clear(self) -> None:
        with self._lock:
            self._hypotheses.clear()

    # ------------------------------------------------------------------
    # Context integration
    # ------------------------------------------------------------------

    def analyze_into_context(
        self,
        context: Dict[str, Any],
        *,
        market_state: Optional[Dict[str, Any]] = None,
        market_dna: Optional[Dict[str, Any]] = None,
        regime: Optional[Dict[str, Any]] = None,
        historical: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not isinstance(context, dict):
            raise TypeError("context must be a dictionary.")

        result = self.generate(
            market_state=market_state,
            market_dna=market_dna,
            regime=regime,
            historical=historical,
        )

        context["market_hypotheses"] = {
            "version": self.VERSION,
            "hypotheses": result["hypotheses"],
            "count": result["count"],
            "generated_at": result["generated_at"],
            "prediction": False,
            "buy_sell_signal": False,
        }

        observations = context.setdefault("observations", [])
        if isinstance(observations, list):
            observations.append(
                {
                    "type": "hypothesis_generation",
                    "timestamp": utc_now(),
                    "hypothesis_count": result["count"],
                }
            )

        return {
            "success": True,
            "market_hypotheses": context["market_hypotheses"],
        }

    def status(self) -> Dict[str, Any]:
        return {
            "module": "HypothesisGenerator",
            "version": self.VERSION,
            "status": "READY",
            "stored_hypotheses": len(self._hypotheses),
            "categories": list(self.CATEGORIES),
        }


__all__ = [
    "MarketHypothesis",
    "HypothesisGenerator",
]
