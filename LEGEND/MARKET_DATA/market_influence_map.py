"""
LEGEND Stage 11 — Market Influence Map
========================================

Maps observable factors that may influence a market state and the
relationships between them.

This is an evidence-mapping component, not a causal-certainty engine.
It distinguishes:
    OBSERVED      -> directly present in supplied evidence
    ASSOCIATED    -> relationship supported by supplied context
    HYPOTHESIZED  -> plausible but not established
    UNKNOWN       -> insufficient evidence

It does not fetch data, fabricate relationships, predict prices, or issue
BUY/SELL instructions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


OBSERVED = "OBSERVED"
ASSOCIATED = "ASSOCIATED"
HYPOTHESIZED = "HYPOTHESIZED"
UNKNOWN = "UNKNOWN"


@dataclass
class InfluenceNode:
    node_id: str
    name: str
    category: str
    value: Any = None
    source: Optional[str] = None
    evidence_strength: float = 0.0
    uncertainty: float = 1.0
    status: str = OBSERVED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InfluenceRelationship:
    relationship_id: str
    source_node: str
    target_node: str
    relationship_type: str
    direction: str = "UNKNOWN"
    strength: float = 0.0
    uncertainty: float = 1.0
    evidence: List[str] = field(default_factory=list)
    status: str = ASSOCIATED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketInfluenceMap:
    """
    LEGEND Stage 11.

    Maintains a structured graph of market factors and their supported or
    hypothesized relationships.

    The engine never treats correlation, timing, or market folklore as proof
    of causation. Causal claims must remain explicitly qualified.
    """

    VERSION = "0.1.0"
    COMPONENT = "LEGEND_MARKET_INFLUENCE_MAP"

    def __init__(self, max_nodes: int = 500, max_relationships: int = 1500):
        self.max_nodes = max(1, int(max_nodes))
        self.max_relationships = max(1, int(max_relationships))
        self.nodes: Dict[str, InfluenceNode] = {}
        self.relationships: Dict[str, InfluenceRelationship] = {}
        self.last_map: Dict[str, Any] = {}

    @staticmethod
    def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return low
        return max(low, min(high, value))

    @staticmethod
    def _slug(value: str) -> str:
        return (
            str(value).strip().lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("/", "_")
        )

    @staticmethod
    def _dict(context: Dict[str, Any], *keys: str) -> Dict[str, Any]:
        for key in keys:
            value = context.get(key)
            if isinstance(value, dict):
                return value
        return {}

    def add_node(
        self,
        name: str,
        category: str,
        value: Any = None,
        source: Optional[str] = None,
        evidence_strength: float = 0.0,
        uncertainty: float = 1.0,
        status: str = OBSERVED,
        metadata: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None,
    ) -> InfluenceNode:
        node_id = node_id or f"{self._slug(category)}:{self._slug(name)}"
        node = InfluenceNode(
            node_id=node_id,
            name=str(name),
            category=str(category),
            value=value,
            source=source,
            evidence_strength=self._clamp(evidence_strength),
            uncertainty=self._clamp(uncertainty),
            status=status,
            metadata=dict(metadata or {}),
        )
        self.nodes[node_id] = node

        if len(self.nodes) > self.max_nodes:
            oldest_key = next(iter(self.nodes))
            if oldest_key != node_id:
                self.nodes.pop(oldest_key, None)

        return node

    def add_relationship(
        self,
        source_node: str,
        target_node: str,
        relationship_type: str,
        direction: str = "UNKNOWN",
        strength: float = 0.0,
        uncertainty: float = 1.0,
        evidence: Optional[Iterable[str]] = None,
        status: str = ASSOCIATED,
        metadata: Optional[Dict[str, Any]] = None,
        relationship_id: Optional[str] = None,
    ) -> InfluenceRelationship:
        relationship_id = relationship_id or (
            f"{self._slug(source_node)}->"
            f"{self._slug(target_node)}:"
            f"{self._slug(relationship_type)}"
        )

        relationship = InfluenceRelationship(
            relationship_id=relationship_id,
            source_node=str(source_node),
            target_node=str(target_node),
            relationship_type=str(relationship_type),
            direction=str(direction),
            strength=self._clamp(strength),
            uncertainty=self._clamp(uncertainty),
            evidence=list(evidence or []),
            status=status,
            metadata=dict(metadata or {}),
        )
        self.relationships[relationship_id] = relationship

        if len(self.relationships) > self.max_relationships:
            oldest_key = next(iter(self.relationships))
            if oldest_key != relationship_id:
                self.relationships.pop(oldest_key, None)

        return relationship

    def _add_observable_context_nodes(
        self, context: Dict[str, Any]
    ) -> List[str]:
        node_ids: List[str] = []

        state = self._dict(context, "market_state")
        state_conf = self._clamp(state.get("confidence", 0.5))
        state_unc = self._clamp(state.get("uncertainty", 0.5))

        for key in (
            "direction",
            "price_structure",
            "momentum",
            "volatility",
            "volume_behavior",
            "range_behavior",
        ):
            value = state.get(key)
            if value not in (None, "", [], {}):
                node = self.add_node(
                    name=f"market_state_{key}",
                    category="MARKET_STATE",
                    value=value,
                    source="market_state",
                    evidence_strength=state_conf,
                    uncertainty=state_unc,
                )
                node_ids.append(node.node_id)

        dna = self._dict(context, "market_dna")
        dna_conf = self._clamp(dna.get("confidence", 0.5))
        dna_unc = self._clamp(dna.get("uncertainty", 0.5))

        for key in (
            "price_behavior",
            "trend_persistence",
            "volatility_behavior",
            "range_behavior",
            "volume_behavior",
            "return_distribution",
        ):
            value = dna.get(key)
            if value not in (None, "", [], {}):
                node = self.add_node(
                    name=f"market_dna_{key}",
                    category="MARKET_DNA",
                    value=value,
                    source="market_dna",
                    evidence_strength=dna_conf,
                    uncertainty=dna_unc,
                )
                node_ids.append(node.node_id)

        regime = self._dict(context, "market_regime")
        regime_value = regime.get("regime", regime.get("regime_label"))
        if regime_value not in (None, "", [], {}):
            node = self.add_node(
                name="market_regime",
                category="REGIME",
                value=regime_value,
                source="market_regime",
                evidence_strength=self._clamp(
                    regime.get("confidence", 0.5)
                ),
                uncertainty=self._clamp(
                    regime.get("uncertainty", 0.5)
                ),
            )
            node_ids.append(node.node_id)

        return node_ids

    def _map_internal_relationships(
        self, context: Dict[str, Any]
    ) -> None:
        """
        Add relationships only where the structure itself supplies a
        meaningful descriptive connection. These are not asserted causal
        mechanisms.
        """
        state = self._dict(context, "market_state")
        dna = self._dict(context, "market_dna")
        regime = self._dict(context, "market_regime")

        if state and dna:
            state_direction = state.get("direction")
            dna_trend = dna.get("trend_persistence")
            if state_direction is not None and dna_trend is not None:
                self.add_relationship(
                    "market_state:market_state_direction",
                    "market_dna:market_dna_trend_persistence",
                    "STRUCTURAL_ASSOCIATION",
                    direction="CONTEXTUAL",
                    strength=min(
                        self._clamp(state.get("confidence", 0.5)),
                        self._clamp(dna.get("confidence", 0.5)),
                    ),
                    uncertainty=max(
                        self._clamp(state.get("uncertainty", 0.5)),
                        self._clamp(dna.get("uncertainty", 0.5)),
                    ),
                    evidence=["Market State", "Market DNA"],
                    status=ASSOCIATED,
                )

        if state and regime:
            if state.get("direction") is not None and regime.get(
                "regime", regime.get("regime_label")
            ) is not None:
                self.add_relationship(
                    "market_state:market_state_direction",
                    "regime:market_regime",
                    "REGIME_CONTEXT",
                    direction="CONTEXTUAL",
                    strength=min(
                        self._clamp(state.get("confidence", 0.5)),
                        self._clamp(regime.get("confidence", 0.5)),
                    ),
                    uncertainty=max(
                        self._clamp(state.get("uncertainty", 0.5)),
                        self._clamp(regime.get("uncertainty", 0.5)),
                    ),
                    evidence=["Market State", "Market Regime"],
                    status=ASSOCIATED,
                )

        if state and dna:
            state_vol = state.get("volatility")
            dna_vol = dna.get("volatility_behavior")
            if state_vol is not None and dna_vol is not None:
                self.add_relationship(
                    "market_state:market_state_volatility",
                    "market_dna:market_dna_volatility_behavior",
                    "VOLATILITY_ASSOCIATION",
                    direction="CONTEXTUAL",
                    strength=min(
                        self._clamp(state.get("confidence", 0.5)),
                        self._clamp(dna.get("confidence", 0.5)),
                    ),
                    uncertainty=max(
                        self._clamp(state.get("uncertainty", 0.5)),
                        self._clamp(dna.get("uncertainty", 0.5)),
                    ),
                    evidence=["Market State", "Market DNA"],
                    status=ASSOCIATED,
                )

    def ingest_external_factor(
        self,
        name: str,
        category: str,
        value: Any,
        source: Optional[str],
        evidence_strength: float,
        uncertainty: float,
        target_node: Optional[str] = None,
        relationship_type: str = "POTENTIAL_INFLUENCE",
        direction: str = "UNKNOWN",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add an externally supplied factor.

        LEGEND accepts the factor only as supplied evidence. It does not
        independently verify causality here.
        """
        node = self.add_node(
            name=name,
            category=category,
            value=value,
            source=source,
            evidence_strength=evidence_strength,
            uncertainty=uncertainty,
            status=OBSERVED,
            metadata=metadata,
        )

        relationship = None
        if target_node:
            relationship = self.add_relationship(
                node.node_id,
                target_node,
                relationship_type=relationship_type,
                direction=direction,
                strength=evidence_strength,
                uncertainty=uncertainty,
                evidence=[source] if source else [],
                status=HYPOTHESIZED,
            )

        return {
            "node": node.to_dict(),
            "relationship": relationship.to_dict()
            if relationship else None,
            "causal_claim": False,
        }

    def build_map(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        context = dict(context or {})

        self._add_observable_context_nodes(context)
        self._map_internal_relationships(context)

        node_values = list(self.nodes.values())
        relationship_values = list(self.relationships.values())

        observed_nodes = sum(
            1 for node in node_values if node.status == OBSERVED
        )
        hypothesized_relationships = sum(
            1 for rel in relationship_values
            if rel.status == HYPOTHESIZED
        )

        uncertainties = [
            node.uncertainty for node in node_values
        ]
        overall_uncertainty = (
            sum(uncertainties) / len(uncertainties)
            if uncertainties else 1.0
        )

        result = {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "mapped_at": utc_now(),
            "status": "READY" if node_values else "INSUFFICIENT_EVIDENCE",
            "node_count": len(node_values),
            "relationship_count": len(relationship_values),
            "observed_node_count": observed_nodes,
            "hypothesized_relationship_count": hypothesized_relationships,
            "overall_uncertainty": round(overall_uncertainty, 4),
            "nodes": [node.to_dict() for node in node_values],
            "relationships": [
                relationship.to_dict()
                for relationship in relationship_values
            ],
            "interpretation_rules": [
                "association_is_not_proof_of_causation",
                "timing_is_not_proof_of_causation",
                "market_folklore_is_not_evidence",
                "weak_evidence_remains_weak",
                "unknown_relationships_remain_unknown",
                "external_factors_require_supplied_evidence",
            ],
        }

        self.last_map = result
        return result

    def analyze_into_context(
        self,
        context: Dict[str, Any],
        context_key: str = "market_influence_map",
    ) -> Dict[str, Any]:
        if not isinstance(context, dict):
            raise TypeError("context must be a dictionary.")

        result = self.build_map(context)
        context[context_key] = result
        context["influence_map_uncertainty"] = result[
            "overall_uncertainty"
        ]
        return result

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        node = self.nodes.get(node_id)
        return node.to_dict() if node else None

    def get_relationship(
        self, relationship_id: str
    ) -> Optional[Dict[str, Any]]:
        relationship = self.relationships.get(relationship_id)
        return relationship.to_dict() if relationship else None

    def connected_nodes(self, node_id: str) -> List[Dict[str, Any]]:
        result = []
        for relationship in self.relationships.values():
            if (
                relationship.source_node == node_id
                or relationship.target_node == node_id
            ):
                result.append(relationship.to_dict())
        return result

    def clear(self) -> None:
        self.nodes.clear()
        self.relationships.clear()
        self.last_map = {}

    def status(self) -> Dict[str, Any]:
        return {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "status": "READY",
            "node_count": len(self.nodes),
            "relationship_count": len(self.relationships),
            "last_map_available": bool(self.last_map),
            "last_map_status": self.last_map.get("status"),
            "checked_at": utc_now(),
        }


__all__ = [
    "InfluenceNode",
    "InfluenceRelationship",
    "MarketInfluenceMap",
    "OBSERVED",
    "ASSOCIATED",
    "HYPOTHESIZED",
    "UNKNOWN",
]
