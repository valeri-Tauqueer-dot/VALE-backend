"""
LEGEND Stage 12 — Market Participant Behavior Engine

Evidence-first modeling of observable/derived participant behavior.
No data fetching, fabricated positions, hidden-intent certainty, prediction,
or BUY/SELL instructions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


PARTICIPANT_CLASSES = {
    "INSTITUTIONAL", "RETAIL", "LIQUIDITY_PROVIDER", "HEDGER",
    "SPECULATOR", "ARBITRAGEUR", "MARKET_MAKER", "UNKNOWN",
}

BEHAVIOR_STATES = {
    "ACCUMULATION_PRESSURE", "DISTRIBUTION_PRESSURE",
    "MOMENTUM_PARTICIPATION", "LIQUIDITY_PROVISION",
    "HEDGING_ACTIVITY", "PROFIT_TAKING", "DELEVERAGING_PRESSURE",
    "RANGE_PARTICIPATION", "BREAKOUT_PARTICIPATION", "UNCERTAIN",
}


@dataclass
class ParticipantObservation:
    participant_class: str
    behavior_state: str
    statement: str
    evidence: List[str] = field(default_factory=list)
    source: Optional[str] = None
    strength: float = 0.0
    uncertainty: float = 1.0
    observation_time: Optional[str] = None
    direct_observation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class ParticipantAssessment:
    participant_class: str
    observed_signals: List[str] = field(default_factory=list)
    possible_behaviors: List[str] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
    opposing_evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    uncertainty: float = 1.0
    status: str = "INSUFFICIENT_EVIDENCE"
    intent_known: bool = False
    limitations: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class MarketParticipantBehaviorEngine:
    VERSION = "0.1.0"
    COMPONENT = "LEGEND_PARTICIPANT_BEHAVIOR"

    def __init__(self, max_observations: int = 1000):
        self.max_observations = max(1, int(max_observations))
        self.observations: List[ParticipantObservation] = []
        self.last_assessment: Dict[str, Any] = {}

    @staticmethod
    def _clamp(value, low=0.0, high=1.0):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return low
        return max(low, min(high, value))

    @staticmethod
    def _dict(context, *keys):
        for key in keys:
            value = context.get(key)
            if isinstance(value, dict):
                return value
        return {}

    @staticmethod
    def _list(context, *keys):
        for key in keys:
            value = context.get(key)
            if isinstance(value, list):
                return value
        return []

    @staticmethod
    def _value(data, *keys):
        for key in keys:
            if data.get(key) not in (None, "", [], {}):
                return data[key]
        return None

    def record_observation(
        self,
        participant_class: str,
        behavior_state: str,
        statement: str,
        evidence: Optional[Iterable[str]] = None,
        source: Optional[str] = None,
        strength: float = 0.0,
        uncertainty: float = 1.0,
        observation_time: Optional[str] = None,
        direct_observation: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ParticipantObservation:
        participant_class = str(participant_class).upper().strip()
        behavior_state = str(behavior_state).upper().strip()
        if participant_class not in PARTICIPANT_CLASSES:
            raise ValueError(f"Unknown participant class: {participant_class}")
        if behavior_state not in BEHAVIOR_STATES:
            raise ValueError(f"Unknown behavior state: {behavior_state}")
        if not str(statement).strip():
            raise ValueError("statement cannot be empty.")

        item = ParticipantObservation(
            participant_class=participant_class,
            behavior_state=behavior_state,
            statement=str(statement).strip(),
            evidence=list(evidence or []),
            source=source,
            strength=self._clamp(strength),
            uncertainty=self._clamp(uncertainty),
            observation_time=observation_time or utc_now(),
            direct_observation=bool(direct_observation),
            metadata=dict(metadata or {}),
        )
        self.observations.append(item)
        if len(self.observations) > self.max_observations:
            self.observations = self.observations[-self.max_observations:]
        return item

    def ingest_context_observations(self, context):
        results = []
        for item in self._list(context, "participant_observations",
                               "participant_behavior")[:200]:
            if not isinstance(item, dict) or not item.get("statement"):
                continue
            participant = str(item.get("participant_class", "UNKNOWN")).upper()
            behavior = str(item.get("behavior_state", "UNCERTAIN")).upper()
            if participant not in PARTICIPANT_CLASSES:
                participant = "UNKNOWN"
            if behavior not in BEHAVIOR_STATES:
                behavior = "UNCERTAIN"
            results.append(self.record_observation(
                participant, behavior, str(item["statement"]),
                item.get("evidence", []), item.get("source"),
                item.get("strength", item.get("confidence", 0.0)),
                item.get("uncertainty", 1.0),
                item.get("observation_time"),
                item.get("direct_observation", False),
                item.get("metadata", {}),
            ))
        return results

    def _derive_market_clues(self, context):
        state = self._dict(context, "market_state")
        dna = self._dict(context, "market_dna")
        regime = self._dict(context, "market_regime")
        return {
            "direction": self._value(state, "direction", "trend_direction"),
            "momentum": state.get("momentum"),
            "volume": self._value(state, "volume_behavior", "volume"),
            "volatility": self._value(
                state, "volatility", "volatility_behavior"
            ),
            "regime": self._value(regime, "regime", "regime_label"),
            "trend_persistence": dna.get("trend_persistence"),
        }

    def _derive_hypotheses(self, clues):
        generated = []

        def add(participant, behavior, statement, evidence, strength=0.25):
            generated.append(self.record_observation(
                participant, behavior, statement, evidence,
                "derived_market_context", strength, 0.75,
                direct_observation=False,
                metadata={"generated_hypothesis": True},
            ))

        volume = str(clues.get("volume") or "").upper()
        momentum = str(clues.get("momentum") or "").upper()
        regime = str(clues.get("regime") or "").upper()
        direction = str(clues.get("direction") or "").upper()
        volatility = str(clues.get("volatility") or "").upper()

        if any(x in volume for x in ("HIGH", "INCREAS", "ELEVAT", "SPIKE")):
            add("SPECULATOR", "MOMENTUM_PARTICIPATION",
                "Elevated activity is compatible with increased speculative "
                "participation, but participant identity is not established.",
                ["market_state.volume_behavior"], 0.30)
            add("INSTITUTIONAL", "UNCERTAIN",
                "Elevated activity may include larger-participant activity, "
                "but the supplied evidence does not identify institutions.",
                ["market_state.volume_behavior"], 0.20)

        if regime in {"RANGING", "TRANSITION"}:
            add("LIQUIDITY_PROVIDER", "RANGE_PARTICIPATION",
                "Range conditions are compatible with repeated two-sided "
                "liquidity participation; actual participants are unknown.",
                ["market_regime.regime"], 0.25)

        if regime in {"TRENDING_UP", "TRENDING_DOWN",
                      "VOLATILITY_EXPANSION"} and momentum:
            add("SPECULATOR", "BREAKOUT_PARTICIPATION",
                "Directional momentum and the current regime are compatible "
                "with momentum-oriented participation.",
                ["market_state.momentum", "market_regime.regime"], 0.30)

        if volatility in {"HIGH", "EXPANDING", "VOLATILITY_EXPANSION"}:
            add("HEDGER", "HEDGING_ACTIVITY",
                "Elevated volatility can be consistent with increased "
                "risk-management or hedging activity, but hedging cannot be "
                "confirmed from volatility alone.",
                ["market_state.volatility"], 0.20)

        if direction in {"UP", "UPWARD", "BULLISH"} and regime == "TRENDING_UP":
            add("SPECULATOR", "MOMENTUM_PARTICIPATION",
                "Persistent upward conditions are compatible with momentum "
                "participation.", ["market_state.direction",
                "market_regime.regime"], 0.30)

        if direction in {"DOWN", "DOWNWARD", "BEARISH"} and regime == "TRENDING_DOWN":
            add("SPECULATOR", "MOMENTUM_PARTICIPATION",
                "Persistent downward conditions are compatible with momentum "
                "participation.", ["market_state.direction",
                "market_regime.regime"], 0.30)
        return generated

    def _assessment_for(self, participant_class, observations):
        relevant = [x for x in observations
                    if x.participant_class == participant_class]
        if not relevant:
            return ParticipantAssessment(
                participant_class=participant_class,
                limitations=[
                    "No participant-specific evidence supplied.",
                    "Absence of evidence does not identify participant behavior.",
                ],
            )
        strengths = [x.strength for x in relevant]
        uncertainties = [x.uncertainty for x in relevant]
        return ParticipantAssessment(
            participant_class=participant_class,
            observed_signals=[x.statement for x in relevant],
            possible_behaviors=list(dict.fromkeys(
                x.behavior_state for x in relevant
            )),
            supporting_evidence=list(dict.fromkeys(
                e for x in relevant for e in x.evidence
            )),
            confidence=round(sum(strengths) / len(strengths), 4),
            uncertainty=round(sum(uncertainties) / len(uncertainties), 4),
            status=("OBSERVED" if all(x.direct_observation for x in relevant)
                    else "HYPOTHESIS"),
            intent_known=False,
            limitations=[
                "Hidden positions are not directly observable.",
                "Behavioral compatibility does not establish participant identity.",
                "Intent is not inferred as fact.",
            ],
        )

    def assess(self, context=None, generate_hypotheses=True):
        context = dict(context or {})
        self.ingest_context_observations(context)
        if generate_hypotheses:
            self._derive_hypotheses(self._derive_market_clues(context))

        assessments = [
            self._assessment_for(name, self.observations)
            for name in sorted(PARTICIPANT_CLASSES)
        ]
        result = {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "assessed_at": utc_now(),
            "status": "READY" if self.observations else "INSUFFICIENT_EVIDENCE",
            "observation_count": len(self.observations),
            "observations": [x.to_dict() for x in self.observations[-300:]],
            "assessments": [x.to_dict() for x in assessments],
            "intent_known": False,
            "causal_certainty": False,
            "limitations": [
                "Participant behavior is inferred only from supplied evidence.",
                "A market variable does not uniquely identify a participant class.",
                "Observed volume does not prove institutional activity.",
                "Price movement does not prove hidden participant intent.",
                "Behavioral hypotheses must remain falsifiable.",
            ],
        }
        self.last_assessment = result
        return result

    def analyze_into_context(self, context, context_key="participant_behavior",
                             generate_hypotheses=True):
        if not isinstance(context, dict):
            raise TypeError("context must be a dictionary.")
        result = self.assess(context, generate_hypotheses)
        context[context_key] = result
        context["participant_behavior_status"] = result["status"]
        return result

    def by_participant(self, participant_class):
        participant_class = str(participant_class).upper().strip()
        return [x.to_dict() for x in self.observations
                if x.participant_class == participant_class]

    def by_behavior(self, behavior_state):
        behavior_state = str(behavior_state).upper().strip()
        return [x.to_dict() for x in self.observations
                if x.behavior_state == behavior_state]

    def clear_observations(self):
        self.observations.clear()
        self.last_assessment = {}

    def status(self):
        return {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "status": "READY",
            "observation_count": len(self.observations),
            "participant_classes": sorted(PARTICIPANT_CLASSES),
            "behavior_states": sorted(BEHAVIOR_STATES),
            "last_assessment_available": bool(self.last_assessment),
            "checked_at": utc_now(),
        }


__all__ = [
    "ParticipantObservation",
    "ParticipantAssessment",
    "MarketParticipantBehaviorEngine",
    "PARTICIPANT_CLASSES",
    "BEHAVIOR_STATES",
]
