"""SUPERVISOR - VALE's operational guardian.

It watches whether VALE's brains and supporting systems are working: health, timing, communication, shared state,
data sources and resources. It detects problems, records them as incidents with evidence, escalates what it must,
and (only in ENFORCE mode) runs a small set of approved, bounded recovery actions and verifies the result.

It does not decide what the user wants (HEROIC), integrate the system (UNITY), orchestrate execution (ALPHA), judge
evidence (COGNITIVE) or reason about the world (MARCO, LEGEND). A signal it cannot see is reported as unknown,
never as healthy. See the SUPERVISOR/engines package for each capability.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from vale_brain_interface import VALEBrainInterface

from .core.config import SupervisorConfig
from .core.enums import (ACTIVE_STATUSES, MUTATING, ActionKind as AK, Breaker, ComponentState as CS,
                         IncidentStatus as IS, IncidentType as T, Mode, sev_rank)
from .core.models import ActionRecord, Incident, Observation, PlannedAction
from .core.store import AuditLog, IncidentStore
from .core.telemetry import Rolling, Telemetry
from .core.util import clip, iso, mono, now as wall_now, parse_iso
from .engines.collector import ProcessSampler, ScanResult, TaskScanner
from .engines.conflict import ConflictManager
from .engines.detector import Detector
from .engines.escalation import EscalationManager
from .engines.integrity import FeedMonitor, IntegrityMonitor
from .engines.interfaces import build_contract, build_health
from .engines.policy import PolicyGuard
from .engines.recovery import RecoveryController
from .engines.registry import HealthRegistry, Prober, norm_name
from .engines.verify import VerificationEngine

_HEALTH_WORDS = frozenset("status health healthy diagnose diagnostics diagnostic working broken down error errors incident "
                          "incidents uptime crash crashed failing problem problems".split())
_SYSTEM_WORDS = frozenset("vale system brain brains supervisor server backend you your".split())
_AUTHORITIES = frozenset({"UNITY", "HEROIC", "OPERATOR"})


class SupervisorBrain(VALEBrainInterface):
    VERSION = "1.0.0"
    ROLE = "OPERATIONAL_GUARDIAN"
    ARCHITECTURE_STAGE = "SUPERVISOR_OPERATIONAL_ENGINE"
    RULES = (
        "Does not replace UNITY's integration role or become a second integration authority.",
        "Does not replace HEROIC's mission coordination, ALPHA's orchestration, or any specialist brain.",
        "Does not decide which factual claim is true. It records the operational conflict; COGNITIVE (MCVL) weighs evidence.",
        "Does not rewrite another brain's reasoning, goals or conclusions.",
        "Does not fabricate health, telemetry, data freshness, recovery success or confidence.",
        "Does not retry or restart without limits, or act beyond its permissions.",
        "Does not hide an incident to look stable.",
        "A signal that is missing is unknown. It is never treated as healthy.",
        "A recovery is verified against something observable. A command that returned is not proof.",
    )

    def __init__(self, connector: Any = None, config: Optional[SupervisorConfig] = None, clock=None, metrics=None) -> None:
        super().__init__(brain_name="SUPERVISOR", connector=connector)
        self.version = self.VERSION
        self.cfg = config or SupervisorConfig.from_env()
        self.clock = clock or wall_now
        self.mode = Mode(self.cfg.mode)
        self.lock = threading.RLock()
        self._tick_lock = threading.Lock()
        self._seq = 0
        self.telemetry = Telemetry()
        self.audit = AuditLog(self.cfg.audit_keep)
        self.store = IncidentStore(self.cfg, self.audit)
        self.registry = HealthRegistry(self.cfg, self.audit)
        self.sampler = ProcessSampler(metrics)
        self.scanner = TaskScanner(self.cfg)
        self.prober = Prober()
        self.detector = Detector(self.cfg, self.registry)
        self.integrity = IntegrityMonitor(self.cfg)
        self.feeds = FeedMonitor(self.cfg)
        self.conflicts = ConflictManager(self.cfg, self.registry, self.audit)
        self.policy = PolicyGuard(self.cfg, self.audit)
        self.recovery = RecoveryController(self)
        self.verifier = VerificationEngine(self)
        self.escalation = EscalationManager(self)
        self.holds: Dict[str, Dict[str, Any]] = {}
        self.delays = Rolling(200)          # seconds from the first evidence to the incident being recorded
        self.handling = Rolling(200)        # seconds from the incident being recorded to the response being recorded
        self._pending: List[Observation] = []
        self.last_metrics: Dict[str, Any] = {}
        self.last_tasks: Optional[int] = None
        self.last_tick = 0.0
        self._last_wall = 0.0
        self.last_probe = 0.0
        self.started_at = self.clock()
        self.detector.start_ts = self.registry.start_ts = self.started_at
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = False
        self._wake = threading.Event()
        self._log_times: Deque[float] = deque(maxlen=40)
        self.logger = logging.getLogger("VALE.SUPERVISOR")

    # ================================================================== small helpers
    def next_id(self, prefix: str) -> str:
        with self.lock:
            self._seq += 1
            return f"{prefix}-{self._seq}"

    def make_state(self) -> Any:
        try:
            from brain_state import VALEBrainState
            return VALEBrainState(user_message="SUPERVISOR system alert")
        except Exception:
            return None

    def log(self, level: str, msg: str) -> None:
        if not self.cfg.log:
            return
        t = time.time()
        if sum(1 for x in self._log_times if t - x < 60) >= 20 and level != "error":
            return
        self._log_times.append(t)
        try:
            getattr(self.logger, level)(msg)
        except Exception:
            pass

    # ================================================================== lifecycle
    def attach_network(self, network: Any) -> None:
        super().attach_network(network)
        try:
            with self.lock:
                self.registry.sync(network, self.clock())
            if self.mode == Mode.ENFORCE:
                self.recovery.install_guards()
            if self.cfg.background:
                self.start()
        except Exception as exc:
            self.telemetry.error("attach", exc)

    def start(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return False
        self._stop_flag = False
        self._wake.clear()
        self._thread = threading.Thread(target=self._loop, name="VALE-SUPERVISOR", daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout: float = 2.0) -> bool:
        self._stop_flag = True
        self._wake.set()
        t = self._thread
        if t is not None and t.is_alive() and t is not threading.current_thread():
            t.join(timeout)
        return True

    def request_tick(self) -> None:
        self._wake.set()

    def _loop(self) -> None:
        self._wake.wait(min(self.cfg.tick_interval_s, self.cfg.startup_grace_s, 10.0))   # let the system finish starting
        self._wake.clear()
        first = True
        while not self._stop_flag:
            try:
                self.tick(force_probe=first)
                first = False
            except Exception as exc:                              # the watcher must never die
                self.telemetry.error("loop", exc)
            self._wake.wait(self.cfg.tick_interval_s)
            self._wake.clear()
            gap = self.cfg.min_tick_gap_s - (time.time() - self._last_wall)   # never check more often than min_tick_gap_s
            if gap > 0 and not self._stop_flag:
                time.sleep(gap)

    def set_mode(self, mode: str) -> Dict[str, Any]:
        m = Mode(str(mode).upper())
        with self.lock:
            prev, self.mode = self.mode, m
        n = self.recovery.install_guards() if m == Mode.ENFORCE else self.recovery.uninstall_guards()
        self.audit.add(self.clock(), "mode_changed", "SUPERVISOR", f"{prev.value} -> {m.value}")
        self.log("warning", f"SUPERVISOR mode changed: {prev.value} -> {m.value}")
        return {"ok": True, "mode": m.value, "previous": prev.value, "guards": len(self.recovery._guards), "changed": n}

    # ================================================================== the loop: observe, measure, classify, act, verify, record, escalate
    def tick(self, force_probe: bool = False) -> Dict[str, Any]:
        if not self._tick_lock.acquire(blocking=False):
            return {"skipped": "another check is already running"}
        t0 = mono()
        try:
            return self._tick(force_probe)
        except Exception as exc:
            self.telemetry.error("tick", exc)
            return {"error": f"{type(exc).__name__}: {str(exc)[:160]}"}
        finally:
            self._tick_lock.release()
            self.telemetry.observe("tick", mono() - t0)
            with self.lock:                                   # evidence about SUPERVISOR itself: the loop is running
                self.registry.record_call("SUPERVISOR", self.clock(), self.telemetry.error_count == 0 or self.telemetry.counters.get("tick", 0) > 3 * self.telemetry.error_count, mono() - t0)

    def _tick(self, force_probe: bool) -> Dict[str, Any]:
        now = self.clock()
        net = self.network
        metrics = self.sampler.sample()
        self.last_metrics = metrics
        if self.mode == Mode.ENFORCE:
            self.recovery.install_guards()
        scan = self.scanner.scan(net, now) if net is not None else ScanResult()
        self.last_tasks = scan.tasks_total
        with self.lock:
            if net is not None:
                self.registry.sync(net, now)
            self.registry.apply_scan(scan)
            due = []
            if force_probe or now - self.last_probe >= self.cfg.probe_interval_s:
                due = [(n, b) for n, b in self.registry._brains.items() if n != "SUPERVISOR"]
        probes = [(n, self.prober.probe(b)) for n, b in due]                     # calls into other brains: no lock held
        with self.lock:
            for n, r in probes:
                self.registry.record_probe(n, now, r)
            if due:
                self.last_probe = now
            self.registry.derive(now)
            obs, checked = self.detector.run(now, metrics, scan)
            for o, c in (self.integrity.analyze(scan.digests, now), self.feeds.check(now), self.conflicts.check(now)):
                obs += o
                checked |= c
            obs += self._pending
            self._pending = []
            observed, new = set(), []
            for o in obs:
                inc, is_new = self.store.observe(o, now)
                observed.add(inc.key)
                if is_new:
                    new.append(inc)
                    if o.first_evidence_ts:
                        self.delays.add(max(0.0, now - o.first_evidence_ts))
            ready = self.store.tick_clear(observed, checked, now)
            for inc in self.store.active():
                if not inc.action_plan and inc.status == IS.DETECTED:
                    inc.action_plan = self.policy.plan(inc, self.registry.components.get(inc.component))
                    self.store.transition(inc, IS.INVESTIGATING, now, "plan prepared")
        for inc in new:
            self.log("warning" if sev_rank(inc.severity) >= 1 else "info",
                     f"incident {inc.id} [{inc.severity}] {inc.type}/{inc.component}: {inc.summary}")
        acted = self._act(now)                                                   # may call other brains: no lock held
        with self.lock:
            resolved = self._resolve(ready, now)
            self._housekeeping(now)
            self.last_tick = now
            self._last_wall = time.time()
            counts = self.store.counts()
        self.telemetry.count("ticks_observations", len(obs))
        return {"at": iso(now), "observations": len(obs), "new_incidents": [i.id for i in new], "resolved": resolved,
                "actions": acted, "probed": [n for n, _ in probes], "events_read": scan.new_events,
                "tasks_in_network": scan.tasks_total, "active_incidents": counts}

    # ------------------------------------------------------------------ acting
    def _due(self, inc: Incident, act: PlannedAction, now: float) -> bool:
        kind, sev = AK(act.kind), sev_rank(inc.severity)
        if kind in (AK.NOTIFY, AK.ESCALATE):
            if sev < 1:
                return False
            # security-sensitive events are escalated at once; other warnings only if they last
            if sev < 2 and inc.type != T.SECURITY.value and now - inc.detected_at < self.cfg.warn_escalate_s:
                return False
            dest = {"MCVL": "COGNITIVE", "USER": "OPERATOR"}.get((act.destination or "UNITY").upper(), (act.destination or "UNITY").upper())
            return dest not in inc.escalated_to
        if kind == AK.HOLD:
            return act.target not in self.holds
        if kind in MUTATING:
            if sev < 1:
                return False
            existing = [a for a in inc.actions if a.kind == act.kind and a.target == act.target]
            if self.mode != Mode.ENFORCE:
                return not existing                                    # recommend once
            if sum(1 for a in existing if a.executed) >= 3:
                return False
            if existing and not existing[-1].executed and now - existing[-1].started < self.cfg.cooldown_s:
                return False
            return True
        return False

    def _act(self, now: float) -> List[Dict[str, Any]]:
        with self.lock:
            work = [(inc, list(inc.action_plan)) for inc in self.store.active()]
        done: List[Dict[str, Any]] = []
        for inc, plan in work:
            for act in plan:
                with self.lock:
                    due = self._due(inc, act, now)
                if due:
                    done.append(self._run(inc, act, now))
        return done

    def _run(self, inc: Incident, act: PlannedAction, now: float) -> Dict[str, Any]:
        t0 = mono()
        allowed, why = self.policy.authorize(act, self.mode, now)
        if not allowed:
            rec = ActionRecord(self.next_id("act"), act.kind, act.target, now, now, False, False, None, why)
            with self.lock:
                inc.actions.append(rec)
                inc.trail.append((now, "action_not_run", f"{act.kind} {act.target}: {why}"))
                self.audit.add(now, "action_not_run", inc.id, f"{act.kind} {act.target}: {why}")
            self.handling.add(mono() - t0)
            return {"incident": inc.id, "action": act.kind, "target": act.target, "executed": False, "why": why}
        rec = self.recovery.execute(act, inc)                                    # may call other brains: no lock held
        ver = self.verifier.verify(rec, act)
        facts = (rec.verification or {}).get("facts")
        rec.verification = {**(ver or {}), **({"facts": facts} if facts else {})} or None
        with self.lock:
            inc.actions.append(rec)
            self.policy.record(act, rec.ended)
            if ver:
                inc.verification.append(ver)
            inc.trail.append((rec.ended, "action_run", f"{act.kind} {act.target}: {rec.detail[:100]}"))
            self.audit.add(rec.ended, "action_run", inc.id, f"{act.kind} {act.target} ok={rec.ok} verified={ver['ok'] if ver else None}")
            follow = self._apply_outcome(inc, act, rec, ver, rec.ended)
        for dest, reason in follow:
            self.escalation.deliver(inc, dest, reason, rec.ended, force=True)
        self.handling.add(mono() - t0)
        return {"incident": inc.id, "action": act.kind, "target": act.target, "executed": True, "ok": rec.ok,
                "verified": ver["ok"] if ver else None, "detail": rec.detail}

    def _apply_outcome(self, inc: Incident, act: PlannedAction, rec: ActionRecord, ver: Optional[Dict[str, Any]], now: float):
        kind = AK(act.kind)
        follow: List[Tuple[str, str]] = []
        if kind in (AK.NOTIFY, AK.ESCALATE):
            if rec.ok:
                self.store.transition(inc, IS.ESCALATED, now, f"escalated to {act.destination or 'UNITY'}")
            return follow
        if kind == AK.HOLD:
            self.store.transition(inc, IS.CONTAINED, now, "hold set on dependent work")
            return follow
        ok = ver["ok"] if ver else None
        if ok is True:
            self.store.transition(inc, IS.CONTAINED if kind == AK.ISOLATE_BRAIN else IS.RECOVERING, now, f"{act.kind} verified")
        elif ok is False:
            failures = sum(1 for a in inc.actions if a.kind == act.kind and a.executed and a.verification and a.verification.get("ok") is False)
            if failures >= 3:
                self.store.transition(inc, IS.UNRESOLVED, now, f"{act.kind} failed verification {failures} times")
            else:
                self.store.transition(inc, IS.ESCALATED, now, f"{act.kind} could not be verified")
            follow.append(("OPERATOR", f"{act.kind} on {act.target} did not work: {rec.detail}"))
        else:
            self.store.transition(inc, IS.RECOVERING, now, f"{act.kind} ran; the effect is not confirmed")
        return follow

    def _resolve(self, ready: List[Incident], now: float) -> List[str]:
        out: List[str] = []
        for inc in ready:
            comp = self.registry.components.get(inc.component)
            if inc.type == T.HEALTH.value and comp is not None and comp.state in (CS.UNHEALTHY, CS.ISOLATED):
                inc.clear_streak = 0
                continue
            evidence = {"check": "condition_absent", "consecutive_checks": inc.clear_streak,
                        "component_state": comp.state.value if comp else None}
            self.store.transition(inc, IS.VERIFYING, now, "condition absent")
            if self.store.resolve(inc, now, f"condition absent for {inc.clear_streak} consecutive checks", evidence):
                out.append(inc.id)
                if any(a.kind == AK.HOLD.value and a.ok for a in inc.actions) and inc.component in self.holds:
                    self.holds.pop(inc.component, None)
                    self.audit.add(now, "hold_released", inc.component, f"incident {inc.id} resolved")
                self.log("info", f"incident {inc.id} resolved: {inc.resolution}")
        return out

    def _housekeeping(self, now: float) -> None:
        for inc in self.store.active():
            if inc.status == IS.ESCALATED and now - inc.detected_at > self.cfg.unresolved_after_s:
                self.store.transition(inc, IS.UNRESOLVED, now, "no resolution long after escalation")

    # ================================================================== views
    def _overall(self, counts: Dict[str, int], inc: Dict[str, int], attention: List[Dict[str, Any]], unknown: List[str]) -> Tuple[str, str]:
        core_bad = [c for c in attention if c["core"] and c["state"] in ("UNHEALTHY", "ISOLATED")]
        if inc["CRITICAL"] or core_bad:
            return "CRITICAL", "a serious problem is open" if inc["CRITICAL"] else f"core brain {core_bad[0]['name']} is {core_bad[0]['state']}"
        if inc["HIGH"] or inc["WARNING"] or attention:
            return "DEGRADED", f"{inc['HIGH'] + inc['WARNING']} open problem(s), {len(attention)} brain(s) need attention"
        if counts.get("HEALTHY", 0) == 0:
            return "UNKNOWN", "not enough evidence yet to say the system is healthy"
        if unknown:
            return "OK_PARTIAL", f"no problem found; no evidence yet about {len(unknown)} brain(s)"
        return "OK", "no problem found and every brain shows recent healthy evidence"

    def status(self) -> Dict[str, Any]:
        now = self.clock()
        with self.lock:
            counts, inc_counts = self.registry.counts(), self.store.counts()
            attention = [c.to_dict() for c in self.registry.brains() if c.state in (CS.DEGRADED, CS.UNHEALTHY, CS.ISOLATED, CS.RECOVERING)]
            unknown = [n for n in self.registry.unknown_names() if self.registry.components[n].registered]
            overall, why = self._overall(counts, inc_counts, attention, unknown)
            top = [i.to_dict() for i in self.store.active()[:5]]
            holds = {k: {"since": iso(v["since"]), "reason": v["reason"]} for k, v in self.holds.items()}
        m = self.last_metrics
        return {"brain": self.brain_name, "version": self.VERSION, "mode": self.mode.value, "overall": overall,
                "reason": why, "brains": counts, "needs_attention": attention, "no_evidence_yet": unknown,
                "incidents": {"active": inc_counts, "top": top}, "holds": holds,
                "unavailable_brains": self.registry.unavailable(),
                "process": {k: (round(v, 1) if isinstance(v, float) else v) for k, v in m.items()
                            if k in ("rss_mb", "mem_pct", "threads", "fds", "load1")},
                "tasks_in_network": self.last_tasks,
                "last_check_age_s": round(now - self.last_tick, 1) if self.last_tick else None,
                "background": bool(self._thread and self._thread.is_alive())}

    def incidents(self, active_only: bool = True, limit: int = 30) -> List[Dict[str, Any]]:
        with self.lock:
            rows = self.store.active() if active_only else self.store.active() + self.store.recent_resolved(limit)
            return [i.to_dict() for i in rows[:limit]]

    def explain(self, incident_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            inc = self.store.get(incident_id)
            return inc.to_dict(full=True) if inc is not None else None

    def component(self, name: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            c = self.registry.components.get(norm_name(name))
            return c.to_dict() if c is not None else None

    def availability(self, name: str) -> Optional[bool]:
        """True / False when the evidence says so. None means unknown."""
        with self.lock:
            return self.registry.availability(name)

    def unavailable_brains(self) -> List[str]:
        with self.lock:
            return self.registry.unavailable()

    def is_held(self, resource: str) -> bool:
        return resource in self.holds

    def acknowledge(self, incident_id: str) -> bool:
        with self.lock:
            inc = self.store.get(incident_id)
            if inc is None:
                return False
            inc.acknowledged = True
            self.audit.add(self.clock(), "acknowledged", incident_id)
            return True

    def register_feed(self, name: str, max_age_s: float, critical: bool = True, dependents: Tuple[str, ...] = ()) -> Dict[str, Any]:
        with self.lock:
            f = self.feeds.register(name, max_age_s, critical, tuple(dependents), self.clock())
            return {"ok": True, "feed": name, "max_age_s": f.max_age_s, "critical": f.critical}

    def report_feed(self, name: str, observed_at: Optional[float] = None) -> bool:
        with self.lock:
            return self.feeds.report(name, observed_at if observed_at is not None else self.clock())

    def isolate(self, name: str, reason: str) -> bool:
        """Called from the guarded call path when a brain has failed too many times in a row."""
        now = self.clock()
        act = PlannedAction(AK.ISOLATE_BRAIN.value, name, reason)
        allowed, why = self.policy.authorize(act, self.mode, now)
        if not allowed:
            self.audit.add(now, "isolate_refused", name, why)
            return False
        rec = self.recovery.execute(act)
        ver = self.verifier.verify(rec, act)
        rec.verification = {**(ver or {}), **({"facts": (rec.verification or {}).get("facts")} if (rec.verification or {}).get("facts") else {})} or None
        with self.lock:
            self.policy.record(act, rec.ended)
            inc = self.store.find(T.HEALTH.value, name, "consecutive_failures")
            if inc is not None:
                inc.actions.append(rec)
                if ver:
                    inc.verification.append(ver)
                self.store.transition(inc, IS.CONTAINED, rec.ended, "brain isolated by circuit breaker")
            self.audit.add(rec.ended, "isolated", name, reason)
        self.log("warning", f"{name} isolated by SUPERVISOR: {reason}")
        self.request_tick()
        return bool(rec.ok)

    # ================================================================== VALE interface
    def _task_view(self, state: Any, now: float) -> Dict[str, Any]:
        events = getattr(state, "events", None) or []
        brains: Dict[str, Dict[str, Any]] = {}
        starts: Dict[str, Optional[float]] = {}
        for ev in events[:2000]:
            et, src, ts = getattr(ev, "event_type", ""), str(getattr(ev, "source", "")).upper(), parse_iso(getattr(ev, "timestamp", None))
            payload = getattr(ev, "payload", None) or {}
            if et == "brain_think_started":
                starts[src] = ts
                brains.setdefault(src, {})["status"] = "running"
            elif et == "brain_think_completed":
                b = brains.setdefault(src, {})
                b["status"] = "completed"
                if ts is not None and starts.get(src) is not None:
                    b["seconds"] = round(ts - starts[src], 4)
            elif et == "brain_think_error":
                b = brains.setdefault(src, {})
                b["status"] = "error"
                b["error"] = clip(payload.get("error", "") if isinstance(payload, dict) else "", 160)
        anomalies = [f"{n} has been running for more than {self.cfg.stall_s:.0f}s" for n, b in brains.items()
                     if b.get("status") == "running" and starts.get(n) is not None and now - starts[n] > self.cfg.stall_s]
        if len(events) > self.cfg.event_storm:
            anomalies.append(f"{len(events)} events in this task (possible loop)")
        return {"events": len(events), "brains": brains, "anomalies": anomalies}

    def think(self, state: Any) -> Dict[str, Any]:
        if state is None:
            raise ValueError("SUPERVISOR.think() requires a VALEBrainState")
        t0 = mono()
        try:
            if not (self._thread and self._thread.is_alive()) and self.clock() - self.last_tick > self.cfg.tick_interval_s:
                self.tick()
            now = self.clock()
            snap = self.status()
            out: Dict[str, Any] = {"brain": self.brain_name, "version": self.VERSION, "role": self.ROLE,
                                   "status": snap["overall"], "mode": self.mode.value,
                                   "task_id": str(getattr(state, "task_id", "")),
                                   "this_task": self._task_view(state, now), "system": snap,
                                   "creates_incidents_from_this_task": False}
            v = self._voice(state, snap)
            if v:
                out["voice"] = v
            self._publish(state, out)
        except Exception as exc:
            self.telemetry.error("think", exc)
            out = {"brain": self.brain_name, "version": self.VERSION, "role": self.ROLE, "status": "SUPERVISOR_ERROR",
                   "error": f"{type(exc).__name__}: {str(exc)[:160]}"}
        finally:
            self.telemetry.observe("think", mono() - t0)
        return out

    def _publish(self, state: Any, out: Dict[str, Any]) -> None:
        try:
            state.set("supervisor_status", out["status"])
            state.set("supervisor_result", out)
            state.event("supervisor_checked", self.brain_name, payload={"overall": out["status"], "mode": self.mode.value})
        except Exception as exc:
            self.telemetry.error("publish", exc)

    def _voice(self, state: Any, snap: Dict[str, Any]) -> Optional[str]:
        if self.cfg.speak != "on_request":
            return None
        words = set(str(getattr(state, "user_message", "") or "").lower().replace("?", " ").replace(",", " ").split())
        if not (words & _HEALTH_WORDS and words & _SYSTEM_WORDS):
            return None
        o = snap["overall"]
        if o == "OK":
            return "I checked the system. I found no problems, and every brain I can see shows recent healthy activity."
        if o == "OK_PARTIAL":
            n = ", ".join(snap["no_evidence_yet"][:4])
            return f"I found no problems. Some brains look healthy. I have no recent evidence about {n}, so I cannot say those are fine."
        if o == "UNKNOWN":
            return "I have only just started watching, so I do not have enough evidence yet to say if the system is healthy."
        top = snap["incidents"]["top"][0]["summary"] if snap["incidents"]["top"] else snap["reason"]
        return (f"There is a serious problem: {top}" if o == "CRITICAL" else f"The system is running, but not fully healthy: {top}")

    # ------------------------------------------------------------------ commands from other brains
    def _c_status(self, p, src): return {"ok": True, "status": self.status()}
    def _c_incidents(self, p, src): return {"ok": True, "incidents": self.incidents(bool(p.get("active_only", True)), int(p.get("limit", 30)))}

    def _c_incident(self, p, src):
        d = self.explain(str(p.get("id", "")))
        return {"ok": True, "incident": d} if d else {"ok": False, "error": "UNKNOWN_INCIDENT"}

    def _c_component(self, p, src):
        d = self.component(str(p.get("name", "")))
        return {"ok": True, "component": d} if d else {"ok": False, "error": "UNKNOWN_COMPONENT"}

    def _c_ack(self, p, src):
        return {"ok": self.acknowledge(str(p.get("id", "")))}

    def _c_audit(self, p, src):
        return {"ok": True, "audit": self.audit.tail(int(p.get("n", 50)), str(p.get("subject", "")))}

    def _c_outbox(self, p, src):
        return {"ok": True, "outbox": [e.to_dict() for e in list(self.escalation.outbox)[-int(p.get("n", 20)):]]}

    def _c_health(self, p, src): return {"ok": True, "health": self.health()}
    def _c_contract(self, p, src): return {"ok": True, "contract": self.contract()}
    def _c_tick(self, p, src): return {"ok": True, "tick": self.tick(force_probe=bool(p.get("probe", True)))}

    def _c_probe(self, p, src):
        name = norm_name(p.get("component"))
        brain = self.registry.brain_object(name)
        if brain is None:
            return {"ok": False, "error": "UNKNOWN_COMPONENT"}
        res = self.prober.probe(brain)
        with self.lock:
            self.registry.record_probe(name, self.clock(), res)
            self.registry.derive(self.clock())
        return {"ok": True, "probe": {k: v for k, v in res.items() if k != "snapshot"}, "component": self.component(name)}

    def _c_signal(self, p, src):
        """A brain reports on itself: {"component", "kind": ok | error | heartbeat, "seconds", "error"}."""
        comp = norm_name(p.get("component") or src)
        if comp != norm_name(src) and norm_name(src) not in _AUTHORITIES:
            return {"ok": False, "error": "NOT_AUTHORISED", "detail": "a brain may only report on itself"}
        kind, now = str(p.get("kind", "")).lower(), self.clock()
        with self.lock:
            if kind == "ok":
                self.registry.record_call(comp, now, True, p.get("seconds"))
            elif kind == "error":
                self.registry.record_call(comp, now, False, p.get("seconds"), str(p.get("error", "")))
            elif kind == "heartbeat":
                c = self.registry.ensure(comp, "BRAIN", now)
                c.live, c.last_seen = True, now
            else:
                return {"ok": False, "error": "UNKNOWN_SIGNAL", "allowed": ["ok", "error", "heartbeat"]}
        self.request_tick()
        return {"ok": True}

    def _c_feed_register(self, p, src):
        return self.register_feed(str(p.get("name", "")), float(p.get("max_age_s", 60)), bool(p.get("critical", True)), tuple(p.get("dependents") or ()))

    def _c_feed_report(self, p, src):
        ts = p.get("observed_at")
        return {"ok": self.report_feed(str(p.get("name", "")), float(ts) if ts is not None else None)}

    def _c_conflict(self, p, src):
        rec, obs = self.conflicts.report(str(p.get("component", "")), list(p.get("claims") or []), self.clock())
        with self.lock:
            self._pending.extend(obs)
        self.request_tick()
        return {"ok": True, "conflict": rec, "escalated": bool(obs)}

    def _c_release_hold(self, p, src):
        if norm_name(src) not in _AUTHORITIES:
            return {"ok": False, "error": "NOT_AUTHORISED"}
        r = str(p.get("resource", ""))
        existed = self.holds.pop(r, None) is not None
        self.audit.add(self.clock(), "hold_released", r, f"by {src}")
        return {"ok": existed}

    def _c_recover(self, p, src):
        if norm_name(src) not in _AUTHORITIES:
            return {"ok": False, "error": "NOT_AUTHORISED", "detail": "only UNITY, HEROIC or an operator may request recovery"}
        name = norm_name(p.get("component"))
        c = self.registry.components.get(name)
        if c is None:
            return {"ok": False, "error": "UNKNOWN_COMPONENT"}
        act = PlannedAction(AK.RESTORE_BRAIN.value if c.breaker != Breaker.CLOSED.value else AK.RESET_BRAIN.value, name, f"requested by {src}")
        allowed, why = self.policy.authorize(act, self.mode, self.clock())
        if not allowed:
            return {"ok": False, "error": "REFUSED", "detail": why}
        rec = self.recovery.execute(act)
        ver = self.verifier.verify(rec, act)
        self.policy.record(act, rec.ended)
        self.audit.add(rec.ended, "recover_requested", name, f"{act.kind} by {src}: ok={rec.ok} verified={ver['ok'] if ver else None}")
        return {"ok": bool(rec.ok), "action": rec.to_dict(), "verification": ver}

    _COMMANDS = {
        "status": "_c_status", "incidents": "_c_incidents", "incident": "_c_incident", "explain": "_c_incident",
        "component": "_c_component", "ack": "_c_ack", "audit": "_c_audit", "outbox": "_c_outbox", "health": "_c_health",
        "contract": "_c_contract", "tick": "_c_tick", "probe": "_c_probe", "signal": "_c_signal",
        "feed_register": "_c_feed_register", "feed_report": "_c_feed_report", "conflict": "_c_conflict",
        "release_hold": "_c_release_hold", "recover": "_c_recover",
    }

    def receive_message(self, message: str, state: Any, source_brain: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload if isinstance(payload, dict) else {}
        cmd = str(payload.get("type") or payload.get("command") or "").lower()
        base: Dict[str, Any] = {"brain": self.brain_name, "received": True, "from": source_brain, "message": message,
                                "command": cmd or None}
        if not cmd:
            return {**base, "ok": True, "note": "message recorded; no command was given"}
        name = self._COMMANDS.get(cmd)
        if name is None:
            return {**base, "ok": False, "error": "UNKNOWN_COMMAND", "allowed": sorted(self._COMMANDS)}
        t0 = mono()
        try:
            out = getattr(self, name)(payload, str(source_brain or ""))
        except Exception as exc:
            self.telemetry.error("receive_message", exc)
            out = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:160]}
        finally:
            self.telemetry.observe("receive_message", mono() - t0)
        return {**base, **out}

    # ================================================================== health, contract, identity, export
    def health(self) -> Dict[str, Any]:
        return build_health(self)

    def contract(self) -> Dict[str, Any]:
        return build_contract(self)

    def export(self) -> Dict[str, Any]:
        with self.lock:
            return {"status": self.status(), "components": [c.to_dict() for c in self.registry.components.values()],
                    "incidents_active": [i.to_dict(full=True) for i in self.store.active()],
                    "incidents_recent": [i.to_dict() for i in self.store.recent_resolved(30)],
                    "escalations": [e.to_dict() for e in list(self.escalation.sent)[-30:]],
                    "conflicts": list(self.conflicts.log)[-20:], "audit": self.audit.tail(100),
                    "telemetry": self.telemetry.snapshot()}

    def reset(self) -> Dict[str, Any]:
        n = self.recovery.uninstall_guards()
        with self.lock:
            cleared = self.store.clear()
            self.holds.clear()
            self._pending = []
            self.scanner = TaskScanner(self.cfg)
        return {"ok": True, "incidents_cleared": cleared, "guards_removed": n}

    def identity(self) -> Dict[str, Any]:
        try:
            base = super().identity()
        except Exception:
            base = {"brain": self.brain_name}
        base.update({
            "version": self.VERSION, "role": self.ROLE, "architecture_stage": self.ARCHITECTURE_STAGE,
            "central_question": "Is VALE operating correctly, and if not, what safe operational response is required?",
            "one_line_rule": "SUPERVISOR does not make VALE intelligent; it protects the reliable operation of the intelligence VALE already has.",
            "mode": self.mode.value, "rules": list(self.RULES),
            "engines": ["collector", "health_registry", "heartbeat_prober", "detector", "state_monitor", "communication_monitor",
                        "data_integrity_monitor", "feed_monitor", "conflict_manager", "policy_guard", "recovery_controller",
                        "circuit_breaker", "verification_engine", "escalation_manager", "incident_store", "audit_log"],
            "changes_the_system": self.mode == Mode.ENFORCE})
        return base

