"""Light, thread-safe telemetry: counters, latency percentiles, recent errors."""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict, Optional


class Telemetry:
    def __init__(self, window: int = 512) -> None:
        self._lock = threading.Lock()
        self._window = window
        self.started_ns = time.time_ns()
        self.counters: Dict[str, int] = {}
        self._lat: Dict[str, Deque[int]] = {}
        self._max: Dict[str, int] = {}
        self.errors: Deque[Dict[str, Any]] = deque(maxlen=20)
        self.error_count = 0
        self.last_ok_ns = 0
        self.last_error_ns = 0

    def count(self, name: str, n: int = 1) -> None:
        with self._lock:
            self.counters[name] = self.counters.get(name, 0) + n

    def observe(self, op: str, ns: int) -> None:
        with self._lock:
            d = self._lat.get(op)
            if d is None:
                d = self._lat[op] = deque(maxlen=self._window)
            d.append(ns)
            if ns > self._max.get(op, 0):
                self._max[op] = ns
            self.counters[op] = self.counters.get(op, 0) + 1
            self.last_ok_ns = time.time_ns()

    def error(self, op: str, exc: BaseException) -> None:
        with self._lock:
            self.error_count += 1
            self.last_error_ns = time.time_ns()
            self.errors.append({"op": op, "type": type(exc).__name__, "msg": str(exc)[:200],
                                "at_ns": self.last_error_ns})

    def percentile(self, op: str, p: float) -> Optional[float]:
        with self._lock:
            d = self._lat.get(op)
            if not d:
                return None
            data = sorted(d)
        idx = min(len(data) - 1, max(0, int(round(p / 100.0 * (len(data) - 1)))))
        return data[idx] / 1e6

    def stats(self, op: str) -> Dict[str, Any]:
        n = self.counters.get(op, 0)
        if not n:
            return {"count": 0, "p50_ms": None, "p95_ms": None, "max_ms": None}
        p50, p95 = self.percentile(op, 50), self.percentile(op, 95)
        return {"count": n, "p50_ms": round(p50, 4) if p50 is not None else None,
                "p95_ms": round(p95, 4) if p95 is not None else None,
                "max_ms": round(self._max.get(op, 0) / 1e6, 4)}

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            ops = list(self._lat)
            counters = dict(self.counters)
            errs = list(self.errors)
        return {"uptime_s": round((time.time_ns() - self.started_ns) / 1e9, 1),
                "counters": counters, "latency": {op: self.stats(op) for op in ops},
                "error_count": self.error_count, "recent_errors": errs}
