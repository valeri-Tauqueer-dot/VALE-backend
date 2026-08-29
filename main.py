import os
import requests
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from ai_core import vale
from database import create_user, login_user, Base, engine
from auth import create_access_token, verify_token

APP_DIR = Path(__file__).resolve().parent
FRONTEND_FILE = APP_DIR / "index.html"

app = FastAPI(title="VALE AI Core", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

class UserMessage(BaseModel):
    message: str

class SignupData(BaseModel):
    username: str
    email: str
    password: str

class LoginData(BaseModel):
    username: str
    password: str

@app.on_event("startup")
def startup():
    # Creates the users table automatically on Render/Supabase.
    Base.metadata.create_all(bind=engine)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    username = verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return username

@app.get("/", include_in_schema=False)
def frontend():
    if not FRONTEND_FILE.exists():
        raise HTTPException(status_code=500, detail="Frontend file not found.")
    return FileResponse(FRONTEND_FILE, media_type="text/html")

@app.get("/api")
def api_home():
    return {"system": "VALE AI", "status": "Online", "version": "1.0"}

@app.get("/health")
def health():
    return {"status": "healthy", "system": "VALE AI", "database": "connected"}

@app.get("/internet-test")
def internet_test():
    try:
        response = requests.get(
            "https://httpbin.org/get",
            timeout=10
        )

        return {
            "internet": True,
            "status": response.status_code,
            "message": "VALE BACKEND INTERNET TEST PASSED"
        }

    except Exception as e:
        return {
            "internet": False,
            "message": "VALE BACKEND INTERNET TEST FAILED",
            "error": str(e)
        }

@app.get("/web-test")
def web_test():
    try:
        response = requests.get(
            "https://www.google.com/search?q=latest+bitcoin+price",
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=10
        )

        return {
            "web_access": True,
            "status": response.status_code,
            "bytes_received": len(response.content),
            "message": "VALE WEB ACCESS TEST PASSED"
        }

    except Exception as e:
        return {
            "web_access": False,
            "message": "VALE WEB ACCESS TEST FAILED",
            "error": str(e)
        }

@app.post("/chat")
def chat(data: UserMessage, username: str = Depends(get_current_user)):
    return {"user": data.message, "vale": vale.process(data.message), "username": username}

@app.post("/signup")
def signup(data: SignupData):
    try:
        success = create_user(data.username, data.email, data.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not success:
        return {"success": False, "message": "Username or email already exists."}

    return {"success": True, "message": "Account created successfully."}

@app.post("/login")
def login(data: LoginData):
    if not login_user(data.username, data.password):
        return {"success": False, "message": "Invalid username or password."}

    token = create_access_token({"sub": data.username})
    return {"success": True, "access_token": token, "token_type": "bearer"}

@app.get("/profile")
def profile(username: str = Depends(get_current_user)):
    return {"username": username, "status": "Authenticated", "system": "VALE AI"}
