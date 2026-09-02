import os

from datetime import datetime, timedelta

from jose import jwt, JWTError

from dotenv import load_dotenv


load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:

    # Same problem as DATABASE_URL: raising here kills the entire app on
    # startup (main.py does `from auth import ...`), so every route
    # including /health goes down. We warn instead and use a temporary
    # key so the app still boots — but you MUST set a real SECRET_KEY on
    # Render, or tokens will stop working every time the server restarts.
    print(
        "VALE AUTH WARNING: SECRET_KEY is not set. "
        "Set it in Render → Environment (or let the Blueprint generate one). "
        "Using a temporary key for now — logins will not survive a restart."
    )
    import secrets
    SECRET_KEY = secrets.token_hex(32)


ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(

        minutes=ACCESS_TOKEN_EXPIRE_MINUTES

    )

    to_encode.update(

        {

            "exp": expire,

            "iat": datetime.utcnow()

        }

    )

    return jwt.encode(

        to_encode,

        SECRET_KEY,

        algorithm=ALGORITHM

    )


def verify_token(token: str):

    try:

        payload = jwt.decode(

            token,

            SECRET_KEY,

            algorithms=[ALGORITHM]

        )

        username = payload.get("sub")

        if username is None:

            return None

        return username

    except JWTError:

        return None