"""Health registry, heartbeat monitor and contract coverage.

A component is HEALTHY only when there is fresh evidence of it working. No evidence means UNKNOWN. A component
that was failing is not called healthy again until it has shown several good signals in a row.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List, Optional, Set

from ..core.config import SupervisorConfig
from ..core.enums import CORE_BRAINS, Breaker, ComponentState as CS
from ..core.models import Component
from ..core.store import AuditLog
from ..core.util import clip
from .collector import ScanResult

_ALIASES = {"FEELING": "FEELINGS", "FEEL": "FEELINGS"}
_OK_WORDS = ("ONLINE", "OK", "HEALTHY", "READY")


def norm_name(name: Any) -> str:
    n = str(name or "").strip().upper()
    return _ALIASES.get(n, n)


class Prober:
    """Asks a brain how it is. Uses health() when the brain has it, identity() (liveness only) when it does not."""

    def probe(self, brain: Any) -> Dict[str, Any]:
        health = getattr(brain, "health", None)
        fn, how = (health, "health") if callable(health) else (getattr(brain, "identity", None), "identity")
        if not callable(fn):
            return {"ok": None, "ready": None, "live": None, "how": "none", "snapshot": {}, "error": "no health() or identity()"}
        try:
            snap = fn()
        except Exception as exc:
            return {"ok": False, "ready": None, "live": False, "how": how, "snapshot": {}, "error": clip(f"{type(exc).__name__}: {exc}", 160)}
        if not isinstance(snap, dict):
            return {"ok": False, "ready": None, "live": None, "how": how, "snapshot": {}, "error": "answer was not a dictionary"}
        small = {k: v for k, v in list(snap.items())[:40] if isinstance(v, (bool, int, float, str)) and len(str(v)) < 80}
        errs = snap.get("errors")
        if isinstance(errs, dict) and isinstance(errs.get("total"), int):
            small["errors_total"] = errs["total"]
        if how == "health":
            ready = snap.get("ready")
            status = str(snap.get("status", "")).upper()
            ready = ready if isinstance(ready, bool) else (True if status in _OK_WORDS else None)
            live = snap.get("live") if isinstance(snap.get("live"), bool) else True
            return {"ok": True, "ready": ready, "live": live, "how": how, "snapshot": small, "error": ""}
        return {"ok": True, "ready": None, "live": True, "how": how, "snapshot": small, "error": ""}


class HealthRegistry:
    def __init__(self, cfg: SupervisorConfig, audit: AuditLog) -> None:
        self.cfg, self.audit = cfg, audit
        self.components: Dict[str, Component] = {}
        self._brains: Dict[str, Any] = {}
        self.start_ts = 0.0
        self.guard_seen: "OrderedDict[tuple, None]" = OrderedDict()   # (task, brain) calls a guard already recorded

    # ------------------------------------------------------------------ membership
    def ensure(self, name: str, kind: str = "BRAIN", now: float = 0.0) -> Component:
        n = norm_name(name)
        c = self.components.get(n)
        if c is None:
            c = self.components[n] = Component(name=n, kind=kind, core=n in CORE_BRAINS, first_seen=now,
                                               expected=n in self.cfg.expected_brains,
                                               breaker_open_s=self.cfg.breaker_open_s)
        return c

    @staticmethod
    def coverage_of(brain: Any) -> Dict[str, bool]:
        return {"identity": callable(getattr(brain, "identity", None)),
                "health": callable(getattr(brain, "health", None)),
                "contract": callable(getattr(brain, "contract", None)),
                "recovery_hook": callable(getattr(brain, "reset", None)),
                "version": bool(getattr(brain, "version", None) or getattr(brain, "VERSION", None))}

    def sync(self, network: Any, now: float) -> None:
        try:
            names = {norm_name(n) for n in network.brain_names()}
        except Exception:
            return
        for n in names:
            c = self.ensure(n, "BRAIN", now)
            if not c.registered:
                self.audit.add(now, "component_registered_again", n)
            c.registered = True
            brain = network.get_brain(n)
            if brain is not None and self._brains.get(n) is not brain:
                self._brains[n] = brain
                c.coverage = self.coverage_of(brain)
        for n, c in self.components.items():
            if c.kind == "BRAIN" and n not in names:
                if c.registered:
                    self.audit.add(now, "component_unregistered", n)
                c.registered = False
        for n in self.cfg.expected_brains:
            self.ensure(n, "BRAIN", now)
        for n in [n for n in self._brains if n not in names]:
            self._brains.pop(n, None)

    def brain_object(self, name: str) -> Any:
        return self._brains.get(norm_name(name))

    # ------------------------------------------------------------------ evidence
    def record_call(self, name: str, ts: float, ok: bool, duration: Optional[float], error: str = "") -> None:
        c = self.ensure(name, "BRAIN", ts)
        c.calls += 1
        c.last_seen = max(c.last_seen, ts)
        if duration is not None and duration >= 0:
            c.latencies.append(duration)
            c.recent_calls.append((ts, duration, ok))
        elif not ok or ok:
            c.recent_calls.append((ts, 0.0, ok))
        if ok:
            c.last_ok, c.consec_ok, c.consec_fail = max(c.last_ok, ts), c.consec_ok + 1, 0
        else:
            c.errors += 1
            c.last_error, c.consec_fail, c.consec_ok = max(c.last_error, ts), c.consec_fail + 1, 0
            c.recent_errors.append((ts, clip(error, 160)))

    def begin_call(self, name: str, task_id: str, ts: float) -> None:
        self.ensure(name, "BRAIN", ts).inflight[task_id] = ts

    def end_call(self, name: str, task_id: str) -> None:
        c = self.components.get(norm_name(name))
        if c is not None:
            c.inflight.pop(task_id, None)

    def mark_guard_seen(self, tid: str, name: str) -> None:
        self.guard_seen[(tid, norm_name(name))] = None
        while len(self.guard_seen) > 4096:
            self.guard_seen.popitem(last=False)

    def apply_scan(self, scan: ScanResult) -> None:
        seen = self.guard_seen
        for name, tid, ts in scan.starts:
            if (tid, norm_name(name)) not in seen:
                self.begin_call(name, tid, ts)
        for name, ts, ok, dur, err, tid in scan.calls:
            if (tid, norm_name(name)) not in seen:
                self.record_call(name, ts, ok, dur, err)
        for name, tid in scan.ends:
            if (tid, norm_name(name)) not in seen:
                self.end_call(name, tid)

    def record_probe(self, name: str, ts: float, result: Dict[str, Any]) -> None:
        c = self.ensure(name, "BRAIN", ts)
        c.probe_ts, c.probe_ok = ts, result.get("ok")
        c.probe, c.probe_error = result.get("snapshot", {}), result.get("error", "")
        c.live, c.ready = result.get("live"), result.get("ready")
        if result.get("ok") and result.get("ready") is not False:
            c.consec_ok += 1
            c.last_seen = ts
        elif result.get("ok") is False:
            c.consec_ok = 0

    # ------------------------------------------------------------------ state
    def derive(self, now: float) -> None:
        for c in self.components.values():
            if c.kind != "BRAIN":
                continue
            prev = c.state
            c.state, c.reason = self._derive(c, now, prev)
            if c.state != prev:
                self.audit.add(now, "component_state", c.name, f"{prev.value}->{c.state.value}: {c.reason}")

    def _derive(self, c: Component, now: float, prev: CS):
        cfg = self.cfg
        if c.breaker == Breaker.OPEN.value:
            return CS.ISOLATED, f"circuit breaker open (trip {c.breaker_trips})"
        if c.breaker == Breaker.HALF_OPEN.value:
            return CS.RECOVERING, "circuit breaker half-open: one trial call is allowed"
        if not c.registered:
            if c.expected and now - self.start_ts >= cfg.startup_grace_s:
                return CS.UNHEALTHY, "not registered with the brain network"
            return CS.UNKNOWN, "not registered (the system may still be starting)" if c.expected else "not registered"
        stalled = [now - t0 for t0 in c.inflight.values() if now - t0 > cfg.stall_s]
        probe_fresh = bool(c.probe_ts) and now - c.probe_ts <= cfg.probe_ttl_s
        evidence_fresh = bool(c.last_ok) and now - c.last_ok <= cfg.fresh_evidence_s
        p95 = c.p95()
        if stalled:
            return CS.UNHEALTHY, f"a call has been running for {max(stalled):.0f}s (possible hang)"
        since = f" (last {now - c.last_error:.0f}s ago; no newer call has succeeded)" if c.last_error else ""
        if c.consec_fail >= cfg.fail_high:
            return CS.UNHEALTHY, f"{c.consec_fail} failed calls in a row{since}"
        if probe_fresh and c.probe_ok is False:
            return CS.UNHEALTHY, f"health probe failed: {c.probe_error}"
        if c.consec_fail >= cfg.fail_warn:
            return CS.DEGRADED, f"the last call failed ({c.consec_fail} in a row){since}"
        if probe_fresh and c.ready is False:
            return CS.DEGRADED, "reports itself not ready"
        if p95 is not None and p95 > cfg.slow_s:
            return CS.DEGRADED, f"slow: p95 {p95:.1f}s"
        positive = evidence_fresh or (probe_fresh and c.probe_ok and c.ready is True)
        if positive:
            if prev in (CS.UNHEALTHY, CS.DEGRADED, CS.ISOLATED, CS.RECOVERING) and c.consec_ok < cfg.recover_ok:
                return CS.DEGRADED, f"recovering: {c.consec_ok} of {cfg.recover_ok} good signals"
            return CS.HEALTHY, "recent successful calls" if evidence_fresh else "health probe reports ready"
        if probe_fresh and c.probe_ok:
            return CS.UNKNOWN, "alive, but readiness is not reported and there are no recent calls"
        return CS.UNKNOWN, "no recent evidence"

    # ------------------------------------------------------------------ views
    def availability(self, name: str) -> Optional[bool]:
        c = self.components.get(norm_name(name))
        if c is None or not c.registered:
            return False if c is not None and c.expected else None
        if c.state in (CS.UNHEALTHY, CS.ISOLATED):
            return False
        if c.state in (CS.HEALTHY, CS.DEGRADED, CS.RECOVERING):
            return True
        return None

    def brains(self) -> List[Component]:
        return [c for c in self.components.values() if c.kind == "BRAIN"]

    def counts(self) -> Dict[str, int]:
        out = {s.value: 0 for s in CS}
        for c in self.brains():
            out[c.state.value] += 1
        return out

    def unknown_names(self) -> List[str]:
        return sorted(c.name for c in self.brains() if c.state == CS.UNKNOWN)

    def unavailable(self) -> List[str]:
        return sorted(c.name for c in self.brains() if self.availability(c.name) is False)
