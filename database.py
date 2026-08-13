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

from passlib.context import CryptContext


# ==========================
# LOAD ENVIRONMENT
# ==========================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL not found in .env")


# ==========================
# DATABASE ENGINE
# ==========================

engine = create_engine(

    DATABASE_URL,

    pool_pre_ping=True,

    pool_recycle=300

)


SessionLocal = sessionmaker(

    autocommit=False,

    autoflush=False,

    bind=engine

)


Base = declarative_base()


# ==========================
# PASSWORD HASHING
# ==========================

pwd_context = CryptContext(

    schemes=["bcrypt"],

    deprecated="auto"

)


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

    password = Column(
        String,
        nullable=False
    )


Base.metadata.create_all(bind=engine)


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
# CREATE USER
# ==========================

def create_user(username, email, password):

    db = SessionLocal()

    try:

        existing = db.query(User).filter(

            User.username == username

        ).first()

        if existing:

            return False

        hashed_password = pwd_context.hash(password)

        user = User(

            username=username,

            email=email,

            password=hashed_password

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

        return pwd_context.verify(

            password,

            user.password

        )

    finally:

        db.close()