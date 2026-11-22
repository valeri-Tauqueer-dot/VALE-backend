"""Telemetry collector.

Two sources, both passive (nothing in the system is changed to collect them):
  * process metrics: memory, threads, file handles, load (read from /proc and the cgroup files)
  * the newest task states of the brain network: lifecycle events with timestamps, plus the shared-state keys
    that describe data sources and brain selection.
A missing signal stays missing (None). It is never filled in with a guess.
"""
from __future__ import annotations

import itertools
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ..core.config import SupervisorConfig
from ..core.util import clip, parse_iso

_MB = 1024.0 * 1024.0


class ProcessSampler:
    def __init__(self, provider: Optional[Callable[[], Dict[str, Any]]] = None) -> None:
        self.provider = provider

    def sample(self) -> Dict[str, Optional[float]]:
        if self.provider is not None:
            try:
                return dict(self.provider())
            except Exception:
                return {}
        out: Dict[str, Optional[float]] = {"rss_mb": None, "mem_limit_mb": None, "mem_pct": None,
                                           "threads": float(threading.active_count()), "fds": None,
                                           "fd_limit": None, "load1": None, "cpus": float(os.cpu_count() or 0) or None}
        try:
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        out["rss_mb"] = int(line.split()[1]) / 1024.0
                        break
        except Exception:
            pass
        out["mem_limit_mb"] = self._cgroup_limit()
        if out["rss_mb"] is not None and out["mem_limit_mb"]:
            out["mem_pct"] = out["rss_mb"] / out["mem_limit_mb"] * 100.0
        try:
            out["fds"] = float(len(os.listdir("/proc/self/fd")))
        except Exception:
            pass
        try:
            import resource
            soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
            out["fd_limit"] = float(soft) if 0 < soft < (1 << 40) else None
        except Exception:
            pass
        try:
            out["load1"] = os.getloadavg()[0]
        except Exception:
            pass
        return out

    @staticmethod
    def _cgroup_limit() -> Optional[float]:
        for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
            try:
                with open(p) as f:
                    raw = f.read().strip()
                if raw and raw != "max":
                    v = int(raw)
                    if 0 < v < (1 << 50):
                        return v / _MB
            except Exception:
                continue
        return None


@dataclass(slots=True)
class TaskDigest:
    """What one finished task looked like, boiled down to what the integrity monitors need."""
    task_id: str
    created: float
    events: int
    started: Set[str]
    completed: Set[str]
    errored: Dict[str, str]
    skipped: List[Tuple[str, str]]
    required: List[str]
    optional: List[str]
    active: Optional[List[str]]
    heroic_status: Optional[str]
    external_required: bool
    internet_available: Optional[bool]
    internet_performed: bool
    internet_error: str
    results_n: int
    results_bad: int


@dataclass
class ScanResult:
    tasks_total: Optional[int] = None
    observed: int = 0
    burst: int = 0
    digests: List[TaskDigest] = field(default_factory=list)
    calls: List[Tuple[str, float, bool, Optional[float], str, str]] = field(default_factory=list)
    starts: List[Tuple[str, str, float]] = field(default_factory=list)
    ends: List[Tuple[str, str]] = field(default_factory=list)
    storms: List[Tuple[str, int, str]] = field(default_factory=list)
    comm_errors: List[Tuple[str, str, str, float]] = field(default_factory=list)
    skipped: List[Tuple[str, str, float]] = field(default_factory=list)
    scan_seconds: float = 0.0
    new_events: int = 0


class _Track:
    __slots__ = ("n", "starts", "completed", "errored", "skipped", "finished", "digested", "rep_key", "rep_n", "storm")

    def __init__(self) -> None:
        self.n = 0
        self.starts: Dict[str, float] = {}
        self.completed: Set[str] = set()
        self.errored: Dict[str, str] = {}
        self.skipped: List[Tuple[str, str]] = []
        self.finished = False
        self.digested = False
        self.rep_key: Tuple[str, str] = ("", "")
        self.rep_n = 0
        self.storm = False


