from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from auth import verify_token
from search_engine import storage_registry as registry

router = APIRouter(prefix="/storage", tags=["Storage Command Center"])
security = HTTPBearer(auto_error=True)


def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    username = verify_token(credentials.credentials)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return username


class TestRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2000)

class ShelfCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider: str = Field(default="PostgreSQL", max_length=40)
    url: str = Field(min_length=8, max_length=2000)
    max_storage_mb: float = Field(gt=0, le=10_000_000)
    threshold_percent: float = Field(default=80, ge=50, le=95)
    priority: int = Field(default=100, ge=1, le=10000)

class ShelfUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    max_storage_mb: Optional[float] = Field(default=None, gt=0, le=10_000_000)
    threshold_percent: Optional[float] = Field(default=None, ge=50, le=95)
    priority: Optional[int] = Field(default=None, ge=1, le=10000)
    enabled: Optional[bool] = None


def _size_for_url(url: str) -> float:
    eng = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 8})
    try:
        with eng.connect() as conn:
            value = conn.execute(text("SELECT pg_database_size(current_database())")).scalar() or 0
        return round(float(value) / (1024 * 1024), 2)
    finally:
        eng.dispose()


def _env_shelves() -> list[dict]:
    rows = []
    try:
        from search_engine.storage import _fix_url
        for i in range(1, 10):
            raw = (os.getenv(f"SEARCH_DB_URL_{i}") or "").strip()
            if not raw:
                continue
            url = _fix_url(raw)
            host = url.split("@")[-1].split("/")[0].lower()
            provider = "Supabase" if "supabase" in host else ("Neon" if "neon" in host else "PostgreSQL")
            maximum = float(os.getenv("SEARCH_DB_MAX_MB", "400"))
            threshold = float(os.getenv("SEARCH_DB_THRESHOLD_PERCENT", "80"))
            try:
                used = _size_for_url(url)
                status = "healthy"
            except Exception:
                used, status = None, "unreachable"
            fill = round(100 * used / maximum, 1) if used is not None and maximum > 0 else None
            rows.append({"id": f"env-{i}", "name": f"Environment shelf {i}", "provider": provider,
                         "max_storage_mb": maximum, "used_mb": used, "threshold_percent": threshold,
                         "fill_percent": fill, "priority": i, "enabled": True, "health": status,
                         "editable": False, "source": "environment"})
    except Exception:
        pass
    return rows


@router.get("/command-center")
def command_center_page():
    page = Path(__file__).with_name("storage_dashboard.html")
    return FileResponse(page, media_type="text/html")


@router.get("/status")
def storage_status(username: str = Depends(current_user)):
    rows = _env_shelves()
    try:
        for s in registry.list_shelves(include_secrets=True):
            if not s.get("url"):
                used, health = None, "configuration_error"
            elif not s["enabled"]:
                used, health = None, "disabled"
            else:
                try:
                    used = _size_for_url(s["url"])
                    health = "healthy"
                except Exception:
                    used, health = None, "unreachable"
            maximum = float(s["max_storage_mb"])
            fill = round(100 * used / maximum, 1) if used is not None and maximum > 0 else None
            rows.append({"id": s["id"], "name": s["name"], "provider": s["provider"],
                         "max_storage_mb": maximum, "used_mb": used,
                         "threshold_percent": s["threshold_percent"], "fill_percent": fill,
                         "priority": s["priority"], "enabled": s["enabled"], "health": health,
                         "editable": True, "source": "registry"})
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Storage registry unavailable: {type(exc).__name__}") from exc
    # Do not disclose connection strings or database credentials in this response.
    return {"policy": {"routing": "priority order", "default_threshold_percent": 80},
            "shelves": rows, "configured_count": len(rows),
            "note": "Capacity is database-size based. Set each shelf's plan allocation accurately; provider-wide shared quotas may not be visible here."}


@router.post("/test")
def test_shelf(data: TestRequest, username: str = Depends(current_user)):
    try:
        result = registry.test_connection(data.url)
        return {"success": True, **result}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # Never return or log the submitted URL/password.
        raise HTTPException(status_code=400, detail=f"Connection test failed: {type(exc).__name__}. Check host, credentials, SSL settings and network access.") from exc


@router.post("/shelves")
def create_shelf(data: ShelfCreate, username: str = Depends(current_user)):
    try:
        shelf_id = registry.add_shelf(name=data.name, provider=data.provider, url=data.url,
                                      max_storage_mb=data.max_storage_mb,
                                      threshold_percent=data.threshold_percent, priority=data.priority)
        try:
            from search_engine.storage import reset_for_tests
            reset_for_tests()
        except Exception:
            pass
        return {"success": True, "id": shelf_id, "message": "Storage shelf connected and saved securely."}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not save shelf: {type(exc).__name__}. Check database access and credentials.") from exc


@router.patch("/shelves/{shelf_id}")
def patch_shelf(shelf_id: int, data: ShelfUpdate, username: str = Depends(current_user)):
    try:
        ok = registry.update_shelf(shelf_id, **data.dict(exclude_unset=True))
        if not ok: raise HTTPException(status_code=404, detail="Storage shelf not found.")
        try:
            from search_engine.storage import reset_for_tests
            reset_for_tests()
        except Exception: pass
        return {"success": True, "message": "Shelf settings updated."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/shelves/{shelf_id}")
def remove_shelf(shelf_id: int, username: str = Depends(current_user)):
    if not registry.delete_shelf(shelf_id):
        raise HTTPException(status_code=404, detail="Storage shelf not found.")
    try:
        from search_engine.storage import reset_for_tests
        reset_for_tests()
    except Exception: pass
    return {"success": True, "message": "VALE's connection configuration was removed. Data inside the external database was not deleted."}
