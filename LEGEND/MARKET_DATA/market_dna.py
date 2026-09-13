"""
VALE LEGEND — MARKET DNA ENGINE
Stage 4 | Additive module

Purpose:
    Identify recurring, observable characteristics ("DNA") of supplied
    market behaviour. This is descriptive intelligence, not prediction.

This module:
    - consumes observations already collected/validated upstream
    - measures recurring price, volatility, volume and range characteristics
    - produces a structured market fingerprint
    - records evidence and uncertainty
    - can compare a current fingerprint with a previous fingerprint

This module does NOT:
    - fetch market data
    - invent missing values
    - claim that a pattern guarantees a future outcome
    - generate BUY/SELL signals
"""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Sequence


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LegendMarketDNA:
    """Stage-4 Market DNA / observable market fingerprint engine."""

    VERSION = "0.1.0"
    STAGE = "LEGEND_MARKET_DNA_ENGINE"

    def __init__(self, minimum_observations: int = 5) -> None:
        self.minimum_observations = max(3, int(minimum_observations))

    def analyze(
        self,
        market_data: Dict[str, Any],
        market_state: Optional[Dict[str, Any]] = None,
        previous_dna: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a descriptive fingerprint from supplied observations."""

        if not isinstance(market_data, dict):
            return self._error("INVALID_INPUT", "market_data must be a dictionary.")

        observations = self._extract_observations(market_data)
        normalized = self._normalize(observations)

        if not normalized:
            return self._error(
                "INSUFFICIENT_DATA",
                "No valid close observations were supplied.",
            )

        closes = [x["close"] for x in normalized]
        changes = self._returns(closes)
        ranges = self._ranges(normalized)
        volumes = [
            x["volume"] for x in normalized
            if x.get("volume") is not None
        ]

        dna: Dict[str, Any] = {
            "version": self.VERSION,
            "stage": self.STAGE,
            "generated_at": utc_now(),
            "instrument": market_data.get("instrument")
            or normalized[-1].get("instrument"),
            "observation_count": len(normalized),
            "data_sufficiency": (
                "SUFFICIENT"
                if len(normalized) >= self.minimum_observations
                else "LIMITED"
            ),
            "fingerprint": {
                "price_behavior": self._price_behavior(closes, changes),
                "trend_persistence": self._trend_persistence(changes),
                "volatility_behavior": self._volatility_behavior(changes),
                "range_behavior": self._range_behavior(ranges),
                "volume_behavior": self._volume_behavior(volumes),
                "return_distribution": self._return_distribution(changes),
            },
            "market_state_reference": self._state_reference(market_state),
            "evidence": [],
            "uncertainty": {},
            "identity": None,
        }

        dna["evidence"] = self._build_evidence(dna)
        dna["uncertainty"] = self._uncertainty(
            normalized,
            changes,
            market_data,
        )
        dna["identity"] = self._identity(dna)

        if isinstance(previous_dna, dict):
            dna["dna_change"] = self._compare(previous_dna, dna)
        else:
            dna["dna_change"] = {
                "status": "NO_PREVIOUS_DNA",
                "changes": [],
            }

        return {
            "success": True,
            "stage": self.STAGE,
            "version": self.VERSION,
            "status": "MARKET_DNA_ASSESSED",
            "market_dna": dna,
        }

    def analyze_into_context(
        self,
        context: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add Stage-4 DNA intelligence to LEGEND shared context."""

        if not isinstance(context, dict):
            return self._error("INVALID_CONTEXT", "context must be a dictionary.")

        result = self.analyze(
            market_data=market_data,
            market_state=context.get("market_state"),
            previous_dna=context.get("market_dna"),
        )

        if not result.get("success"):
            context.setdefault("errors", []).append({
                "timestamp": utc_now(),
                "stage": self.STAGE,
                "status": result.get("status"),
                "error": result.get("error"),
            })
            return result

        dna = result["market_dna"]
        context["market_dna"] = dna
        context["updated_at"] = utc_now()

        context.setdefault("observations", []).append({
            "timestamp": utc_now(),
            "type": "MARKET_DNA",
            "statement": dna["identity"],
            "instrument": dna.get("instrument"),
            "data_sufficiency": dna["data_sufficiency"],
        })

        context.setdefault("evidence", []).extend(dna["evidence"])

        context.setdefault("timeline", []).append({
            "timestamp": utc_now(),
            "event": "market_dna_assessed",
            "details": {
                "instrument": dna.get("instrument"),
                "observation_count": dna["observation_count"],
                "data_sufficiency": dna["data_sufficiency"],
                "uncertainty": dna["uncertainty"],
            },
        })

        return result

    # ------------------------------------------------------------------
    # INPUT
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_observations(
        data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        for key in ("observations", "candles", "bars", "ohlcv"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]

        if any(k in data for k in ("close", "price", "last")):
            return [data]

        return []

    @staticmethod
    def _normalize(
        observations: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        result = []

        for item in observations:
            close = LegendMarketDNA._number(
                item.get("close", item.get("price", item.get("last")))
            )

            if close is None or close <= 0:
                continue

            result.append({
                "timestamp": item.get("timestamp") or item.get("time"),
                "instrument": item.get("instrument"),
                "open": LegendMarketDNA._number(item.get("open")),
                "high": LegendMarketDNA._number(item.get("high")),
                "low": LegendMarketDNA._number(item.get("low")),
                "close": close,
                "volume": LegendMarketDNA._number(item.get("volume")),
            })

        return result

    @staticmethod
    def _number(value: Any) -> Optional[float]:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None

        return value if isfinite(value) else None

    # ------------------------------------------------------------------
    # DNA COMPONENTS
    # ------------------------------------------------------------------

    @staticmethod
    def _returns(closes: List[float]) -> List[float]:
        result = []

        for previous, current in zip(closes[:-1], closes[1:]):
            if previous:
                result.append((current - previous) / previous * 100)

        return result

    @staticmethod
    def _ranges(observations: List[Dict[str, Any]]) -> List[float]:
        result = []

        for item in observations:
            high = item.get("high")
            low = item.get("low")

            if high is not None and low is not None and high >= low:
                result.append(high - low)

        return result

    @staticmethod
    def _price_behavior(
        closes: List[float],
        changes: List[float],
    ) -> Dict[str, Any]:
        if not changes:
            return {
                "state": "UNKNOWN",
                "net_change_pct": None,
                "positive_periods": 0,
                "negative_periods": 0,
            }

        net = ((closes[-1] - closes[0]) / closes[0]) * 100
        positive = sum(1 for x in changes if x > 0)
        negative = sum(1 for x in changes if x < 0)

        if net > 0:
            state = "NET_UP"
        elif net < 0:
            state = "NET_DOWN"
        else:
            state = "NET_FLAT"

        return {
            "state": state,
            "net_change_pct": net,
            "positive_periods": positive,
            "negative_periods": negative,
            "observed_periods": len(changes),
        }

    @staticmethod
    def _trend_persistence(changes: List[float]) -> Dict[str, Any]:
        if not changes:
            return {"state": "UNKNOWN", "same_direction_ratio": None}

        directions = [1 if x > 0 else -1 if x < 0 else 0 for x in changes]
        pairs = [
            (a, b) for a, b in zip(directions[:-1], directions[1:])
            if a != 0 and b != 0
        ]

        if not pairs:
            return {"state": "UNKNOWN", "same_direction_ratio": None}

        same = sum(1 for a, b in pairs if a == b)
        ratio = same / len(pairs)

        if ratio >= 0.70:
            state = "PERSISTENT"
        elif ratio <= 0.30:
            state = "FREQUENTLY_REVERSING"
        else:
            state = "MIXED"

        return {
            "state": state,
            "same_direction_ratio": ratio,
            "comparable_periods": len(pairs),
        }

    @staticmethod
    def _volatility_behavior(changes: List[float]) -> Dict[str, Any]:
        if not changes:
            return {
                "state": "UNKNOWN",
                "mean_abs_change_pct": None,
                "dispersion": None,
            }

        absolute = [abs(x) for x in changes]
        average = mean(absolute)
        dispersion = pstdev(changes) if len(changes) > 1 else 0.0

        if len(absolute) >= 4:
            first_half = mean(absolute[:len(absolute) // 2])
            second_half = mean(absolute[len(absolute) // 2:])

            if second_half > first_half * 1.20:
                state = "EXPANDING"
            elif second_half < first_half * 0.80:
                state = "CONTRACTING"
            else:
                state = "STABLE"
        else:
            state = "OBSERVATION_LIMITED"

        return {
            "state": state,
            "mean_abs_change_pct": average,
            "dispersion": dispersion,
        }

    @staticmethod
    def _range_behavior(ranges: List[float]) -> Dict[str, Any]:
        if not ranges:
            return {"state": "UNKNOWN", "latest_range": None}

        if len(ranges) < 2:
            return {
                "state": "OBSERVATION_LIMITED",
                "latest_range": ranges[-1],
            }

        previous = ranges[-2]
        latest = ranges[-1]

        if previous == 0:
            state = "UNDEFINED"
        elif latest > previous:
            state = "EXPANDING"
        elif latest < previous:
            state = "CONTRACTING"
        else:
            state = "STABLE"

        return {
            "state": state,
            "latest_range": latest,
            "previous_range": previous,
        }

    @staticmethod
    def _volume_behavior(volumes: List[float]) -> Dict[str, Any]:
        if len(volumes) < 2:
            return {
                "state": "UNKNOWN",
                "latest_vs_previous_pct": None,
            }

        previous, latest = volumes[-2], volumes[-1]

        if previous == 0:
            return {
                "state": "UNDEFINED",
                "latest_vs_previous_pct": None,
            }

        change = (latest - previous) / previous * 100

        return {
            "state": (
                "INCREASING" if change > 5
                else "DECREASING" if change < -5
                else "STABLE"
            ),
            "latest_vs_previous_pct": change,
        }

    @staticmethod
    def _return_distribution(changes: List[float]) -> Dict[str, Any]:
        if not changes:
            return {
                "mean_pct": None,
                "median_like": None,
                "max_gain_pct": None,
                "max_loss_pct": None,
            }

        ordered = sorted(changes)
        middle = len(ordered) // 2

        if len(ordered) % 2:
            median_like = ordered[middle]
        else:
            median_like = (ordered[middle - 1] + ordered[middle]) / 2

        return {
            "mean_pct": mean(changes),
            "median_like": median_like,
            "max_gain_pct": max(changes),
            "max_loss_pct": min(changes),
        }

    @staticmethod
    def _state_reference(
        market_state: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not isinstance(market_state, dict):
            return {"available": False}

        return {
            "available": True,
            "direction": market_state.get("direction", {}).get("state"),
            "momentum": market_state.get("momentum", {}).get("state"),
            "volatility": market_state.get("volatility", {}).get("state"),
            "price_structure": market_state.get(
                "price_structure", {}
            ).get("state"),
        }

    @staticmethod
    def _build_evidence(dna: Dict[str, Any]) -> List[Dict[str, Any]]:
        fingerprint = dna["fingerprint"]
        instrument = dna.get("instrument") or "supplied instrument"

        evidence = []

        for component, value in fingerprint.items():
            evidence.append({
                "timestamp": utc_now(),
                "type": "OBSERVATION",
                "source": "LEGEND_MARKET_DNA_ENGINE",
                "instrument": instrument,
                "component": component,
                "observation": value,
            })

        return evidence

    @staticmethod
    def _uncertainty(
        observations: List[Dict[str, Any]],
        changes: List[float],
        market_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        reasons = []

        if len(observations) < 5:
            reasons.append("limited_observation_count")

        if not changes:
            reasons.append("no_return_series")

        if any(x.get("timestamp") is None for x in observations):
            reasons.append("missing_timestamps")

        if market_data.get("freshness_status") in {
            "STALE",
            "UNKNOWN",
            "INVALID_FUTURE_TIMESTAMP",
        }:
            reasons.append("freshness_constraint")

        return {
            "level": "ELEVATED" if reasons else "LOW",
            "reasons": reasons,
        }

    @staticmethod
    def _identity(dna: Dict[str, Any]) -> str:
        instrument = dna.get("instrument") or "the supplied instrument"
        fp = dna["fingerprint"]

        return (
            f"{instrument} DNA fingerprint: "
            f"price={fp['price_behavior']['state']}, "
            f"persistence={fp['trend_persistence']['state']}, "
            f"volatility={fp['volatility_behavior']['state']}, "
            f"range={fp['range_behavior']['state']}, "
            f"volume={fp['volume_behavior']['state']}. "
            "This is a descriptive fingerprint of supplied observations, "
            "not a prediction or trading signal."
        )

    @staticmethod
    def _compare(
        previous: Dict[str, Any],
        current: Dict[str, Any],
    ) -> Dict[str, Any]:
        old_fp = previous.get("fingerprint", {})
        new_fp = current.get("fingerprint", {})
        changes = []

        for component in (
            "price_behavior",
            "trend_persistence",
            "volatility_behavior",
            "range_behavior",
            "volume_behavior",
        ):
            old_state = old_fp.get(component, {}).get("state")
            new_state = new_fp.get(component, {}).get("state")

            if old_state != new_state:
                changes.append({
                    "component": component,
                    "from": old_state,
                    "to": new_state,
                })

        return {
            "status": "COMPARED",
            "changes": changes,
        }

    @staticmethod
    def _error(status: str, message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "stage": LegendMarketDNA.STAGE,
            "version": LegendMarketDNA.VERSION,
            "status": status,
            "error": message,
        }
