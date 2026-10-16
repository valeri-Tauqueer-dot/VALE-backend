"""
VALE AI — Persistent Storage Shelf Registry
===========================================

Drop-in module required by search_engine/storage.py and storage_api.py.

What it does:
- Persists shelf configuration in VALE's primary DATABASE_URL database.
- Encrypts connection URLs at rest using SECRET_KEY (stable 32+ character secret).
- Keeps external database contents untouched when a shelf is edited or removed.
- Exposes the exact functions expected by the existing Storage Command Center.

Important:
- Keep SECRET_KEY stable. Changing it makes previously encrypted URLs unreadable.
- This registry stores connection configuration only; it does not migrate or delete
  research records in the connected Supabase/Neon databases.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def _normalize_url(url: str) -> str:
    value = (url or "").strip()
    if value.startswith("postgres://"):
        return "postgresql+psycopg2://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg2://" + value[len("postgresql://"):]
    return value


def _primary_database_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        # Match database.py's local fallback for local development only.
        raw = "sqlite:///./vale_fallback.db"
    return _normalize_url(raw)


def _registry_engine():
    url = _primary_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args=connect_args,
    )


def _fernet() -> Fernet:
    secret = (os.getenv("SECRET_KEY") or "").strip()
    if len(secret) < 32:
        raise RuntimeError(
            "Storage registry encryption is not configured. Set a stable SECRET_KEY "
            "of at least 32 characters in Render environment variables."
        )
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def _encrypt_url(url: str) -> str:
    return _fernet().encrypt(url.encode("utf-8")).decode("ascii")


def _decrypt_url(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError(
            "A saved storage URL could not be decrypted. Confirm that Render's SECRET_KEY "
            "is the same stable value used when the shelf was saved."
        ) from exc


def _ensure_registry_table() -> None:
    engine = _registry_engine()
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS vale_storage_shelves (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    provider VARCHAR(40) NOT NULL,
                    encrypted_url TEXT NOT NULL,
                    max_storage_mb FLOAT NOT NULL,
                    threshold_percent FLOAT NOT NULL DEFAULT 80,
                    priority INTEGER NOT NULL DEFAULT 100,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at VARCHAR(40) NOT NULL DEFAULT ''
                )
            """))
            # SQLite accepts the schema above. PostgreSQL INTEGER primary keys need
            # generated IDs, so use a sequence-backed BIGSERIAL table when first created.
            # Existing tables are never dropped or rebuilt.
            if engine.dialect.name == "postgresql":
                # If table was just created with INTEGER PK, create a sequence and attach it.
                conn.execute(text("CREATE SEQUENCE IF NOT EXISTS vale_storage_shelves_id_seq"))
                conn.execute(text("""
                    ALTER TABLE vale_storage_shelves
                    ALTER COLUMN id SET DEFAULT nextval('vale_storage_shelves_id_seq')
                """))
                conn.execute(text("""
                    SELECT setval(
                        'vale_storage_shelves_id_seq',
                        GREATEST(COALESCE((SELECT MAX(id) FROM vale_storage_shelves), 0) + 1, 1),
                        false
                    )
                """))
    finally:
        engine.dispose()


