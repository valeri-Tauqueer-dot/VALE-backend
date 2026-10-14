"""Persistent job queue for VALE Research Network.

Uses DATABASE_URL (the same persistent PostgreSQL database as VALE) when set.
For local development only, it falls back to VALE_RESEARCH_QUEUE_DB or a local
SQLite file. Render's local filesystem is ephemeral, so production should set
DATABASE_URL to a persistent database.

Supported job type: web_search_save
Payload: {"query": str, "num_results": int, "market": str}
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
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


def _parse_time(value: Optional[str]) -> str:
    if not value:
        return _now()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError) as exc:
        raise ValueError("run_at must be an ISO-8601 date/time, for example 2026-10-20T10:00:00Z") from exc


def _database_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if raw:
        if raw.startswith("postgres://"):
            raw = "postgresql+psycopg2://" + raw[len("postgres://"):]
        elif raw.startswith("postgresql://"):
            raw = "postgresql+psycopg2://" + raw[len("postgresql://"):]
        return raw
    # Local fallback. This is NOT durable across Render deploys/restarts.
    return "sqlite:///" + os.path.abspath(os.getenv("VALE_RESEARCH_QUEUE_DB", "vale_research_queue.db"))


_engine: Optional[Engine] = None
_metadata = MetaData()
jobs = Table(
    "vale_research_jobs",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("job_type", String(80), nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("status", String(30), nullable=False, index=True),
    Column("attempts", Integer, nullable=False, default=0),
    Column("max_attempts", Integer, nullable=False, default=3),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
    Column("run_at", String(40), nullable=False, index=True),
    Column("locked_at", String(40), nullable=True),
    Column("last_error", Text, nullable=True),
    Column("result_json", Text, nullable=True),
    Column("checkpoint_json", Text, nullable=True),
)


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = _database_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, pool_pre_ping=True, pool_recycle=300, connect_args=connect_args)
        _metadata.create_all(_engine)
        if url.startswith("sqlite"):
            print("RESEARCH QUEUE: using local SQLite fallback; use persistent DATABASE_URL on Render", flush=True)
        else:
            print("RESEARCH QUEUE: persistent database initialized", flush=True)
    return _engine


def init_queue() -> None:
    _get_engine()


def _decode(row: Any) -> Dict[str, Any]:
    data = dict(row)
    for key in ("payload_json", "result_json", "checkpoint_json"):
        raw = data.pop(key, None)
        try:
            data[key.removesuffix("_json")] = json.loads(raw) if raw else None
        except (TypeError, ValueError):
            data[key.removesuffix("_json")] = None
    return data


def enqueue_job(
    job_type: str,
    payload: Dict[str, Any],
    max_attempts: int = 3,
    run_at: Optional[str] = None,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if not 1 <= int(max_attempts) <= 10:
        raise ValueError("max_attempts must be between 1 and 10")
    now = _now()
    scheduled = _parse_time(run_at)
    engine = _get_engine()
    with engine.begin() as conn:
        result = conn.execute(jobs.insert().values(
            job_type=job_type,
            payload_json=json.dumps(payload, ensure_ascii=False),
            status="queued",
            attempts=0,
            max_attempts=int(max_attempts),
            created_at=now,
            updated_at=now,
            run_at=scheduled,
            locked_at=None,
            last_error=None,
            result_json=None,
            checkpoint_json=json.dumps({"stage": "queued", "processed": 0}, ensure_ascii=False),
        ))
        job_id = result.inserted_primary_key[0]
        row = conn.execute(select(jobs).where(jobs.c.id == job_id)).mappings().first()
    return _decode(row)


def claim_next_job() -> Optional[Dict[str, Any]]:
    """Atomically claim the next due job; PostgreSQL workers use SKIP LOCKED."""
    engine = _get_engine()
    now = _now()
    with engine.begin() as conn:
        stmt = (
            select(jobs)
            .where(jobs.c.status.in_(["queued", "retry_wait"]), jobs.c.run_at <= now)
            .order_by(jobs.c.run_at.asc(), jobs.c.id.asc())
            .limit(1)
        )
        if engine.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)
        row = conn.execute(stmt).mappings().first()
        if not row:
            return None
        job_id = row["id"]
        conn.execute(update(jobs).where(jobs.c.id == job_id).values(
            status="running", attempts=int(row["attempts"] or 0) + 1,
            updated_at=now, locked_at=now,
            checkpoint_json=json.dumps({"stage": "started", "processed": 0}),
        ))
        claimed = conn.execute(select(jobs).where(jobs.c.id == job_id)).mappings().first()
    return _decode(claimed)


def update_checkpoint(job_id: int, checkpoint: Dict[str, Any]) -> bool:
    engine = _get_engine()
    with engine.begin() as conn:
        result = conn.execute(update(jobs).where(jobs.c.id == int(job_id), jobs.c.status == "running").values(
            checkpoint_json=json.dumps(checkpoint, ensure_ascii=False), updated_at=_now(),
        ))
    return bool(result.rowcount)


def complete_job(job_id: int, result: Dict[str, Any]) -> bool:
    engine = _get_engine()
    with engine.begin() as conn:
        updated = conn.execute(update(jobs).where(jobs.c.id == int(job_id)).values(
            status="completed", result_json=json.dumps(result, ensure_ascii=False),
            checkpoint_json=json.dumps({"stage": "completed", **result}, ensure_ascii=False),
            last_error=None, locked_at=None, updated_at=_now(),
        ))
    return bool(updated.rowcount)


def fail_job(job_id: int, error: str) -> Optional[Dict[str, Any]]:
    engine = _get_engine()
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat(timespec="seconds")
    with engine.begin() as conn:
        row = conn.execute(select(jobs).where(jobs.c.id == int(job_id))).mappings().first()
        if not row:
            return None
        attempts = int(row["attempts"] or 0)
        max_attempts = int(row["max_attempts"] or 3)
        if attempts < max_attempts:
            wait_seconds = min(60 * (2 ** max(0, attempts - 1)), 3600)
            status = "retry_wait"
            run_at = (now_dt + timedelta(seconds=wait_seconds)).isoformat(timespec="seconds")
            checkpoint = {"stage": "retry_wait", "attempt": attempts, "retry_in_seconds": wait_seconds}
        else:
            status = "failed"
            run_at = row["run_at"]
            checkpoint = {"stage": "failed", "attempt": attempts}
        conn.execute(update(jobs).where(jobs.c.id == int(job_id)).values(
            status=status, run_at=run_at, updated_at=now, locked_at=None,
            last_error=(error or "Unknown error")[:2000],
            checkpoint_json=json.dumps(checkpoint),
        ))
        updated = conn.execute(select(jobs).where(jobs.c.id == int(job_id))).mappings().first()
    return _decode(updated)


def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    with _get_engine().connect() as conn:
        row = conn.execute(select(jobs).where(jobs.c.id == int(job_id))).mappings().first()
    return _decode(row) if row else None


def list_jobs(status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), 100))
    stmt = select(jobs).order_by(jobs.c.id.desc()).limit(limit)
    if status:
        stmt = select(jobs).where(jobs.c.status == status).order_by(jobs.c.id.desc()).limit(limit)
    with _get_engine().connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [_decode(row) for row in rows]


def retry_job(job_id: int) -> Optional[Dict[str, Any]]:
    """Manually requeue a failed/completed job immediately, resetting attempts."""
    engine = _get_engine()
    now = _now()
    with engine.begin() as conn:
        row = conn.execute(select(jobs).where(jobs.c.id == int(job_id))).mappings().first()
        if not row:
            return None
        if row["status"] == "running":
            raise ValueError("A running job cannot be retried yet.")
        conn.execute(update(jobs).where(jobs.c.id == int(job_id)).values(
            status="queued", attempts=0, run_at=now, updated_at=now, locked_at=None,
            last_error=None, result_json=None,
            checkpoint_json=json.dumps({"stage": "queued_for_retry", "processed": 0}),
        ))
        updated = conn.execute(select(jobs).where(jobs.c.id == int(job_id))).mappings().first()
    return _decode(updated)


def recover_stale_jobs(stale_after_minutes: int = 15) -> int:
    """Recover jobs left running by a crashed process, without touching fresh work."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes)).isoformat(timespec="seconds")
    now = _now()
    engine = _get_engine()
    with engine.begin() as conn:
        result = conn.execute(update(jobs).where(
            jobs.c.status == "running", jobs.c.locked_at.is_not(None), jobs.c.locked_at < cutoff,
        ).values(status="retry_wait", run_at=now, locked_at=None, updated_at=now,
                 last_error="Recovered after worker stopped before finishing."))
    return int(result.rowcount or 0)
