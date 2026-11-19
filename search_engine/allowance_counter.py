"""
VALE allowance counter - batch 8's half of "search providers and allowance
counter".

Some providers (Brave, Tavily, and others later) are free only up to a
monthly limit, then they start charging. This file is VALE's memory of
"how much have I used this month?" for each one, so providers.py (the
other half of this batch) can check before calling, and never go over
the free amount by accident.

Same small-table pattern as source_state.py: its own table
(vale_provider_allowance), one row per provider per month, using the
same DATABASE_URL as the rest of VALE.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select, update
from sqlalchemy.engine import Engine


def _this_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _database_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if raw:
        if raw.startswith("postgres://"):
            raw = "postgresql+psycopg2://" + raw[len("postgres://"):]
        elif raw.startswith("postgresql://"):
            raw = "postgresql+psycopg2://" + raw[len("postgresql://"):]
        return raw
    # Local fallback only - NOT durable across Render deploys/restarts.
    return "sqlite:///" + os.path.abspath(os.getenv("VALE_ALLOWANCE_DB", "vale_allowance.db"))


_engine: Optional[Engine] = None
_metadata = MetaData()
usage = Table(
    "vale_provider_allowance",
    _metadata,
    Column("provider", String(80), primary_key=True),
    Column("month", String(7), primary_key=True),  # "YYYY-MM"
    Column("used", Integer, nullable=False, default=0),
)

# One line per provider: its free amount for one month, "as found" on the
# provider's own pricing page. Add a new provider here any time - nothing
# else needs to change.
MONTHLY_LIMITS = {
    "brave": 2000,   # Brave Search API free tier: 2,000 queries/month
    "tavily": 1000,  # Tavily free tier: 1,000 credits/month
}


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = _database_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, pool_pre_ping=True, pool_recycle=300, connect_args=connect_args)
        _metadata.create_all(_engine)
    return _engine


def used_this_month(provider: str) -> int:
    """How many calls have already been counted against this provider this month. Never raises."""

    try:
        engine = _get_engine()
        month = _this_month()
        with engine.connect() as connection:
            row = connection.execute(
                select(usage.c.used).where(usage.c.provider == provider, usage.c.month == month)
            ).first()
        return int(row[0]) if row else 0

    except Exception as error:
        print("ALLOWANCE COUNTER: could not read usage:", type(error).__name__, flush=True)
        return 0


def can_use(provider: str, cost: int = 1) -> bool:
    """
    True if using this provider now would still stay inside its free
    monthly amount. An unknown provider (not in MONTHLY_LIMITS) is
    treated as having no free limit tracked here, so it is allowed
    through - add it to MONTHLY_LIMITS once you know its real limit.
    """

    limit = MONTHLY_LIMITS.get(provider)
    if limit is None:
        return True

    return used_this_month(provider) + cost <= limit


def record_use(provider: str, cost: int = 1) -> None:
    """Count one more use against this provider's monthly total. Never raises."""

    try:
        engine = _get_engine()
        month = _this_month()
        with engine.begin() as connection:
            existing = connection.execute(
                select(usage.c.used).where(usage.c.provider == provider, usage.c.month == month)
            ).first()

            if existing:
                connection.execute(
                    update(usage)
                    .where(usage.c.provider == provider, usage.c.month == month)
                    .values(used=int(existing[0]) + cost)
                )
            else:
                connection.execute(usage.insert().values(provider=provider, month=month, used=cost))

    except Exception as error:
        print("ALLOWANCE COUNTER: could not record usage:", type(error).__name__, flush=True)


def remaining(provider: str) -> Optional[int]:
    """How many free calls are left this month, or None if this provider's limit isn't tracked."""

    limit = MONTHLY_LIMITS.get(provider)
    if limit is None:
        return None
    return max(0, limit - used_this_month(provider))