def _rows(include_secrets: bool = False) -> List[Dict[str, Any]]:
    _ensure_registry_table()
    engine = _registry_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, name, provider, encrypted_url, max_storage_mb,
                       threshold_percent, priority, enabled, created_at
                FROM vale_storage_shelves
                ORDER BY priority ASC, id ASC
            """)).mappings().all()
        result: List[Dict[str, Any]] = []
        for row in rows:
            item = {
                "id": int(row["id"]),
                "name": row["name"],
                "provider": row["provider"],
                "max_storage_mb": float(row["max_storage_mb"]),
                "threshold_percent": float(row["threshold_percent"]),
                "priority": int(row["priority"]),
                "enabled": bool(row["enabled"]),
                "created_at": row["created_at"] or "",
            }
            if include_secrets:
                item["url"] = _decrypt_url(row["encrypted_url"])
            result.append(item)
        return result
    finally:
        engine.dispose()


def list_shelves(include_secrets: bool = False) -> List[Dict[str, Any]]:
    """List dashboard shelves. URL is omitted unless explicitly requested internally."""
    return _rows(include_secrets=include_secrets)


def runtime_shelves() -> List[Dict[str, Any]]:
    """Return enabled shelves in priority order for the search-storage router."""
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "provider": row["provider"],
            "url": row["url"],
            "max_storage_mb": row["max_storage_mb"],
            "threshold_percent": row["threshold_percent"],
            "priority": row["priority"],
            "enabled": row["enabled"],
        }
        for row in list_shelves(include_secrets=True)
        if row["enabled"]
    ]


def test_connection(url: str) -> Dict[str, Any]:
    """Verify a PostgreSQL URL and return safe database metadata."""
    raw = (url or "").strip()
    if not raw:
        raise ValueError("A PostgreSQL connection URL is required.")
    fixed = _normalize_url(raw)
    try:
        parsed = make_url(fixed)
    except Exception as exc:
        raise ValueError("The connection URL is not valid.") from exc
    if parsed.get_backend_name() != "postgresql":
        raise ValueError("Only PostgreSQL connection URLs are supported.")
    if not parsed.host or not parsed.database or not parsed.username:
        raise ValueError("The URL must include a host, database name and username.")
    engine = None
    try:
        engine = create_engine(
            fixed,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 8},
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            size_bytes = conn.execute(
                text("SELECT pg_database_size(current_database())")
            ).scalar() or 0
            db_name = conn.execute(
                text("SELECT current_database()")
            ).scalar() or parsed.database
        return {
            "database_name": str(db_name),
            "used_mb": round(float(size_bytes) / (1024 * 1024), 2),
        }
    except Exception as exc:
        # Do not include exception messages: drivers can sometimes echo connection details.
        raise RuntimeError(
            f"Connection test failed ({type(exc).__name__}). Check host, credentials, SSL and network access."
        ) from exc
    finally:
        if engine is not None:
            engine.dispose()


def add_shelf(
    name: str,
    provider: str,
    url: str,
    max_storage_mb: float,
    threshold_percent: float = 80,
    priority: int = 100,
) -> int:
    """Test and persist a new shelf; never modifies the external database's records."""
    clean_name = (name or "").strip()
    clean_provider = (provider or "PostgreSQL").strip() or "PostgreSQL"
    clean_url = (url or "").strip()
    maximum = float(max_storage_mb)
    threshold = float(threshold_percent)
    priority_value = int(priority)

    if not clean_name:
        raise ValueError("Shelf name is required.")
    if len(clean_name) > 100 or len(clean_provider) > 40:
        raise ValueError("Shelf name or provider is too long.")
    if maximum <= 0:
        raise ValueError("Allocated capacity must be greater than zero.")
    if not 50 <= threshold <= 95:
        raise ValueError("Routing threshold must be between 50 and 95 percent.")
    if not 1 <= priority_value <= 10000:
        raise ValueError("Priority must be between 1 and 10000.")

    # Check the database first; only store the URL after a successful connection.
    test_connection(clean_url)
    encrypted = _encrypt_url(_normalize_url(clean_url))
    _ensure_registry_table()
    engine = _registry_engine()
    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
                INSERT INTO vale_storage_shelves
                    (name, provider, encrypted_url, max_storage_mb,
                     threshold_percent, priority, enabled, created_at)
                VALUES
                    (:name, :provider, :encrypted_url, :maximum,
                     :threshold, :priority, TRUE, :created_at)
            """), {
                "name": clean_name,
                "provider": clean_provider,
                "encrypted_url": encrypted,
                "maximum": maximum,
                "threshold": threshold,
                "priority": priority_value,
                "created_at": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(timespec="seconds"),
            })
            shelf_id = result.lastrowid
            if shelf_id is None:
                shelf_id = conn.execute(text(
                    "SELECT id FROM vale_storage_shelves WHERE name=:name AND encrypted_url=:url ORDER BY id DESC LIMIT 1"
                ), {"name": clean_name, "url": encrypted}).scalar()
            if shelf_id is None:
                raise RuntimeError("Shelf was saved but its ID could not be read.")
            return int(shelf_id)
    finally:
        engine.dispose()


def update_shelf(shelf_id: int, **changes: Any) -> bool:
    """Update only supported configuration fields; connection URL is immutable here."""
    allowed = {"name", "max_storage_mb", "threshold_percent", "priority", "enabled"}
    updates: Dict[str, Any] = {}
    for key, value in changes.items():
        if key not in allowed or value is None:
            continue
        if key == "name":
            value = str(value).strip()
            if not value or len(value) > 100:
                raise ValueError("Shelf name must contain 1 to 100 characters.")
        elif key == "max_storage_mb":
            value = float(value)
            if value <= 0:
                raise ValueError("Allocated capacity must be greater than zero.")
        elif key == "threshold_percent":
            value = float(value)
            if not 50 <= value <= 95:
                raise ValueError("Routing threshold must be between 50 and 95 percent.")
        elif key == "priority":
            value = int(value)
            if not 1 <= value <= 10000:
                raise ValueError("Priority must be between 1 and 10000.")
        elif key == "enabled":
            value = bool(value)
        updates[key] = value

    if not updates:
        return bool(_shelf_exists(shelf_id))

    _ensure_registry_table()
    engine = _registry_engine()
    try:
        with engine.begin() as conn:
            assignments = ", ".join(f"{key} = :{key}" for key in updates)
            params = dict(updates)
            params["id"] = int(shelf_id)
            result = conn.execute(text(
                f"UPDATE vale_storage_shelves SET {assignments} WHERE id=:id"
            ), params)
            return result.rowcount > 0
    finally:
        engine.dispose()


def _shelf_exists(shelf_id: int) -> bool:
    _ensure_registry_table()
    engine = _registry_engine()
    try:
        with engine.connect() as conn:
            return conn.execute(text(
                "SELECT 1 FROM vale_storage_shelves WHERE id=:id"
            ), {"id": int(shelf_id)}).first() is not None
    finally:
        engine.dispose()


def delete_shelf(shelf_id: int) -> bool:
    """Delete the saved connection configuration only, not external database data."""
    _ensure_registry_table()
    engine = _registry_engine()
    try:
        with engine.begin() as conn:
            result = conn.execute(text(
                "DELETE FROM vale_storage_shelves WHERE id=:id"
            ), {"id": int(shelf_id)})
            return result.rowcount > 0
    finally:
        engine.dispose()
