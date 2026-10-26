from __future__ import annotations

import os
import re
import time
from typing import Generator

import bcrypt
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()

# People often paste:  psql 'postgresql://...'   or a URL wrapped in quotes.
DATABASE_URL = re.sub(r"^\s*psql\s+", "", DATABASE_URL, flags=re.IGNORECASE).strip().strip("\"'`").strip()

if not DATABASE_URL:
    print(
        "VALE DATABASE WARNING: DATABASE_URL is not set. "
        "Using local SQLite fallback; set DATABASE_URL on Render for persistent accounts.",
        flush=True,
    )
    DATABASE_URL = "sqlite:///./vale_fallback.db"

connect_args: dict = {}

if DATABASE_URL.lower().startswith(("libsql://", "sqlite+libsql://")):
    # Turso / libSQL. Needs the auth token in TURSO_AUTH_TOKEN (or DATABASE_AUTH_TOKEN).
    if DATABASE_URL.lower().startswith("libsql://"):
        _host = DATABASE_URL[len("libsql://"):].split("?", 1)[0].strip("/")
        DATABASE_URL = f"sqlite+libsql://{_host}?secure=true"
    _token = (os.getenv("TURSO_AUTH_TOKEN") or os.getenv("DATABASE_AUTH_TOKEN") or "").strip()
    if _token:
        connect_args["auth_token"] = _token
    else:
        print("VALE DATABASE WARNING: Turso needs TURSO_AUTH_TOKEN to be set.", flush=True)
elif DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # Neon, Supabase, CockroachDB, Aiven and other PostgreSQL-compatible hosts.
    # SQLAlchemy 2.x may resolve postgresql:// to psycopg3; select psycopg2 explicitly.
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgresql://"):]
    elif DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgres://"):]
    elif DATABASE_URL.startswith("cockroachdb://"):
        DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("cockroachdb://"):]

    # Remote hosts need SSL; add it when the pasted URL forgot it.
    try:
        _parsed = make_url(DATABASE_URL)
        if (_parsed.host or "").lower() not in ("", "localhost", "127.0.0.1", "::1") and "sslmode" not in _parsed.query:
            DATABASE_URL = _parsed.update_query_dict({"sslmode": "require"}).render_as_string(hide_password=False)
    except Exception:
        pass

    # Free databases sleep and drop idle connections: wake-up time + keepalives.
    connect_args.update({
        "connect_timeout": 15,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    })

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)


_tables_ready = False


def ensure_tables() -> None:
    global _tables_ready
    if _tables_ready:
        return
    last_error = None
    for attempt in range(3):  # free databases may need a few seconds to wake up
        try:
            Base.metadata.create_all(bind=engine)
            _tables_ready = True
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise last_error


def check_database() -> dict:
    """Return a real database connectivity check without crashing startup."""
    try:
        for attempt in range(3):
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        return {
            "status": "connected",
            "configured": bool(os.getenv("DATABASE_URL")),
            "error": None,
        }
    except Exception as exc:
        return {
            "status": "error",
            "configured": bool(os.getenv("DATABASE_URL")),
            "error": f"{type(exc).__name__}: {exc}",
        }


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("Password cannot be longer than 72 bytes.")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        return False
    try:
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_user(username: str, email: str, password: str) -> bool:
    ensure_tables()
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            return False
        if db.query(User).filter(User.email == email).first():
            return False

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def login_user(username: str, password: str) -> bool:
    ensure_tables()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False
        return verify_password(password, user.password_hash)
    finally:
        db.close()
