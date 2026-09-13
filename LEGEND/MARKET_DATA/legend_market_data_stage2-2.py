"""
VALE LEGEND — MARKET DATA INTELLIGENCE STAGE 2

Additive module:
- Does NOT replace LEGEND/legend_brain.py.
- Does NOT delete or modify the existing MARKET_DATA modules.
- Uses the existing MarketDataIntelligence engine.
- Keeps real-data/evidence-first rules explicit.

Pipeline:

    structured market data
          ↓
    MarketDataIntelligence
          ↓
    validation + provenance + freshness + normalization
          ↓
    quality assessment
          ↓
    LEGEND shared state
          ↓
    observation / timeline

This module does not fetch market data and does not create BUY/SELL
signals or predictions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .data_intelligence import MarketDataIntelligence


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LegendMarketDataStage2:
    """
    Stage-2 integration layer for LEGEND market-data intelligence.

    It is intentionally independent from LegendBrain so the current
    Stage-1 file can remain untouched.
    """

    VERSION = "0.1.0"
    STAGE = "LEGEND_MARKET_DATA_INTELLIGENCE"

    def __init__(
        self,
        intelligence: Optional[MarketDataIntelligence] = None,
    ) -> None:
        self.intelligence = intelligence or MarketDataIntelligence()

    # --------------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------------

    def process(
        self,
        state: Any,
        market_data: Dict[str, Any],
        max_age_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Validate and integrate one structured market-data payload.

        Accepted data is stored in shared state under legend_context.
        Rejected data is never promoted to a market observation.

        Freshness warnings remain explicit; stale data is not silently
        treated as fresh.
        """

        if not isinstance(market_data, dict):
            return self._fail(
                state,
                "INVALID_INPUT",
                ["Market data must be a dictionary."],
            )

        result = self.intelligence.ingest(
            market_data,
            max_age_seconds=max_age_seconds,
        )

        context = self._get_or_create_context(state)

        record = result.get("market_data") or {}
        md_state = result.get("state") or {}

        # Always preserve the ingestion result for auditability.
        context["market_data_intelligence"] = {
            "version": self.VERSION,
            "stage": self.STAGE,
            "processed_at": utc_now(),
            "status": result.get("status"),
            "success": bool(result.get("success")),
            "record_id": record.get("record_id"),
            "instrument": record.get("instrument"),
            "source": record.get("source"),
            "source_type": record.get("source_type"),
            "validation_status": record.get("validation_status"),
            "freshness_status": record.get("freshness_status"),
            "quality_score": record.get("quality_score"),
            "quality": md_state.get("quality", {}),
            "errors": list(md_state.get("validation_errors", [])),
            "warnings": list(md_state.get("warnings", [])),
            "provenance": md_state.get("metadata", {}).get("provenance"),
        }

        if result.get("success"):
            # Promote only accepted records into the market-data context.
            context.setdefault("data", {})
            context["data"].setdefault("records", [])
            context["data"].setdefault("sources", [])
            context["data"].setdefault("freshness", [])

            context["data"]["latest"] = record
            context["data"]["records"].append(record)

            source = record.get("source")
            if source and source not in context["data"]["sources"]:
                context["data"]["sources"].append(source)

            freshness = {
                "record_id": record.get("record_id"),
                "status": record.get("freshness_status"),
                "timestamp": record.get("timestamp"),
                "checked_at": utc_now(),
            }
            context["data"]["freshness"].append(freshness)

            # Keep the market identity synchronized without interpreting it.
            market = context.setdefault("market", {})
            for key in ("instrument", "asset_class", "exchange"):
                if record.get(key) is not None:
                    market[key] = record.get(key)

            observation = {
                "id": f"legend-md-obs-{record.get('record_id', 'unknown')}",
                "timestamp": utc_now(),
                "type": "MARKET_DATA",
                "statement": (
                    "Structured market data was accepted by the LEGEND "
                    "market-data intelligence pipeline."
                ),
                "record_id": record.get("record_id"),
                "instrument": record.get("instrument"),
                "source": record.get("source"),
                "freshness_status": record.get("freshness_status"),
                "quality_score": record.get("quality_score"),
            }
            context.setdefault("observations", []).append(observation)

            self._timeline(
                context,
                "market_data_accepted",
                {
                    "record_id": record.get("record_id"),
                    "instrument": record.get("instrument"),
                    "freshness_status": record.get("freshness_status"),
                    "quality_score": record.get("quality_score"),
                },
            )

            # Evidence quality, not prediction confidence.
            context.setdefault("uncertainty", {})
            if record.get("freshness_status") in {
                "STALE",
                "UNKNOWN",
                "INVALID_FUTURE_TIMESTAMP",
            }:
                context["uncertainty"]["state"] = "DATA_FRESHNESS_CONSTRAINED"
            elif record.get("quality_score") is not None:
                context["uncertainty"]["state"] = "DATA_QUALITY_ASSESSED"

        else:
            self._timeline(
                context,
                "market_data_rejected",
                {
                    "status": result.get("status"),
                    "errors": md_state.get("validation_errors", []),
                    "warnings": md_state.get("warnings", []),
                },
            )

        context["updated_at"] = utc_now()
        self._set_context(state, context)

        if hasattr(state, "event"):
            state.event(
                "legend_market_data_stage2_completed",
                "LEGEND",
                payload={
                    "status": result.get("status"),
                    "success": bool(result.get("success")),
                    "instrument": record.get("instrument"),
                    "record_id": record.get("record_id"),
                },
            )

        return {
            "success": bool(result.get("success")),
            "stage": self.STAGE,
            "version": self.VERSION,
            "status": result.get("status"),
            "market_data": record,
            "market_data_state": md_state,
            "legend_context": context,
        }

    # --------------------------------------------------------------
    # STATE HELPERS
    # --------------------------------------------------------------

    @staticmethod
    def _get_or_create_context(state: Any) -> Dict[str, Any]:
        existing = state.get("legend_context") if hasattr(state, "get") else None

        if isinstance(existing, dict):
            return existing

        return {
            "context_id": f"legend-stage2-{utc_now()}",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "task_type": "market_intelligence",
            "status": "INITIALIZING",
            "market": {
                "instrument": None,
                "asset_class": None,
                "exchange": None,
                "timeframe": None,
            },
            "data": {
                "available": [],
                "missing": [],
                "sources": [],
                "freshness": [],
                "records": [],
            },
            "observations": [],
            "hypotheses": [],
            "evidence": [],
            "contradictions": [],
            "risks": [],
            "scenarios": [],
            "uncertainty": {
                "state": "UNASSESSED",
                "reasons": [],
            },
            "decision": {
                "status": "NOT_READY",
                "conclusion": None,
            },
            "timeline": [],
        }

    @staticmethod
    def _set_context(state: Any, context: Dict[str, Any]) -> None:
        if hasattr(state, "set"):
            state.set("legend_context", context)

    @staticmethod
    def _timeline(
        context: Dict[str, Any],
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        context.setdefault("timeline", []).append(
            {
                "timestamp": utc_now(),
                "event": event_type,
                "details": details or {},
            }
        )

    @staticmethod
    def _fail(
        state: Any,
        status: str,
        errors: list[str],
    ) -> Dict[str, Any]:
        if hasattr(state, "event"):
            state.event(
                "legend_market_data_stage2_failed",
                "LEGEND",
                payload={"status": status, "errors": errors},
            )

        return {
            "success": False,
            "stage": LegendMarketDataStage2.STAGE,
            "version": LegendMarketDataStage2.VERSION,
            "status": status,
            "errors": errors,
        }
