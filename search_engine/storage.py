"""
VALE search engine - storage manager (step 1).

One small place that saves and finds documents (news pieces, later more).
The rest of VALE only says "save this" or "find that".

How it picks a database:
  - It reads these Render / GitHub secrets (set only the ones you have):
        SEARCH_DB_URL_1   first database  (your Supabase)
        SEARCH_DB_URL_2   second database (later, for example Neon)
        SEARCH_DB_URL_3   third database  (later)
  - It writes to the first database that still has room.
  - If no secret is set, it uses a local file "search_data.db" (good for testing).
  - SEARCH_DB_MAX_MB is the size where a database counts as "full".
    Default 400 (safe for a free 500 MB plan).

We keep only the title, a short text and the link. Never full articles.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

MAX_TEXT_CHARS = 600
MAX_TITLE_CHARS = 300

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS search_documents (
    url_hash     TEXT PRIMARY KEY,
    url          TEXT NOT NULL,
    title        TEXT,
    body         TEXT,
    source       TEXT,
    market       TEXT,
    published_at TEXT,
    fetched_at   TEXT
)
"""

_INSERT = """
INSERT INTO search_documents
    (url_hash, url, title, body, source, market, published_at, fetched_at)
VALUES
    (:url_hash, :url, :title, :body, :source, :market, :published_at, :fetched_at)
ON CONFLICT (url_hash) DO NOTHING
"""

_engines: Optional[List[Engine]] = None


def _fix_url(url: str) -> str:
    """Use the psycopg2 driver for Postgres links (same as database.py)."""
    url = url.strip()
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    return url


def _get_engines() -> List[Engine]:
    global _engines
    if _engines is not None:
        return _engines

    urls = []
    for i in range(1, 10):
        value = (os.getenv(f"SEARCH_DB_URL_{i}") or "").strip()
        if value:
            urls.append(value)

    if not urls:
        print("STORAGE: no SEARCH_DB_URL_1 set, using local file search_data.db", flush=True)
        urls = ["sqlite:///./search_data.db"]

    engines = []
    for url in urls:
        fixed = _fix_url(url)
        args = {"check_same_thread": False} if fixed.startswith("sqlite") else {}
        engine = create_engine(fixed, pool_pre_ping=True, pool_recycle=300, connect_args=args)
        with engine.begin() as conn:
            conn.execute(text(_CREATE_TABLE))
        engines.append(engine)

    _engines = engines
    print(f"STORAGE: {len(engines)} database(s) ready", flush=True)
    return engines


def reset_for_tests() -> None:
    global _engines
    _engines = None


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def _size_mb(engine: Engine) -> float:
    """Size of the database in MB."""
    name = engine.dialect.name
    try:
        with engine.connect() as conn:
            if name == "postgresql":
                size = conn.execute(text("SELECT pg_database_size(current_database())")).scalar()
                return float(size or 0) / (1024 * 1024)
            if name == "sqlite":
                page_count = conn.execute(text("PRAGMA page_count")).scalar() or 0
                page_size = conn.execute(text("PRAGMA page_size")).scalar() or 0
                return float(page_count * page_size) / (1024 * 1024)
    except Exception as error:
        print("STORAGE: could not read size:", type(error).__name__, flush=True)
    return 0.0


def _max_mb() -> float:
    try:
        return float(os.getenv("SEARCH_DB_MAX_MB", "400"))
    except ValueError:
        return 400.0


def exists(url: str) -> bool:
    """True if this link is already saved in any database."""
    h = url_hash(url)
    for engine in _get_engines():
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM search_documents WHERE url_hash = :h"), {"h": h}
            ).first()
        if row:
            return True
    return False


def save_document(
    url: str,
    title: str = "",
    body: str = "",
    source: str = "",
    market: str = "",
    published_at: str = "",
) -> bool:
    """
    Save one document. Returns True if it was saved, False if it was
    already there (or every database is full).
    """
    url = (url or "").strip()
    if not url:
        return False
    if exists(url):
        return False

    record: Dict[str, str] = {
        "url_hash": url_hash(url),
        "url": url,
        "title": (title or "").strip()[:MAX_TITLE_CHARS],
        "body": (body or "").strip()[:MAX_TEXT_CHARS],
        "source": (source or "").strip(),
        "market": (market or "").strip(),
        "published_at": (published_at or "").strip(),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    limit = _max_mb()
    for engine in _get_engines():
        if _size_mb(engine) >= limit:
            continue  # this one is full, try the next
        with engine.begin() as conn:
            conn.execute(text(_INSERT), record)
        return True

    print("STORAGE: all databases are full. Add another SEARCH_DB_URL_n.", flush=True)
    return False


def search(query: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    Simple word search over every database.
    A document scores 1 point for each query word found in title or body.
    Newer documents win ties.
    """
    words = [w for w in (query or "").lower().split() if len(w) > 1][:8]
    if not words:
        return []

    found: List[Dict[str, str]] = []
    for engine in _get_engines():
        clauses = []
        params: Dict[str, str] = {}
        for i, word in enumerate(words):
            clauses.append(f"(lower(coalesce(title,'')) LIKE :w{i} OR lower(coalesce(body,'')) LIKE :w{i})")
            params[f"w{i}"] = f"%{word}%"
        sql = (
            "SELECT url, title, body, source, market, published_at, fetched_at "
            "FROM search_documents WHERE " + " OR ".join(clauses) +
            " ORDER BY fetched_at DESC LIMIT 200"
        )
        with engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        found.extend(dict(r) for r in rows)

    def score(doc: Dict[str, str]) -> int:
        haystack = ((doc.get("title") or "") + " " + (doc.get("body") or "")).lower()
        return sum(1 for w in words if w in haystack)

    found.sort(key=lambda d: (score(d), d.get("fetched_at") or ""), reverse=True)
    return found[:limit]


def count() -> int:
    total = 0
    for engine in _get_engines():
        with engine.connect() as conn:
            total += int(conn.execute(text("SELECT count(*) FROM search_documents")).scalar() or 0)
    return total
