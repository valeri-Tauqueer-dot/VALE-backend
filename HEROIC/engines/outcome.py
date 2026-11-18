"""Completion, escalation and response controllers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.config import HeroicConfig
from ..core.enums import DONE_TASK, OPEN_INFO, Outcome, TaskState
from ..core.models import Escalation, Mission
from ..core.util import now_ns
from .evidence import ConflictEngine, EvidenceController
from .information import InformationController
from .objectives import ObjectiveEngine


def collect_limitations(m: Mission) -> List[str]:
    """Everything the user must be told is not fully known, verified or done. Nothing is hidden."""
    out: List[str] = []
    for r in m.info.values():
        if r.state in OPEN_INFO:
            out.append(f"{r.text}: {r.state.value.lower().replace('_', ' ')}" + (f" ({r.note})" if r.note else ""))
    for e in m.evidence:
        if e.status == "UNVERIFIABLE":
            out.append(f"Not independently verified: {e.claim}")
        elif e.status == "REFUTED":
            out.append(f"Verification contradicted: {e.claim}")
        elif e.status == "REQUIRED":
            out.append(f"Verification still pending: {e.claim}")
    for c in m.conflicts:
        if c.status in ("OPEN", "PRESERVED"):
            out.append(f"Unresolved disagreement: {c.text}")
    for t in m.tasks.values():
        if t.state == TaskState.SKIPPED and not t.mandatory and t.note and not t.note.startswith("already satisfied"):
            out.append(f"Skipped: {t.name} ({t.note})")
    for t in m.tasks.values():
        if t.degraded and t.state not in (TaskState.CANCELLED, TaskState.SKIPPED):
            out.append(f"{t.name} is handled by {t.target} instead of the usual specialist ({t.note.split(': ', 1)[-1]})")
    covered = " ".join(out).lower()
    for u in m.uncertainties:
        if not u.resolved and u.impact == "HIGH" and u.text.lower() not in covered and not u.source.startswith("info:"):
            out.append(u.text)
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


@dataclass(slots=True)
class CompletionReport:
    can_complete: bool
    outcome: Optional[Outcome]
    met: List[str] = field(default_factory=list)
    unmet: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"can_complete": self.can_complete, "outcome": self.outcome.value if self.outcome else None,
                "met": self.met, "unmet": self.unmet, "limitations": self.limitations}


class CompletionController:
    def __init__(self, objectives: ObjectiveEngine, evidence: EvidenceController, conflicts: ConflictEngine,
                 info: InformationController) -> None:
        self.objectives, self.evidence, self.conflicts, self.info = objectives, evidence, conflicts, info

    def evaluate(self, m: Mission) -> CompletionReport:
        self.objectives.refresh(m)
        unmet, met = [], []
        for t in m.tasks.values():
            if t.mandatory:
                (met if t.state in DONE_TASK else unmet).append(f"task:{t.id}")
        for o in m.objectives.values():
            if o.status == "DROPPED" or o.kind == "SECONDARY" and not o.success:
                continue
            (met if o.status == "MET" else unmet).append(f"objective:{o.id}")
        for r in self.info.blocking(m):
            unmet.append(f"information:{r.key}")
        if self.evidence.pending(m):
            unmet.append("evidence:verification_pending")
        if self.conflicts.open(m):
            unmet.append("conflicts:open")
        can = not unmet and bool(m.tasks)
        lim = collect_limitations(m)
        outcome = (Outcome.FULL_COMPLETION if not lim else Outcome.PARTIAL_COMPLETION) if can else None
        return CompletionReport(can, outcome, met, unmet, lim)


class EscalationController:
    _DEST = {"NEEDS_USER": "USER", "SAFETY": "USER", "OPERATIONAL": "SUPERVISOR", "INTEGRATION": "UNITY",
             "EVIDENCE": "COGNITIVE"}

    def escalate(self, m: Mission, reason: str, summary: str, severity: str = "HIGH") -> Escalation:
        for e in m.escalations:
            if e.reason == reason and e.summary == summary and e.status == "OPEN":
                return e
        e = Escalation(m.next_id("x"), reason, self._DEST.get(reason, "UNITY"), severity, summary, "OPEN", now_ns())
        m.escalations.append(e)
        m.log("escalation", e.id, f"{reason} -> {e.destination}")
        return e

    def reason_for(self, decision_reasons: List[str]) -> str:
        r = " ".join(decision_reasons)
        if "task_failed" in r or "capability" in r or "blocked" in r:
            return "OPERATIONAL"
        if "conflict" in r or "plan_invalid" in r:
            return "INTEGRATION"
        if "verification" in r or "evidence" in r:
            return "EVIDENCE"
        return "OPERATIONAL"


class ResponseController:
    def __init__(self, cfg: HeroicConfig, info: InformationController) -> None:
        self.cfg, self.info = cfg, info

    def build(self, m: Mission, report: CompletionReport) -> Dict[str, Any]:
        accomplished = [{"task": t.id, "name": t.name, "output": t.result} for t in m.tasks.values()
                        if t.state == TaskState.COMPLETED]
        remaining = [t.name for t in m.tasks.values() if t.mandatory and t.state not in DONE_TASK]
        steps: List[str] = []
        for r in self.info.blocking(m):
            steps.append(("Ask the user: " if r.resolvable == "USER" else "Obtain: ") + r.text)
        if any(e.status == "REQUIRED" for e in m.evidence):
            steps.append("Run verification of the material claims (COGNITIVE)")
        for t in m.tasks.values():
            if t.state == TaskState.READY and len(steps) < 8:
                steps.append(f"Run '{t.name}' via {t.target or 'the response layer'}")
        d = {"accomplished": accomplished, "remaining": remaining, "limitations": report.limitations,
             "evidence": [e.to_dict() for e in m.evidence], "next_steps": steps,
             "outcome": m.outcome.value if m.outcome else None,
             "completion": {"can_complete": report.can_complete, "unmet": report.unmet}}
        return d

    def voice(self, m: Mission) -> Optional[str]:
        """Only used when HEROIC_SPEAK is on and a real clarification is needed."""
        if not self.cfg.speak or m.decision is None or m.decision.decision.value != "CLARIFY":
            return None
        qs = m.decision.detail.get("questions") or []
        return f"I need one more detail to help properly: {qs[0].lower()}." if qs else None
