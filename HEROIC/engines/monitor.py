"""Mission monitor, replanner and interrupt controller."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from ..core.config import HeroicConfig
from ..core.enums import TERMINAL_TASK, TaskState
from ..core.models import Finding, IntentProfile, Mission
from ..core.util import content_tokens, fingerprint, now_ns
from .capabilities import CapabilityRegistry
from .context import Context
from .planning import DependencyPlanner, TaskPlanner


class MissionMonitor:
    def __init__(self, cfg: HeroicConfig) -> None:
        self.cfg = cfg

    def check(self, m: Mission, active_brains: Optional[Iterable[str]] = None) -> List[Finding]:
        f: List[Finding] = []
        now = now_ns()
        live = {o.id for o in m.objectives.values() if o.status != "DROPPED"}
        live_tasks = [t for t in m.tasks.values() if t.state not in (TaskState.CANCELLED, TaskState.SKIPPED)]
        for t in live_tasks:
            if live and not (set(t.serves) & live):
                f.append(Finding("IRRELEVANT_TASK", "WARNING", t.id, "the task serves no live objective"))
            if t.attempts > self.cfg.max_attempts:
                f.append(Finding("EXCESS_RETRIES", "WARNING", t.id, f"{t.attempts} attempts"))
            if t.state == TaskState.RUNNING and t.started_ns and (now - t.started_ns) / 1e9 > self.cfg.task_stall_s:
                f.append(Finding("POSSIBLE_STALL", "WARNING", t.id, f"running for more than {self.cfg.task_stall_s:.0f}s"))
            if t.state == TaskState.BLOCKED and any(b.startswith(("failed:", "upstream:")) for b in t.blocked_by):
                f.append(Finding("FAILED_DEPENDENCY", "HIGH", t.id, ",".join(t.blocked_by)))
        seen: Dict[str, List[str]] = {}
        for t in live_tasks:
            seen.setdefault(t.fp, []).append(t.id)
        for ids in seen.values():
            if len(ids) > 1:
                f.append(Finding("REPEATED_WORK", "WARNING", ",".join(ids), "the same work is planned more than once"))
        if m.baseline_tasks and len(live_tasks) > m.baseline_tasks * 1.5 + 2:
            f.append(Finding("SCOPE_EXPANSION", "WARNING", m.id, f"{len(live_tasks)} tasks against a baseline of {m.baseline_tasks}"))
        prim = m.primary()
        if prim and m.intent and prim.fp != fingerprint(*sorted(set(content_tokens(m.intent.text)))):
            f.append(Finding("OBJECTIVE_DRIFT", "HIGH", prim.id, "the primary objective no longer matches the request"))
        if active_brains:
            planned = {t.target for t in m.tasks.values() if t.target}
            extra = {str(b).upper() for b in active_brains} - planned - {"HEROIC", "UNITY", "SUPERVISOR"}
            if extra:
                f.append(Finding("UNNECESSARY_ACTIVATION", "INFO", ",".join(sorted(extra)),
                                 "brains ran that the plan did not need"))
        m.findings = f
        return f


class Replanner:
    def __init__(self, cfg: HeroicConfig, planner: TaskPlanner, deps: DependencyPlanner) -> None:
        self.cfg, self.planner, self.deps = cfg, planner, deps

    def replan(self, m: Mission, reason: str, intent: IntentProfile, ctx: Context,
               caps: CapabilityRegistry, keep_valid: bool = True) -> Dict[str, Any]:
        """Rebuild the plan. Completed and in-flight work that is still valid is kept, with its original id.

        keep_valid=False is used when the objective itself changed: old work answered a different question,
        so nothing is kept and in-flight tasks are reported so they can be cancelled."""
        if m.replans >= self.cfg.max_replans:
            m.log("replan_refused", reason, "replan limit reached")
            return {"replanned": False, "refused": "replan_limit_reached", "reason": reason}
        old = {t.fp: t for t in m.tasks.values()}
        self.planner.build(m, intent, ctx, caps, reuse={fp: t.id for fp, t in old.items()} if keep_valid else {})
        preserved, added = [], []
        for t in m.tasks.values():
            prev = old.get(t.fp) if keep_valid else None
            if prev is not None and prev.state in (TaskState.COMPLETED, TaskState.RUNNING):
                t.state, t.result, t.attempts = prev.state, prev.result, prev.attempts
                t.started_ns, t.ended_ns, t.note, t.preserved = prev.started_ns, prev.ended_ns, "kept from the earlier plan", True
                preserved.append(t.id)
            elif prev is not None and prev.state in (TaskState.FAILED,):
                t.attempts, t.failure = prev.attempts, prev.failure
                added.append(t.id)
            else:
                added.append(t.id)
        new_fps = {t.fp for t in m.tasks.values()}
        removed = [p.id for fp, p in old.items() if fp not in new_fps or not keep_valid]
        in_flight = [p.id for p in old.values() if p.state == TaskState.RUNNING and (not keep_valid or p.fp not in new_fps)]
        issues = self.deps.analyze(m, reason=f"replan: {reason}")
        # kept work is only valid if everything it now depends on is also done
        for tid in (m.plan.order if m.plan else []):
            t = m.tasks[tid]
            if t.preserved and any(m.tasks[d].state not in (TaskState.COMPLETED, TaskState.SKIPPED) for d in t.deps if d in m.tasks):
                t.state, t.result, t.preserved, t.started_ns, t.ended_ns = TaskState.PENDING, None, False, 0, 0
                t.note = "redo: a new prerequisite is not finished"
                preserved.remove(tid)
                added.append(tid)
        m.replans += 1
        m.log("replan", f"v{m.plan.version if m.plan else '?'}", f"{reason}; +{len(added)} -{len(removed)} kept {len(preserved)}")
        return {"replanned": True, "reason": reason, "plan_version": m.plan.version if m.plan else None,
                "added": added, "removed": removed, "preserved": preserved, "issues": issues,
                "cancel_in_flight": in_flight}


@dataclass(slots=True)
class InterruptPlan:
    action: str
    replan: bool = False
    reason: str = ""
    notes: List[str] = field(default_factory=list)


class InterruptController:
    """Maps an important incoming change to the smallest sufficient reaction."""

    def classify(self, m: Mission, event: str, data: Dict[str, Any], max_attempts: int = 2) -> InterruptPlan:
        e = event.upper()
        if e == "CANCEL":
            return InterruptPlan("CANCEL", reason="the user or the system cancelled the mission")
        if e == "USER_UPDATE":
            verdict = data.get("verdict", "CHANGED")
            if verdict == "SAME":
                return InterruptPlan("NONE", reason="the request did not change")
            return InterruptPlan("UPDATE_OBJECTIVE", True, f"request {verdict.lower()}")
        if e == "NEW_CONSTRAINT":
            kind = data.get("kind", "")
            return InterruptPlan("UPDATE_CONSTRAINTS", kind in ("deadline", "urgency", "exclude"), f"new constraint: {kind}")
        if e == "PRIORITY_CHANGE":
            return InterruptPlan("UPDATE_PRIORITY", False, "priority changed")
        if e == "BRAIN_UNAVAILABLE":
            brain = str(data.get("brain", "")).upper()
            hit = [t.id for t in m.tasks.values() if t.target == brain and t.state not in TERMINAL_TASK]
            return InterruptPlan("REROUTE" if hit else "NONE", bool(hit), f"{brain} is unavailable", hit)
        if e == "TASK_FAILED":
            t = m.find_task(str(data.get("task", "")))
            if t is not None and t.attempts < max_attempts:
                return InterruptPlan("RETRY", False, f"attempt {t.attempts} of {max_attempts}", [t.id])
            return InterruptPlan("REPLAN_OR_ESCALATE", True, "the task failed and retries are used up", [t.id] if t else [])
        if e in ("INFO_UPDATE", "NEW_EVIDENCE", "VERIFICATION_RESULT"):
            return InterruptPlan("REASSESS", False, "new information or evidence arrived")
        if e in ("CONFLICT_REPORTED", "BRAIN_RESULTS"):
            return InterruptPlan("INVESTIGATE", False, "possible disagreement between brains")
        return InterruptPlan("RECORD", False, f"unrecognised event {event}")
