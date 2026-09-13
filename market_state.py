"""VALE LEGEND — MARKET STATE INTELLIGENCE, Stage 3. Additive only."""
from __future__ import annotations
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Dict, List, Optional, Sequence

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class LegendMarketState:
    VERSION = "0.1.0"
    STAGE = "LEGEND_MARKET_STATE_INTELLIGENCE"

    def __init__(self, minimum_observations: int = 3, momentum_lookback: int = 5) -> None:
        self.minimum_observations = max(2, int(minimum_observations))
        self.momentum_lookback = max(2, int(momentum_lookback))

    def analyze(self, market_data: Dict[str, Any], previous_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not isinstance(market_data, dict):
            return self._error("INVALID_INPUT", "market_data must be a dictionary.")
        observations = self._normalize_observations(self._extract_observations(market_data))
        if not observations:
            return self._error("INSUFFICIENT_DATA", "No observation contained a valid numeric close.")
        closes = [x["close"] for x in observations]
        volumes = [x["volume"] for x in observations if x.get("volume") is not None]
        latest = observations[-1]
        state = {
            "version": self.VERSION, "stage": self.STAGE, "analyzed_at": utc_now(),
            "instrument": market_data.get("instrument") or latest.get("instrument"),
            "asset_class": market_data.get("asset_class"), "exchange": market_data.get("exchange"),
            "timeframe": market_data.get("timeframe"), "observation_count": len(observations),
            "data_sufficiency": "SUFFICIENT" if len(closes) >= self.minimum_observations else "LIMITED",
            "latest": latest,
            "price_structure": self._price_structure(observations),
            "direction": self._direction(closes), "momentum": self._momentum(closes),
            "volatility": self._volatility(closes), "volume_behavior": self._volume_behavior(volumes),
            "range_behavior": self._range_behavior(observations),
            "quality_constraints": self._quality_constraints(market_data),
            "uncertainty": self._uncertainty(observations, closes),
        }
        state["interpretation"] = self._interpretation(state)
        state["state_change"] = self._compare_states(previous_state, state) if isinstance(previous_state, dict) else {"status": "NO_PREVIOUS_STATE", "changes": []}
        return {"success": True, "stage": self.STAGE, "version": self.VERSION, "status": "OBSERVABLE_STATE_ASSESSED", "market_state": state}

    def analyze_into_context(self, context: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(context, dict):
            return self._error("INVALID_CONTEXT", "context must be a dictionary.")
        result = self.analyze(market_data, context.get("market_state"))
        if not result.get("success"):
            context.setdefault("errors", []).append({"timestamp": utc_now(), "stage": self.STAGE, "status": result.get("status"), "error": result.get("error")})
            return result
        state = result["market_state"]
        context["market_state"] = state
        context["updated_at"] = utc_now()
        context.setdefault("observations", []).append({"timestamp": utc_now(), "type": "MARKET_STATE", "statement": state["interpretation"], "instrument": state.get("instrument"), "direction": state["direction"]["state"], "momentum": state["momentum"]["state"], "volatility": state["volatility"]["state"], "data_sufficiency": state["data_sufficiency"]})
        context.setdefault("timeline", []).append({"timestamp": utc_now(), "event": "market_state_assessed", "details": {"instrument": state.get("instrument"), "direction": state["direction"]["state"], "momentum": state["momentum"]["state"], "volatility": state["volatility"]["state"], "observation_count": state["observation_count"]}})
        return result

    @staticmethod
    def _extract_observations(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        for key in ("observations", "candles", "bars", "ohlcv"):
            value = data.get(key)
            if isinstance(value, list): return [x for x in value if isinstance(x, dict)]
        return [data] if any(k in data for k in ("close", "price", "last")) else []

    @staticmethod
    def _normalize_observations(observations: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for item in observations:
            close = LegendMarketState._number(item.get("close", item.get("price", item.get("last"))))
            if close is None or close <= 0: continue
            result.append({"timestamp": item.get("timestamp") or item.get("time"), "instrument": item.get("instrument"), "open": LegendMarketState._number(item.get("open")), "high": LegendMarketState._number(item.get("high")), "low": LegendMarketState._number(item.get("low")), "close": close, "volume": LegendMarketState._number(item.get("volume"))})
        return result

    @staticmethod
    def _number(value: Any) -> Optional[float]:
        try: n = float(value)
        except (TypeError, ValueError): return None
        return n if isfinite(n) else None

    def _price_structure(self, obs: List[Dict[str, Any]]) -> Dict[str, Any]:
        highs = [x["high"] for x in obs if x["high"] is not None]; lows = [x["low"] for x in obs if x["low"] is not None]
        if len(highs) < 2 or len(lows) < 2: return {"state":"INCOMPLETE","higher_highs":None,"higher_lows":None,"lower_highs":None,"lower_lows":None}
        hh, hl = highs[-1] > highs[-2], lows[-1] > lows[-2]; lh, ll = highs[-1] < highs[-2], lows[-1] < lows[-2]
        state = "HIGHER_HIGH_HIGHER_LOW" if hh and hl else "LOWER_HIGH_LOWER_LOW" if lh and ll else "MIXED_BULLISH_STRUCTURE" if hh or hl else "MIXED_BEARISH_STRUCTURE" if lh or ll else "FLAT_STRUCTURE"
        return {"state":state,"higher_highs":hh,"higher_lows":hl,"lower_highs":lh,"lower_lows":ll}

    @staticmethod
    def _direction(closes: List[float]) -> Dict[str, Any]:
        if len(closes) < 2: return {"state":"UNKNOWN","change":None,"change_pct":None}
        change = closes[-1] - closes[0]; pct = change / closes[0] * 100
        return {"state":"UP" if change > 0 else "DOWN" if change < 0 else "FLAT","change":change,"change_pct":pct}

    def _momentum(self, closes: List[float]) -> Dict[str, Any]:
        if len(closes) < self.minimum_observations: return {"state":"UNKNOWN","change_pct":None,"lookback":len(closes)}
        lookback = min(self.momentum_lookback, len(closes)); pct = (closes[-1] - closes[-lookback]) / closes[-lookback] * 100
        return {"state":"POSITIVE" if pct > 0 else "NEGATIVE" if pct < 0 else "NEUTRAL","change_pct":pct,"lookback":lookback}

    def _volatility(self, closes: List[float]) -> Dict[str, Any]:
        if len(closes) < self.minimum_observations: return {"state":"UNKNOWN","average_abs_change_pct":None}
        changes = [abs((b-a)/a)*100 for a,b in zip(closes[:-1],closes[1:]) if a]
        if not changes: return {"state":"UNKNOWN","average_abs_change_pct":None}
        avg = sum(changes)/len(changes); state = "LOW" if avg < .25 else "MODERATE" if avg < 1 else "HIGH"
        return {"state":state,"average_abs_change_pct":avg,"sample_count":len(changes)}

    @staticmethod
    def _volume_behavior(volumes: List[float]) -> Dict[str, Any]:
        if len(volumes) < 2: return {"state":"UNKNOWN","latest_vs_previous_pct":None}
        prev, latest = volumes[-2], volumes[-1]
        if prev == 0: return {"state":"UNDEFINED","latest_vs_previous_pct":None}
        pct=(latest-prev)/prev*100; return {"state":"INCREASING" if pct>5 else "DECREASING" if pct<-5 else "STABLE","latest_vs_previous_pct":pct}

    @staticmethod
    def _range_behavior(obs: List[Dict[str, Any]]) -> Dict[str, Any]:
        ranges=[x["high"]-x["low"] for x in obs if x["high"] is not None and x["low"] is not None and x["high"] >= x["low"]]
        if not ranges: return {"state":"UNKNOWN","latest_range":None}
        if len(ranges)<2: return {"state":"FIRST_OBSERVATION","latest_range":ranges[-1]}
        prev, latest=ranges[-2],ranges[-1]
        return {"state":"UNDEFINED" if prev==0 else "EXPANDING" if latest>prev else "CONTRACTING" if latest<prev else "STABLE","latest_range":latest,"previous_range":prev}

    @staticmethod
    def _quality_constraints(data: Dict[str, Any]) -> Dict[str, Any]:
        return {"constraints":[f"{k}={data[k]}" for k in ("quality","freshness_status","validation_status") if data.get(k) is not None],"source":data.get("source"),"source_type":data.get("source_type")}

    @staticmethod
    def _uncertainty(obs: List[Dict[str, Any]], closes: List[float]) -> Dict[str, Any]:
        reasons=[]
        if len(closes)<3: reasons.append("limited_observation_count")
        if any(x.get("timestamp") is None for x in obs): reasons.append("missing_timestamp_on_observation")
        if any(x.get("high") is None or x.get("low") is None for x in obs): reasons.append("incomplete_ohlc")
        return {"level":"ELEVATED" if reasons else "LOW","reasons":reasons}

    @staticmethod
    def _interpretation(state: Dict[str, Any]) -> str:
        instrument=state.get("instrument") or "the supplied instrument"
        return f"{instrument}: observable state is {state['direction']['state']} direction, {state['momentum']['state']} momentum, {state['volatility']['state']} volatility, with {state['price_structure']['state']} price structure. Data sufficiency is {state['data_sufficiency']}. This describes supplied observations and is not a prediction."

    @staticmethod
    def _compare_states(previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        changes=[]
        for group in ("direction","momentum","volatility"):
            old=previous.get(group,{}).get("state"); new=current.get(group,{}).get("state")
            if old != new: changes.append({"component":group,"from":old,"to":new})
        return {"status":"COMPARED","changes":changes}

    @staticmethod
    def _error(status: str, message: str) -> Dict[str, Any]:
        return {"success":False,"stage":LegendMarketState.STAGE,"version":LegendMarketState.VERSION,"status":status,"error":message}
