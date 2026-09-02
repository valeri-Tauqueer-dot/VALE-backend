from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from ai_core import vale
from database import create_user, login_user
from auth import create_access_token, verify_token
from media import MediaOrchestrator, MediaError
from vale_connector import VALEConnector

app = FastAPI(title="VALE AI Core", version="1.1")
media_orchestrator = MediaOrchestrator()
connector = VALEConnector()

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

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    username = verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return username

@app.get("/")
def home():
    return {
        "system": "VALE AI",
        "status": "Online",
        "version": "1.1",
        "media_system": "available",
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "system": "VALE AI",
        "database": "connected",
        "media_system": "available",
    }

@app.post("/chat")
def chat(data: UserMessage, username: str = Depends(get_current_user)):
    response = vale.process(data.message)
    return {"user": data.message, "vale": response}

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

        if message.strip():
            vale_message = (
                "USER QUESTION:\n"
                f"{message.strip()}\n\n"
                f"{media_context}"
            )
        else:
            vale_message = media_context

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
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"VALE media processing failed: {str(exc)}",
        )

@app.get("/media/supported")
def supported_media():
    return media_orchestrator.supported_media()

@app.post("/signup")
def signup(data: SignupData):
    success = create_user(data.username, data.email, data.password)

    if not success:
        return {
            "success": False,
            "message": "Username already exists.",
        }

    return {
        "success": True,
        "message": "Account created successfully.",
    }

@app.post("/login")
def login(data: LoginData):
    success = login_user(data.username, data.password)

    if not success:
        return {
            "success": False,
            "message": "Invalid username or password.",
        }

    token = create_access_token({"sub": data.username})

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
    }

@app.get("/profile")
def profile(username: str = Depends(get_current_user)):
    return {
        "username": username,
        "status": "Authenticated",
        "system": "VALE AI",
    }


# ======================================================================
# CONNECTOR TEST ROUTES
#
# These do NOT contain any "brain" / thinking logic — they only prove
# that VALEConnector can reach the real internet (i.e. that EXA_API_KEY
# is set correctly on Render). Once you build your own brain logic in
# alpha_brain.py / legend_brain.py, that code will call
# self.search_web(...) itself and won't need these routes at all.
# Safe to delete later.
# ======================================================================

@app.get("/connector/status")
def connector_status(username: str = Depends(get_current_user)):
    return connector.status()

@app.get("/connector/search")
def connector_search(
    q: str,
    num_results: int = 5,
    username: str = Depends(get_current_user),
):
    results = connector.search_web(q, num_results)
    return {
        "query": q,
        "internet_available": connector.internet_available(),
        "result_count": len(results),
        "results": results,
    }
