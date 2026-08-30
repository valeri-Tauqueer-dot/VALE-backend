import os
import requests
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from vale_brain import VALEBrain
from vale_connector import VALEConnector

from unity_brain import UnityBrain
from heroic_brain import HeroicBrain
from supervisor_brain import SupervisorBrain
from alpha_brain import AlphaBrain
from legend_brain import LegendBrain
from marco_brain import MarcoBrain
from feelings_brain import FeelingsBrain
from cognitive_brain import CognitiveBrain

from database import create_user, login_user, Base, engine
from auth import create_access_token, verify_token


# ============================================================
# APP SETUP
# ============================================================

APP_DIR = Path(__file__).resolve().parent
FRONTEND_FILE = APP_DIR / "index.html"

app = FastAPI(
    title="VALE AI Core",
    version="1.0"
)


# ============================================================
# SHARED VALE INFRASTRUCTURE
# ============================================================

connector = VALEConnector()


# ============================================================
# VALE CENTRAL BRAIN
# ============================================================

brain = VALEBrain()


# ============================================================
# VALE BRAIN SYSTEM
#
# Every brain receives the SAME connector.
# We are only connecting them right now.
# Actual intelligence will be added later.
# ============================================================

unity = UnityBrain(connector)

heroic = HeroicBrain(connector)

supervisor = SupervisorBrain(connector)

alpha = AlphaBrain(connector)

legend = LegendBrain(connector)

marco = MarcoBrain(connector)

feelings = FeelingsBrain(connector)

cognitive = CognitiveBrain(connector)


# ============================================================
# BRAIN REGISTRY
#
# Central list of all VALE brains.
# ============================================================

brains = {
    "UNITY": unity,
    "HEROIC": heroic,
    "SUPERVISOR": supervisor,
    "ALPHA": alpha,
    "LEGEND": legend,
    "MARCO": marco,
    "FEELINGS": feelings,
    "COGNITIVE": cognitive,
}


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# SECURITY
# ============================================================

security = HTTPBearer()


# ============================================================
# DATA MODELS
# ============================================================

class UserMessage(BaseModel):
    message: str


class SignupData(BaseModel):
    username: str
    email: str
    password: str


class LoginData(BaseModel):
    username: str
    password: str


# ============================================================
# DATABASE STARTUP
# ============================================================

@app.on_event("startup")
def startup():

    Base.metadata.create_all(
        bind=engine
    )


# ============================================================
# AUTHENTICATION
# ============================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    username = verify_token(
        credentials.credentials
    )

    if username is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    return username


# ============================================================
# FRONTEND
# ============================================================

@app.get(
    "/",
    include_in_schema=False
)
def frontend():

    if not FRONTEND_FILE.exists():

        raise HTTPException(
            status_code=500,
            detail="Frontend file not found."
        )

    return FileResponse(
        FRONTEND_FILE,
        media_type="text/html"
    )


# ============================================================
# SYSTEM API
# ============================================================

@app.get("/api")
def api_home():

    return {
        "system": "VALE AI",
        "status": "Online",
        "version": "1.0",
        "brains": len(brains)
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "system": "VALE AI",
        "brain": "connected",
        "brains_connected": len(brains)
    }


# ============================================================
# CONNECTOR TEST
# ============================================================

@app.get("/connector-test")
def connector_test():

    return {
        "connector": connector.status(),
        "capabilities": connector.capabilities()
    }


# ============================================================
# BRAIN SYSTEM TEST
# ============================================================

@app.get("/brains-test")
def brains_test():

    results = {}

    for name, brain_instance in brains.items():

        results[name] = {
            "identity": brain_instance.identity(),
            "connector": brain_instance.connector_status(),
            "capabilities": brain_instance.capabilities()
        }

    return {
        "total_brains": len(brains),
        "brains": results
    }


# ============================================================
# SINGLE BRAIN TEST
# ============================================================

@app.get("/brain-test/{brain_name}")
def single_brain_test(brain_name: str):

    name = brain_name.upper()

    if name not in brains:

        raise HTTPException(
            status_code=404,
            detail=f"Brain '{brain_name}' not found."
        )

    brain_instance = brains[name]

    return {
        "identity": brain_instance.identity(),
        "connector": brain_instance.connector_status(),
        "capabilities": brain_instance.capabilities()
    }


# ============================================================
# INTERNET TEST
# ============================================================

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
            "message": "VALE INTERNET TEST PASSED"
        }

    except Exception as error:

        return {
            "internet": False,
            "message": "VALE INTERNET TEST FAILED",
            "error": str(error)
        }


