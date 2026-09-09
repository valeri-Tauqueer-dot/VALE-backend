"""
LEGEND MARKET DATA FRESHNESS

Determines whether incoming market data is fresh enough
for the requested analytical context.

This module does not decide whether data is economically
useful. It only evaluates temporal freshness.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


class FreshnessEvaluator:

    VERSION = "0.1.0"

    @staticmethod
    def _parse_timestamp(
        timestamp: Optional[str],
    ) -> Optional[datetime]:

        if not timestamp:
            return None

        try:
            value = timestamp.replace(
                "Z",
                "+00:00",
            )

            parsed = datetime.fromisoformat(value)

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed.astimezone(
                timezone.utc
            )

        except (
            ValueError,
            TypeError,
        ):
            return None

    def evaluate(
        self,
        timestamp: Optional[str],
        max_age_seconds: Optional[float] = None,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:

        parsed = self._parse_timestamp(
            timestamp
        )

        if parsed is None:
            return {
                "status": "UNKNOWN",
                "fresh": False,
                "age_seconds": None,
                "reason": "Invalid or missing timestamp.",
            }

        current = now or datetime.now(
            timezone.utc
        )

        age = (
            current - parsed
        ).total_seconds()

        if age < 0:
            return {
                "status": "INVALID_FUTURE_TIMESTAMP",
                "fresh": False,
                "age_seconds": age,
                "reason": (
                    "Data timestamp is in the future "
                    "relative to evaluation time."
                ),
            }

        if max_age_seconds is None:
            return {
                "status": "TIMESTAMP_VALID",
                "fresh": True,
                "age_seconds": age,
                "reason": (
                    "Timestamp is valid; no maximum "
                    "age threshold was supplied."
                ),
            }

        fresh = age <= float(
            max_age_seconds
        )

        return {
            "status": (
                "FRESH"
                if fresh
                else "STALE"
            ),
            "fresh": fresh,
            "age_seconds": age,
            "max_age_seconds": float(
                max_age_seconds
            ),
            "reason": (
                "Data is within the configured "
                "freshness threshold."
                if fresh
                else
                "Data exceeds the configured "
                "freshness threshold."
            ),
        }
