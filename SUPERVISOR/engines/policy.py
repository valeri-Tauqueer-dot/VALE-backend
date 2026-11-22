"""Policy and permission guard.

Plans which actions suit an incident, and decides whether each one may run. Least privilege: in ADVISORY mode
nothing that changes the system is allowed. Every action is also limited by a budget and a cooldown, so recovery
can never turn into an endless loop.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from ..core.config import SupervisorConfig
from ..core.enums import ActionKind as AK, IncidentType as T, MUTATING, Mode, sev_rank
from ..core.models import Component, Incident, PlannedAction
from ..core.store import AuditLog


class PolicyGuard:
    def __init__(self, cfg: SupervisorConfig, audit: AuditLog) -> None:
        self.cfg, self.audit = cfg, audit
        self._exec: Deque[Tuple[float, str]] = deque(maxlen=200)
        self._last: Dict[Tuple[str, str], float] = {}

    # ------------------------------------------------------------------ what could help
    def plan(self, inc: Incident, comp: Optional[Component]) -> List[PlannedAction]:
        cfg, sev, sig, t = self.cfg, sev_rank(inc.severity), inc.signature, inc.type
        A: List[PlannedAction] = []

        def add(kind: AK, target: str, reason: str, dest: str = "", **params) -> None:
            A.append(PlannedAction(kind.value, target, reason, dict(params), dest))

        name = inc.component
        if t == T.HEALTH.value and sig == "consecutive_failures":
            if sev >= 2 and comp is not None and comp.coverage.get("recovery_hook"):
                add(AK.RESET_BRAIN, name, "the brain exposes a recovery hook (reset) and keeps failing")
            if comp is not None and comp.consec_fail >= cfg.breaker_failures:
                add(AK.ISOLATE_BRAIN, name, f"{comp.consec_fail} failures in a row: stop sending work to it")
            if sev >= 2:
                add(AK.NOTIFY, name, "missions that depend on this brain must plan without it", "UNITY" if comp is not None and comp.core else "HEROIC")
        elif t == T.HEALTH.value and sig in ("probe_failed", "not_ready"):
            if comp is not None and comp.coverage.get("recovery_hook") and sig == "probe_failed":
                add(AK.RESET_BRAIN, name, "health probe failed and a recovery hook exists")
            add(AK.NOTIFY, name, "the brain is not ready", "UNITY" if comp is not None and comp.core else "HEROIC")
        elif t == T.HEALTH.value:                                   # not_registered, selected_but_unregistered
            add(AK.NOTIFY, name, "the brain is missing from the network", "UNITY")
            add(AK.NOTIFY, name, "plans must not rely on a missing brain", "HEROIC")
        elif t == T.TIMEOUT.value and sig == "stalled_call":
            add(AK.NOTIFY, name, "a call is not finishing; it cannot be stopped from here", "UNITY")
            add(AK.ESCALATE, name, "a possible hang needs a person to look at it", "OPERATOR")
        elif t == T.TIMEOUT.value:
            add(AK.NOTIFY, name, "slow answers affect mission timing", "HEROIC")
        elif t == T.RESOURCE.value and sig == "task_registry_growth":
            add(AK.PRUNE_TASKS, "NETWORK", "finished task states can be closed to free memory")
            add(AK.GC_COLLECT, "PROCESS", "release unused memory")
            if sev >= 2:
                add(AK.ESCALATE, "NETWORK", "task states keep piling up", "OPERATOR")
        elif t == T.RESOURCE.value and sig in ("memory_pressure", "memory_growth"):
            add(AK.GC_COLLECT, "PROCESS", "release unused memory")
            add(AK.PRUNE_TASKS, "NETWORK", "finished task states can be closed to free memory")
            if sev >= 2:
                add(AK.ESCALATE, "PROCESS", "memory is a risk to the whole system", "OPERATOR")
        elif t == T.RESOURCE.value:
            if sev >= 1:
                add(AK.ESCALATE, name, inc.summary, "OPERATOR")
        elif t == T.DATA_INTEGRITY.value:
            if sig == "stale_feed" and sev >= 2:
                add(AK.HOLD, name, "stale critical input: dependent work must not proceed on it", scope=list(inc.scope))
            add(AK.NOTIFY, name, "data quality needs checking", "COGNITIVE")
            if sig in ("stale_feed", "provider_unavailable", "search_error") and sev >= 1:
                add(AK.NOTIFY, name, "missions that need this data must wait or say so", "HEROIC")
        elif t in (T.COMMUNICATION.value, T.STATE_CONFLICT.value):
            add(AK.NOTIFY, name, "an integration problem", "UNITY")
        elif t == T.SECURITY.value:
            add(AK.ESCALATE, name, "security-sensitive events are escalated, never acted on automatically", "OPERATOR")
        return A

    # ------------------------------------------------------------------ may it run?
    def authorize(self, act: PlannedAction, mode: Mode, now: float) -> Tuple[bool, str]:
        kind = AK(act.kind)
        if kind == AK.ROLLBACK:
            return False, "refused: no versioned rollback controls exist in this system"
        if kind not in MUTATING:
            return True, "ok"
        if mode != Mode.ENFORCE:
            return False, "ADVISORY mode: recommended, not executed"
        recent = sum(1 for ts, k in self._exec if now - ts <= self.cfg.budget_window_s)
        if recent >= self.cfg.action_budget:
            return False, f"refused: action budget used up ({recent} actions in {self.cfg.budget_window_s:.0f}s)"
        last = self._last.get((act.kind, act.target))
        if last is not None and now - last < self.cfg.cooldown_s:
            return False, f"refused: cooldown, last {act.kind} on {act.target} was {now - last:.0f}s ago"
        return True, "ok"

    def record(self, act: PlannedAction, now: float) -> None:
        if AK(act.kind) in MUTATING:
            self._exec.append((now, act.kind))
            self._last[(act.kind, act.target)] = now
