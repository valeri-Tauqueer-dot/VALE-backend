"""SUPERVISOR's own telemetry: counters, latency percentiles, recent errors."""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict, Optional


class Rolling:
    """A bounded window of numbers with cheap percentiles."""
    __slots__ = ("d",)

    def __init__(self, size: int = 100) -> None:
        self.d: Deque[float] = deque(maxlen=size)

    def add(self, v: float) -> None:
        self.d.append(v)

    def __len__(self) -> int:
        return len(self.d)

    def pct(self, p: float) -> Optional[float]:
        if not self.d:
            return None
        data = sorted(self.d)
        return data[min(len(data) - 1, max(0, int(round(p / 100.0 * (len(data) - 1)))))]


class Telemetry:
    def __init__(self, window: int = 512) -> None:
        self._lock = threading.Lock()
        self.started = time.time()
        self.counters: Dict[str, int] = {}
        self._lat: Dict[str, Rolling] = {}
        self._max: Dict[str, float] = {}
        self.errors: Deque[Dict[str, Any]] = deque(maxlen=20)
        self.error_count = 0
        self.last_ok = 0.0
        self._window = window

    def count(self, name: str, n: int = 1) -> None:
        with self._lock:
            self.counters[name] = self.counters.get(name, 0) + n

    def observe(self, op: str, seconds: float) -> None:
        with self._lock:
            r = self._lat.get(op)
            if r is None:
                r = self._lat[op] = Rolling(self._window)
            r.add(seconds)
            if seconds > self._max.get(op, 0.0):
                self._max[op] = seconds
            self.counters[op] = self.counters.get(op, 0) + 1
            self.last_ok = time.time()

    def error(self, op: str, exc: BaseException) -> None:
        with self._lock:
            self.error_count += 1
            self.errors.append({"op": op, "type": type(exc).__name__, "msg": str(exc)[:200], "at": time.time()})

    def stats(self, op: str) -> Dict[str, Any]:
        with self._lock:
            r = self._lat.get(op)
            n = self.counters.get(op, 0)
            if not r or not n:
                return {"count": 0, "p50_ms": None, "p95_ms": None, "max_ms": None}
            return {"count": n, "p50_ms": round((r.pct(50) or 0) * 1000, 4),
                    "p95_ms": round((r.pct(95) or 0) * 1000, 4), "max_ms": round(self._max.get(op, 0) * 1000, 4)}

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            ops = list(self._lat)
            counters = dict(self.counters)
            errs = list(self.errors)
        return {"uptime_s": round(time.time() - self.started, 1), "counters": counters,
                "latency": {o: self.stats(o) for o in ops}, "error_count": self.error_count, "recent_errors": errs}
