
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
import re
import threading
import time
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
_engines_incomplete: bool = False   # True if a shelf/registry failed to load (retry later)
_engines_loaded_at: float = 0.0
_engines_lock = threading.RLock()
_RETRY_SECONDS = 60                 # how often to retry shelves that failed (sleeping free DBs)

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
            return ("sqlite", (parsed.host or "").lower(), parsed.database or "")

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


def _build_engine(url: str, provider: str, auth_token: str) -> Engine:
    """One place that builds an engine for every provider (Neon, Supabase, CockroachDB,
    Aiven, other PostgreSQL, Turso/libSQL, local SQLite)."""
    if url.startswith("sqlite:"):
        return create_engine(
            url, pool_pre_ping=True, pool_recycle=300,
            connect_args={"check_same_thread": False},
        )
    try:
        from search_engine.storage_registry import create_shelf_engine
        return create_shelf_engine(url, provider=provider, auth_token=auth_token or None)
    except ImportError as error:
        # e.g. the 'cryptography' package is missing: PostgreSQL shelves can still work.
        if str(provider).strip().lower() in {"turso", "libsql"}:
            raise
        print("STORAGE: registry helpers unavailable (", type(error).__name__, ") - using plain PostgreSQL engine", flush=True)
        return create_engine(
            _fix_url(url), pool_pre_ping=True, pool_recycle=300,
            connect_args={"connect_timeout": 15},
        )


def _init_engine(url: str, provider: str, auth_token: str) -> Engine:
    """Create the engine and the search table. Retries because free databases sleep."""
    last: Optional[BaseException] = None
    for attempt in range(3):
        engine = None
        try:
            engine = _build_engine(url, provider, auth_token)
            with engine.begin() as connection:
                connection.execute(text(_CREATE_TABLE))
            return engine
        except Exception as error:  # noqa: BLE001
            last = error
            if engine is not None:
                engine.dispose()
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    assert last is not None
    raise last


def _get_engines() -> List[Engine]:
    """Load configured shelves and initialize their search tables.

    A shelf that fails (for example a sleeping Neon/Supabase/Turso database) is
    retried every _RETRY_SECONDS instead of being lost until the next restart.
    """
    global _engines, _engine_limits, _engines_incomplete, _engines_loaded_at

    with _engines_lock:
        if _engines is not None:
            if not _engines_incomplete or (time.time() - _engines_loaded_at) < _RETRY_SECONDS:
                return _engines
            # Something failed last time: rebuild so it gets another chance.
            for old in _engines:
                try:
                    old.dispose()
                except Exception:
                    pass
            _engines = None

        dashboard_sources = []
        environment_sources = []
        registry_failed = False

        # Dashboard-managed shelves are the primary configuration.
        try:
            from search_engine.storage_registry import runtime_shelves

            for shelf in runtime_shelves():
                url = (shelf.get("url") or "").strip()
                if not url:
                    continue
                try:
                    maximum = float(shelf.get("max_storage_mb", 400))
                    threshold = float(shelf.get("threshold_percent", 80))
                    priority = int(shelf.get("priority", 100))
                    if maximum <= 0 or not 1 <= threshold <= 100:
                        print("STORAGE: skipping shelf with invalid limits", flush=True)
                        continue
                    dashboard_sources.append(
                        (url, maximum, threshold, priority,
                         str(shelf.get("provider") or "PostgreSQL"),
                         str(shelf.get("auth_token") or ""))
                    )
                except (TypeError, ValueError):
                    print("STORAGE: skipping shelf with invalid configuration", flush=True)
        except Exception as error:
            registry_failed = True
            print("STORAGE: dashboard registry unavailable:", type(error).__name__, str(error)[:200], flush=True)

        # Environment-variable shelves: SEARCH_DB_URL_1..9 (+ SEARCH_DB_TOKEN_n for Turso).
        for number in range(1, 10):
            url = (os.getenv(f"SEARCH_DB_URL_{number}") or "").strip()
            if not url:
                continue
            is_turso = url.lower().startswith(("libsql://", "sqlite+libsql://"))
            token = (os.getenv(f"SEARCH_DB_TOKEN_{number}") or os.getenv("TURSO_AUTH_TOKEN") or "").strip() if is_turso else ""
            environment_sources.append(
                (url,
                 _env_float(f"SEARCH_DB_MAX_MB_{number}", _env_float("SEARCH_DB_MAX_MB", 400)),
                 _env_float("SEARCH_DB_THRESHOLD_PERCENT", 80),
                 number,
                 "Turso" if is_turso else "PostgreSQL",
                 token)
            )

        # Lower dashboard priority numbers are attempted first; env shelves come after.
        sources = sorted(dashboard_sources, key=lambda item: item[3])
        sources.extend(environment_sources)

        # Local SQLite is for development only. Never silently switch to it when the
        # registry merely failed to load - that would hide every real shelf.
        if not sources and not registry_failed:
            print("STORAGE: no database configured; using local search_data.db", flush=True)
            sources = [("sqlite:///./search_data.db", 400, 80, 999999, "SQLite", "")]

        engines: List[Engine] = []
        limits: Dict[int, tuple] = {}
        seen = set()
        any_failed = registry_failed

        for url, maximum, threshold, _priority, provider, auth_token in sources:
            identity = _database_identity(url)
            if identity in seen:
                print("STORAGE: duplicate database configuration skipped", flush=True)
                continue
            seen.add(identity)

            try:
                engine = _init_engine(url, provider, auth_token)
                engines.append(engine)
                limits[id(engine)] = (maximum, threshold)
            except Exception as error:
                any_failed = True
                # Never print connection URLs or database passwords.
                print("STORAGE: shelf initialization failed:", provider, type(error).__name__, str(error)[:160], flush=True)

        _engine_limits = limits
        _engines = engines
        _engines_incomplete = any_failed
        _engines_loaded_at = time.time()

        print(f"STORAGE: {len(engines)} database shelf(s) ready", flush=True)
        return engines


