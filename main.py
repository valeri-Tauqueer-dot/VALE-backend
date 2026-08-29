import os
import requests
from pathlib import Path

from vale_brain import VALEBrain

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

brain = VALEBrain()

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

@app.get("/web-search")
def web_search(q: str):
    api_key = os.environ.get("EXA_API_KEY")

    if not api_key:
        return {
            "success": False,
            "query": q,
            "results": [],
            "count": 0,
            "message": "EXA_API_KEY is not configured."
        }

    try:
        response = requests.post(
            "https://api.exa.ai/search",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key
            },
            json={
                "query": q,
                "type": "auto",
                "numResults": 5,
                "contents": {
                    "highlights": True
                }
            },
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        results = []

        for item in data.get("results", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "highlights": item.get("highlights", [])
            })

        return {
            "success": True,
            "query": q,
            "results": results,
            "count": len(results),
            "message": "VALE EXA WEB SEARCH PASSED"
        }

    except Exception as e:
        return {
            "success": False,
            "query": q,
            "results": [],
            "count": 0,
            "message": "VALE EXA WEB SEARCH FAILED",
            "error": str(e)
                }

def search_exa(query: str, num_results: int = 5):
    api_key = os.environ.get("EXA_API_KEY")

    if not api_key:
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

        for item in response.json().get("results", []):
            highlights = item.get("highlights", [])

            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "highlights": highlights
            })

        return results

    except Exception as e:
        print("EXA SEARCH ERROR:", str(e))
        return []

@app.post("/chat")
def chat(data: UserMessage, username: str = Depends(get_current_user)):

    message = data.message.strip()

    if not message:
        return {
            "user": "",
            "vale": "Please ask me something.",
            "username": username
        }

    # VALE Brain analyzes the user's message first
    thinking = brain.think(message)

    # If VALE decides internet research is needed,
    # search Exa.
    if thinking["needs_internet"]:

        web_results = search_exa(message)

        if web_results:

            answer = "I researched this using available web information.\n\n"

            for index, result in enumerate(web_results[:3], start=1):

                answer += f"{index}. {result['title']}\n"

                if result["highlights"]:
                    answer += (
                        result["highlights"][0]
                        .replace("\n", " ")[:700]
                    )

                answer += "\n\n"

            answer += (
                "This information was retrieved through "
                "VALE's web intelligence system."
            )

            return {
                "user": message,
                "vale": answer,
                "username": username,
                "internet_used": True,
                "intent": thinking["intent"],
                "web_results": web_results
            }

        # Internet was requested but Exa returned nothing
        return {
            "user": message,
            "vale": (
                "I determined that this question needs current "
                "or external information, but I could not retrieve "
                "reliable results right now."
            ),
            "username": username,
            "internet_used": True,
            "intent": thinking["intent"]
        }

    # VALE handles greetings and local conversation itself
    return {
        "user": message,
        "vale": thinking["response"],
        "username": username,
        "internet_used": False,
        "intent": thinking["intent"]
            }
            
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
