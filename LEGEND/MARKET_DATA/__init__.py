
"""
LEGEND MARKET DATA SUBSYSTEM

The Market Data subsystem provides controlled ingestion,
validation, provenance, freshness, and normalization of
market information before it becomes usable by LEGEND.

No prediction logic belongs here.
No BUY/SELL logic belongs here.
No strategy logic belongs here.
"""

from .data_contract import MarketDataRecord, MarketDataState
from .data_intelligence import MarketDataIntelligence

__all__ = [
    "MarketDataRecord",
    "MarketDataState",
    "MarketDataIntelligence",
]
