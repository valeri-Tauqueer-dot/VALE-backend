
"""
VALE AI — Search Storage Manager
=================================

Supports:
1. Dashboard-managed PostgreSQL shelves from storage_registry.py
2. Legacy SEARCH_DB_URL_1 through SEARCH_DB_URL_9 environment variables
3. Local SQLite fallback only when no database is configured

Stores only URLs, titles, short excerpts, and source metadata.
Never intentionally stores full articles.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url


MAX_TEXT_CHARS = 600
MAX_TITLE_CHARS = 300

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS search_documents (
    url_hash TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    body TEXT,
    source TEXT,
    market TEXT,
    published_at TEXT,
    fetched_at TEXT
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

# Maps engine identity to (allocated maximum MB, routing threshold %).
_engine_limits: Dict[int, tuple[float, float]] = {}


def _env_float(name: str, default: float) -> float:
    """Read a positive numeric environment setting safely."""
    try:
        value = float(os.getenv(name, str(default)))
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def _fix_url(url: str) -> str:
    """Normalize PostgreSQL URLs for psycopg2."""
    url = (url or "").strip()

    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]

    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]

    return url


def _database_identity(url: str) -> tuple:
    """Identify duplicate database configurations without logging credentials."""
    try:
        parsed = make_url(_fix_url(url))

        if parsed.get_backend_name() == "sqlite":
            return ("sqlite", parsed.database or "")

        return (
            parsed.get_backend_name(),
            (parsed.host or "").lower(),
            parsed.port,
            (parsed.database or "").strip("/"),
        )
    except Exception:
        return (
            "unknown",
            hashlib.sha256(url.encode("utf-8")).hexdigest(),
        )


def _get_engines() -> List[Engine]:
    """Load configured shelves once and initialize their search tables."""
    global _engines, _engine_limits

    if _engines is not None:
        return _engines

    dashboard_sources = []
    environment_sources = []

    # Dashboard-managed shelves are the primary configuration.
    try:
        from search_engine.storage_registry import runtime_shelves

        shelves = runtime_shelves()

        for shelf in shelves:
            url = (shelf.get("url") or "").strip()

            if not url:
                continue

            try:
                maximum = float(shelf.get("max_storage_mb", 400))
                threshold = float(shelf.get("threshold_percent", 80))
                priority = int(shelf.get("priority", 100))

                if maximum <= 0 or not 1 <= threshold <= 100:
                    print(
                        "STORAGE: skipping shelf with invalid limits",
                        flush=True,
                    )
                    continue

                dashboard_sources.append(
                    (url, maximum, threshold, priority)
                )

            except (TypeError, ValueError):
                print(
                    "STORAGE: skipping shelf with invalid configuration",
                    flush=True,
                )

    except Exception as error:
        print(
            "STORAGE: dashboard registry unavailable:",
            type(error).__name__,
            flush=True,
        )

    # Backward-compatible environment-variable configuration.
    for number in range(1, 10):
        url = (os.getenv(f"SEARCH_DB_URL_{number}") or "").strip()

        if url:
            environment_sources.append(
                (
                    url,
                    _env_float("SEARCH_DB_MAX_MB", 400),
                    _env_float("SEARCH_DB_THRESHOLD_PERCENT", 80),
                    number,
                )
            )

    # Lower dashboard priority numbers are attempted first.
    sources = sorted(dashboard_sources, key=lambda item: item[3])

    # Dashboard shelves take precedence over legacy environment shelves.
    sources.extend(environment_sources)

    # Local SQLite is for development only when no database is configured.
    if not sources:
        print(
            "STORAGE: no database configured; using local search_data.db",
            flush=True,
        )
        sources = [
            ("sqlite:///./search_data.db", 400, 80, 999999)
        ]

    engines: List[Engine] = []
    limits: Dict[int, tuple[float, float]] = {}
    seen = set()

    for url, maximum, threshold, _priority in sources:
        identity = _database_identity(url)

        if identity in seen:
            print(
                "STORAGE: duplicate database configuration skipped",
                flush=True,
            )
            continue

        seen.add(identity)
        engine = None

        try:
            fixed_url = _fix_url(url)

            connect_args: Dict[str, Any] = {}

            if fixed_url.startswith("sqlite"):
                connect_args["check_same_thread"] = False
            else:
                connect_args["connect_timeout"] = 8

            engine = create_engine(
                fixed_url,
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args=connect_args,
            )

            with engine.begin() as connection:
                connection.execute(text(_CREATE_TABLE))

            engines.append(engine)
            limits[id(engine)] = (maximum, threshold)

        except Exception as error:
            if engine is not None:
                engine.dispose()

            # Never print connection URLs or database passwords.
            print(
                "STORAGE: shelf initialization failed:",
                type(error).__name__,
                flush=True,
            )

    _engine_limits = limits
    _engines = engines

    print(
        f"STORAGE: {len(engines)} database shelf(s) ready",
        flush=True,
    )

    return engines


def reset_for_tests() -> None:
    """Dispose cached connections and reload configuration next time."""
    global _engines, _engine_limits

    if _engines:
        for engine in _engines:
            try:
                engine.dispose()
            except Exception:
                pass

    _engines = None
    _engine_limits = {}


def url_hash(url: str) -> str:
    """Create a stable identifier for a URL."""
    return hashlib.sha256(
        (url or "").strip().encode("utf-8")
    ).hexdigest()


def _size_mb(engine: Engine) -> float:
    """
    Read database size in MiB.
    If size cannot be checked, treat the shelf as full for safety.
    """
    try:
        with engine.connect() as connection:

            if engine.dialect.name == "postgresql":
                size = connection.execute(
                    text("SELECT pg_database_size(current_database())")
                ).scalar()

                return float(size or 0) / (1024 * 1024)

            if engine.dialect.name == "sqlite":
                pages = connection.execute(
                    text("PRAGMA page_count")
                ).scalar() or 0

                page_size = connection.execute(
                    text("PRAGMA page_size")
                ).scalar() or 0

                return float(pages * page_size) / (1024 * 1024)

    except Exception as error:
        print(
            "STORAGE: size check failed:",
            type(error).__name__,
            flush=True,
        )

    return float("inf")




def _routing_limit_mb(engine: Engine) -> float:
    """Return the maximum permitted size before routing skips this shelf."""
    if not _engine_limits:
        _get_engines()

    try:
        default_maximum = _env_float("SEARCH_DB_MAX_MB", 400)
        default_threshold = _env_float(
            "SEARCH_DB_THRESHOLD_PERCENT", 80
        )
    except (TypeError, ValueError):
        default_maximum = 400.0
        default_threshold = 80.0

    maximum, threshold = _engine_limits.get(
        id(engine),
        (default_maximum, default_threshold),
    )

    return maximum * threshold / 100.0
    
    

def _has_room(engine: Engine) -> bool:
    """Check whether the shelf is below its configured threshold."""
    return _size_mb(engine) < _routing_limit_mb(engine)


def exists(url: str) -> bool:
    """Check whether a URL already exists on any reachable shelf."""
    url = (url or "").strip()

    if not url:
        return False

    digest = url_hash(url)

    for engine in _get_engines():
        try:
            with engine.connect() as connection:
                row = connection.execute(
                    text(
                        "SELECT 1 FROM search_documents "
                        "WHERE url_hash = :digest"
                    ),
                    {"digest": digest},
                ).first()

            if row:
                return True

        except Exception as error:
            print(
                "STORAGE: duplicate check failed:",
                type(error).__name__,
                flush=True,
            )

    return False


def _make_record(
    url: str,
    title: str = "",
    body: str = "",
    source: str = "",
    market: str = "",
    published_at: str = "",
) -> Dict[str, str]:
    """Build a size-limited search record."""
    clean_url = (url or "").strip()

    return {
        "url_hash": url_hash(clean_url),
        "url": clean_url,
        "title": (title or "").strip()[:MAX_TITLE_CHARS],
        "body": (body or "").strip()[:MAX_TEXT_CHARS],
        "source": (source or "").strip()[:200],
        "market": (market or "").strip()[:100],
        "published_at": (published_at or "").strip()[:100],
        "fetched_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
    }


def save_document(
    url: str,
    title: str = "",
    body: str = "",
    source: str = "",
    market: str = "",
    published_at: str = "",
) -> bool:
    """
    Save one URL and its short excerpt.

    Returns True if inserted, False if already present or not saved.
    Tries the next eligible shelf if a write fails.
    """
    url = (url or "").strip()

    if not url:
        return False

    if exists(url):
        return False

    record = _make_record(
        url, title, body, source, market, published_at
    )

    for engine in _get_engines():
        try:
            if not _has_room(engine):
                continue

            with engine.begin() as connection:
                result = connection.execute(
                    text(_INSERT), record
                )

            if result.rowcount == 1:
                return True

            # The URL may have been inserted by another request.
            if result.rowcount == 0:
                return False

            # A successful write with an unknown rowcount should not be
            # retried on another shelf, which could create a duplicate.
            if result.rowcount is None or result.rowcount < 0:
                return True

        except Exception as error:
            print(
                "STORAGE: write failed; trying next shelf:",
                type(error).__name__,
                flush=True,
            )

    print(
        "STORAGE: no eligible shelf accepted the document",
        flush=True,
    )

    return False


def save_many(docs: List[Dict[str, str]]) -> int:
    """
    Save a list of search documents.

    Each item can contain url, title, body, source, market and published_at.
    Returns the database driver's reported number of inserted rows.
    """
    records: Dict[str, Dict[str, str]] = {}

    for doc in docs or []:
        if not isinstance(doc, dict):
            continue

        url = (doc.get("url") or "").strip()

        if not url:
            continue

        digest = url_hash(url)

        if digest not in records:
            records[digest] = _make_record(
                url=url,
                title=doc.get("title", ""),
                body=doc.get("body", ""),
                source=doc.get("source", ""),
                market=doc.get("market", ""),
                published_at=doc.get("published_at", ""),
            )

    if not records:
        return 0

    engines = _get_engines()

    # Remove records already stored on reachable shelves.
    for engine in engines:
        hashes = list(records)

        try:
            with engine.connect() as connection:
                for start in range(0, len(hashes), 200):
                    chunk = hashes[start:start + 200]

                    params = {
                        f"h{i}": digest
                        for i, digest in enumerate(chunk)
                    }

                    placeholders = ",".join(
                        f":h{i}" for i in range(len(chunk))
                    )

                    sql = (
                        "SELECT url_hash FROM search_documents "
                        f"WHERE url_hash IN ({placeholders})"
                    )

                    rows = connection.execute(
                        text(sql), params
                    ).fetchall()

                    for row in rows:
                        records.pop(row[0], None)

        except Exception as error:
            print(
                "STORAGE: batch duplicate check failed:",
                type(error).__name__,
                flush=True,
            )

    if not records:
        return 0

    batch = list(records.values())

    for engine in engines:
        try:
            if not _has_room(engine):
                continue

            with engine.begin() as connection:
                result = connection.execute(
                    text(_INSERT), batch
                )

            if isinstance(result.rowcount, int):
                if result.rowcount >= 0:
                    return min(result.rowcount, len(batch))

            return len(batch)

        except Exception as error:
            print(
                "STORAGE: batch write failed; trying next shelf:",
                type(error).__name__,
                flush=True,
            )

    print(
        "STORAGE: no eligible shelf accepted the batch",
        flush=True,
    )

    return 0


def search(
    query: str,
    limit: int = 10,
) -> List[Dict[str, str]]:
    """Search titles and excerpts across all reachable shelves."""
    words = [
        word
        for word in (query or "").lower().split()
        if len(word) > 1
    ][:8]

    if not words:
        return []

    try:
        limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        limit = 10

    results: List[Dict[str, Any]] = []

    for engine in _get_engines():
        clauses = []
        params: Dict[str, str] = {}

        for index, word in enumerate(words):
            clauses.append(
                f"(lower(coalesce(title,'')) LIKE :w{index} "
                f"OR lower(coalesce(body,'')) LIKE :w{index})"
            )

            params[f"w{index}"] = f"%{word}%"

        sql = (
            "SELECT url, title, body, source, market, "
            "published_at, fetched_at "
            "FROM search_documents WHERE "
            + " OR ".join(clauses)
            + " ORDER BY fetched_at DESC LIMIT 200"
        )

        try:
            with engine.connect() as connection:
                rows = connection.execute(
                    text(sql), params
                ).mappings().all()

            results.extend(dict(row) for row in rows)

        except Exception as error:
            print(
                "STORAGE: search failed on a shelf:",
                type(error).__name__,
                flush=True,
            )

    # Deduplicate results if the same URL is present on multiple shelves.
    unique: Dict[str, Dict[str, Any]] = {}

    for doc in results:
        url = str(doc.get("url") or "")

        if url:
            unique[url_hash(url)] = doc

    def score(doc: Dict[str, Any]) -> int:
        content = (
            (doc.get("title") or "")
            + " "
            + (doc.get("body") or "")
        ).lower()

        return sum(1 for word in words if word in content)

    output = list(unique.values())

    output.sort(
        key=lambda doc: (
            score(doc),
            str(doc.get("fetched_at") or ""),
        ),
        reverse=True,
    )

    return output[:limit]


def count() -> int:
    """Return the total number of search records across reachable shelves."""
    total = 0

    for engine in _get_engines():
        try:
            with engine.connect() as connection:
                value = connection.execute(
                    text("SELECT count(*) FROM search_documents")
                ).scalar()

            total += int(value or 0)

        except Exception as error:
            print(
                "STORAGE: count failed on a shelf:",
                type(error).__name__,
                flush=True,
            )

    return total
      
