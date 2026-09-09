"""
LEGEND MARKET DATA PROVENANCE

Tracks where market information came from.

A data point without provenance should not silently
become trusted intelligence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProvenanceTracker:

    VERSION = "0.1.0"

    def create(
        self,
        source: str,
        source_type: Optional[str] = None,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        source = (source or "").strip()

        return {
            "source": source or None,
            "source_type": source_type,
            "source_timestamp": timestamp,
            "received_at": utc_now(),
            "metadata": dict(metadata or {}),
            "provenance_complete": bool(
                source and timestamp
            ),
        }

    def validate(
        self,
        provenance: Dict[str, Any],
    ) -> Dict[str, Any]:

        errors = []
        warnings = []

        if not provenance.get("source"):
            errors.append("Data source is missing.")

        if not provenance.get("source_timestamp"):
            errors.append(
                "Original data timestamp is missing."
            )

        if not provenance.get("source_type"):
            warnings.append(
                "Source type is not specified."
            )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "provenance": provenance,
        }
