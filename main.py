import os
import requests
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from vale_brain import VALEBrain
from vale_connector import VALEConnector
from database import create_user, login_user, Base, engine
from auth import create_access_token, verify_token


# --------------------------------------------------
# APP SETUP
# --------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
FRONTEND_FILE = APP_DIR / "index.html"

app = FastAPI(
    title="VALE AI Core",
    version="1.0"
)


# --------------------------------------------------
# VALE BRAIN CONNECTION
# --------------------------------------------------

brain = VALEBrain()

# Shared VALE Connector
connector = VALEConnector()


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# SECURITY
# --------------------------------------------------

security = HTTPBearer()


# --------------------------------------------------
# DATA MODELS
# --------------------------------------------------

class UserMessage(BaseModel):
    message: str


class SignupData(BaseModel):
    username: str
    email: str
    password: str


class LoginData(BaseModel):
    username: str
    password: str


# --------------------------------------------------
# DATABASE STARTUP
# --------------------------------------------------

@app.on_event("startup")
def startup():

    Base.metadata.create_all(
        bind=engine
    )


# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------

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


# --------------------------------------------------
# FRONTEND
# --------------------------------------------------

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


# --------------------------------------------------
# SYSTEM API
# --------------------------------------------------

@app.get("/api")
def api_home():

    return {
        "system": "VALE AI",
        "status": "Online",
        "version": "1.0"
    }


# --------------------------------------------------
# HEALTH
# --------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "system": "VALE AI",
        "brain": "connected"
    }


# --------------------------------------------------
# CONNECTOR TEST
# --------------------------------------------------

@app.get("/connector-test")
def connector_test():

    return {
        "connector": connector.status(),
        "capabilities": connector.capabilities()
    }


# --------------------------------------------------
# INTERNET TEST
# --------------------------------------------------

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


# --------------------------------------------------
# EXA WEB SEARCH
# --------------------------------------------------

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


# --------------------------------------------------
# WEB SEARCH API
# --------------------------------------------------

@app.get("/web-search")
def web_search(q: str):

    results = search_exa(q)

    return {

        "success": len(results) > 0,

        "query": q,

        "results": results,

        "count": len(results)
    }


# --------------------------------------------------
# VALE CHAT
# --------------------------------------------------

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


    # ----------------------------------------------
    # STEP 1
    # SEND USER MESSAGE TO VALE BRAIN
    # ----------------------------------------------

    thinking = brain.think(
        message
    )


    # ----------------------------------------------
    # STEP 2
    # BRAIN DECIDES IF WEB INFORMATION IS NEEDED
    # ----------------------------------------------

    if thinking.get(
        "needs_internet",
        False
    ):

        web_results = search_exa(
            message
        )


        # ------------------------------------------
        # STEP 3
        # SEND WEB DATA BACK TO VALE BRAIN
        # ------------------------------------------

        final_thinking = brain.think(
            message,
            web_results=web_results
        )

        return {

            "user": message,

            "vale": final_thinking.get(
                "response",
                "I could not generate a response."
            ),

            "username": username,

            "internet_used": True,

            "intent": final_thinking.get(
                "intent",
                "general"
            )
        }


    # ----------------------------------------------
    # STEP 4
    # LOCAL BRAIN RESPONSE
    # ----------------------------------------------

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
        )
    }


# --------------------------------------------------
# SIGNUP
# --------------------------------------------------

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


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

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


# --------------------------------------------------
# USER PROFILE
# --------------------------------------------------

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
