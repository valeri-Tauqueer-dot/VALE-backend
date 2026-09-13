"""
VALE LEGEND — MARKET REGIME DETECTION ENGINE
Stage 5 | Additive module

Purpose:
    Classify the CURRENT OBSERVABLE market regime from supplied evidence.

This module:
    - consumes supplied observations and/or Stage-3 Market State / Stage-4 Market DNA
    - classifies observable conditions such as trend, range, transition, volatility,
      expansion and contraction
    - separates regime classification from prediction
    - exposes evidence, data sufficiency and uncertainty
    - can compare the current regime with a previous regime
    - can write the result into LEGEND shared context

This module does NOT:
    - fetch market data
    - invent missing values
    - predict the next regime
    - generate BUY/SELL signals
    - claim a regime guarantees a future outcome

Architecture rule:
    Regime = description of the market environment supported by current evidence.
    Regime != forecast.
"""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LegendMarketRegime:
    """Stage-5 observable market regime detection engine."""

    VERSION = "0.1.0"
    STAGE = "LEGEND_MARKET_REGIME_DETECTION"

    REGIMES = (
        "TRENDING_UP",
        "TRENDING_DOWN",
        "RANGING",
        "VOLATILITY_EXPANSION",
        "VOLATILITY_CONTRACTION",
        "TRANSITION",
        "INSUFFICIENT_EVIDENCE",
    )

    def __init__(
        self,
        minimum_observations: int = 8,
        trend_threshold_pct: float = 1.0,
        range_threshold_pct: float = 0.75,
        volatility_change_threshold_pct: float = 20.0,
    ) -> None:
        self.minimum_observations = max(3, int(minimum_observations))
        self.trend_threshold_pct = max(0.0, float(trend_threshold_pct))
        self.range_threshold_pct = max(0.0, float(range_threshold_pct))
        self.volatility_change_threshold_pct = max(
            1.0, float(volatility_change_threshold_pct)
        )

    def analyze(
        self,
        market_data: Dict[str, Any],
        market_state: Optional[Dict[str, Any]] = None,
        market_dna: Optional[Dict[str, Any]] = None,
        previous_regime: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Classify the observable current regime from supplied evidence."""

        if not isinstance(market_data, dict):
            return self._error("INVALID_INPUT", "market_data must be a dictionary.")

        observations = self._normalize(
            self._extract_observations(market_data)
        )
        if not observations:
            return self._error(
                "INSUFFICIENT_DATA",
                "No valid close observations were supplied.",
            )

        closes = [item["close"] for item in observations]
        changes = self._returns(closes)
        volatility_series = self._rolling_volatility(changes)

        evidence = self._build_evidence(
            observations=observations,
            closes=closes,
            changes=changes,
            volatility_series=volatility_series,
            market_state=market_state,
            market_dna=market_dna,
        )

        sufficient = len(observations) >= self.minimum_observations
        regime, basis, score = self._classify(
            observations=observations,
            closes=closes,
            changes=changes,
            volatility_series=volatility_series,
            market_state=market_state,
            market_dna=market_dna,
            sufficient=sufficient,
        )

        confidence = self._confidence(
            observations=observations,
            regime=regime,
            evidence_count=len(evidence),
            market_state=market_state,
            market_dna=market_dna,
        )

        result_regime: Dict[str, Any] = {
            "version": self.VERSION,
            "stage": self.STAGE,
            "detected_at": utc_now(),
            "instrument": market_data.get("instrument")
            or observations[-1].get("instrument"),
            "regime": regime,
            "basis": basis,
            "classification_score": score,
            "confidence": confidence,
            "observation_count": len(observations),
            "data_sufficiency": "SUFFICIENT" if sufficient else "LIMITED",
            "market_state_reference": self._state_reference(market_state),
            "market_dna_reference": self._dna_reference(market_dna),
            "evidence": evidence,
            "uncertainty": self._uncertainty(
                observations=observations,
                changes=changes,
                market_data=market_data,
                regime=regime,
                sufficient=sufficient,
            ),
            "interpretation": self._interpretation(regime, basis, sufficient),
        }

        if isinstance(previous_regime, dict):
            result_regime["regime_change"] = self._compare(
                previous_regime, result_regime
            )
        else:
            result_regime["regime_change"] = {
                "status": "NO_PREVIOUS_REGIME",
                "changed": False,
                "from": None,
                "to": regime,
            }

        return {
            "success": True,
            "stage": self.STAGE,
            "version": self.VERSION,
            "status": "MARKET_REGIME_ASSESSED",
            "market_regime": result_regime,
        }

    def analyze_into_context(
        self,
        context: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add Stage-5 regime intelligence to LEGEND shared context."""

        if not isinstance(context, dict):
            return self._error("INVALID_CONTEXT", "context must be a dictionary.")

        result = self.analyze(
            market_data=market_data,
            market_state=context.get("market_state"),
            market_dna=context.get("market_dna"),
            previous_regime=context.get("market_regime"),
        )

        if not result.get("success"):
            context.setdefault("errors", []).append({
                "timestamp": utc_now(),
                "stage": self.STAGE,
                "status": result.get("status"),
                "error": result.get("error"),
            })
            return result

        regime = result["market_regime"]
        context["market_regime"] = regime
        context["updated_at"] = utc_now()
        context.setdefault("observations", []).append({
            "timestamp": utc_now(),
            "type": "MARKET_REGIME",
            "statement": regime["interpretation"],
            "instrument": regime.get("instrument"),
            "regime": regime["regime"],
            "confidence": regime["confidence"],
            "data_sufficiency": regime["data_sufficiency"],
        })
        context.setdefault("evidence", []).extend(regime["evidence"])
        context.setdefault("timeline", []).append({
            "timestamp": utc_now(),
            "event": "market_regime_assessed",
            "details": {
                "instrument": regime.get("instrument"),
                "regime": regime["regime"],
                "confidence": regime["confidence"],
                "data_sufficiency": regime["data_sufficiency"],
                "regime_change": regime["regime_change"],
            },
        })
        return result

    # ------------------------------------------------------------------
    # INPUT / NORMALIZATION
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_observations(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        for key in ("observations", "candles", "bars", "ohlcv"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [data] if any(k in data for k in ("close", "price", "last")) else []

    @staticmethod
    def _normalize(
        observations: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in observations:
            close = LegendMarketRegime._number(
                item.get("close", item.get("price", item.get("last")))
            )
            if close is None or close <= 0:
                continue
            normalized.append({
                "timestamp": item.get("timestamp") or item.get("time"),
                "instrument": item.get("instrument"),
                "open": LegendMarketRegime._number(item.get("open")),
                "high": LegendMarketRegime._number(item.get("high")),
                "low": LegendMarketRegime._number(item.get("low")),
                "close": close,
                "volume": LegendMarketRegime._number(item.get("volume")),
            })
        return normalized

    @staticmethod
    def _number(value: Any) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if isfinite(number) else None

    @staticmethod
    def _returns(closes: Sequence[float]) -> List[float]:
        values: List[float] = []
        for previous, current in zip(closes[:-1], closes[1:]):
            if previous == 0:
                continue
            values.append((current - previous) / previous * 100.0)
        return values

    @staticmethod
    def _rolling_volatility(changes: Sequence[float]) -> List[float]:
        """Return expanding-window mean absolute return volatility."""
        if not changes:
            return []
        series: List[float] = []
        window = max(3, min(5, len(changes)))
        for index in range(window, len(changes) + 1):
            sample = changes[index - window:index]
            series.append(mean(abs(value) for value in sample))
        return series

    # ------------------------------------------------------------------
    # CLASSIFICATION
    # ------------------------------------------------------------------

    def _classify(
        self,
        observations: List[Dict[str, Any]],
        closes: List[float],
        changes: List[float],
        volatility_series: List[float],
        market_state: Optional[Dict[str, Any]],
        market_dna: Optional[Dict[str, Any]],
        sufficient: bool,
    ) -> tuple[str, List[str], float]:
        if not sufficient:
            return (
                "INSUFFICIENT_EVIDENCE",
                ["observation_count_below_minimum"],
                0.0,
            )

        direction = self._state_value(market_state, "direction", "state")
        structure = self._state_value(market_state, "price_structure", "state")
        momentum = self._state_value(market_state, "momentum", "state")

        total_change = 0.0
        if closes and closes[0] != 0:
            total_change = (closes[-1] - closes[0]) / closes[0] * 100.0

        average_abs_return = (
            mean(abs(value) for value in changes) if changes else 0.0
        )

        volatility_expansion = self._volatility_expanding(volatility_series)
        volatility_contraction = self._volatility_contracting(volatility_series)

        basis: List[str] = []
        scores = {name: 0.0 for name in self.REGIMES}

        # Volatility regime gets priority when a clear recent change exists.
        if volatility_expansion:
            scores["VOLATILITY_EXPANSION"] += 3.0
            basis.append("recent_realized_volatility_is_expanding")
        if volatility_contraction:
            scores["VOLATILITY_CONTRACTION"] += 3.0
            basis.append("recent_realized_volatility_is_contracting")

        # Trend evidence: direction + momentum + structure + meaningful net move.
        if total_change >= self.trend_threshold_pct:
            scores["TRENDING_UP"] += 2.0
            basis.append("net_price_change_is_positive")
        elif total_change <= -self.trend_threshold_pct:
            scores["TRENDING_DOWN"] += 2.0
            basis.append("net_price_change_is_negative")

        if direction == "UP":
            scores["TRENDING_UP"] += 1.0
        elif direction == "DOWN":
            scores["TRENDING_DOWN"] += 1.0

        if momentum == "POSITIVE":
            scores["TRENDING_UP"] += 1.0
        elif momentum == "NEGATIVE":
            scores["TRENDING_DOWN"] += 1.0

        if structure == "HIGHER_HIGH_HIGHER_LOW":
            scores["TRENDING_UP"] += 2.0
            basis.append("higher_high_higher_low_structure")
        elif structure == "LOWER_HIGH_LOWER_LOW":
            scores["TRENDING_DOWN"] += 2.0
            basis.append("lower_high_lower_low_structure")
        elif structure in ("MIXED_BULLISH_STRUCTURE", "MIXED_BEARISH_STRUCTURE"):
            scores["TRANSITION"] += 1.5
            basis.append("mixed_price_structure")

        # Range evidence: small net movement relative to typical movement and
        # absence of a clean directional structure.
        if abs(total_change) <= self.range_threshold_pct:
            scores["RANGING"] += 2.0
            basis.append("limited_net_price_displacement")
        if structure in ("FLAT_STRUCTURE", "INCOMPLETE", None):
            scores["RANGING"] += 1.0

        # Mixed directional evidence is treated as transition rather than forced
        # into bullish/bearish classification.
        if direction in ("UP", "DOWN") and momentum in ("POSITIVE", "NEGATIVE"):
            if (direction == "UP" and momentum == "NEGATIVE") or (
                direction == "DOWN" and momentum == "POSITIVE"
            ):
                scores["TRANSITION"] += 2.5
                basis.append("direction_and_momentum_disagree")

        # DNA can reinforce observable characteristics without overriding raw data.
        dna_fp = self._dna_fingerprint(market_dna)
        trend_persistence = self._dna_state(dna_fp, "trend_persistence", "state")
        if trend_persistence == "PERSISTENT_UP":
            scores["TRENDING_UP"] += 1.0
            basis.append("dna_supports_persistent_upward_behavior")
        elif trend_persistence == "PERSISTENT_DOWN":
            scores["TRENDING_DOWN"] += 1.0
            basis.append("dna_supports_persistent_downward_behavior")

        if average_abs_return == 0:
            scores["RANGING"] += 1.0

        ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
        winner, winner_score = ranked[0]
        runner_up_score = ranked[1][1] if len(ranked) > 1 else 0.0

        # Close competition between regimes means the environment is better
        # represented as a transition than as a forced single state.
        if winner_score <= 0:
            return "TRANSITION", ["no_dominant_regime_signal"], 0.0
        if winner not in ("TRANSITION", "RANGING") and winner_score - runner_up_score < 1.0:
            basis.append("competing_regime_evidence")
            return "TRANSITION", basis, round(winner_score, 4)

        # Keep volatility labels descriptive, but only when they clearly dominate.
        if winner in ("VOLATILITY_EXPANSION", "VOLATILITY_CONTRACTION"):
            return winner, basis, round(winner_score, 4)

        return winner, basis, round(winner_score, 4)

    def _volatility_expanding(self, series: Sequence[float]) -> bool:
        if len(series) < 2 or series[-2] == 0:
            return False
        change_pct = (series[-1] - series[-2]) / series[-2] * 100.0
        return change_pct >= self.volatility_change_threshold_pct

    def _volatility_contracting(self, series: Sequence[float]) -> bool:
        if len(series) < 2 or series[-2] == 0:
            return False
        change_pct = (series[-1] - series[-2]) / series[-2] * 100.0
        return change_pct <= -self.volatility_change_threshold_pct

    # ------------------------------------------------------------------
    # EVIDENCE / QUALITY
    # ------------------------------------------------------------------

    def _build_evidence(
        self,
        observations: List[Dict[str, Any]],
        closes: List[float],
        changes: List[float],
        volatility_series: List[float],
        market_state: Optional[Dict[str, Any]],
        market_dna: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        evidence: List[Dict[str, Any]] = []
        if len(closes) >= 2 and closes[0] != 0:
            total_pct = (closes[-1] - closes[0]) / closes[0] * 100.0
            evidence.append({
                "type": "price_displacement",
                "value_pct": round(total_pct, 6),
                "observation_count": len(closes),
                "basis": "first_to_latest_close",
            })
        if changes:
            evidence.append({
                "type": "average_absolute_return",
                "value_pct": round(mean(abs(x) for x in changes), 6),
                "sample_count": len(changes),
            })
        if volatility_series:
            evidence.append({
                "type": "realized_volatility_proxy",
                "latest": round(volatility_series[-1], 6),
                "previous": round(volatility_series[-2], 6) if len(volatility_series) > 1 else None,
            })
        if market_state:
            evidence.append({
                "type": "market_state_reference",
                "direction": self._state_value(market_state, "direction", "state"),
                "momentum": self._state_value(market_state, "momentum", "state"),
                "structure": self._state_value(market_state, "price_structure", "state"),
            })
        if market_dna:
            evidence.append({
                "type": "market_dna_reference",
                "identity": market_dna.get("identity"),
                "data_sufficiency": market_dna.get("data_sufficiency"),
            })
        return evidence

    def _confidence(
        self,
        observations: List[Dict[str, Any]],
        regime: str,
        evidence_count: int,
        market_state: Optional[Dict[str, Any]],
        market_dna: Optional[Dict[str, Any]],
    ) -> float:
        if regime == "INSUFFICIENT_EVIDENCE":
            return 0.0

        confidence = 0.35
        if len(observations) >= self.minimum_observations:
            confidence += 0.15
        if len(observations) >= self.minimum_observations * 2:
            confidence += 0.10
        if evidence_count >= 3:
            confidence += 0.10
        if isinstance(market_state, dict):
            confidence += 0.10
        if isinstance(market_dna, dict):
            confidence += 0.05
        return round(min(0.85, confidence), 3)

    def _uncertainty(
        self,
        observations: List[Dict[str, Any]],
        changes: List[float],
        market_data: Dict[str, Any],
        regime: str,
        sufficient: bool,
    ) -> Dict[str, Any]:
        reasons: List[str] = []
        if not sufficient:
            reasons.append("limited_observation_count")
        if len(changes) < 5:
            reasons.append("short_return_sample")
        if any(item.get("timestamp") is None for item in observations):
            reasons.append("missing_timestamp_on_observation")
        if any(item.get("high") is None or item.get("low") is None for item in observations):
            reasons.append("incomplete_ohlc")
        for key in ("quality", "freshness_status", "validation_status"):
            if market_data.get(key) in ("STALE", "INVALID", "LOW", "UNKNOWN"):
                reasons.append(f"data_{key}_constraint")
        if regime == "TRANSITION":
            reasons.append("competing_or_mixed_regime_evidence")
        level = "HIGH" if len(reasons) >= 3 else "ELEVATED" if reasons else "LOW"
        return {"level": level, "reasons": reasons}

    # ------------------------------------------------------------------
    # REFERENCES / CHANGE DETECTION
    # ------------------------------------------------------------------

    @staticmethod
    def _state_value(data: Optional[Dict[str, Any]], group: str, field: str) -> Any:
        if not isinstance(data, dict):
            return None
        value = data.get(group)
        return value.get(field) if isinstance(value, dict) else None

    @staticmethod
    def _dna_fingerprint(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return {}
        fingerprint = data.get("fingerprint")
        return fingerprint if isinstance(fingerprint, dict) else {}

    @staticmethod
    def _dna_state(data: Dict[str, Any], group: str, field: str) -> Any:
        value = data.get(group)
        return value.get(field) if isinstance(value, dict) else None

    @staticmethod
    def _state_reference(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return {"available": False}
        return {
            "available": True,
            "direction": LegendMarketRegime._state_value(data, "direction", "state"),
            "momentum": LegendMarketRegime._state_value(data, "momentum", "state"),
            "volatility": LegendMarketRegime._state_value(data, "volatility", "state"),
            "structure": LegendMarketRegime._state_value(data, "price_structure", "state"),
        }

    @staticmethod
    def _dna_reference(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return {"available": False}
        fingerprint = LegendMarketRegime._dna_fingerprint(data)
        return {
            "available": True,
            "identity": data.get("identity"),
            "data_sufficiency": data.get("data_sufficiency"),
            "trend_persistence": LegendMarketRegime._dna_state(
                fingerprint, "trend_persistence", "state"
            ),
            "volatility_state": LegendMarketRegime._dna_state(
                fingerprint, "volatility_behavior", "state"
            ),
        }

    @staticmethod
    def _compare(
        previous: Dict[str, Any],
        current: Dict[str, Any],
    ) -> Dict[str, Any]:
        previous_value = previous.get("regime")
        current_value = current.get("regime")
        changed = previous_value != current_value
        return {
            "status": "COMPARED",
            "changed": changed,
            "from": previous_value,
            "to": current_value,
        }

    # ------------------------------------------------------------------
    # INTERPRETATION / ERROR
    # ------------------------------------------------------------------

    @staticmethod
    def _interpretation(
        regime: str,
        basis: List[str],
        sufficient: bool,
    ) -> str:
        evidence_text = ", ".join(basis[:3]) if basis else "limited distinguishing evidence"
        suffix = "" if sufficient else " Evidence is limited."
        return (
            f"Observable market regime is {regime}. "
            f"Classification is based on {evidence_text}. "
            f"This describes supplied market conditions and is not a prediction."
            f"{suffix}"
        )

    @staticmethod
    def _error(status: str, message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "stage": LegendMarketRegime.STAGE,
            "version": LegendMarketRegime.VERSION,
            "status": status,
            "error": message,
        }
