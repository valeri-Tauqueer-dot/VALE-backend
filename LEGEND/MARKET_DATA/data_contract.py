"""
LEGEND MARKET DATA CONTRACT

Defines the canonical structure of market information
inside LEGEND.

The contract exists so that every future market-data
provider can feed LEGEND through the same structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MarketDataRecord:
    """
    One normalized market-data record.

    This object describes data.
    It does not interpret the market.
    """

    instrument: str
    asset_class: Optional[str] = None
    exchange: Optional[str] = None

    timestamp: Optional[str] = None

    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None

    volume: Optional[float] = None

    source: Optional[str] = None
    source_type: Optional[str] = None

    record_id: str = field(
        default_factory=lambda: f"md-{uuid4().hex[:12]}"
    )

    received_at: str = field(
        default_factory=utc_now
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    validation_status: str = "UNVALIDATED"

    quality_score: Optional[float] = None

    freshness_status: str = "UNKNOWN"

    errors: List[str] = field(
        default_factory=list
    )

    warnings: List[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "instrument": self.instrument,
            "asset_class": self.asset_class,
            "exchange": self.exchange,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "source": self.source,
            "source_type": self.source_type,
            "received_at": self.received_at,
            "metadata": dict(self.metadata),
            "validation_status": self.validation_status,
            "quality_score": self.quality_score,
            "freshness_status": self.freshness_status,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


@dataclass
class MarketDataState:
    """
    Aggregate state of one market-data ingestion operation.
    """

    state_id: str = field(
        default_factory=lambda: f"mds-{uuid4().hex[:12]}"
    )

    created_at: str = field(
        default_factory=utc_now
    )

    updated_at: str = field(
        default_factory=utc_now
    )

    status: str = "INITIALIZING"

    instrument: Optional[str] = None

    records: List[Dict[str, Any]] = field(
        default_factory=list
    )

    sources: List[str] = field(
        default_factory=list
    )

    validation_errors: List[str] = field(
        default_factory=list
    )

    warnings: List[str] = field(
        default_factory=list
    )

    freshness: Dict[str, Any] = field(
        default_factory=dict
    )

    quality: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def touch(self) -> None:
        self.updated_at = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "instrument": self.instrument,
            "records": list(self.records),
            "sources": list(self.sources),
            "validation_errors": list(
                self.validation_errors
            ),
            "warnings": list(self.warnings),
            "freshness": dict(self.freshness),
            "quality": dict(self.quality),
            "metadata": dict(self.metadata),
        }
