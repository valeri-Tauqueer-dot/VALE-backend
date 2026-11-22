"""Anomaly and failure detector. It turns evidence into observations and never changes anything."""
from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from ..core.config import SupervisorConfig
from ..core.enums import IncidentType as T, sev_up
from ..core.models import Component, Observation
from .collector import ScanResult
from .registry import HealthRegistry


class Detector:
    def __init__(self, cfg: SupervisorConfig, registry: HealthRegistry) -> None:
        self.cfg, self.reg = cfg, registry
        self.start_ts = 0.0
        self.rss: Deque[Tuple[float, float]] = deque(maxlen=120)
        self.tasks_hist: Deque[Tuple[float, int]] = deque(maxlen=120)

    def run(self, now: float, metrics: Dict[str, Any], scan: ScanResult) -> Tuple[List[Observation], Set[tuple]]:
        obs: List[Observation] = []
        checked: Set[tuple] = set()
        for c in self.reg.brains():
            self._brain(c, now, obs, checked)
        self._process(now, metrics, obs, checked)
        self._network(now, scan, obs, checked)
        return obs, checked

    # ------------------------------------------------------------------ brains
    def _brain(self, c: Component, now: float, obs: List[Observation], checked: Set[tuple]) -> None:
        cfg, name = self.cfg, c.name
        checked.add((T.HEALTH.value, name))
        checked.add((T.TIMEOUT.value, name))
        if not c.registered:
            if c.expected and now - self.start_ts >= cfg.startup_grace_s:
                obs.append(Observation(T.HEALTH.value, name, "not_registered", "HIGH" if c.core else "WARNING",
                                       f"{name} is not registered with the brain network", {"expected": True}, [name], "UNITY"))
            return
        dest = "UNITY" if c.core else "HEROIC"
        if c.consec_fail >= cfg.fail_warn:
            n = c.consec_fail
            sev = "CRITICAL" if n >= cfg.fail_critical else "HIGH" if n >= cfg.fail_high else "WARNING"
            if c.core and sev != "CRITICAL":
                sev = sev_up(sev)
            ts, err = c.recent_errors[-1] if c.recent_errors else (0.0, "")
            obs.append(Observation(T.HEALTH.value, name, "consecutive_failures", sev,
                                   f"{name}: {n} failed call(s) in a row. Last error: {err}",
                                   {"consecutive_failures": n, "recent_errors": [e for _, e in list(c.recent_errors)[-3:]]},
                                   [name], dest, first_evidence_ts=ts))
        worst = max((d for ts, d, ok in c.recent_calls if ts >= now - 300), default=0.0)
        if worst > cfg.slow_s:
            obs.append(Observation(T.TIMEOUT.value, name, "slow_call", "HIGH" if worst > cfg.timeout_s else "WARNING",
                                   f"{name} took {worst:.1f}s to answer (slow limit {cfg.slow_s:.0f}s)",
                                   {"slowest_s": round(worst, 2)}, [name], dest))
        for tid, t0 in c.inflight.items():
            age = now - t0
            if age > cfg.stall_s:
                obs.append(Observation(T.TIMEOUT.value, name, "stalled_call", "CRITICAL",
                                       f"{name} has not answered for {age:.0f}s (possible hang or deadlock)",
                                       {"task": tid, "seconds": round(age, 1)}, [name], "UNITY", first_evidence_ts=t0))
                break
        fresh = bool(c.probe_ts) and now - c.probe_ts <= cfg.probe_ttl_s
        if fresh and c.probe_ok is False:
            obs.append(Observation(T.HEALTH.value, name, "probe_failed", "HIGH" if c.core else "WARNING",
                                   f"{name} did not pass its health probe: {c.probe_error}", {"error": c.probe_error},
                                   [name], dest, first_evidence_ts=c.probe_ts))
        elif fresh and c.ready is False:
            obs.append(Observation(T.HEALTH.value, name, "not_ready", "WARNING", f"{name} reports itself not ready",
                                   {"probe": c.probe}, [name], dest, first_evidence_ts=c.probe_ts))

    # ------------------------------------------------------------------ process resources
    def _process(self, now: float, m: Dict[str, Any], obs: List[Observation], checked: Set[tuple]) -> None:
        cfg = self.cfg
        rss, pct = m.get("rss_mb"), m.get("mem_pct")
        if any(m.get(k) is not None for k in ("rss_mb", "mem_pct", "threads", "fds")):
            checked.add((T.RESOURCE.value, "PROCESS"))
        if pct is not None:
            sev = ("CRITICAL" if pct >= cfg.mem_critical_pct else "HIGH" if pct >= cfg.mem_high_pct
                   else "WARNING" if pct >= cfg.mem_warn_pct else None)
            if sev:
                obs.append(Observation(T.RESOURCE.value, "PROCESS", "memory_pressure", sev,
                                       f"Memory use is {pct:.0f}% of the limit ({rss:.0f} MB of {m.get('mem_limit_mb'):.0f} MB)",
                                       {"mem_pct": round(pct, 1), "rss_mb": round(rss or 0, 1)}, ["ALL"], "OPERATOR"))
        if rss is not None:
            self.rss.append((now, rss))
            window = [(t, v) for t, v in self.rss if now - t <= cfg.growth_window_s]
            if len(window) >= 3 and window[-1][0] - window[0][0] >= 0.5 * cfg.growth_window_s:
                growth = window[-1][1] - window[0][1]
                if growth >= cfg.mem_growth_mb:
                    mins = (window[-1][0] - window[0][0]) / 60.0
                    obs.append(Observation(T.RESOURCE.value, "PROCESS", "memory_growth",
                                           "HIGH" if growth >= 3 * cfg.mem_growth_mb else "WARNING",
                                           f"Memory grew by {growth:.0f} MB in {mins:.0f} minutes (possible leak)",
                                           {"growth_mb": round(growth, 1), "minutes": round(mins, 1), "rss_mb": round(rss, 1)},
                                           ["ALL"], "OPERATOR", first_evidence_ts=window[0][0]))
        th = m.get("threads")
        if th is not None and th >= cfg.threads_warn:
            obs.append(Observation(T.RESOURCE.value, "PROCESS", "thread_count", "WARNING", f"{th:.0f} threads are running",
                                   {"threads": th}, ["ALL"], "OPERATOR"))
        fds, lim = m.get("fds"), m.get("fd_limit")
        if fds is not None and lim and fds / lim * 100 >= cfg.fd_warn_pct:
            obs.append(Observation(T.RESOURCE.value, "PROCESS", "fd_pressure", "WARNING",
                                   f"{fds:.0f} of {lim:.0f} file handles are open", {"fds": fds, "limit": lim}, ["ALL"], "OPERATOR"))

    # ------------------------------------------------------------------ the brain network itself
    def _network(self, now: float, scan: ScanResult, obs: List[Observation], checked: Set[tuple]) -> None:
        cfg = self.cfg
        n = scan.tasks_total
        if n is not None:
            self.tasks_hist.append((now, n))
            checked.add((T.RESOURCE.value, "NETWORK"))
            sev = ("CRITICAL" if n >= cfg.tasks_critical else "HIGH" if n >= cfg.tasks_high
                   else "WARNING" if n >= cfg.tasks_warn else None)
            if sev:
                first = self.tasks_hist[0]
                span = max(1e-9, now - first[0])
                rate = (n - first[1]) / span * 60.0 if span >= 30 else None
                obs.append(Observation(T.RESOURCE.value, "NETWORK", "task_registry_growth", sev,
                                       f"The brain network is holding {n} task states in memory",
                                       {"tasks": n, "growth_per_min": round(rate, 2) if rate is not None else None},
                                       ["ALL"], "OPERATOR"))
        if scan.observed:
            checked.add((T.SECURITY.value, "NETWORK"))
            if scan.burst >= cfg.burst_warn:
                obs.append(Observation(T.SECURITY.value, "NETWORK", "request_burst",
                                       "HIGH" if scan.burst >= cfg.burst_high else "WARNING",
                                       f"{scan.burst} tasks were created in the last 10 seconds (unusual request volume)",
                                       {"tasks_in_10s": scan.burst}, ["ALL"], "OPERATOR"))
        if scan.new_events:
            checked.add((T.COMMUNICATION.value, "*", "event_storm"))
            checked.add((T.COMMUNICATION.value, "*", "message_delivery_failed"))
        for tid, n_events, why in scan.storms:
            obs.append(Observation(T.COMMUNICATION.value, f"task:{tid[:8]}", "event_storm", "HIGH",
                                   f"Possible loop: {why}", {"task": tid, "events": n_events}, ["NETWORK"], "UNITY"))
        for kind, target, err, ts in scan.comm_errors:
            obs.append(Observation(T.COMMUNICATION.value, target or "NETWORK", "message_delivery_failed", "WARNING",
                                   f"A message to {target} failed ({err})", {"kind": kind, "error": err}, [target], "UNITY",
                                   first_evidence_ts=ts))
