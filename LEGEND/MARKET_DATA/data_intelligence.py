"""
LEGEND MARKET DATA INTELLIGENCE

Coordinates:

    raw input
        ↓
    validation
        ↓
    provenance
        ↓
    freshness
        ↓
    normalized market-data state

This module deliberately does not fetch arbitrary market
data from the Internet.

External providers will be connected through controlled
adapters later.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .data_contract import (
    MarketDataRecord,
    MarketDataState,
)
from .provenance import ProvenanceTracker
from .freshness import FreshnessEvaluator
from .validation import MarketDataValidator


class MarketDataIntelligence:

    VERSION = "0.1.0"

    def __init__(self):

        self.provenance = ProvenanceTracker()
        self.freshness = FreshnessEvaluator()
        self.validator = MarketDataValidator()

    # ==========================================================
    # INGEST
    # ==========================================================

    def ingest(
        self,
        data: Dict[str, Any],
        max_age_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:

        if not isinstance(data, dict):

            return {
                "success": False,
                "status": "INVALID_INPUT",
                "errors": [
                    "Market data must be a dictionary."
                ],
            }

        state = MarketDataState(
            instrument=data.get("instrument")
        )

        # ------------------------------------------------------
        # VALIDATION
        # ------------------------------------------------------

        validation = self.validator.validate(
            data
        )

        state.validation_errors.extend(
            validation["errors"]
        )

        state.warnings.extend(
            validation["warnings"]
        )

        # ------------------------------------------------------
        # PROVENANCE
        # ------------------------------------------------------

        provenance = self.provenance.create(
            source=data.get("source", ""),
            source_type=data.get(
                "source_type"
            ),
            timestamp=data.get(
                "timestamp"
            ),
            metadata=data.get(
                "metadata",
                {},
            ),
        )

        provenance_check = (
            self.provenance.validate(
                provenance
            )
        )

        state.validation_errors.extend(
            provenance_check["errors"]
        )

        state.warnings.extend(
            provenance_check["warnings"]
        )

        # ------------------------------------------------------
        # FRESHNESS
        # ------------------------------------------------------

        freshness = self.freshness.evaluate(
            timestamp=data.get(
                "timestamp"
            ),
            max_age_seconds=max_age_seconds,
        )

        state.freshness = freshness

        # ------------------------------------------------------
        # NORMALIZATION
        # ------------------------------------------------------

        record = MarketDataRecord(
            instrument=str(
                data.get(
                    "instrument",
                    ""
                )
            ).strip(),

            asset_class=data.get(
                "asset_class"
            ),

            exchange=data.get(
                "exchange"
            ),

            timestamp=data.get(
                "timestamp"
            ),

            open=self._number(
                data.get("open")
            ),

            high=self._number(
                data.get("high")
            ),

            low=self._number(
                data.get("low")
            ),

            close=self._number(
                data.get("close")
            ),

            volume=self._number(
                data.get("volume")
            ),

            source=data.get(
                "source"
            ),

            source_type=data.get(
                "source_type"
            ),

            metadata=dict(
                data.get(
                    "metadata",
                    {}
                )
            ),

            validation_status=(
                "VALID"
                if validation["valid"]
                and provenance_check["valid"]
                else "INVALID"
            ),

            freshness_status=freshness[
                "status"
            ],

            errors=list(
                validation["errors"]
            )
            + list(
                provenance_check["errors"]
            ),

            warnings=list(
                validation["warnings"]
            )
            + list(
                provenance_check["warnings"]
            ),
        )

        # ------------------------------------------------------
        # QUALITY
        # ------------------------------------------------------

        quality = self._quality_assessment(
            record
        )

        record.quality_score = quality[
            "score"
        ]

        state.quality = quality

        state.records.append(
            record.to_dict()
        )

        if record.source:
            state.sources.append(
                record.source
            )

        # ------------------------------------------------------
        # FINAL STATE
        # ------------------------------------------------------

        if state.validation_errors:

            state.status = "REJECTED"

        elif freshness["fresh"]:

            state.status = "ACCEPTED"

        else:

            state.status = "ACCEPTED_WITH_FRESHNESS_WARNING"

        state.metadata = {
            "market_data_version": self.VERSION,
            "provenance": provenance,
        }

        state.touch()

        return {
            "success": state.status != "REJECTED",
            "status": state.status,
            "market_data": record.to_dict(),
            "state": state.to_dict(),
        }

    # ==========================================================
    # HELPERS
    # ==========================================================

    @staticmethod
    def _number(
        value: Any,
    ) -> Optional[float]:

        if value is None:
            return None

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _quality_assessment(
        record: MarketDataRecord,
    ) -> Dict[str, Any]:

        score = 1.0
        reasons: List[str] = []

        if record.errors:

            score -= 0.60

            reasons.append(
                "Validation errors detected."
            )

        if not record.source:

            score -= 0.20

            reasons.append(
                "Missing source."
            )

        if not record.timestamp:

            score -= 0.20

            reasons.append(
                "Missing timestamp."
            )

        if record.freshness_status in {
            "STALE",
            "UNKNOWN",
            "INVALID_FUTURE_TIMESTAMP",
        }:

            score -= 0.20

            reasons.append(
                "Freshness is insufficient or unknown."
            )

        score = max(
            0.0,
            min(1.0, score)
        )

        if score >= 0.90:

            label = "HIGH"

        elif score >= 0.70:

            label = "MEDIUM"

        elif score > 0:

            label = "LOW"

        else:

            label = "UNUSABLE"

        return {
            "score": score,
            "label": label,
            "reasons": reasons,
      }
