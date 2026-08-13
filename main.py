from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_core import vale
from database import create_user, login_user
from auth import create_access_token, verify_token


app = FastAPI(
    title="VALE AI Core",
    version="1.0"
)


# ==========================
# CORS
# ==========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================
# DATA MODELS
# ==========================

class UserMessage(BaseModel):
    message: str


class SignupData(BaseModel):
    username: str
    email: str
    password: str


class LoginData(BaseModel):
    username: str
    password: str


# ==========================
# AUTHENTICATION
# ==========================

def get_current_user(
    authorization: str = Header(None)
):

    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing."
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid token format."
        )

    token = authorization.replace("Bearer ", "")

    username = verify_token(token)

    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    return username


# ==========================
# HOME
# ==========================

@app.get("/")
def home():

    return {
        "system": "VALE AI",
        "status": "Online",
        "version": "1.0"
    }


# ==========================
# HEALTH
# ==========================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "system": "VALE AI",
        "database": "connected"
    }


# ==========================
# CHAT
# ==========================

@app.post("/chat")
def chat(data: UserMessage):

    response = vale.process(data.message)

    return {
        "user": data.message,
        "vale": response
    }


# ==========================
# SIGNUP
# ==========================

@app.post("/signup")
def signup(data: SignupData):

    success = create_user(
        data.username,
        data.email,
        data.password
    )

    if not success:

        return {
            "success": False,
            "message": "Username already exists."
        }

    return {
        "success": True,
        "message": "Account created successfully."
    }


# ==========================
# LOGIN
# ==========================

@app.post("/login")
def login(data: LoginData):

    success = login_user(
        data.username,
        data.password
    )

    if not success:

        return {
            "success": False,
            "message": "Invalid username or password."
        }

    token = create_access_token(
        {
            "sub": data.username
        }
    )

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer"
    }


# ==========================
# PROFILE
# ==========================

@app.get("/profile")
def profile(
    username: str = Depends(get_current_user)
):

    return {
        "username": username,
        "status": "Authenticated",
        "system": "VALE AI"
    }