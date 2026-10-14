from __future__ import annotations

import threading
import time
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from ai_core import vale
from auth import create_access_token, verify_token
from database import check_database, create_user, login_user
from media import MediaError, MediaOrchestrator
from vale_connector import VALEConnector

try:
    from search_engine import storage as search_storage
except Exception as error:  # VALE must still start if the news search cannot load
    print("SEARCH ENGINE NOT LOADED:", type(error).__name__, error)
    search_storage = None

try:
    from search_engine import research_queue
except Exception as error:
    print("RESEARCH QUEUE NOT LOADED:", type(error).__name__, error, flush=True)
    research_queue = None

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


# Storage Command Center is a separate, authenticated router. Existing VALE routes remain unchanged.
try:
    from search_engine.storage_api import router as storage_router
    app.include_router(storage_router)
except Exception as error:
    print("STORAGE COMMAND CENTER NOT LOADED:", type(error).__name__, error, flush=True)


# One lightweight worker per app process. Jobs themselves live in the database,
# so queued work survives restarts when DATABASE_URL points to persistent Postgres.
_worker_stop = threading.Event()
_worker_thread: threading.Thread | None = None


def _result_list(raw):
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("results", "items", "data"):
            value = raw.get(key)
            if isinstance(value, list):
                return value
    return []


def _process_research_job(job: dict) -> dict:
    if job.get("job_type") != "web_search_save":
        raise ValueError(f"Unsupported research job type: {job.get('job_type')}")
    if search_storage is None:
        raise RuntimeError("Research storage is not ready.")

    payload = job.get("payload") or {}
    query = str(payload.get("query") or "").strip()
    if not query:
        raise ValueError("Research job has no query.")
    requested = max(1, min(int(payload.get("num_results", 5)), 20))
    market = str(payload.get("market") or "general")[:100]
    raw_results = connector.search_web(query, requested)
    results = _result_list(raw_results)
    saved = duplicates = skipped = 0

    for index, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            skipped += 1
            research_queue.update_checkpoint(job["id"], {
                "stage": "saving_results", "processed": index,
                "total_results": len(results), "saved": saved,
                "duplicates": duplicates, "skipped": skipped,
            })
            continue
        url = str(item.get("url") or item.get("link") or item.get("href") or "").strip()
        if not url.startswith(("https://", "http://")):
            skipped += 1
            continue
        title = str(item.get("title") or item.get("name") or "")[:300]
        body = str(item.get("body") or item.get("text") or item.get("snippet") or item.get("summary") or item.get("description") or "")[:600]
        published_at = str(item.get("published_at") or item.get("published_date") or item.get("date") or "")
        parsed = urlparse(url)
        source = str(item.get("source") or item.get("source_name") or parsed.netloc)[:150]
        already = search_storage.exists(url)
        did_save = search_storage.save_document(
            url=url, title=title, body=body, source=source,
            market=market, published_at=published_at,
        )
        if did_save:
            saved += 1
        elif already or search_storage.exists(url):
            duplicates += 1
        else:
            raise RuntimeError("Research storage rejected a result; check storage shelf capacity and connectivity.")
        research_queue.update_checkpoint(job["id"], {
            "stage": "saving_results", "processed": index,
            "total_results": len(results), "saved": saved,
            "duplicates": duplicates, "skipped": skipped,
        })

    return {
        "query": query,
        "provider_result_count": len(results),
        "saved": saved,
        "duplicates": duplicates,
        "skipped": skipped,
        "record_count": search_storage.count(),
    }


