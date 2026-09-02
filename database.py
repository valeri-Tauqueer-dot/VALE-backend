import os

from dotenv import load_dotenv

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String
)

from sqlalchemy.orm import (
    declarative_base,
    sessionmaker
)

import bcrypt


# ==========================
# LOAD ENVIRONMENT
# ==========================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Do NOT crash the whole app at import time. If this raises here,
    # main.py's `from database import ...` fails, FastAPI never starts,
    # and EVERY route (including /health) goes down — which looks like
    # "the network isn't connecting" even though the real cause is one
    # missing environment variable on Render.
    #
    # Instead we log loudly and let create_engine fail later, with a
    # clear error, only when a DB call actually happens.
    print(
        "VALE DATABASE WARNING: DATABASE_URL is not set. "
        "Set it in Render → Environment. Login/signup will fail until you do."
    )
    DATABASE_URL = "sqlite:///./vale_fallback.db"


# ==========================
# DATABASE ENGINE
# ==========================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


# ==========================
# USER TABLE
# ==========================

class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = Column(
        String,
        nullable=False
    )


# ==========================
# CREATE TABLE IF NEEDED
# ==========================

# This was commented out before, which meant the "users" table never
# got created on a fresh Postgres/Supabase database — signup and login
# would fail with a "relation users does not exist" error. This creates
# the table only if it doesn't already exist, so it's safe to leave on.
try:
    Base.metadata.create_all(bind=engine)
except Exception as error:
    print("VALE DATABASE WARNING: could not create tables:", str(error))


# ==========================
# DATABASE SESSION
# ==========================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ==========================
# PASSWORD HASHING
# ==========================

def hash_password(password):

    password_bytes = password.encode("utf-8")

    # bcrypt supports a maximum of 72 bytes
    if len(password_bytes) > 72:
        raise ValueError(
            "Password cannot be longer than 72 bytes."
        )

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed.decode("utf-8")


def verify_password(password, password_hash):

    password_bytes = password.encode("utf-8")
    hash_bytes = password_hash.encode("utf-8")

    if len(password_bytes) > 72:
        return False

    return bcrypt.checkpw(
        password_bytes,
        hash_bytes
    )


# ==========================
# CREATE USER
# ==========================

def create_user(username, email, password):

    db = SessionLocal()

    try:

        # Check username
        existing_username = db.query(User).filter(
            User.username == username
        ).first()

        if existing_username:
            return False

        # Check email
        existing_email = db.query(User).filter(
            User.email == email
        ).first()

        if existing_email:
            return False

        # Hash password
        hashed_password = hash_password(password)

        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password
        )

        db.add(user)

        db.commit()

        db.refresh(user)

        return True

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


# ==========================
# LOGIN USER
# ==========================

def login_user(username, password):

    db = SessionLocal()

    try:

        user = db.query(User).filter(
            User.username == username
        ).first()

        if not user:
            return False

        return verify_password(
            password,
            user.password_hash
        )

    finally:

        db.close()