# ============================================================
# EXA WEB SEARCH
# ============================================================

def search_exa(
    query: str,
    num_results: int = 5
):

    api_key = os.environ.get(
        "EXA_API_KEY"
    )

    if not api_key:

        print(
            "EXA_API_KEY is not configured."
        )

        return []

    try:

        response = requests.post(

            "https://api.exa.ai/search",

            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key
            },

            json={
                "query": query,
                "type": "auto",
                "numResults": num_results,
                "contents": {
                    "highlights": True
                }
            },

            timeout=20
        )

        response.raise_for_status()

        results = []

        for item in response.json().get(
            "results",
            []
        ):

            results.append({

                "title": item.get(
                    "title",
                    ""
                ),

                "url": item.get(
                    "url",
                    ""
                ),

                "highlights": item.get(
                    "highlights",
                    []
                )
            })

        return results

    except Exception as error:

        print(
            "EXA SEARCH ERROR:",
            str(error)
        )

        return []


# ============================================================
# WEB SEARCH API
# ============================================================

@app.get("/web-search")
def web_search(q: str):

    results = search_exa(q)

    return {

        "success": len(results) > 0,

        "query": q,

        "results": results,

        "count": len(results)
    }


# ============================================================
# VALE CHAT
# ============================================================

@app.post("/chat")
def chat(
    data: UserMessage,
    username: str = Depends(
        get_current_user
    )
):

    message = data.message.strip()

    if not message:

        return {

            "user": "",

            "vale": "Please ask me something.",

            "username": username,

            "internet_used": False
        }


    thinking = brain.think(
        message
    )


    if thinking.get(
        "needs_internet",
        False
    ):

        web_results = search_exa(
            message
        )

        return {

            "user": message,

            "vale": thinking.get(
                "response",
                "I could not generate a response."
            ),

            "username": username,

            "internet_used": True,

            "intent": thinking.get(
                "intent",
                "general"
            ),

            "brain_system": "connected"
        }


    return {

        "user": message,

        "vale": thinking.get(
            "response",
            "I am analyzing your question."
        ),

        "username": username,

        "internet_used": thinking.get(
            "internet_used",
            False
        ),

        "intent": thinking.get(
            "intent",
            "general"
        ),

        "brain_system": "connected"
    }


# ============================================================
# VALE CHAT — MEDIA (camera / photo / file / voice)
# ============================================================

MAX_MEDIA_BYTES = 8 * 1024 * 1024  # 8MB cap

ALLOWED_MEDIA_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "audio/webm",
    "audio/mpeg",
    "audio/wav",
    "application/pdf",
}


@app.post("/chat-media")
async def chat_media(
    file: UploadFile = File(...),
    username: str = Depends(
        get_current_user
    )
):

    if file.content_type not in ALLOWED_MEDIA_TYPES:

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}"
        )

    raw = await file.read()

    if len(raw) > MAX_MEDIA_BYTES:

        raise HTTPException(
            status_code=400,
            detail="File too large. Max size is 8MB."
        )

    media_kind = "image"

    if file.content_type.startswith("audio/"):
        media_kind = "voice"
    elif file.content_type == "application/pdf":
        media_kind = "document"

    prompt = f"[User sent a {media_kind} attachment: {file.filename}]"

    thinking = brain.think(
        prompt
    )

    return {

        "user": prompt,

        "vale": thinking.get(
            "response",
            "I received your file and I am reviewing it."
        ),

        "username": username,

        "internet_used": False,

        "intent": thinking.get(
            "intent",
            "general"
        ),

        "brain_system": "connected",

        "media": {
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(raw),
            "kind": media_kind
        }
    }


# ============================================================
# SIGNUP
# ============================================================

@app.post("/signup")
def signup(
    data: SignupData
):

    try:

        success = create_user(
            data.username,
            data.email,
            data.password
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


    if not success:

        return {

            "success": False,

            "message":
            "Username or email already exists."
        }


    return {

        "success": True,

        "message":
        "Account created successfully."
    }


# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
def login(
    data: LoginData
):

    if not login_user(
        data.username,
        data.password
    ):

        return {

            "success": False,

            "message":
            "Invalid username or password."
        }


    token = create_access_token({

        "sub": data.username
    })


    return {

        "success": True,

        "access_token": token,

        "token_type": "bearer"
    }


# ============================================================
# USER PROFILE
# ============================================================

@app.get("/profile")
def profile(
    username: str = Depends(
        get_current_user
    )
):

    return {

        "username": username,

        "status": "Authenticated",

        "system": "VALE AI"
}
