from __future__ import annotations

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from ai_core import vale
from auth import create_access_token, verify_token
from database import check_database, create_user, login_user
from media import MediaError, MediaOrchestrator
from vale_connector import VALEConnector

app = FastAPI(title="VALE AI Core", version="1.2")
media_orchestrator = MediaOrchestrator()
connector = VALEConnector()
security = HTTPBearer(auto_error=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserMessage(BaseModel):
    message: str


class SignupData(BaseModel):
    username: str
    email: str
    password: str


class LoginData(BaseModel):
    username: str
    password: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    username = verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return username


@app.get("/")
def home():
    return {
        "system": "VALE AI",
        "status": "Online",
        "version": "1.2",
        "talking_brain": vale.talking_brain.status(),
        "media_system": "available",
    }


@app.get("/health")
def health():
    db = check_database()
    talking = vale.talking_brain.status()
    overall = "healthy" if db["status"] == "connected" and talking["available"] else "degraded"
    return {
        "status": overall,
        "system": "VALE AI",
        "database": db,
        "talking_brain": talking,
        "media_system": "available",
    }


@app.options("/chat")
def chat_options():
    return {"status": "ok", "route": "/chat", "method": "OPTIONS"}


@app.post("/chat")
def chat(
    data: UserMessage,
    request: Request,
    username: str = Depends(get_current_user),
):
    message = (data.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    print("============================================================", flush=True)
    print(
        f"📨 POST /chat RECEIVED | user={username!r} | "
        f"message={message[:200]!r} | origin={request.headers.get('origin')!r}",
        flush=True,
    )

    try:
        response = vale.process(message)
        print(
            f"✅ POST /chat COMPLETE | response_type={type(response).__name__}",
            flush=True,
        )
        return {"user": message, "vale": response}
    except Exception as exc:
        print(f"❌ POST /chat ERROR | {type(exc).__name__}: {exc}", flush=True)
        raise HTTPException(
            status_code=500,
            detail=f"VALE chat processing failed: {type(exc).__name__}: {exc}",
        ) from exc


@app.post("/chat-media")
async def chat_media(
    file: UploadFile = File(...),
    message: str = Form(""),
    username: str = Depends(get_current_user),
):
    try:
        raw_data = await file.read()
        media_result = await media_orchestrator.process(
            data=raw_data,
            filename=file.filename,
            content_type=file.content_type,
            user_message=message,
        )
        media_context = media_result.build_brain_context()
        vale_message = (
            f"USER QUESTION:\n{message.strip()}\n\n{media_context}"
            if message.strip()
            else media_context
        )
        response = vale.process(vale_message)
        return {
            "success": True,
            "user": message,
            "filename": media_result.filename,
            "media_type": media_result.media_type.value,
            "processing_status": media_result.status.value,
            "vale": response,
            "media": media_result.to_dict(include_full_text=False),
        }
    except MediaError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"VALE media processing failed: {type(exc).__name__}: {exc}",
        ) from exc


@app.get("/media/supported")
def supported_media():
    return media_orchestrator.supported_media()


@app.post("/signup")
def signup(data: SignupData):
    try:
        success = create_user(data.username.strip(), data.email.strip(), data.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"❌ SIGNUP ERROR | {type(exc).__name__}: {exc}", flush=True)
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable. Check DATABASE_URL and database connectivity.",
        ) from exc

    if not success:
        return {"success": False, "message": "Username or email already exists."}
    return {"success": True, "message": "Account created successfully."}


@app.post("/login")
def login(data: LoginData):
    try:
        success = login_user(data.username.strip(), data.password)
    except Exception as exc:
        print(f"❌ LOGIN ERROR | {type(exc).__name__}: {exc}", flush=True)
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable. Check DATABASE_URL and database connectivity.",
        ) from exc

    if not success:
        return {"success": False, "message": "Invalid username or password."}

    token = create_access_token({"sub": data.username.strip()})
    return {"success": True, "access_token": token, "token_type": "bearer"}


@app.get("/profile")
def profile(username: str = Depends(get_current_user)):
    return {"username": username, "status": "Authenticated", "system": "VALE AI"}


@app.get("/connector/status")
def connector_status(username: str = Depends(get_current_user)):
    return connector.status()


@app.get("/connector/search")
def connector_search(
    q: str,
    num_results: int = 5,
    username: str = Depends(get_current_user),
):
    num_results = max(1, min(int(num_results), 20))
    results = connector.search_web(q, num_results)
    return {
        "query": q,
        "internet_available": connector.internet_available(),
        "result_count": len(results),
        "results": results,
    }
