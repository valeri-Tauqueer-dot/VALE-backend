"""Small helpers: time, ISO parsing, clipping."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional


def now() -> float:
    return time.time()


def mono() -> float:
    return time.perf_counter()


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def parse_iso(text: object) -> Optional[float]:
    if not isinstance(text, str):
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def clip(text: object, n: int = 160) -> str:
    s = str(text)
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"