def _research_worker_loop():
    initialized = False
    while not _worker_stop.is_set():
        if not initialized:
            try:
                research_queue.init_queue()
                recovered = research_queue.recover_stale_jobs()
                if recovered:
                    print(f"RESEARCH QUEUE: recovered {recovered} stale job(s)", flush=True)
                initialized = True
            except Exception as error:
                print("RESEARCH QUEUE INIT ERROR:", type(error).__name__, str(error), flush=True)
                _worker_stop.wait(10)
                continue
        try:
            job = research_queue.claim_next_job()
            if job is None:
                _worker_stop.wait(5)
                continue
            try:
                result = _process_research_job(job)
                research_queue.complete_job(job["id"], result)
                print(f"RESEARCH QUEUE: job {job['id']} completed", flush=True)
            except Exception as error:
                updated = research_queue.fail_job(job["id"], f"{type(error).__name__}: {error}")
                status = updated.get("status") if updated else "unknown"
                print(f"RESEARCH QUEUE: job {job['id']} {status} ({type(error).__name__})", flush=True)
        except Exception as error:
            print("RESEARCH QUEUE WORKER ERROR:", type(error).__name__, str(error), flush=True)
            _worker_stop.wait(5)


@app.on_event("startup")
def start_research_worker():
    global _worker_thread
    _worker_stop.clear()
    if research_queue is None:
        print("RESEARCH QUEUE: worker disabled because module did not load", flush=True)
        return
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(target=_research_worker_loop, name="vale-research-worker", daemon=True)
        _worker_thread.start()


@app.on_event("shutdown")
def stop_research_worker():
    _worker_stop.set()


class ResearchDocument(BaseModel):
    url: str
    title: str = ""
    body: str = ""
    source: str = ""
    market: str = ""
    published_at: str = ""


class ResearchJobRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    num_results: int = Field(default=5, ge=1, le=20)
    market: str = Field(default="general", max_length=100)
    max_attempts: int = Field(default=3, ge=1, le=10)
    # Optional ISO-8601 schedule time, e.g. 2026-10-20T10:00:00Z.
    run_at: str | None = None


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


@app.post("/research/save")
def research_save(
    data: ResearchDocument,
    username: str = Depends(get_current_user),
):
    """Save a short research record to VALE's configured storage shelves."""
    if search_storage is None:
        raise HTTPException(
            status_code=503,
            detail="Research storage is not ready.",
        )

    url = (data.url or "").strip()
    if not url.startswith(("https://", "http://")):
        raise HTTPException(
            status_code=400,
            detail="URL must start with http:// or https://.",
        )

    try:
        already_exists = search_storage.exists(url)
        saved = search_storage.save_document(
            url=url,
            title=data.title,
            body=data.body,
            source=data.source,
            market=data.market,
            published_at=data.published_at,
        )

        if not saved and not already_exists:
            raise HTTPException(
                status_code=503,
                detail="No configured storage shelf accepted the research record.",
            )

        return {
            "success": True,
            "status": "saved" if saved else "already_exists",
            "url": url,
            "record_count": search_storage.count(),
        }
    except Exception as error:
        print(
            "RESEARCH SAVE ERROR:",
            type(error).__name__,
            flush=True,
        )
        raise HTTPException(
            status_code=503,
            detail="Research record could not be saved.",
        ) from error


@app.get("/research/search")
def research_search(
    q: str,
    limit: int = 10,
    username: str = Depends(get_current_user),
):
    """Search saved research records."""
    if search_storage is None:
        raise HTTPException(
            status_code=503,
            detail="Research storage is not ready.",
        )

    query = (q or "").strip()
    if not query:
        raise HTTPException(
            status_code=400,
            detail="Write something to search.",
        )

    limit = max(1, min(int(limit), 30))
    try:
        found = search_storage.search(query, limit)
    except Exception as error:
        print(
            "RESEARCH SEARCH ERROR:",
            type(error).__name__,
            flush=True,
        )
        raise HTTPException(
            status_code=503,
            detail="Research search is not available right now.",
        ) from error

    results = [
        {
            "title": item.get("title") or "",
            "summary": item.get("body") or "",
            "url": item.get("url") or "",
            "source": item.get("source") or "",
            "market": item.get("market") or "",
            "published_at": item.get("published_at") or "",
        }
        for item in found
    ]
    return {
        "query": query,
        "result_count": len(results),
        "results": results,
    }


