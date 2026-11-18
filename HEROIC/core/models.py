"""HEROIC records. Slotted dataclasses: small in memory and fast to create."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

from .enums import Decision, Gap, InfoState, MissionState, Outcome, PlanState, PlanType, TaskState
from .util import now_ns


@dataclass(frozen=True, slots=True)
class IntentProfile:
    text: str
    subject: str
    mission_type: str
    domains: Tuple[str, ...]
    secondary_types: Tuple[str, ...]
    clarity: float                      # heuristic strength of the language evidence, NOT a probability
    ambiguity: Tuple[str, ...]
    implicit: Tuple[str, ...]
    time_sensitive: bool
    entities: Tuple[Tuple[str, str], ...]
    constraints: Tuple[Tuple[str, str], ...]
    hypotheses: Tuple[str, ...]
    sub_intents: Tuple[Tuple[str, str], ...]
    emotional: bool
    crisis: bool
    follow_up: bool
    conflicts: Tuple[str, ...]
    token_count: int
    tokens: frozenset

    def has_domain(self, name: str) -> bool:
        return name in self.domains

    def entity(self, kind: str) -> Optional[str]:
        for k, v in self.entities:
            if k == kind:
                return v
        return None

    def constraint(self, kind: str) -> Optional[str]:
        for k, v in self.constraints:
            if k == kind:
                return v
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_type": self.mission_type, "secondary_types": list(self.secondary_types),
            "domains": list(self.domains), "subject": self.subject, "clarity": round(self.clarity, 3),
            "ambiguity": list(self.ambiguity), "implicit": list(self.implicit),
            "time_sensitive": self.time_sensitive, "entities": [list(e) for e in self.entities],
            "constraints": [list(c) for c in self.constraints], "hypotheses": list(self.hypotheses),
            "sub_intents": [list(s) for s in self.sub_intents], "emotional": self.emotional,
            "crisis": self.crisis, "follow_up": self.follow_up, "conflicts": list(self.conflicts),
        }


@dataclass(slots=True)
class SuccessCondition:
    kind: str      # TASKS_DONE | INFO_OK | CLAIMS_VERIFIED | DELIVERED | AUTHORIZED | NO_OPEN_CONFLICT
    text: str
    met: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "text": self.text, "met": self.met}


@dataclass(slots=True)
class Objective:
    id: str
    text: str
    kind: str                           # PRIMARY | SECONDARY | PREREQUISITE
    priority: str = "NORMAL"
    success: List[SuccessCondition] = field(default_factory=list)
    prereq: List[str] = field(default_factory=list)
    status: str = "OPEN"                # OPEN | MET | DROPPED
    fp: str = ""
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "text": self.text, "kind": self.kind, "priority": self.priority,
                "status": self.status, "version": self.version, "prereq": list(self.prereq),
                "success": [s.to_dict() for s in self.success]}


@dataclass(slots=True)
class Task:
    id: str
    key: str
    name: str
    description: str
    kind: str
    capability: str
    target: Optional[str] = None
    degraded: bool = False
    priority: str = "NORMAL"
    serves: Tuple[str, ...] = ()
    deps: List[str] = field(default_factory=list)
    soft_deps: List[str] = field(default_factory=list)
    needs: Tuple[str, ...] = ()          # information keys that must be available before this task is READY
    produces: Tuple[str, ...] = ()       # information keys this task makes available when it completes
    state: TaskState = TaskState.PENDING
    mandatory: bool = True
    cost: float = 1.0                    # relative cost units, not seconds
    level: int = 0
    expected_output: str = ""
    criteria: Tuple[str, ...] = ()
    verification: bool = False
    fp: str = ""
    attempts: int = 0
    started_ns: int = 0
    ended_ns: int = 0
    result: Optional[str] = None
    failure: Optional[str] = None
    blocked_by: List[str] = field(default_factory=list)
    note: str = ""
    preserved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "key": self.key, "name": self.name, "description": self.description,
            "kind": self.kind, "capability": self.capability, "target": self.target,
            "degraded": self.degraded, "state": self.state.value, "priority": self.priority,
            "mandatory": self.mandatory, "serves": list(self.serves), "deps": list(self.deps),
            "soft_deps": list(self.soft_deps), "needs": list(self.needs), "produces": list(self.produces),
            "level": self.level, "relative_cost": self.cost, "expected_output": self.expected_output,
            "criteria": list(self.criteria), "verification": self.verification,
            "attempts": self.attempts, "blocked_by": list(self.blocked_by), "note": self.note,
            "failure": self.failure, "preserved": self.preserved,
        }


@dataclass(slots=True)
class Plan:
    id: str
    version: int = 1
    type: PlanType = PlanType.SINGLE_TASK
    state: PlanState = PlanState.CREATED
    order: List[str] = field(default_factory=list)
    layers: List[List[str]] = field(default_factory=list)
    critical_path: List[str] = field(default_factory=list)
    critical_cost: float = 0.0
    total_cost: float = 0.0
    issues: List[str] = field(default_factory=list)
    edges: int = 0
    reason: str = "initial"
    created_ns: int = 0

    def max_parallelism(self) -> int:
        return max((len(x) for x in self.layers), default=0)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "version": self.version, "type": self.type.value, "state": self.state.value,
                "order": list(self.order), "layers": [list(x) for x in self.layers],
                "critical_path": list(self.critical_path), "critical_cost": round(self.critical_cost, 2),
                "total_cost": round(self.total_cost, 2), "max_parallelism": self.max_parallelism(),
                "edges": self.edges, "issues": list(self.issues), "reason": self.reason}


@dataclass(slots=True)
class InfoRequirement:
    id: str
    key: str
    text: str
    state: InfoState
    gap: Gap                             # how serious it is when this information is not available
    resolvable: str = "TOOL"             # USER | TOOL | BRAIN
    ttl_s: float = 0.0                   # freshness limit, 0 = does not expire
    observed_ns: int = 0
    source: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "key": self.key, "text": self.text, "state": self.state.value,
                "gap": self.gap.value, "resolvable_by": self.resolvable, "ttl_s": self.ttl_s,
                "source": self.source, "note": self.note}


@dataclass(slots=True)
class Uncertainty:
    id: str
    kind: str                            # AMBIGUITY | INCOMPLETE | STALE | CONFLICTING | UNVERIFIED | EPISTEMIC
    source: str
    impact: str                          # LOW | MEDIUM | HIGH
    text: str
    resolved: bool = False
    resolution: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "source": self.source, "impact": self.impact,
                "text": self.text, "resolved": self.resolved, "resolution": self.resolution}


@dataclass(slots=True)
class Conflict:
    id: str
    kind: str                            # BRAIN_OUTPUT | EVIDENCE | OBJECTIVE | PLAN | CONSTRAINT
    parties: List[str]
    text: str
    cause: str = "UNKNOWN"               # TIMEFRAME | ASSUMPTION | INPUT | INTERPRETATION | UNKNOWN
    status: str = "OPEN"                 # OPEN | PRESERVED | RESOLVED
    basis: str = ""
    created_ns: int = 0
    fp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "parties": list(self.parties), "text": self.text,
                "cause": self.cause, "status": self.status, "basis": self.basis}


@dataclass(slots=True)
class EvidenceReq:
    id: str
    claim: str
    kind: str
    verifier: str
    status: str = "REQUIRED"             # REQUIRED | VERIFIED | REFUTED | UNVERIFIABLE | WAIVED
    refs: List[str] = field(default_factory=list)
    note: str = ""
    provenance: bool = False             # must carry source + timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "claim": self.claim, "kind": self.kind, "verifier": self.verifier,
                "status": self.status, "needs_provenance": self.provenance, "refs": list(self.refs),
                "note": self.note}


@dataclass(slots=True)
class PriorityAssessment:
    level: str = "NORMAL"
    importance: float = 0.3
    urgency: float = 0.2
    reasons: List[str] = field(default_factory=list)
    consequence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"level": self.level, "importance": round(self.importance, 2),
                "urgency": round(self.urgency, 2), "reasons": list(self.reasons),
                "consequence_of_delay": self.consequence}


@dataclass(slots=True)
class Escalation:
    id: str
    reason: str
    destination: str                     # USER | UNITY | SUPERVISOR | COGNITIVE
    severity: str
    summary: str
    status: str = "OPEN"
    created_ns: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "reason": self.reason, "destination": self.destination,
                "severity": self.severity, "summary": self.summary, "status": self.status}


@dataclass(slots=True)
class Finding:
    kind: str
    severity: str
    subject: str
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "severity": self.severity, "subject": self.subject, "detail": self.detail}


@dataclass(slots=True)
class DecisionRecord:
    decision: Decision
    reasons: List[str] = field(default_factory=list)
    detail: Dict[str, Any] = field(default_factory=dict)
    at_ns: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"decision": self.decision.value, "reasons": list(self.reasons), "detail": dict(self.detail)}


@dataclass(slots=True)
class Mission:
    id: str
    request: str
    created_ns: int = field(default_factory=now_ns)
    updated_ns: int = field(default_factory=now_ns)
    state: MissionState = MissionState.NEW
    state_since_ns: int = field(default_factory=now_ns)
    intent: Optional[IntentProfile] = None
    objectives: Dict[str, Objective] = field(default_factory=dict)
    tasks: Dict[str, Task] = field(default_factory=dict)
    plan: Optional[Plan] = None
    info: Dict[str, InfoRequirement] = field(default_factory=dict)
    uncertainties: List[Uncertainty] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    evidence: List[EvidenceReq] = field(default_factory=list)
    escalations: List[Escalation] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    priority: Optional[PriorityAssessment] = None
    decision: Optional[DecisionRecord] = None
    outcome: Optional[Outcome] = None
    constraints: List[Tuple[str, str]] = field(default_factory=list)
    activation: Dict[str, Any] = field(default_factory=dict)
    quality: Dict[str, Any] = field(default_factory=dict)
    history: Deque[Tuple[int, str, str]] = field(default_factory=lambda: deque(maxlen=60))
    ledger: Deque[Tuple[int, str, str, str]] = field(default_factory=lambda: deque(maxlen=200))
    seq: Dict[str, int] = field(default_factory=dict)
    version: int = 0
    replans: int = 0
    rounds: int = 0
    baseline_tasks: int = 0
    progress_marker: str = ""
    delivered: bool = False
    external_success: Optional[bool] = None
    parent_id: Optional[str] = None
    media: bool = False
    down: List[str] = field(default_factory=list)
    registered: List[str] = field(default_factory=list)
    internet: Optional[bool] = None
    stage_ms: Dict[str, float] = field(default_factory=dict)
    last_ctx_sig: str = ""

    def next_id(self, prefix: str) -> str:
        n = self.seq.get(prefix, 0) + 1
        self.seq[prefix] = n
        return f"{prefix}{n}"

    def log(self, kind: str, subject: str, reason: str) -> None:
        self.ledger.append((now_ns(), kind, subject, reason))

    def touch(self) -> None:
        self.updated_ns = now_ns()
        self.version += 1

    def task_by_key(self, key: str) -> Optional[Task]:
        for t in self.tasks.values():
            if t.key == key:
                return t
        return None

    def find_task(self, ref: str) -> Optional[Task]:
        t = self.tasks.get(ref)
        return t if t is not None else self.task_by_key(ref)

    def primary(self) -> Optional[Objective]:
        for o in self.objectives.values():
            if o.kind == "PRIMARY" and o.status != "DROPPED":
                return o
        return None

    def summary(self) -> Dict[str, Any]:
        done = sum(1 for t in self.tasks.values() if t.state in (TaskState.COMPLETED, TaskState.SKIPPED))
        return {
            "id": self.id, "state": self.state.value, "outcome": self.outcome.value if self.outcome else None,
            "mission_type": self.intent.mission_type if self.intent else None,
            "domains": list(self.intent.domains) if self.intent else [],
            "priority": self.priority.level if self.priority else None,
            "tasks_total": len(self.tasks), "tasks_done": done,
            "plan_type": self.plan.type.value if self.plan else None,
            "plan_state": self.plan.state.value if self.plan else None,
            "plan_version": self.plan.version if self.plan else 0,
            "decision": self.decision.decision.value if self.decision else None,
            "replans": self.replans, "rounds": self.rounds, "version": self.version,
            "open_conflicts": sum(1 for c in self.conflicts if c.status == "OPEN"),
            "request": self.request[:160],
        }

    def to_dict(self) -> Dict[str, Any]:
        d = self.summary()
        d["history"] = [{"at_ns": t, "transition": s, "reason": r} for t, s, r in list(self.history)[-12:]]
        d["constraints"] = [list(c) for c in self.constraints]
        d["escalations"] = [e.to_dict() for e in self.escalations]
        d["findings"] = [f.to_dict() for f in self.findings]
        return d
