"""
VALE source state - batch 7's memory for the wave system.

Keeps one row per URL: when it was last checked, whether it was healthy
that time, and how many times in a row it has failed. This is what lets
the wave runner skip a source it just checked an hour ago, and notice one
that has been broken for a while.

Its own small table (vale_source_state), separate from search_documents -
this file is only ever about "when did I last look, and was it OK?", never
about the actual saved content. Uses the same DATABASE_URL as the rest of
VALE. Falls back to a local SQLite file only for quick local testing -
Render's own disk is not persistent, so production should always have
DATABASE_URL set (the same one your news collector and research queue
already use).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
    update,
)
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
    # Local fallback only - NOT durable across Render deploys/restarts.
    return "sqlite:///" + os.path.abspath(os.getenv("VALE_SOURCE_STATE_DB", "vale_source_state.db"))


_engine: Optional[Engine] = None
_metadata = MetaData()
sources = Table(
    "vale_source_state",
    _metadata,
    Column("url", String(1000), primary_key=True),
    Column("name", String(300), nullable=True),
    Column("source", String(80), nullable=True),
    Column("last_checked_at", String(40), nullable=True, index=True),
    Column("healthy", Boolean, nullable=False, default=True),
    Column("consecutive_failures", Integer, nullable=False, default=0),
    Column("last_error", Text, nullable=True),
)


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = _database_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, pool_pre_ping=True, pool_recycle=300, connect_args=connect_args)
        _metadata.create_all(_engine)
        if url.startswith("sqlite"):
            print("SOURCE STATE: using local SQLite fallback; use persistent DATABASE_URL on Render", flush=True)
        else:
            print("SOURCE STATE: persistent database initialized", flush=True)
    return _engine


def remember(url: str, name: str = "", source: str = "", healthy: bool = True, error: str = "") -> None:
    """Record the result of checking one URL just now. Never raises."""

    url = (url or "").strip()
    if not url:
        return

    try:
        engine = _get_engine()
        now = _now()
        with engine.begin() as connection:
            existing = connection.execute(
                select(sources).where(sources.c.url == url)
            ).mappings().first()

            if existing:
                failures = 0 if healthy else int(existing["consecutive_failures"] or 0) + 1
                connection.execute(
                    update(sources).where(sources.c.url == url).values(
                        last_checked_at=now,
                        healthy=healthy,
                        consecutive_failures=failures,
                        last_error=(error or "")[:1000] or None,
                    )
                )
            else:
                connection.execute(
                    sources.insert().values(
                        url=url,
                        name=name,
                        source=source,
                        last_checked_at=now,
                        healthy=healthy,
                        consecutive_failures=0 if healthy else 1,
                        last_error=(error or "")[:1000] or None,
                    )
                )

    except Exception as error_obj:
        print("SOURCE STATE: could not save a result:", type(error_obj).__name__, flush=True)


def due_for_check(max_age_hours: int = 6, limit: int = 300) -> List[Dict[str, Any]]:
    """
    URLs worth checking again right now: checked longer ago than
    max_age_hours (oldest first). Does not include URLs never checked at
    all - see known_urls() for finding those from storage.
    """

    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat(timespec="seconds")
        engine = _get_engine()
        with engine.connect() as connection:
            rows = connection.execute(
                select(sources)
                .where(sources.c.last_checked_at < cutoff)
                .order_by(sources.c.last_checked_at.asc())
                .limit(limit)
            ).mappings().all()
        return [dict(row) for row in rows]

    except Exception as error:
        print("SOURCE STATE: could not read the due list:", type(error).__name__, flush=True)
        return []


def known_urls() -> Set[str]:
    """Every URL already being tracked, so new candidates can skip duplicates. Never raises."""

    try:
        engine = _get_engine()
        with engine.connect() as connection:
            rows = connection.execute(select(sources.c.url)).all()
        return {row[0] for row in rows}

    except Exception as error:
        print("SOURCE STATE: could not read known urls:", type(error).__name__, flush=True)
        return set()
