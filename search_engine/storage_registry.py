"""Secure dynamic storage-shelf registry for VALE.

Connection strings are encrypted at rest using a key derived from SECRET_KEY.
Only PostgreSQL URLs are accepted. Provider capacity is user-configured because
free-plan limits and project-level quotas differ by provider.
"""
from __future__ import annotations

import base64
import hashlib
import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from database import engine as app_engine

Base = declarative_base()

class StorageShelf(Base):
    __tablename__ = "vale_storage_shelves"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    provider = Column(String(40), nullable=False, default="postgresql")
    encrypted_url = Column(Text, nullable=False)
    max_storage_mb = Column(Float, nullable=False)
    threshold_percent = Column(Float, nullable=False, default=80.0)
    priority = Column(Integer, nullable=False, default=100)
    enabled = Column(Boolean, nullable=False, default=True)
    last_test_status = Column(String(30), nullable=False, default="not_tested")
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

Session = sessionmaker(bind=app_engine, autoflush=False, autocommit=False)
_tables_ready = False


def _fernet() -> Fernet:
    secret = (os.getenv("SECRET_KEY") or "").strip()
    if len(secret) < 32:
        raise RuntimeError("Set a stable SECRET_KEY of at least 32 characters in Render before saving database credentials.")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def _ensure_tables() -> None:
    global _tables_ready
    if not _tables_ready:
        Base.metadata.create_all(bind=app_engine)
        _tables_ready = True


def validate_postgres_url(url: str) -> str:
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg2"}:
        raise ValueError("Only PostgreSQL connection URLs are supported by this storage manager.")
    if not parsed.hostname or not parsed.path.strip("/"):
        raise ValueError("The connection URL must include a database host and database name.")
    # Normalize SQLAlchemy driver to match this project's psycopg2 dependency.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def test_connection(url: str) -> dict[str, Any]:
    fixed = validate_postgres_url(url)
    temp_engine = create_engine(fixed, pool_pre_ping=True, connect_args={"connect_timeout": 8})
    try:
        with temp_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_name = conn.execute(text("SELECT current_database()")).scalar() or "PostgreSQL"
            size_bytes = conn.execute(text("SELECT pg_database_size(current_database())")).scalar() or 0
        return {"connected": True, "database_name": str(db_name), "used_mb": round(float(size_bytes) / (1024 * 1024), 2)}
    finally:
        temp_engine.dispose()


def add_shelf(*, name: str, provider: str, url: str, max_storage_mb: float,
              threshold_percent: float = 80.0, priority: int = 100) -> int:
    _ensure_tables()
    fixed = validate_postgres_url(url)
    if not name.strip():
        raise ValueError("Give this storage shelf a name.")
    if max_storage_mb <= 0 or max_storage_mb > 10_000_000:
        raise ValueError("Maximum storage must be greater than 0 MB.")
    if not 50 <= threshold_percent <= 95:
        raise ValueError("The routing threshold must be between 50% and 95%.")
    # Verify credentials before storing them.
    test_connection(fixed)
    encrypted = _fernet().encrypt(fixed.encode("utf-8")).decode("ascii")
    db = Session()
    try:
        shelf = StorageShelf(name=name.strip()[:100], provider=(provider or "PostgreSQL").strip()[:40],
                             encrypted_url=encrypted, max_storage_mb=float(max_storage_mb),
                             threshold_percent=float(threshold_percent), priority=int(priority), enabled=True,
                             last_test_status="connected", last_tested_at=datetime.now(timezone.utc))
        db.add(shelf)
        db.commit()
        db.refresh(shelf)
        return int(shelf.id)
    finally:
        db.close()


def list_shelves(include_secrets: bool = False) -> list[dict[str, Any]]:
    _ensure_tables()
    db = Session()
    result = []
    try:
        shelves = db.query(StorageShelf).order_by(StorageShelf.priority.asc(), StorageShelf.id.asc()).all()
        for s in shelves:
            item = {"id": s.id, "name": s.name, "provider": s.provider,
                    "max_storage_mb": float(s.max_storage_mb), "threshold_percent": float(s.threshold_percent),
                    "priority": int(s.priority), "enabled": bool(s.enabled),
                    "last_test_status": s.last_test_status,
                    "last_tested_at": s.last_tested_at.isoformat() if s.last_tested_at else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None}
            if include_secrets:
                try:
                    item["url"] = _fernet().decrypt(s.encrypted_url.encode("ascii")).decode("utf-8")
                except (InvalidToken, ValueError):
                    item["url"] = None
            result.append(item)
        return result
    finally:
        db.close()


def runtime_shelves() -> list[dict[str, Any]]:
    """Return active dynamic shelves for the search storage adapter."""
    return [s for s in list_shelves(include_secrets=True) if s["enabled"] and s.get("url")]


def update_shelf(shelf_id: int, *, name: str | None = None, max_storage_mb: float | None = None,
                 threshold_percent: float | None = None, priority: int | None = None,
                 enabled: bool | None = None) -> bool:
    _ensure_tables()
    db = Session()
    try:
        s = db.query(StorageShelf).filter(StorageShelf.id == shelf_id).first()
        if not s:
            return False
        if name is not None:
            if not name.strip(): raise ValueError("Shelf name cannot be empty.")
            s.name = name.strip()[:100]
        if max_storage_mb is not None:
            if max_storage_mb <= 0: raise ValueError("Maximum storage must be greater than 0 MB.")
            s.max_storage_mb = float(max_storage_mb)
        if threshold_percent is not None:
            if not 50 <= threshold_percent <= 95: raise ValueError("Threshold must be between 50% and 95%.")
            s.threshold_percent = float(threshold_percent)
        if priority is not None: s.priority = int(priority)
        if enabled is not None: s.enabled = bool(enabled)
        db.commit()
        return True
    finally:
        db.close()


def delete_shelf(shelf_id: int) -> bool:
    """Remove only VALE's saved connection configuration, never database contents."""
    _ensure_tables()
    db = Session()
    try:
        s = db.query(StorageShelf).filter(StorageShelf.id == shelf_id).first()
        if not s: return False
        db.delete(s)
        db.commit()
        return True
    finally:
        db.close()


def mark_test(shelf_id: int, status: str) -> None:
    _ensure_tables()
    db = Session()
    try:
        s = db.query(StorageShelf).filter(StorageShelf.id == shelf_id).first()
        if s:
            s.last_test_status = status[:30]
            s.last_tested_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