def reset_for_tests() -> None:
    """Dispose cached connections and reload configuration next time."""
    global _engines, _engine_limits, _engines_incomplete, _engines_loaded_at

    _engines_incomplete = False
    _engines_loaded_at = 0.0

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


_EST_SQL = (
    "SELECT COALESCE(SUM(LENGTH(COALESCE(url,'')) + LENGTH(COALESCE(title,'')) + "
    "LENGTH(COALESCE(body,'')) + LENGTH(COALESCE(source,'')) + LENGTH(COALESCE(market,''))),0) "
    "FROM search_documents"
)


def _estimate_table_mb(engine: Engine) -> float:
    """Estimate VALE's own research table size (used when the provider hides real size)."""
    with engine.connect() as connection:
        size = connection.execute(text(_EST_SQL)).scalar() or 0
    return float(size) / (1024 * 1024)


def _size_mb(engine: Engine) -> float:
    """
    Read database size in MiB.
    Supabase/Neon/Aiven: real size via pg_database_size.
    CockroachDB, Turso/libSQL and others that hide it: estimate VALE's own table.
    Only if nothing at all can be measured is the shelf treated as full.
    """
    if engine.dialect.name == "postgresql":
        try:
            with engine.connect() as connection:
                size = connection.execute(
                    text("SELECT pg_database_size(current_database())")
                ).scalar()
            if size is not None:
                return float(size) / (1024 * 1024)
        except Exception:
            pass  # CockroachDB does not implement it - fall through to the estimate

    elif engine.dialect.name == "sqlite":
        try:
            with engine.connect() as connection:
                pages = connection.execute(text("PRAGMA page_count")).scalar() or 0
                page_size = connection.execute(text("PRAGMA page_size")).scalar() or 0
            measured = float(pages * page_size) / (1024 * 1024)
            if measured > 0:
                return measured
        except Exception:
            pass  # remote libSQL may not expose PRAGMA page_count

    try:
        return _estimate_table_mb(engine)
    except Exception as error:
        print("STORAGE: size check failed:", type(error).__name__, flush=True)

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


# ----------------------------------------------------------------------
# SEARCH (version 2): ignores useless words, ranks by match, full-text on Postgres
# ----------------------------------------------------------------------
STOPWORDS = set("""
a an the of in on at to for from with about and or but me my i you we it this that these those is are was were be been being
what whats which who whom whose when where why how do does did can could should would will may might please tell show give
find search look get got any some all latest news today now new update updates happening happened going
""".split())

