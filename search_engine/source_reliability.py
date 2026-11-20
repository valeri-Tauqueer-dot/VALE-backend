"""
VALE source reliability - batch 13 of the plan (the "history" half of
"history and forecast scoring").

What this deliberately does NOT do, on purpose, to match LEGEND's own
stated rules: it does not score whether a past prediction was right or
wrong, and it does not automatically change what VALE believes based on
outcomes. LEGEND's own docstring is explicit that it must not learn from
outcomes automatically - this file respects that completely.

What it DOES do: keep a simple, honest history of how often each source
has actually turned up in real evidence, and how recently. That's a
"how established is this source" signal, built from plain usage counts -
nothing more. A forecast-scoring engine that judges actual outcomes is a
bigger, separate decision for later, once there's a real track record of
market outcomes to judge against - not something to bolt on quietly here.

Same small-table pattern as source_state.py and allowance_counter.py.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select, update
from sqlalchemy.engine import Engine


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _database_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if raw:
        if raw.startswith("postgres://"):
            raw = "postgresql+psycopg2://" + raw[len("postgres://"):]
        elif raw.startswith("postgresql://"):
            raw = "postgresql+psycopg2://" + raw[len("postgresql://"):]
        return raw
    return "sqlite:///" + os.path.abspath(os.getenv("VALE_RELIABILITY_DB", "vale_source_reliability.db"))


_engine: Optional[Engine] = None
_metadata = MetaData()
history = Table(
    "vale_source_reliability",
    _metadata,
    Column("source", String(200), primary_key=True),  # a tag like "link-finder" or a specific domain
    Column("times_seen", Integer, nullable=False, default=0),
    Column("first_seen_at", String(40), nullable=True),
    Column("last_seen_at", String(40), nullable=True),
)


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = _database_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, pool_pre_ping=True, pool_recycle=300, connect_args=connect_args)
        _metadata.create_all(_engine)
    return _engine


def record_sighting(source: str) -> None:
    """One more piece of evidence just came from this source, right now. Never raises."""

    source = (source or "").strip()
    if not source:
        return

    try:
        engine = _get_engine()
        now = _now()
        with engine.begin() as connection:
            existing = connection.execute(
                select(history).where(history.c.source == source)
            ).mappings().first()

            if existing:
                connection.execute(
                    update(history)
                    .where(history.c.source == source)
                    .values(times_seen=int(existing["times_seen"] or 0) + 1, last_seen_at=now)
                )
            else:
                connection.execute(
                    history.insert().values(source=source, times_seen=1, first_seen_at=now, last_seen_at=now)
                )

    except Exception as error:
        print("SOURCE RELIABILITY: could not record a sighting:", type(error).__name__, flush=True)


def record_evidence_sources(evidence: List[Dict]) -> None:
    """Convenience: record a sighting for every item's source/via field in one go. Never raises."""

    for item in evidence or []:
        tag = item.get("source") or item.get("via") or ""
        if tag:
            record_sighting(tag)


def times_seen(source: str) -> int:
    """How many times this source has shown up in real evidence, ever. Never raises."""

    try:
        engine = _get_engine()
        with engine.connect() as connection:
            row = connection.execute(
                select(history.c.times_seen).where(history.c.source == source)
            ).first()
        return int(row[0]) if row else 0

    except Exception as error:
        print("SOURCE RELIABILITY: could not read history:", type(error).__name__, flush=True)
        return 0


def most_seen(limit: int = 20) -> List[Dict]:
    """The sources that have turned up the most, most-seen first. Never raises."""

    try:
        engine = _get_engine()
        with engine.connect() as connection:
            rows = connection.execute(
                select(history).order_by(history.c.times_seen.desc()).limit(limit)
            ).mappings().all()
        return [dict(row) for row in rows]

    except Exception as error:
        print("SOURCE RELIABILITY: could not read the list:", type(error).__name__, flush=True)
        return []
