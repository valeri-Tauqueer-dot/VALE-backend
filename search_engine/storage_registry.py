"""VALE AI persistent storage shelf registry.

Compatible with the existing VALE Storage Command Center and research storage.
Supports PostgreSQL-compatible providers and Turso/libSQL through SQLAlchemy.
Shelf URLs and Turso auth tokens are encrypted at rest using SECRET_KEY.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

_CONFIG_PREFIX = "VALE-CONNECTION-V1:"
_POSTGRES_PROVIDERS = {
    "postgresql", "postgres", "other postgresql", "supabase", "neon",
    "aiven", "nile", "prisma postgres", "cockroachdb", "freebase.cloud",
}
_TURSO_PROVIDERS = {"turso", "libsql"}


def _is_turso(provider: str, url: str = "") -> bool:
    return (provider or "").strip().lower() in _TURSO_PROVIDERS or (url or "").strip().lower().startswith(("libsql://", "https://")) and "turso" in (url or "").lower()


def _clean_pasted_url(url: str) -> str:
    """Strip things people paste by accident: psql '...', quotes, spaces, newlines."""
    value = (url or "").strip()
    value = re.sub(r"^\s*psql\s+", "", value, flags=re.IGNORECASE)
    value = value.strip().strip("\"'`").strip()
    return value.replace("\n", "").replace("\r", "").replace(" ", "")


def _normalize_postgres_url(url: str) -> str:
    """Normalize any PostgreSQL-compatible URL (Neon, Supabase, CockroachDB, Aiven, ...)
    for psycopg2 and make sure SSL is requested for remote hosts."""
    value = _clean_pasted_url(url)
    if value.startswith("postgres://"):
        value = "postgresql+psycopg2://" + value[len("postgres://"):]
    elif value.startswith("postgresql://"):
        value = "postgresql+psycopg2://" + value[len("postgresql://"):]
    elif value.startswith("cockroachdb://"):
        value = "postgresql+psycopg2://" + value[len("cockroachdb://"):]
    if not value.startswith("postgresql"):
        return value
    try:
        parsed = make_url(value)
        host = (parsed.host or "").lower()
        if host and host not in ("localhost", "127.0.0.1", "::1") and "sslmode" not in parsed.query:
            parsed = parsed.update_query_dict({"sslmode": "require"})
            return parsed.render_as_string(hide_password=False)
    except Exception:
        pass
    return value


_PG_CONNECT_ARGS: Dict[str, Any] = {
    "connect_timeout": 15,      # Neon/Supabase free databases need a few seconds to wake up
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
}


def _safe_error(exc: BaseException) -> str:
    """Short, password-free reason so the dashboard can show WHY a connection failed."""
    root = exc.__cause__ or exc.__context__ or exc
    text_value = " ".join(str(getattr(root, "orig", root)).split())
    text_value = re.sub(r"(://[^:/@\s]+:)[^@\s]+@", r"\1***@", text_value)
    return f"{type(root).__name__}: {text_value[:220]}"


def _with_retries(action, attempts: int = 3, delay: float = 2.0):
    """Free databases (Neon, Supabase, Turso) sleep when idle; the first try may fail."""
    last: Optional[BaseException] = None
    for number in range(attempts):
        try:
            return action()
        except Exception as exc:  # noqa: BLE001
            last = exc
            if number < attempts - 1:
                time.sleep(delay * (number + 1))
    assert last is not None
    raise last


def _normalize_turso_url(url: str) -> str:
    """Convert a Turso libsql:// URL to the SQLAlchemy libSQL dialect URL."""
    value = _clean_pasted_url(url)
    if value.startswith("sqlite+libsql://"):
        return value
    if value.startswith("libsql://"):
        host = value[len("libsql://"):].split("?", 1)[0].strip("/")
    elif value.startswith("https://"):
        host = value[len("https://"):].split("?", 1)[0].strip("/")
    else:
        raise ValueError("For Turso, enter the libsql:// URL from the Turso dashboard.")
    if not host or "/" in host:
        raise ValueError("Turso URL must contain a database host, such as libsql://database-org.turso.io.")
    return f"sqlite+libsql://{host}?secure=true"