_TSV = (
    "to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(body,'') || ' ' || coalesce(market,''))"
)

_SEARCH_COLUMNS = "url, title, body, source, market, published_at, fetched_at"

# shelves whose full-text index we already tried to create (once per run)
_fts_checked: set = set()


def clean_query(query: str) -> List[str]:
    """Pick the useful words of a question ('what is the latest gold news' -> ['gold'])."""
    words: List[str] = []
    for raw in re.findall(r"[^\W_]+", (query or "").lower()):
        if len(raw) < 2 or raw in STOPWORDS:
            continue
        if raw not in words:
            words.append(raw)
    return words[:8]


def _ensure_fts_index(engine: Engine) -> None:
    key = id(engine)
    if key in _fts_checked:
        return
    _fts_checked.add(key)
    try:
        with engine.begin() as connection:
            connection.execute(text(
                f"CREATE INDEX IF NOT EXISTS idx_search_documents_fts "
                f"ON search_documents USING GIN ({_TSV})"
            ))
    except Exception as error:  # the search still works without the index
        print("STORAGE: could not create the search index:", type(error).__name__, flush=True)


def _search_postgres(engine: Engine, words: List[str], limit: int) -> List[Dict[str, Any]]:
    _ensure_fts_index(engine)
    query = " | ".join(f"{word}:*" for word in words)
    sql = (
        f"SELECT {_SEARCH_COLUMNS}, ts_rank({_TSV}, to_tsquery('simple', :q)) AS score "
        f"FROM search_documents "
        f"WHERE {_TSV} @@ to_tsquery('simple', :q) "
        f"ORDER BY score DESC, fetched_at DESC LIMIT :lim"
    )
    with engine.connect() as connection:
        rows = connection.execute(text(sql), {"q": query, "lim": limit * 3}).mappings().all()
    return [dict(row) for row in rows]


def _search_like(engine: Engine, words: List[str]) -> List[Dict[str, Any]]:
    clauses = []
    params: Dict[str, Any] = {"lim": 200}
    for index, word in enumerate(words):
        clauses.append(
            f"(lower(coalesce(title,'')) LIKE :w{index} "
            f"OR lower(coalesce(body,'')) LIKE :w{index} "
            f"OR lower(coalesce(market,'')) LIKE :w{index})"
        )
        params[f"w{index}"] = f"%{word}%"
    sql = (
        f"SELECT {_SEARCH_COLUMNS} FROM search_documents WHERE "
        + " OR ".join(clauses)
        + " ORDER BY fetched_at DESC LIMIT :lim"
    )
    with engine.connect() as connection:
        rows = connection.execute(text(sql), params).mappings().all()
    return [dict(row) for row in rows]


def _newest(engine: Engine, limit: int) -> List[Dict[str, Any]]:
    sql = f"SELECT {_SEARCH_COLUMNS} FROM search_documents ORDER BY fetched_at DESC LIMIT :lim"
    with engine.connect() as connection:
        rows = connection.execute(text(sql), {"lim": limit}).mappings().all()
    return [dict(row) for row in rows]


def search(
    query: str,
    limit: int = 10,
) -> List[Dict[str, str]]:
    """
    Search titles, excerpts and tags across all reachable shelves.
    Useless words ('what', 'is', 'news') are ignored. If a question has only useless
    words (for example 'latest news'), the newest documents are returned.
    """
    if not (query or "").strip():
        return []

    try:
        limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        limit = 10

    words = clean_query(query)
    results: List[Dict[str, Any]] = []

    for engine in _get_engines():
        try:
            if not words:
                results.extend(_newest(engine, limit))
            elif engine.dialect.name == "postgresql":
                try:
                    results.extend(_search_postgres(engine, words, limit))
                except Exception as error:
                    print(
                        "STORAGE: full-text search failed, using simple search:",
                        type(error).__name__,
                        flush=True,
                    )
                    results.extend(_search_like(engine, words))
            else:
                results.extend(_search_like(engine, words))
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
            doc.pop("score", None)
            unique[url_hash(url)] = doc

    def score(doc: Dict[str, Any]) -> int:
        content = (
            (doc.get("title") or "")
            + " "
            + (doc.get("body") or "")
            + " "
            + (doc.get("market") or "")
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
      
