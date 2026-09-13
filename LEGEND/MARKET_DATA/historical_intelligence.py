"""
LEGEND Stage 7 — Historical Intelligence

Purpose:
    Analyze supplied historical market observations and identify comparable
    historical conditions across long time horizons.

Scope:
    - Supports configurable historical depth, including 50–100+ years when
      the underlying dataset actually contains that history.
    - Does not invent historical prices, dates, regimes, or events.
    - Does not fetch external historical data.
    - Does not produce BUY/SELL signals.
    - Historical similarity is descriptive evidence, never a guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from math import isfinite
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional, Sequence


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class HistoricalObservation:
    timestamp: str
    price: Optional[float] = None
    return_value: Optional[float] = None
    regime: Optional[str] = None
    volatility: Optional[float] = None
    volume: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HistoricalIntelligence:
    """
    Evidence-aware historical comparison engine.

    It can inspect a supplied historical dataset spanning decades or more,
    but it never assumes that older history is automatically relevant to the
    present.
    """

    VERSION = "0.1.0"
    DEFAULT_MAX_HISTORY_YEARS = 100
    MIN_HISTORY_YEARS = 1
    MAX_HISTORY_YEARS = 200

    def __init__(
        self,
        max_history_years: int = DEFAULT_MAX_HISTORY_YEARS,
        max_observations: int = 250_000,
    ) -> None:
        self.max_history_years = max(
            self.MIN_HISTORY_YEARS,
            min(self.MAX_HISTORY_YEARS, int(max_history_years)),
        )
        self.max_observations = max(100, int(max_observations))
        self._observations: List[HistoricalObservation] = []
        self._lock = RLock()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _number(value: Any) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if isfinite(number) else None

    @staticmethod
    def _timestamp(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _regime(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip().upper()
        return text or None

    def _normalize(self, item: Any) -> Optional[HistoricalObservation]:
        if isinstance(item, HistoricalObservation):
            return item

        if not isinstance(item, dict):
            return None

        timestamp = self._timestamp(
            item.get("timestamp")
            or item.get("time")
            or item.get("datetime")
            or item.get("date")
        )
        if not timestamp:
            return None

        return HistoricalObservation(
            timestamp=timestamp,
            price=self._number(item.get("price") or item.get("close")),
            return_value=self._number(
                item.get("return_value")
                if item.get("return_value") is not None
                else item.get("return")
            ),
            regime=self._regime(
                item.get("regime") or item.get("market_regime")
            ),
            volatility=self._number(item.get("volatility")),
            volume=self._number(item.get("volume")),
            metadata=dict(item.get("metadata") or {}),
        )

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest(
        self,
        observations: Iterable[Any],
        *,
        replace: bool = False,
    ) -> Dict[str, Any]:
        """
        Ingest already-supplied historical observations.

        The module deliberately accepts data only from the caller. It does not
        silently reach the Internet for missing history.
        """
        normalized: List[HistoricalObservation] = []

        for item in observations:
            record = self._normalize(item)
            if record is not None:
                normalized.append(record)

        with self._lock:
            if replace:
                self._observations.clear()

            self._observations.extend(normalized)

            if len(self._observations) > self.max_observations:
                self._observations = self._observations[
                    -self.max_observations :
                ]

        return {
            "success": True,
            "accepted": len(normalized),
            "rejected": max(0, len(list(observations)) - len(normalized))
            if not isinstance(observations, list)
            else len(observations) - len(normalized),
            "stored_count": self.size(),
        }

    def ingest_records(
        self,
        observations: Sequence[Dict[str, Any]],
        *,
        replace: bool = False,
    ) -> Dict[str, Any]:
        """Deterministic ingestion helper for list/sequence inputs."""
        normalized: List[HistoricalObservation] = []

        for item in observations:
            record = self._normalize(item)
            if record is not None:
                normalized.append(record)

        with self._lock:
            if replace:
                self._observations.clear()
            self._observations.extend(normalized)
            if len(self._observations) > self.max_observations:
                self._observations = self._observations[
                    -self.max_observations :
                ]

        return {
            "success": True,
            "accepted": len(normalized),
            "rejected": len(observations) - len(normalized),
            "stored_count": self.size(),
        }

    def size(self) -> int:
        with self._lock:
            return len(self._observations)

    # ------------------------------------------------------------------
    # Historical horizon
    # ------------------------------------------------------------------

    def coverage(self) -> Dict[str, Any]:
        with self._lock:
            records = list(self._observations)

        if not records:
            return {
                "available": False,
                "observation_count": 0,
                "oldest_timestamp": None,
                "newest_timestamp": None,
                "estimated_years": None,
            }

        timestamps = []
        for record in records:
            try:
                timestamps.append(
                    datetime.fromisoformat(record.timestamp.replace("Z", "+00:00"))
                )
            except ValueError:
                continue

        if not timestamps:
            return {
                "available": True,
                "observation_count": len(records),
                "oldest_timestamp": records[0].timestamp,
                "newest_timestamp": records[-1].timestamp,
                "estimated_years": None,
                "timestamp_quality": "UNPARSEABLE",
            }

        oldest = min(timestamps)
        newest = max(timestamps)
        years = max(0.0, (newest - oldest).total_seconds() / 31_556_952)

        return {
            "available": True,
            "observation_count": len(records),
            "oldest_timestamp": oldest.isoformat(),
            "newest_timestamp": newest.isoformat(),
            "estimated_years": round(years, 2),
            "supports_50_years": years >= 50,
            "supports_100_years": years >= 100,
            "timestamp_quality": "VALID",
        }

    # ------------------------------------------------------------------
    # Descriptive statistics
    # ------------------------------------------------------------------

    @staticmethod
    def _mean(values: List[float]) -> Optional[float]:
        return sum(values) / len(values) if values else None

    @staticmethod
    def _std(values: List[float]) -> Optional[float]:
        if len(values) < 2:
            return None
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5

    def summary(self, years: Optional[int] = None) -> Dict[str, Any]:
        with self._lock:
            records = list(self._observations)

        horizon = (
            self.max_history_years
            if years is None
            else max(self.MIN_HISTORY_YEARS, int(years))
        )

        prices = [
            record.price for record in records if record.price is not None
        ]
        returns = [
            record.return_value
            for record in records
            if record.return_value is not None
        ]
        volatilities = [
            record.volatility
            for record in records
            if record.volatility is not None
        ]

        regimes: Dict[str, int] = {}
        for record in records:
            if record.regime:
                regimes[record.regime] = regimes.get(record.regime, 0) + 1

        return {
            "horizon_requested_years": horizon,
            "observation_count": len(records),
            "price_observations": len(prices),
            "return_observations": len(returns),
            "volatility_observations": len(volatilities),
            "price_mean": self._mean(prices),
            "return_mean": self._mean(returns),
            "return_std": self._std(returns),
            "volatility_mean": self._mean(volatilities),
            "regime_counts": regimes,
            "coverage": self.coverage(),
        }

    # ------------------------------------------------------------------
    # Historical similarity
    # ------------------------------------------------------------------

    def find_comparable_conditions(
        self,
        current: Dict[str, Any],
        *,
        years_back: int = 100,
        limit: int = 20,
        tolerance: float = 0.20,
    ) -> Dict[str, Any]:
        """
        Find historical observations with similar supplied characteristics.

        Similarity is a transparent descriptive score. It is NOT a probability
        of future price movement.
        """
        horizon = max(self.MIN_HISTORY_YEARS, int(years_back))
        tolerance = max(0.01, min(1.0, float(tolerance)))

        current_regime = self._regime(
            current.get("regime") or current.get("market_regime")
        )
        current_vol = self._number(current.get("volatility"))
        current_return = self._number(
            current.get("return_value")
            if current.get("return_value") is not None
            else current.get("return")
        )

        with self._lock:
            records = list(self._observations)

        scored: List[Dict[str, Any]] = []

        for record in records:
            score_parts: List[float] = []
            reasons: List[str] = []

            if current_regime and record.regime:
                if current_regime == record.regime:
                    score_parts.append(1.0)
                    reasons.append("same_regime")
                else:
                    score_parts.append(0.0)

            if current_vol is not None and record.volatility is not None:
                denominator = max(abs(current_vol), 1e-12)
                distance = abs(record.volatility - current_vol) / denominator
                similarity = max(0.0, 1.0 - min(1.0, distance))
                if distance <= tolerance:
                    reasons.append("similar_volatility")
                score_parts.append(similarity)

            if current_return is not None and record.return_value is not None:
                denominator = max(abs(current_return), 1e-12)
                distance = abs(record.return_value - current_return) / denominator
                similarity = max(0.0, 1.0 - min(1.0, distance))
                if distance <= tolerance:
                    reasons.append("similar_return")
                score_parts.append(similarity)

            if not score_parts:
                continue

            score = sum(score_parts) / len(score_parts)

            scored.append(
                {
                    "timestamp": record.timestamp,
                    "regime": record.regime,
                    "price": record.price,
                    "return_value": record.return_value,
                    "volatility": record.volatility,
                    "similarity_score": round(score, 6),
                    "reasons": reasons,
                    "metadata": record.metadata,
                }
            )

        scored.sort(key=lambda item: item["similarity_score"], reverse=True)

        return {
            "success": True,
            "years_back_requested": horizon,
            "comparison_type": "DESCRIPTIVE_HISTORICAL_SIMILARITY",
            "prediction": False,
            "buy_sell_signal": False,
            "matches": scored[: max(1, int(limit))],
            "match_count": len(scored),
            "caution": (
                "Historical similarity does not establish future causality "
                "or guarantee a repeated outcome."
            ),
        }

    # ------------------------------------------------------------------
    # Context integration
    # ------------------------------------------------------------------

    def analyze_into_context(
        self,
        context: Dict[str, Any],
        current_conditions: Dict[str, Any],
        *,
        years_back: int = 100,
        limit: int = 20,
    ) -> Dict[str, Any]:
        if not isinstance(context, dict):
            raise TypeError("context must be a dictionary.")

        comparison = self.find_comparable_conditions(
            current_conditions,
            years_back=years_back,
            limit=limit,
        )
        coverage = self.coverage()

        historical_view = {
            "version": self.VERSION,
            "coverage": coverage,
            "comparison": comparison,
            "historical_depth_requested_years": int(years_back),
            "evidence_quality": self._evidence_quality(
                coverage,
                comparison["match_count"],
            ),
            "timestamp": utc_now(),
        }

        context["historical_intelligence"] = historical_view

        observations = context.setdefault("observations", [])
        if isinstance(observations, list):
            observations.append(
                {
                    "type": "historical_intelligence",
                    "timestamp": utc_now(),
                    "coverage_years": coverage.get("estimated_years"),
                    "matches": comparison["match_count"],
                }
            )

        return {
            "success": True,
            "historical_intelligence": historical_view,
        }

    @staticmethod
    def _evidence_quality(
        coverage: Dict[str, Any],
        match_count: int,
    ) -> str:
        years = coverage.get("estimated_years")
        count = int(coverage.get("observation_count") or 0)

        if not count or years is None:
            return "INSUFFICIENT"

        if years >= 100 and match_count >= 10:
            return "STRONG"
        if years >= 50 and match_count >= 5:
            return "MODERATE"
        if years >= 10 and match_count >= 2:
            return "LIMITED"
        return "WEAK"

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._observations.clear()

    def export(self) -> Dict[str, Any]:
        with self._lock:
            records = [record.to_dict() for record in self._observations]

        return {
            "version": self.VERSION,
            "records": records,
            "record_count": len(records),
            "coverage": self.coverage(),
        }

    def status(self) -> Dict[str, Any]:
        return {
            "module": "HistoricalIntelligence",
            "version": self.VERSION,
            "status": "READY",
            "max_history_years": self.max_history_years,
            "observation_count": self.size(),
            "coverage": self.coverage(),
        }


__all__ = [
    "HistoricalObservation",
    "HistoricalIntelligence",
]