def _fernet() -> Fernet:
    secret = (os.getenv("SECRET_KEY") or "").strip()
    if len(secret) < 32:
        raise RuntimeError("Set a stable SECRET_KEY of at least 32 characters in Render before saving storage credentials.")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def _encrypt_config(url: str, auth_token: str = "") -> str:
    # Prefix allows existing encrypted URL rows to remain readable without migration.
    payload = _CONFIG_PREFIX + json.dumps({"url": url, "auth_token": auth_token or ""}, separators=(",", ":"))
    return _fernet().encrypt(payload.encode("utf-8")).decode("ascii")


def _decrypt_config(ciphertext: str) -> Dict[str, str]:
    try:
        raw = _fernet().decrypt((ciphertext or "").encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("A saved storage credential could not be decrypted. Confirm SECRET_KEY has not changed.") from exc
    if raw.startswith(_CONFIG_PREFIX):
        try:
            data = json.loads(raw[len(_CONFIG_PREFIX):])
            return {"url": str(data.get("url", "")), "auth_token": str(data.get("auth_token", ""))}
        except Exception as exc:
            raise RuntimeError("A saved storage credential has an invalid format.") from exc
    # Backward compatibility with the previous registry that encrypted only the URL.
    return {"url": raw, "auth_token": ""}


def _primary_database_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        raw = "sqlite:///./vale_fallback.db"
    if raw.lower().startswith("libsql://"):
        return _normalize_turso_url(raw)
    return _normalize_postgres_url(raw)


def _registry_engine() -> Engine:
    url = _primary_database_url()
    if url.startswith("sqlite+libsql"):
        token = (os.getenv("TURSO_AUTH_TOKEN") or os.getenv("DATABASE_AUTH_TOKEN") or "").strip()
        return create_engine(url, pool_pre_ping=True, pool_recycle=300,
                             connect_args={"auth_token": token} if token else {})
    if url.startswith("sqlite"):
        return create_engine(url, pool_pre_ping=True, pool_recycle=300, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, pool_recycle=300, connect_args=dict(_PG_CONNECT_ARGS))


def create_shelf_engine(url: str, provider: str = "PostgreSQL", auth_token: Optional[str] = None) -> Engine:
    """Create a shelf engine. Turso requires a token stored separately from its URL."""
    if _is_turso(provider, url):
        try:
            from importlib.util import find_spec
            if find_spec("sqlalchemy_libsql") is None and find_spec("sqlalchemy-libsql") is None:
                # Import name for the package is supplied by SQLAlchemy entry points;
                # create_engine below will give the clear missing-dialect error.
                pass
        except Exception:
            pass
        normalized = _normalize_turso_url(url)
        args: Dict[str, Any] = {}
        if auth_token:
            args["auth_token"] = auth_token
        return create_engine(normalized, pool_pre_ping=True, pool_recycle=300, connect_args=args)
    normalized = _normalize_postgres_url(url)
    if not normalized.startswith(("postgresql+psycopg2://", "postgresql://")):
        raise ValueError("This provider needs a PostgreSQL connection URL. Choose Turso for a libSQL URL.")
    return create_engine(normalized, pool_pre_ping=True, pool_recycle=300, connect_args=dict(_PG_CONNECT_ARGS))


_registry_ready = False


def _ensure_registry_table() -> None:
    global _registry_ready
    if _registry_ready:
        return

    def _create() -> None:
        engine = _registry_engine()
        try:
            with engine.begin() as conn:
                conn.execute(text("""CREATE TABLE IF NOT EXISTS vale_storage_shelves (
                    id INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL, provider VARCHAR(40) NOT NULL,
                    encrypted_url TEXT NOT NULL, max_storage_mb FLOAT NOT NULL,
                    threshold_percent FLOAT NOT NULL DEFAULT 80, priority INTEGER NOT NULL DEFAULT 100,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE, created_at VARCHAR(40) NOT NULL DEFAULT ''
                )"""))
                if engine.dialect.name == "postgresql":
                    conn.execute(text("CREATE SEQUENCE IF NOT EXISTS vale_storage_shelves_id_seq"))
                    conn.execute(text("ALTER TABLE vale_storage_shelves ALTER COLUMN id SET DEFAULT nextval('vale_storage_shelves_id_seq')"))
                    conn.execute(text("SELECT setval('vale_storage_shelves_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM vale_storage_shelves), 0) + 1, 1), false)"))
        finally:
            engine.dispose()

    _with_retries(_create)
    _registry_ready = True


def list_shelves(include_secrets: bool = False) -> List[Dict[str, Any]]:
    _ensure_registry_table()
    engine = _registry_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""SELECT id,name,provider,encrypted_url,max_storage_mb,
                threshold_percent,priority,enabled,created_at FROM vale_storage_shelves ORDER BY priority ASC,id ASC""")).mappings().all()
        output: List[Dict[str, Any]] = []
        for row in rows:
            item: Dict[str, Any] = {
                "id": int(row["id"]), "name": row["name"], "provider": row["provider"],
                "max_storage_mb": float(row["max_storage_mb"]), "threshold_percent": float(row["threshold_percent"]),
                "priority": int(row["priority"]), "enabled": bool(row["enabled"]), "created_at": row["created_at"] or "",
            }
            if include_secrets:
                cfg = _decrypt_config(row["encrypted_url"])
                item["url"] = cfg["url"]
                item["auth_token"] = cfg["auth_token"]
            output.append(item)
        return output
    finally:
        engine.dispose()


def runtime_shelves() -> List[Dict[str, Any]]:
    return [row for row in list_shelves(include_secrets=True) if row.get("enabled")]


def _ensure_search_table(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("""CREATE TABLE IF NOT EXISTS search_documents (
            url_hash TEXT PRIMARY KEY, url TEXT NOT NULL, title TEXT, body TEXT, source TEXT,
            market TEXT, published_at TEXT, fetched_at TEXT
        )"""))


def _used_mb(engine: Engine) -> float:
    if engine.dialect.name == "postgresql":
        try:
            with engine.connect() as conn:
                size = conn.execute(text("SELECT pg_database_size(current_database())")).scalar()
            if size is not None:
                return round(float(size) / (1024 * 1024), 2)
        except Exception:
            pass  # CockroachDB and some hosted Postgres variants do not allow this function
    # Fresh connection: estimate VALE's own research table (CockroachDB, SQLite, Turso/libSQL).
    try:
        with engine.connect() as conn:
            size = conn.execute(text("SELECT COALESCE(SUM(LENGTH(COALESCE(url,'')) + LENGTH(COALESCE(title,'')) + LENGTH(COALESCE(body,'')) + LENGTH(COALESCE(source,'')) + LENGTH(COALESCE(market,''))),0) FROM search_documents")).scalar() or 0
        return round(float(size) / (1024 * 1024), 2)
    except Exception:
        return 0.0


def test_connection(url: str, provider: str = "PostgreSQL", auth_token: Optional[str] = None) -> Dict[str, Any]:
    raw = (url or "").strip()
    if not raw:
        raise ValueError("A database connection URL is required.")
    is_turso = _is_turso(provider, raw)
    if is_turso and not (auth_token or "").strip():
        raise ValueError("Turso requires its database authentication token. Paste it in the Turso token field.")
    if not is_turso:
        try:
            parsed = make_url(_normalize_postgres_url(raw))
        except Exception as exc:
            raise ValueError("The PostgreSQL connection URL is not valid.") from exc
        if parsed.get_backend_name() != "postgresql" or not parsed.host or not parsed.database or not parsed.username:
            raise ValueError("The PostgreSQL URL must include host, database, username and password as supplied by the provider.")
    engine = None
    try:
        engine = create_shelf_engine(raw, provider, auth_token)

        def _probe() -> None:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

        _with_retries(_probe)
        _ensure_search_table(engine)
        used = _used_mb(engine)
        try:
            with engine.connect() as conn:
                db_name = conn.execute(text("SELECT current_database()")).scalar() if engine.dialect.name == "postgresql" else engine.url.host or "Turso/libSQL database"
        except Exception:
            db_name = engine.url.host or provider
        return {"database_name": str(db_name or provider), "used_mb": round(float(used), 2), "database_type": "libSQL" if is_turso else "PostgreSQL"}
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise RuntimeError(f"Connection test failed - {_safe_error(exc)}. Check the URL, token/password, SSL and provider limits.") from exc
    finally:
        if engine is not None:
            engine.dispose()


def add_shelf(name: str, provider: str, url: str, max_storage_mb: float,
              threshold_percent: float = 80, priority: int = 100,
              auth_token: Optional[str] = None) -> int:
    clean_name, clean_provider, clean_url = (name or "").strip(), (provider or "PostgreSQL").strip(), (url or "").strip()
    maximum, threshold, priority_value = float(max_storage_mb), float(threshold_percent), int(priority)
    if not clean_name or len(clean_name) > 100:
        raise ValueError("Shelf name must contain 1 to 100 characters.")
    if not clean_provider or len(clean_provider) > 40:
        raise ValueError("Provider name must contain 1 to 40 characters.")
    if maximum <= 0:
        raise ValueError("Allocated capacity must be greater than zero.")
    if not 50 <= threshold <= 95:
        raise ValueError("Routing threshold must be between 50 and 95 percent.")
    if not 1 <= priority_value <= 10000:
        raise ValueError("Priority must be between 1 and 10000.")
    test_connection(clean_url, clean_provider, auth_token)
    normalized = _normalize_turso_url(clean_url) if _is_turso(clean_provider, clean_url) else _normalize_postgres_url(clean_url)
    encrypted = _encrypt_config(normalized, auth_token or "")
    _ensure_registry_table()
    engine = _registry_engine()
    try:
        with engine.begin() as conn:
            shelf_id = conn.execute(text("""INSERT INTO vale_storage_shelves
                (name,provider,encrypted_url,max_storage_mb,threshold_percent,priority,enabled,created_at)
                VALUES (:name,:provider,:encrypted_url,:maximum,:threshold,:priority,TRUE,:created_at)
                RETURNING id"""), {
                "name": clean_name, "provider": clean_provider, "encrypted_url": encrypted,
                "maximum": maximum, "threshold": threshold, "priority": priority_value,
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }).scalar()
            if shelf_id is None:
                raise RuntimeError("Shelf was saved but its ID could not be read.")
            return int(shelf_id)
    finally:
        engine.dispose()


def _shelf_exists(shelf_id: int) -> bool:
    _ensure_registry_table()
    engine = _registry_engine()
    try:
        with engine.connect() as conn:
            return conn.execute(text("SELECT 1 FROM vale_storage_shelves WHERE id=:id"), {"id": int(shelf_id)}).first() is not None
    finally:
        engine.dispose()


def update_shelf(shelf_id: int, **changes: Any) -> bool:
    allowed = {"name", "max_storage_mb", "threshold_percent", "priority", "enabled"}
    updates: Dict[str, Any] = {}
    for key, value in changes.items():
        if key not in allowed or value is None:
            continue
        if key == "name":
            value = str(value).strip()
            if not value or len(value) > 100: raise ValueError("Shelf name must contain 1 to 100 characters.")
        elif key == "max_storage_mb":
            value = float(value)
            if value <= 0: raise ValueError("Allocated capacity must be greater than zero.")
        elif key == "threshold_percent":
            value = float(value)
            if not 50 <= value <= 95: raise ValueError("Routing threshold must be between 50 and 95 percent.")
        elif key == "priority":
            value = int(value)
            if not 1 <= value <= 10000: raise ValueError("Priority must be between 1 and 10000.")
        elif key == "enabled":
            value = bool(value)
        updates[key] = value
    if not updates: return _shelf_exists(shelf_id)
    _ensure_registry_table()
    engine = _registry_engine()
    try:
        with engine.begin() as conn:
            assignments = ", ".join(f"{key}=:{key}" for key in updates)
            params = dict(updates); params["id"] = int(shelf_id)
            result = conn.execute(text(f"UPDATE vale_storage_shelves SET {assignments} WHERE id=:id"), params)
            return result.rowcount > 0
    finally:
        engine.dispose()


def delete_shelf(shelf_id: int) -> bool:
    """Delete only the VALE connection configuration, never provider-side research data."""
    _ensure_registry_table()
    engine = _registry_engine()
    try:
        with engine.begin() as conn:
            result = conn.execute(text("DELETE FROM vale_storage_shelves WHERE id=:id"), {"id": int(shelf_id)})
            return result.rowcount > 0
    finally:
        engine.dispose()