@app.post("/research/jobs")
def research_create_job(
    data: ResearchJobRequest,
    username: str = Depends(get_current_user),
):
    """Queue a web search and save its short metadata into VALE Research storage."""
    if research_queue is None:
        raise HTTPException(status_code=503, detail="Research queue is not available.")
    try:
        job = research_queue.enqueue_job(
            job_type="web_search_save",
            payload={"query": data.query.strip(), "num_results": data.num_results, "market": data.market.strip() or "general"},
            max_attempts=data.max_attempts,
            run_at=data.run_at,
        )
        return {"success": True, "message": "Research job queued.", "job": job}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        print("RESEARCH JOB CREATE ERROR:", type(error).__name__, flush=True)
        raise HTTPException(status_code=503, detail="Could not queue the research job. Check queue database connectivity.") from error


@app.get("/research/jobs")
def research_list_jobs(
    status: str | None = None,
    limit: int = 20,
    username: str = Depends(get_current_user),
):
    """List recent research jobs; optionally filter by status."""
    if research_queue is None:
        raise HTTPException(status_code=503, detail="Research queue is not available.")
    allowed = {"queued", "running", "retry_wait", "completed", "failed"}
    if status and status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(sorted(allowed))}")
    try:
        jobs = research_queue.list_jobs(status=status, limit=limit)
        return {"count": len(jobs), "jobs": jobs}
    except Exception as error:
        print("RESEARCH JOB LIST ERROR:", type(error).__name__, flush=True)
        raise HTTPException(status_code=503, detail="Could not read research jobs.") from error


@app.get("/research/jobs/{job_id}")
def research_get_job(
    job_id: int,
    username: str = Depends(get_current_user),
):
    if research_queue is None:
        raise HTTPException(status_code=503, detail="Research queue is not available.")
    try:
        job = research_queue.get_job(job_id)
    except Exception as error:
        print("RESEARCH JOB GET ERROR:", type(error).__name__, flush=True)
        raise HTTPException(status_code=503, detail="Could not read research job.") from error
    if job is None:
        raise HTTPException(status_code=404, detail="Research job not found.")
    return {"job": job}


@app.post("/research/jobs/{job_id}/retry")
def research_retry_job(
    job_id: int,
    username: str = Depends(get_current_user),
):
    if research_queue is None:
        raise HTTPException(status_code=503, detail="Research queue is not available.")
    try:
        job = research_queue.retry_job(job_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except Exception as error:
        print("RESEARCH JOB RETRY ERROR:", type(error).__name__, flush=True)
        raise HTTPException(status_code=503, detail="Could not retry research job.") from error
    if job is None:
        raise HTTPException(status_code=404, detail="Research job not found.")
    return {"success": True, "message": "Research job queued again.", "job": job}


@app.get("/research/status")
def research_status(
    username: str = Depends(get_current_user),
):
    """Report whether the research storage module is loaded and its record count."""
    if search_storage is None:
        return {
            "available": False,
            "record_count": 0,
        }

    try:
        return {
            "available": True,
            "record_count": search_storage.count(),
        }
    except Exception as error:
        print(
            "RESEARCH STATUS ERROR:",
            type(error).__name__,
            flush=True,
        )
        raise HTTPException(
            status_code=503,
            detail="Research storage status is unavailable.",
        ) from error


@app.get("/news/search")
def news_search(
    q: str,
    limit: int = 10,
    username: str = Depends(get_current_user),
):
    if search_storage is None:
        raise HTTPException(status_code=503, detail="News search is not ready.")

    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Write something to search.")

    limit = max(1, min(int(limit), 30))

    try:
        found = search_storage.search(query, limit)
    except Exception as error:
        print("NEWS SEARCH ERROR:", type(error).__name__)
        raise HTTPException(status_code=503, detail="News search is not available right now.")

    results = [
        {
            "title": item.get("title") or "",
            "summary": item.get("body") or "",
            "url": item.get("url") or "",
            "source": item.get("source") or "",
            "markets": [x for x in (item.get("market") or "").split(",") if x],
            "published_at": item.get("published_at") or "",
        }
        for item in found
    ]

    return {"query": query, "result_count": len(results), "results": results}
