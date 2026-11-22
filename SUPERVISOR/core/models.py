"""SUPERVISOR records."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

from .enums import Breaker, ComponentState, IncidentStatus
from .util import iso


@dataclass(slots=True)
class Component:
    name: str
    kind: str                                   # BRAIN | NETWORK | PROCESS | DATASOURCE | FEED
    core: bool = False
    state: ComponentState = ComponentState.UNKNOWN
    reason: str = "no evidence yet"
    registered: bool = True
    expected: bool = False
    live: Optional[bool] = None
    ready: Optional[bool] = None
    first_seen: float = 0.0
    last_seen: float = 0.0
    last_ok: float = 0.0
    last_error: float = 0.0
    calls: int = 0
    errors: int = 0
    blocked: int = 0
    consec_fail: int = 0
    consec_ok: int = 0
    latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=50))
    recent_errors: Deque[Tuple[float, str]] = field(default_factory=lambda: deque(maxlen=8))
    recent_calls: Deque[Tuple[float, float, bool]] = field(default_factory=lambda: deque(maxlen=50))
    inflight: Dict[str, float] = field(default_factory=dict)
    probe: Dict[str, Any] = field(default_factory=dict)
    probe_ts: float = 0.0
    probe_ok: Optional[bool] = None
    probe_error: str = ""
    coverage: Dict[str, bool] = field(default_factory=dict)
    guard: bool = False
    breaker: str = Breaker.CLOSED.value
    breaker_opened: float = 0.0
    breaker_open_s: float = 60.0
    breaker_trips: int = 0
    half_open_busy: bool = False
    last_reset: float = 0.0

    def p95(self) -> Optional[float]:
        if len(self.latencies) < 5:
            return None
        data = sorted(self.latencies)
        return data[int(round(0.95 * (len(data) - 1)))]

    def to_dict(self) -> Dict[str, Any]:
        p95 = self.p95()
        return {"name": self.name, "kind": self.kind, "core": self.core, "state": self.state.value,
                "reason": self.reason, "registered": self.registered, "live": self.live, "ready": self.ready,
                "calls": self.calls, "errors": self.errors, "consecutive_failures": self.consec_fail,
                "p95_ms": round(p95 * 1000, 2) if p95 is not None else None,
                "last_ok": iso(self.last_ok) if self.last_ok else None,
                "last_error": iso(self.last_error) if self.last_error else None,
                "breaker": self.breaker, "guarded": self.guard,
                "coverage": dict(self.coverage), "in_flight": len(self.inflight)}


@dataclass(slots=True)
class Observation:
    """One fact the detectors found on a tick. The incident store turns it into an incident."""
    type: str
    component: str
    signature: str
    severity: str
    summary: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    scope: List[str] = field(default_factory=list)
    destination: str = "UNITY"                  # where it is escalated if it must be
    first_evidence_ts: float = 0.0


@dataclass(slots=True)
class PlannedAction:
    kind: str
    target: str
    reason: str
    params: Dict[str, Any] = field(default_factory=dict)
    destination: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "target": self.target, "reason": self.reason, "destination": self.destination}


@dataclass(slots=True)
class ActionRecord:
    id: str
    kind: str
    target: str
    started: float
    ended: float = 0.0
    executed: bool = False
    allowed: bool = True
    ok: Optional[bool] = None                   # None = not executed or not known
    detail: str = ""
    verification: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "target": self.target, "at": iso(self.started),
                "executed": self.executed, "allowed": self.allowed, "ok": self.ok, "detail": self.detail,
                "verification": self.verification}


@dataclass(slots=True)
class Incident:
    id: str
    type: str
    component: str
    signature: str
    severity: str
    summary: str
    status: IncidentStatus = IncidentStatus.DETECTED
    scope: List[str] = field(default_factory=list)
    evidence: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=5))
    action_plan: List[PlannedAction] = field(default_factory=list)
    actions: List[ActionRecord] = field(default_factory=list)
    verification: List[Dict[str, Any]] = field(default_factory=list)
    detected_at: float = 0.0
    first_evidence_ts: float = 0.0
    last_seen: float = 0.0
    resolved_at: float = 0.0
    occurrences: int = 1
    clear_streak: int = 0
    destination: str = "UNITY"
    escalated_to: List[str] = field(default_factory=list)
    resolution: str = ""
    acknowledged: bool = False
    trail: Deque[Tuple[float, str, str]] = field(default_factory=lambda: deque(maxlen=40))

    @property
    def key(self) -> Tuple[str, str, str]:
        return (self.type, self.component, self.signature)

    def to_dict(self, full: bool = False) -> Dict[str, Any]:
        d = {"id": self.id, "type": self.type, "component": self.component, "signature": self.signature,
             "severity": self.severity, "status": self.status.value, "summary": self.summary,
             "scope": list(self.scope), "detected_at": iso(self.detected_at), "last_seen": iso(self.last_seen),
             "occurrences": self.occurrences, "escalated_to": list(self.escalated_to),
             "resolution": self.resolution, "acknowledged": self.acknowledged,
             "resolved_at": iso(self.resolved_at) if self.resolved_at else None,
             "detection_delay_s": round(max(0.0, self.detected_at - self.first_evidence_ts), 3)
             if self.first_evidence_ts else None}
        if full:
            d.update({"evidence": list(self.evidence), "action_plan": [a.to_dict() for a in self.action_plan],
                      "actions_attempted": [a.to_dict() for a in self.actions],
                      "verification": list(self.verification),
                      "audit_trail": [{"at": iso(t), "event": e, "detail": x} for t, e, x in self.trail]})
        return d


@dataclass(slots=True)
class Escalation:
    id: str
    incident: str
    destination: str
    severity: str
    summary: str
    at: float
    delivered: Optional[bool] = None
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "incident": self.incident, "destination": self.destination,
                "severity": self.severity, "summary": self.summary, "at": iso(self.at),
                "delivered": self.delivered, "note": self.note}
