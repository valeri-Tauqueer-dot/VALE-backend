"""Incident store and audit log. Both are bounded, so they can never grow without limit."""
from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from .config import SupervisorConfig
from .enums import ACTIVE_STATUSES, IncidentStatus as S, sev_max, sev_rank
from .models import Incident, Observation
from .util import iso

_ALLOWED = {
    S.DETECTED: {S.INVESTIGATING, S.CONTAINED, S.RECOVERING, S.ESCALATED, S.RESOLVED, S.UNRESOLVED},
    S.INVESTIGATING: {S.CONTAINED, S.RECOVERING, S.ESCALATED, S.RESOLVED, S.UNRESOLVED},
    S.CONTAINED: {S.RECOVERING, S.VERIFYING, S.ESCALATED, S.RESOLVED, S.UNRESOLVED},
    S.RECOVERING: {S.CONTAINED, S.VERIFYING, S.ESCALATED, S.UNRESOLVED, S.RESOLVED},
    S.VERIFYING: {S.RESOLVED, S.RECOVERING, S.ESCALATED, S.UNRESOLVED},
    S.ESCALATED: {S.CONTAINED, S.RECOVERING, S.VERIFYING, S.RESOLVED, S.UNRESOLVED},
    S.UNRESOLVED: {S.RECOVERING, S.VERIFYING, S.RESOLVED, S.ESCALATED},
    S.RESOLVED: set(),
}


class AuditLog:
    def __init__(self, size: int) -> None:
        self._d: Deque[Dict[str, Any]] = deque(maxlen=max(100, size))

    def add(self, ts: float, kind: str, subject: str, detail: str = "") -> None:
        self._d.append({"ts": ts, "at": iso(ts), "kind": kind, "subject": subject, "detail": detail[:240]})

    def tail(self, n: int = 50, subject: str = "") -> List[Dict[str, Any]]:
        rows = [r for r in self._d if not subject or subject in r["subject"] or subject in r["kind"]]
        return rows[-n:]

    def __len__(self) -> int:
        return len(self._d)


class IncidentStore:
    def __init__(self, cfg: SupervisorConfig, audit: AuditLog) -> None:
        self.cfg, self.audit = cfg, audit
        self._active: Dict[Tuple[str, str, str], Incident] = {}
        self._by_id: Dict[str, Incident] = {}
        self._resolved: Deque[Incident] = deque(maxlen=cfg.incident_keep)
        self._seq = 0
        self.dropped = 0

    # ------------------------------------------------------------------ lifecycle
    def observe(self, obs: Observation, now: float) -> Tuple[Incident, bool]:
        key = (obs.type, obs.component, obs.signature)
        inc = self._active.get(key)
        if inc is not None:
            inc.occurrences += 1
            inc.last_seen = now
            inc.clear_streak = 0
            inc.summary = obs.summary
            inc.evidence.append({"at": iso(now), **obs.evidence})
            if sev_rank(obs.severity) > sev_rank(inc.severity):
                self._note(inc, now, "severity_raised", f"{inc.severity} -> {obs.severity}")
                inc.severity = obs.severity
            for s in obs.scope:
                if s not in inc.scope:
                    inc.scope.append(s)
            return inc, False
        self._seq += 1
        inc = Incident(id=f"inc-{self._seq}", type=obs.type, component=obs.component, signature=obs.signature,
                       severity=obs.severity, summary=obs.summary, scope=list(obs.scope), detected_at=now,
                       first_evidence_ts=obs.first_evidence_ts or now, last_seen=now, destination=obs.destination)
        inc.evidence.append({"at": iso(now), **obs.evidence})
        self._note(inc, now, "detected", f"{obs.severity}: {obs.summary}")
        self._active[key] = inc
        self._by_id[inc.id] = inc
        self.audit.add(now, "incident_detected", inc.id, f"{obs.severity} {obs.type}/{obs.component}: {obs.summary}")
        if len(self._active) > self.cfg.max_active:
            self._drop_least_important(now)
        return inc, True

    def _drop_least_important(self, now: float) -> None:
        victim = min(self._active.values(), key=lambda i: (sev_rank(i.severity), i.last_seen))
        self._active.pop(victim.key, None)
        self._by_id.pop(victim.id, None)
        self.dropped += 1
        self.audit.add(now, "incident_dropped", victim.id, "active incident limit reached; lowest severity dropped")

    def _note(self, inc: Incident, now: float, event: str, detail: str) -> None:
        inc.trail.append((now, event, detail[:160]))

    def transition(self, inc: Incident, status: IncidentStatus, now: float, why: str = "") -> bool:
        if inc.status == status:
            return True
        if status not in _ALLOWED[inc.status]:
            self.audit.add(now, "transition_refused", inc.id, f"{inc.status.value}->{status.value}")
            return False
        self._note(inc, now, f"{inc.status.value}->{status.value}", why)
        self.audit.add(now, "incident_status", inc.id, f"{inc.status.value}->{status.value} {why}")
        inc.status = status
        return True

    def resolve(self, inc: Incident, now: float, how: str, evidence: Optional[Dict[str, Any]] = None) -> bool:
        if inc.status == S.RESOLVED:
            return True
        if not self.transition(inc, S.RESOLVED, now, how):
            if inc.status in (S.DETECTED, S.INVESTIGATING, S.CONTAINED, S.RECOVERING, S.VERIFYING, S.ESCALATED, S.UNRESOLVED):
                return False
        inc.resolved_at, inc.resolution = now, how
        if evidence:
            inc.verification.append({"at": iso(now), "ok": True, **evidence})
        self._active.pop(inc.key, None)
        self._resolved.append(inc)
        return True

    def tick_clear(self, observed: set, checked: set, now: float) -> List[Incident]:
        """Incidents whose condition was checked this tick and was not seen. Returns those ready to be resolved."""
        ready: List[Incident] = []
        for key, inc in list(self._active.items()):
            t, comp, sig = key
            if key in observed or not (checked & {(t, comp), (t, "*"), (t, comp, sig), (t, "*", sig)}):
                continue
            inc.clear_streak += 1
            if inc.clear_streak >= self.cfg.clear_ticks:
                ready.append(inc)
        return ready

    # ------------------------------------------------------------------ queries
    def find(self, type_: str, component: str, signature: str) -> Optional[Incident]:
        return self._active.get((type_, component, signature))

    def active(self) -> List[Incident]:
        return sorted(self._active.values(), key=lambda i: (-sev_rank(i.severity), i.detected_at))

    def recent_resolved(self, n: int = 20) -> List[Incident]:
        return list(self._resolved)[-n:]

    def get(self, incident_id: str) -> Optional[Incident]:
        inc = self._by_id.get(incident_id)
        if inc is not None:
            return inc
        for r in self._resolved:
            if r.id == incident_id:
                return r
        return None

    def counts(self) -> Dict[str, int]:
        out = {s: 0 for s in ("INFORMATIONAL", "WARNING", "HIGH", "CRITICAL")}
        for i in self._active.values():
            out[i.severity] += 1
        return out

    def clear(self) -> int:
        n = len(self._active)
        self._active.clear()
        self._by_id.clear()
        self._resolved.clear()
        return n

    def __len__(self) -> int:
        return len(self._active)
