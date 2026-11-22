"""Recovery controller: the bounded, approved actions, and the circuit breaker that isolates a failing brain.

Nothing here runs unless the policy guard allows it. In ADVISORY mode no guard is installed on any brain.
"""
from __future__ import annotations

import gc
import time
from typing import Any, Dict, Optional, Tuple

from ..core.enums import ActionKind as AK, Breaker
from ..core.models import ActionRecord, PlannedAction
from ..core.util import clip, parse_iso

TRANSIENT = (TimeoutError, ConnectionError, OSError)


class BrainIsolatedError(RuntimeError):
    """Raised instead of calling a brain that SUPERVISOR has isolated. The network records it like any brain error."""


class GuardedThink:
    __slots__ = ("rc", "name", "orig")

    def __init__(self, rc: "RecoveryController", name: str, orig: Any) -> None:
        self.rc, self.name, self.orig = rc, name, orig

    def __call__(self, state: Any) -> Any:
        return self.rc.guarded_call(self.name, self.orig, state)


class RecoveryController:
    def __init__(self, sup: Any) -> None:
        self.sup = sup
        self._guards: Dict[str, Tuple[Any, Any, GuardedThink]] = {}
        self.retries = 0

    # ------------------------------------------------------------------ guards (ENFORCE only)
    def install_guard(self, name: str) -> bool:
        sup = self.sup
        brain = sup.registry.brain_object(name)
        if brain is None or name in self._guards or name == "SUPERVISOR":
            return name in self._guards
        orig = getattr(brain, "think", None)
        if not callable(orig):
            return False
        g = GuardedThink(self, name, orig)
        try:
            brain.think = g
        except Exception:
            return False
        self._guards[name] = (brain, orig, g)
        with sup.lock:
            sup.registry.ensure(name).guard = True
        sup.audit.add(sup.clock(), "guard_installed", name)
        return True

    def install_guards(self) -> int:
        n = 0
        for name in list(self.sup.registry.components):
            c = self.sup.registry.components[name]
            if c.kind == "BRAIN" and c.registered and self.install_guard(name):
                n += 1
        return n

    def uninstall_guards(self) -> int:
        n = 0
        for name, (brain, orig, g) in list(self._guards.items()):
            try:
                if brain.__dict__.get("think") is g:
                    del brain.__dict__["think"]
                else:
                    brain.think = orig
            except Exception:
                pass
            with self.sup.lock:
                c = self.sup.registry.components.get(name)
                if c is not None:
                    c.guard, c.breaker, c.half_open_busy = False, Breaker.CLOSED.value, False
            self._guards.pop(name, None)
            n += 1
        if n:
            self.sup.audit.add(self.sup.clock(), "guards_removed", "ALL", f"{n} guard(s) removed, breakers closed")
        return n

    # ------------------------------------------------------------------ the call path
    def guarded_call(self, name: str, orig: Any, state: Any) -> Any:
        sup, cfg = self.sup, self.sup.cfg
        allow, why = self.before_call(name)
        if not allow:
            with sup.lock:
                sup.registry.ensure(name).blocked += 1
            raise BrainIsolatedError(f"{name} is isolated by SUPERVISOR: {why}")
        tid = str(getattr(state, "task_id", "") or f"call-{id(state)}")
        attempt = 0
        while True:
            t0 = sup.clock()
            with sup.lock:
                sup.registry.begin_call(name, tid, t0)
            try:
                result = orig(state)
            except Exception as exc:
                t1 = sup.clock()
                with sup.lock:
                    sup.registry.end_call(name, tid)
                if attempt < cfg.retry_max and isinstance(exc, TRANSIENT) and self._retry_ok(name):
                    attempt += 1
                    self.retries += 1
                    sup.audit.add(t1, "retry", name, f"transient {type(exc).__name__}; attempt {attempt} of {cfg.retry_max}")
                    time.sleep(cfg.retry_backoff_s * attempt)
                    continue
                with sup.lock:
                    sup.registry.record_call(name, t1, False, t1 - t0, f"{type(exc).__name__}: {exc}")
                    sup.registry.mark_guard_seen(tid, name)
                self.after_call(name, False)
                raise
            except BaseException:
                with sup.lock:
                    sup.registry.end_call(name, tid)
                raise
            t1 = sup.clock()
            with sup.lock:
                sup.registry.end_call(name, tid)
                sup.registry.record_call(name, t1, True, t1 - t0)
                sup.registry.mark_guard_seen(tid, name)
            self.after_call(name, True)
            return result

    def _retry_ok(self, name: str) -> bool:
        brain = self.sup.registry.brain_object(name)
        return getattr(brain, "IDEMPOTENT", True) is not False

    def before_call(self, name: str) -> Tuple[bool, str]:
        sup, cfg = self.sup, self.sup.cfg
        with sup.lock:
            c, now = sup.registry.ensure(name), sup.clock()
            if c.breaker == Breaker.CLOSED.value:
                return True, ""
            if c.breaker == Breaker.OPEN.value:
                left = c.breaker_open_s - (now - c.breaker_opened)
                if left <= 0:
                    c.breaker, c.half_open_busy = Breaker.HALF_OPEN.value, True
                    sup.audit.add(now, "breaker_half_open", name, "one trial call allowed")
                    return True, "trial call"
                return False, f"circuit breaker open for another {left:.0f}s"
            if not c.half_open_busy:
                c.half_open_busy = True
                return True, "trial call"
            return False, "a trial call is already running"

    def after_call(self, name: str, ok: bool) -> None:
        sup, cfg = self.sup, self.sup.cfg
        trip = False
        with sup.lock:
            c, now = sup.registry.ensure(name), sup.clock()
            if c.breaker == Breaker.HALF_OPEN.value:
                c.half_open_busy = False
                if ok:
                    c.breaker, c.breaker_open_s, c.consec_fail = Breaker.CLOSED.value, cfg.breaker_open_s, 0
                    sup.audit.add(now, "breaker_closed", name, "trial call succeeded")
                else:
                    c.breaker, c.breaker_opened = Breaker.OPEN.value, now
                    c.breaker_open_s = min(c.breaker_open_s * 2, cfg.breaker_max_open_s)
                    sup.audit.add(now, "breaker_reopened", name, f"trial call failed; open for {c.breaker_open_s:.0f}s")
                return
            trip = (not ok) and c.consec_fail >= cfg.breaker_failures and c.breaker == Breaker.CLOSED.value
        if trip:
            sup.isolate(name, f"{cfg.breaker_failures} failed calls in a row")

    def would_block(self, name: str) -> bool:
        c = self.sup.registry.components.get(name)
        return bool(c and c.breaker == Breaker.OPEN.value and self.sup.clock() - c.breaker_opened < c.breaker_open_s)

    # ------------------------------------------------------------------ actions
    def execute(self, act: PlannedAction, inc: Any = None) -> ActionRecord:
        sup = self.sup
        rec = ActionRecord(id=sup.next_id("act"), kind=act.kind, target=act.target, started=sup.clock())
        facts: Dict[str, Any] = {}
        try:
            kind = AK(act.kind)
            if kind == AK.RESET_BRAIN:
                rec.ok, rec.detail = self._reset(act.target)
            elif kind == AK.ISOLATE_BRAIN:
                rec.ok, rec.detail = self._isolate(act.target)
            elif kind == AK.RESTORE_BRAIN:
                rec.ok, rec.detail = self._restore(act.target)
            elif kind == AK.PRUNE_TASKS:
                rec.ok, rec.detail = self._prune(facts)
            elif kind == AK.GC_COLLECT:
                rec.ok, rec.detail = self._gc(facts)
            elif kind == AK.HOLD:
                sup.holds[act.target] = {"since": rec.started, "reason": act.reason, "scope": act.params.get("scope", [])}
                rec.ok, rec.detail = True, f"hold set on {act.target}: dependent work should wait"
            elif kind == AK.RELEASE_HOLD:
                sup.holds.pop(act.target, None)
                rec.ok, rec.detail = True, f"hold released on {act.target}"
            elif kind in (AK.NOTIFY, AK.ESCALATE):
                e = sup.escalation.deliver(inc, act.destination or "UNITY", act.reason, rec.started, force=True) if inc else None
                rec.ok = None if e is None else e.delivered
                rec.detail = "suppressed (rate limit or cooldown)" if e is None else (e.note or "delivered")
            else:
                rec.ok, rec.detail = False, f"unsupported action {act.kind}"
            rec.executed = True
        except Exception as exc:
            rec.executed, rec.ok = True, False
            rec.detail = clip(f"{type(exc).__name__}: {exc}", 200)
        rec.ended = sup.clock()
        rec.verification = {"facts": facts} if facts else None
        return rec

    def _reset(self, name: str) -> Tuple[bool, str]:
        brain = self.sup.registry.brain_object(name)
        reset = getattr(brain, "reset", None)
        if not callable(reset):
            return False, "the brain has no reset() recovery hook"
        out = reset()
        with self.sup.lock:
            self.sup.registry.ensure(name).last_reset = self.sup.clock()
        return True, f"reset() returned {clip(out, 80)}"

    def _isolate(self, name: str) -> Tuple[bool, str]:
        sup, cfg = self.sup, self.sup.cfg
        if not self.install_guard(name):
            return False, "a guard could not be installed on this brain"
        with sup.lock:
            c, now = sup.registry.ensure(name), sup.clock()
            c.breaker_trips += 1
            c.breaker_open_s = min(cfg.breaker_open_s * (2 ** min(c.breaker_trips - 1, 4)), cfg.breaker_max_open_s)
            c.breaker, c.breaker_opened, c.half_open_busy = Breaker.OPEN.value, now, False
        return True, f"circuit breaker open for {c.breaker_open_s:.0f}s: calls are refused instead of failing slowly"

    def _restore(self, name: str) -> Tuple[bool, str]:
        with self.sup.lock:
            c = self.sup.registry.ensure(name)
            c.breaker, c.half_open_busy, c.consec_fail = Breaker.CLOSED.value, False, 0
        return True, "circuit breaker closed"

    def _prune(self, facts: Dict[str, Any]) -> Tuple[bool, str]:
        sup, cfg = self.sup, self.sup.cfg
        net = sup.network
        tasks, close = getattr(net, "tasks", None), getattr(net, "close_task", None)
        if tasks is None or not callable(close):
            return False, "the network has no task registry or no close_task()"
        lock = getattr(net, "_lock", None)
        if lock is not None:
            with lock:
                ids = list(tasks.keys())
        else:
            ids = list(tasks.keys())
        busy = {tid for c in sup.registry.components.values() for tid in c.inflight}
        candidates = ids[:-cfg.tasks_keep] if cfg.tasks_keep > 0 else ids
        now, closed = sup.clock(), 0
        for tid in candidates:
            st = tasks.get(tid)
            if st is None or tid in busy:
                continue
            created = parse_iso(getattr(st, "created_at", None))
            if created is None or now - created < cfg.tasks_prune_age_s:
                continue
            close(tid)
            closed += 1
        facts.update({"before": len(ids), "after": len(tasks), "closed": closed})
        return True, f"closed {closed} finished task states older than {cfg.tasks_prune_age_s:.0f}s; the newest {cfg.tasks_keep} are kept"

    def _gc(self, facts: Dict[str, Any]) -> Tuple[bool, str]:
        before = self.sup.sampler.sample().get("rss_mb")
        collected = gc.collect()
        after = self.sup.sampler.sample().get("rss_mb")
        facts.update({"rss_before": before, "rss_after": after, "objects_collected": collected})
        return True, f"gc.collect() freed {collected} objects"
