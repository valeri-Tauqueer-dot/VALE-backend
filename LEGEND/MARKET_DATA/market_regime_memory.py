"""
LEGEND Stage 6 — Market Regime Memory

Purpose:
    Preserve validated historical regime observations so LEGEND can compare
    the current observable market environment with previously observed regimes.

Design constraints:
    - No market-data fetching.
    - No fabricated observations.
    - No future prediction.
    - No BUY/SELL generation.
    - Memory is descriptive and evidence-aware.
    - Uncertain or insufficient observations are retained with their quality
      rather than silently treated as facts.

This module is additive. It does not replace earlier LEGEND modules.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from math import isfinite
from threading import RLock
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RegimeMemoryRecord:
    """One historical, evidence-backed regime observation."""

    regime: str
    timestamp: str
    confidence: float = 0.0
    uncertainty: float = 1.0
    evidence: List[str] = field(default_factory=list)
    market_state: Dict[str, Any] = field(default_factory=dict)
    market_dna: Dict[str, Any] = field(default_factory=dict)
    source: str = "LEGEND"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketRegimeMemory:
    """
    Bounded historical memory for observed market regimes.

    The memory does not decide what the market will do next. It stores and
    compares observations that were already produced by upstream intelligence.
    """

    VERSION = "0.1.0"
    MAX_DEFAULT_RECORDS = 5000

    def __init__(self, max_records: int = MAX_DEFAULT_RECORDS) -> None:
        self.max_records = max(100, int(max_records))
        self._records: Deque[RegimeMemoryRecord] = deque(maxlen=self.max_records)
        self._lock = RLock()

    # ------------------------------------------------------------------
    # Normalization / validation
    # ------------------------------------------------------------------

    @staticmethod
    def _bounded(value: Any, default: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default

        if not isfinite(number):
            return default

        return max(0.0, min(1.0, number))

    @staticmethod
    def _clean_regime(regime: Any) -> str:
        value = str(regime or "").strip().upper()
        return value or "UNKNOWN"

    @staticmethod
    def _clean_evidence(evidence: Any) -> List[str]:
        if evidence is None:
            return []

        if isinstance(evidence, str):
            return [evidence.strip()] if evidence.strip() else []

        if isinstance(evidence, Iterable):
            result: List[str] = []
            for item in evidence:
                text = str(item).strip()
                if text and text not in result:
                    result.append(text)
            return result

        return []

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def remember(
        self,
        regime: str,
        *,
        timestamp: Optional[str] = None,
        confidence: float = 0.0,
        uncertainty: float = 1.0,
        evidence: Optional[Iterable[str]] = None,
        market_state: Optional[Dict[str, Any]] = None,
        market_dna: Optional[Dict[str, Any]] = None,
        source: str = "LEGEND",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store one observed regime.

        A record is not interpreted as truth merely because it is remembered.
        Its confidence, uncertainty, evidence, and source remain attached.
        """
        record = RegimeMemoryRecord(
            regime=self._clean_regime(regime),
            timestamp=str(timestamp or utc_now()),
            confidence=self._bounded(confidence, 0.0),
            uncertainty=self._bounded(uncertainty, 1.0),
            evidence=self._clean_evidence(evidence),
            market_state=dict(market_state or {}),
            market_dna=dict(market_dna or {}),
            source=str(source or "LEGEND"),
            metadata=dict(metadata or {}),
        )

        with self._lock:
            self._records.append(record)

        return {
            "success": True,
            "stored": record.to_dict(),
            "memory_size": self.size(),
        }

    def remember_from_regime_result(
        self,
        regime_result: Dict[str, Any],
        *,
        market_state: Optional[Dict[str, Any]] = None,
        market_dna: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
        source: str = "LEGEND.MARKET_REGIME",
    ) -> Dict[str, Any]:
        """
        Store a result produced by a regime detector.

        Supports common result shapes without requiring the detector to depend
        on this module.
        """
        if not isinstance(regime_result, dict):
            return {"success": False, "error": "regime_result must be a dictionary."}

        regime = (
            regime_result.get("regime")
            or regime_result.get("current_regime")
            or regime_result.get("classification")
            or "UNKNOWN"
        )

        evidence = regime_result.get("evidence", [])
        confidence = regime_result.get("confidence", 0.0)
        uncertainty = regime_result.get("uncertainty", 1.0)

        metadata = {
            "detector_result_keys": sorted(str(key) for key in regime_result.keys())
        }

        return self.remember(
            regime=regime,
            timestamp=timestamp or regime_result.get("timestamp"),
            confidence=confidence,
            uncertainty=uncertainty,
            evidence=evidence,
            market_state=market_state or regime_result.get("market_state", {}),
            market_dna=market_dna or regime_result.get("market_dna", {}),
            source=source,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def size(self) -> int:
        with self._lock:
            return len(self._records)

    def all_records(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [record.to_dict() for record in self._records]

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        limit = max(1, int(limit))
        with self._lock:
            records = list(self._records)[-limit:]
        return [record.to_dict() for record in reversed(records)]

    def records_for_regime(
        self,
        regime: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        target = self._clean_regime(regime)

        with self._lock:
            matches = [
                record.to_dict()
                for record in reversed(self._records)
                if record.regime == target
            ]

        if limit is not None:
            matches = matches[: max(1, int(limit))]

        return matches

    def regime_counts(self) -> Dict[str, int]:
        with self._lock:
            counts = Counter(record.regime for record in self._records)
        return dict(counts)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def latest(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self._records:
                return None
            return self._records[-1].to_dict()

    def compare_with_latest(
        self,
        current_regime: str,
        *,
        current_confidence: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Compare an externally detected current regime with the latest memory.

        This describes continuity/change only. It does not forecast duration
        or future direction.
        """
        current = self._clean_regime(current_regime)
        confidence = self._bounded(current_confidence, 0.0)
        latest = self.latest()

        if latest is None:
            return {
                "success": True,
                "has_previous": False,
                "current_regime": current,
                "previous_regime": None,
                "continuity": "NO_HISTORY",
                "regime_changed": False,
                "confidence": confidence,
                "evidence": ["No prior regime observation is stored."],
            }

        previous = self._clean_regime(latest.get("regime"))
        changed = previous != current

        return {
            "success": True,
            "has_previous": True,
            "current_regime": current,
            "previous_regime": previous,
            "continuity": "CHANGED" if changed else "CONTINUING",
            "regime_changed": changed,
            "previous_timestamp": latest.get("timestamp"),
            "previous_confidence": latest.get("confidence", 0.0),
            "current_confidence": confidence,
            "evidence": [
                f"Previous observed regime: {previous}.",
                f"Current observed regime: {current}.",
                (
                    "The regime label differs from the latest memory."
                    if changed
                    else "The regime label matches the latest memory."
                ),
            ],
        }

    def similar_regimes(
        self,
        regime: str,
        *,
        min_confidence: float = 0.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve prior observations of the same descriptive regime.

        No prediction score is generated from these records.
        """
        target = self._clean_regime(regime)
        threshold = self._bounded(min_confidence, 0.0)

        with self._lock:
            matches = [
                record.to_dict()
                for record in reversed(self._records)
                if record.regime == target
                and float(record.confidence) >= threshold
            ]

        return matches[: max(1, int(limit))]

    # ------------------------------------------------------------------
    # Context integration
    # ------------------------------------------------------------------

    def analyze_into_context(
        self,
        context: Dict[str, Any],
        regime_result: Dict[str, Any],
        *,
        market_state: Optional[Dict[str, Any]] = None,
        market_dna: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Remember a detected regime and expose the resulting memory view in a
        LEGEND context dictionary.
        """
        if not isinstance(context, dict):
            raise TypeError("context must be a dictionary.")

        stored = self.remember_from_regime_result(
            regime_result,
            market_state=market_state,
            market_dna=market_dna,
        )

        if not stored.get("success"):
            return stored

        regime = stored["stored"]["regime"]
        comparison = self.compare_with_latest(
            regime,
            current_confidence=stored["stored"]["confidence"],
        )

        # compare_with_latest sees the record just inserted. Therefore derive
        # transition information against the second-latest observation instead.
        history = self.recent(2)
        previous_record = history[1] if len(history) > 1 else None

        if previous_record is None:
            transition = {
                "regime_changed": False,
                "continuity": "NO_HISTORY",
                "previous_regime": None,
            }
        else:
            previous_regime = self._clean_regime(previous_record.get("regime"))
            transition = {
                "regime_changed": previous_regime != regime,
                "continuity": (
                    "CHANGED" if previous_regime != regime else "CONTINUING"
                ),
                "previous_regime": previous_regime,
                "previous_timestamp": previous_record.get("timestamp"),
            }

        memory_view = {
            "version": self.VERSION,
            "current_regime": regime,
            "latest_record": stored["stored"],
            "previous_record": previous_record,
            "transition": transition,
            "regime_counts": self.regime_counts(),
            "memory_size": self.size(),
            "recent_records": self.recent(10),
            "comparison": comparison,
        }

        context["market_regime_memory"] = memory_view
        context["market_regime"] = regime

        observations = context.setdefault("observations", [])
        if isinstance(observations, list):
            observations.append(
                {
                    "type": "market_regime_memory",
                    "timestamp": utc_now(),
                    "regime": regime,
                    "continuity": transition["continuity"],
                    "evidence_quality": stored["stored"]["confidence"],
                }
            )

        return {
            "success": True,
            "memory": memory_view,
        }

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._records.clear()

    def export(self) -> Dict[str, Any]:
        return {
            "version": self.VERSION,
            "max_records": self.max_records,
            "record_count": self.size(),
            "records": self.all_records(),
            "regime_counts": self.regime_counts(),
        }

    def status(self) -> Dict[str, Any]:
        return {
            "module": "MarketRegimeMemory",
            "version": self.VERSION,
            "status": "READY",
            "record_count": self.size(),
            "max_records": self.max_records,
            "regimes": self.regime_counts(),
        }


__all__ = [
    "RegimeMemoryRecord",
    "MarketRegimeMemory",
]