class TaskScanner:
    """Reads only the events it has not read yet. Cost per tick is proportional to new events, not to history."""

    def __init__(self, cfg: SupervisorConfig) -> None:
        self.cfg = cfg
        self._tracks: "OrderedDict[str, _Track]" = OrderedDict()
        self._watch: "OrderedDict[str, Any]" = OrderedDict()     # tasks with a call still in flight

    def _recent(self, network: Any) -> List[Any]:
        tasks = getattr(network, "tasks", None)
        if not tasks:
            return []
        lock = getattr(network, "_lock", None)
        for _ in range(3):
            try:
                if lock is not None:
                    with lock:
                        return list(itertools.islice(reversed(tasks.values()), self.cfg.scan_tasks))
                return list(itertools.islice(reversed(tasks.values()), self.cfg.scan_tasks))
            except RuntimeError:
                continue
        return []

    def scan(self, network: Any, now: float) -> ScanResult:
        res = ScanResult()
        tasks = getattr(network, "tasks", None)
        res.tasks_total = len(tasks) if tasks is not None else None
        states = self._recent(network)
        have = {getattr(s, "task_id", None) for s in states}
        for tid, st in list(self._watch.items()):
            if tid not in have:
                states.append(st)
        cfg, ten = self.cfg, now - 10.0
        for st in states:
            tid = getattr(st, "task_id", None)
            events = getattr(st, "events", None)
            if tid is None or not isinstance(events, list):
                continue
            res.observed += 1
            created = parse_iso(getattr(st, "created_at", None))
            if created is not None and created >= ten:
                res.burst += 1
            tr = self._tracks.get(tid)
            if tr is None:
                tr = self._tracks[tid] = _Track()
            else:
                self._tracks.move_to_end(tid)
            n = len(events)
            if n > tr.n:
                self._process(tid, events[tr.n:n], tr, res, now)
                tr.n = n
                if n > cfg.event_storm and not tr.storm:
                    tr.storm = True
                    res.storms.append((tid, n, f"{n} events in one task"))
            if tr.starts:
                self._watch[tid] = st
            else:
                self._watch.pop(tid, None)
            if tr.finished and not tr.digested:
                tr.digested = True
                res.digests.append(self._digest(tid, st, tr, created or now, n))
        while len(self._tracks) > max(256, cfg.scan_tasks * 4):
            self._tracks.popitem(last=False)
        while len(self._watch) > 128:
            self._watch.popitem(last=False)
        return res

    def _process(self, tid: str, events: List[Any], tr: _Track, res: ScanResult, now: float) -> None:
        for ev in events:
            et = getattr(ev, "event_type", "")
            src = str(getattr(ev, "source", "") or "").upper()
            ts = parse_iso(getattr(ev, "timestamp", None))
            if ts is None or now - ts > self.cfg.history_window_s:
                continue
            res.new_events += 1
            key = (et, src)
            if key == tr.rep_key:
                tr.rep_n += 1
                if tr.rep_n == self.cfg.event_repeat and not tr.storm:
                    tr.storm = True
                    res.storms.append((tid, tr.n, f"{et} from {src} repeated {tr.rep_n} times in a row"))
            else:
                tr.rep_key, tr.rep_n = key, 1
            payload = getattr(ev, "payload", None) or {}
            if et == "brain_think_started":
                tr.starts[src] = ts
                res.starts.append((src, tid, ts))
            elif et in ("brain_think_completed", "brain_think_error"):
                start = tr.starts.pop(src, None)
                dur = (ts - start) if start is not None else None
                ok = et == "brain_think_completed"
                err = "" if ok else clip(payload.get("error", "unknown error") if isinstance(payload, dict) else "error", 200)
                if ok:
                    tr.completed.add(src)
                else:
                    tr.errored[src] = err
                res.calls.append((src, ts, ok, dur, err, tid))
                res.ends.append((src, tid))
            elif et == "brain_selection_skipped":
                reason = str(payload.get("reason", "")) if isinstance(payload, dict) else ""
                brain = str(payload.get("brain", src)).upper() if isinstance(payload, dict) else src
                tr.skipped.append((brain, reason))
                res.skipped.append((brain, reason, ts))
            elif et in ("brain_message_failed", "brain_message_error"):
                # brain_message_failed: the target is the brain that was missing. brain_message_error: the source is the brain that raised.
                tgt = (str(getattr(ev, "target", "") or src) if et == "brain_message_failed" else src).upper()
                err = clip(payload.get("reason") or payload.get("error") or et, 160) if isinstance(payload, dict) else et
                res.comm_errors.append((et, tgt, err, ts))
            elif et == "selected_brains_completed":
                tr.finished = True

    @staticmethod
    def _digest(tid: str, st: Any, tr: _Track, created: float, n: int) -> TaskDigest:
        def get(k: str, d: Any = None) -> Any:
            try:
                return st.get(k, d)
            except Exception:
                return d
        plan = get("task_plan")
        plan = plan if isinstance(plan, dict) else {}
        active = get("active_brains")
        results = get("internet_results") or []
        results = results if isinstance(results, list) else []
        bad = 0
        for r in results:
            if not isinstance(r, dict) or not (r.get("url") or r.get("link") or r.get("source")) \
                    or not (r.get("title") or r.get("snippet") or r.get("content") or r.get("text")):
                bad += 1
        avail = get("internet_available")
        return TaskDigest(
            task_id=tid, created=created, events=n, started=set(tr.completed) | set(tr.errored) | set(tr.starts),
            completed=set(tr.completed), errored=dict(tr.errored), skipped=list(tr.skipped),
            required=[str(b).upper() for b in plan.get("required_brains", []) or []],
            optional=[str(b).upper() for b in plan.get("optional_brains", []) or []],
            active=[str(b).upper() for b in active] if isinstance(active, list) else None,
            heroic_status=get("heroic_status"), external_required=bool(get("external_information_required", False)),
            internet_available=avail if isinstance(avail, bool) else None,
            internet_performed=bool(get("internet_research_performed", False)),
            internet_error=clip(get("internet_error") or get("internet_research_error") or "", 160),
            results_n=len(results), results_bad=bad)
