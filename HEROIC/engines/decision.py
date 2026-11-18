"""Decision sufficiency, stopping intelligence and decision-quality analysis.

HEROIC chooses one of: PROCEED, CONTINUE_INVESTIGATING, CLARIFY, WAIT, REPLAN, ESCALATE, BLOCK, COMPLETE,
COMPLETE_WITH_LIMITATIONS. It avoids endless analysis (round limit and no-progress stop) and premature
conclusions (every completion condition is checked). The quality score judges the PROCESS, never the outcome.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..core.config import HeroicConfig
from ..core.enums import (DONE_TASK, OPEN_INFO, TERMINAL_TASK, Decision, InfoState, MissionState, TaskState)
from ..core.models import DecisionRecord, Mission
from ..core.util import fingerprint, now_ns
from .evidence import ConflictEngine, EvidenceController
from .information import InformationController


class SufficiencyEngine:
    def __init__(self, cfg: HeroicConfig, info: InformationController, evidence: EvidenceController,
                 conflicts: ConflictEngine) -> None:
        self.cfg, self.info, self.evidence, self.conflicts = cfg, info, evidence, conflicts

    def marker(self, m: Mission) -> str:
        done = sum(1 for t in m.tasks.values() if t.state in DONE_TASK)
        return fingerprint(str(done), "".join(sorted(f"{r.key}:{r.state.value}" for r in m.info.values())),
                           "".join(sorted(f"{e.id}:{e.status}" for e in m.evidence)),
                           str(sum(1 for c in m.conflicts if c.status == "OPEN")))

    def _stalled(self, m: Mission) -> bool:
        return m.rounds > 0 and m.progress_marker == self.marker(m)

    def decide(self, m: Mission, verifier_ok: bool = True) -> DecisionRecord:
        def rec(d: Decision, reasons: List[str], **detail: Any) -> DecisionRecord:
            return DecisionRecord(d, reasons, detail, now_ns())

        if m.state == MissionState.COMPLETED:
            return rec(Decision.COMPLETE, ["mission_completed"])
        if m.state == MissionState.CANCELLED:
            return rec(Decision.BLOCK, ["mission_cancelled"])
        if m.state == MissionState.FAILED:
            return rec(Decision.ESCALATE, ["mission_failed"])
        plan = m.plan
        if plan is None:
            return rec(Decision.CLARIFY if self.info.blocking(m) else Decision.BLOCK,
                       [f"missing:{r.key}" for r in self.info.blocking(m)] or ["no_plan"],
                       questions=[r.text for r in self.info.blocking(m)])
        if plan.issues:
            if m.replans < self.cfg.max_replans:
                return rec(Decision.REPLAN, ["plan_invalid"], issues=list(plan.issues))
            return rec(Decision.ESCALATE, ["plan_invalid_and_replan_limit_reached"], issues=list(plan.issues))

        blocking = self.info.blocking(m)
        user_gaps = [r for r in blocking if r.resolvable == "USER" and r.key != "execution_authorization"]
        if user_gaps:
            return rec(Decision.CLARIFY, [f"missing:{r.key}" for r in user_gaps], questions=[r.text for r in user_gaps])

        failed = [t for t in m.tasks.values() if t.mandatory and t.state == TaskState.FAILED]
        exhausted = [t for t in failed if t.attempts >= self.cfg.max_attempts]
        if exhausted:
            return rec(Decision.ESCALATE, [f"task_failed:{t.id}" for t in exhausted],
                       failures=[t.failure or "" for t in exhausted])
        if failed:
            return rec(Decision.PROCEED, [f"retry:{t.id}" for t in failed], retry=[t.id for t in failed])

        cap_blocked = [t for t in m.tasks.values() if t.mandatory and t.state == TaskState.BLOCKED
                       and any(b.startswith("capability:") for b in t.blocked_by)]
        if cap_blocked:
            return rec(Decision.BLOCK, [f"capability_unavailable:{t.capability}" for t in cap_blocked],
                       tasks=[t.id for t in cap_blocked])

        tool_gaps = [r for r in blocking if r.resolvable != "USER"]
        if tool_gaps:
            unavailable = [r for r in tool_gaps if r.state == InfoState.UNAVAILABLE]
            if unavailable:
                return rec(Decision.BLOCK, [f"unavailable:{r.key}" for r in unavailable],
                           note="a strong conclusion is not justified without this information")
            producers = [t for t in m.tasks.values() if any(k in t.produces for r in tool_gaps for k in (r.key,))]
            if any(t.state not in TERMINAL_TASK for t in producers):
                pass                                    # the information is still being acquired
            elif m.rounds < self.cfg.max_rounds and not self._stalled(m):
                return rec(Decision.CONTINUE_INVESTIGATING, [f"information_still_open:{r.key}" for r in tool_gaps])
            else:
                return rec(Decision.BLOCK, [f"information_not_obtained:{r.key}" for r in tool_gaps])

        mand = [t for t in m.tasks.values() if t.mandatory]
        notdone = [t for t in mand if t.state not in DONE_TASK]
        if notdone:
            ready = [t.id for t in notdone if t.state in (TaskState.READY, TaskState.RUNNING)]
            if ready:
                return rec(Decision.PROCEED, ["work_ready_or_running"], ready=ready)
            blocked = [t for t in notdone if t.state == TaskState.BLOCKED]
            if blocked:
                gated = set()                                   # blocked on input, or only on tasks that are
                for tid in plan.order:
                    t = m.tasks[tid]
                    if t.state != TaskState.BLOCKED:
                        continue
                    ups = [b[9:] for b in t.blocked_by if b.startswith("upstream:")]
                    if any(b.startswith("info:") for b in t.blocked_by) or (ups and len(ups) == len(t.blocked_by) and all(u in gated for u in ups)):
                        gated.add(tid)
                if all(t.id in gated for t in blocked):
                    return rec(Decision.WAIT, sorted({b for t in blocked for b in t.blocked_by if b.startswith("info:")}),
                               note="waiting for information or authorisation that only the user or a tool can supply")
                return rec(Decision.ESCALATE, ["mandatory_work_blocked"], tasks=[t.id for t in blocked])
            return rec(Decision.WAIT, ["waiting_for_prerequisites"])

        # all mandatory work is finished: is the result sufficient?
        stalled = self._stalled(m)
        if self.evidence.pending(m):
            if verifier_ok and m.rounds < self.cfg.max_rounds and not stalled:
                return rec(Decision.CONTINUE_INVESTIGATING, ["verification_pending"])
            return rec(Decision.COMPLETE_WITH_LIMITATIONS, ["verification_not_obtained"])
        open_conf = self.conflicts.open(m)
        if open_conf:
            if m.rounds < self.cfg.max_rounds and not stalled:
                return rec(Decision.CONTINUE_INVESTIGATING, [f"conflict_open:{c.id}" for c in open_conf])
            return rec(Decision.COMPLETE_WITH_LIMITATIONS, [f"conflict_preserved:{c.id}" for c in open_conf])
        limits = []
        if self.evidence.limited(m):
            limits.append("evidence_limited")
        if any(r.state in OPEN_INFO for r in m.info.values()):
            limits.append("information_gaps_remain")
        if any(not u.resolved and u.impact == "HIGH" for u in m.uncertainties):
            limits.append("high_uncertainty_remains")
        if any(t.state == TaskState.SKIPPED and not t.mandatory and not t.note.startswith("already satisfied") for t in m.tasks.values()):
            limits.append("optional_work_skipped")
        if limits:
            return rec(Decision.COMPLETE_WITH_LIMITATIONS, limits)
        return rec(Decision.COMPLETE, ["all_conditions_met"])


class DecisionQualityAnalyzer:
    """Scores how good the decision PROCESS was. It is a rubric, not a probability and not an outcome measure."""

    def analyze(self, m: Mission) -> Dict[str, Any]:
        I = m.intent
        checks: List[tuple] = []
        finished = m.state in (MissionState.COMPLETED, MissionState.VERIFYING)

        def chk(name: str, ok: bool, w: float = 1.0) -> None:
            checks.append((name, bool(ok), w))

        mt = I.mission_type if I else "OTHER"
        chk("objective_defined", m.primary() is not None or m.plan is None)
        chk("plan_is_valid", m.plan is None or not m.plan.issues)
        sources = {u.source for u in m.uncertainties}
        chk("information_gaps_disclosed", all(f"info:{r.key}" in sources for r in m.info.values() if r.state in OPEN_INFO))
        chk("claims_have_evidence_requirements",
            not (I and (mt in ("ANALYSIS", "DECISION_SUPPORT", "RESEARCH", "COMPARISON") or ("MARKET" in I.domains and I.time_sensitive))) or bool(m.evidence))
        chk("verification_obtained_or_limited", not finished or all(e.status != "REQUIRED" for e in m.evidence))
        chk("conflicts_preserved_or_resolved", not finished or all(c.status != "OPEN" for c in m.conflicts))
        chk("alternatives_considered", mt not in ("ANALYSIS", "DECISION_SUPPORT") or
            any(t.key in ("challenge_findings", "competing_hypotheses") for t in m.tasks.values()))
        chk("user_beliefs_not_assumed", not (I and I.hypotheses) or any(t.key == "challenge_hypothesis" for t in m.tasks.values()))
        chk("no_premature_completion", not (m.state == MissionState.COMPLETED and
            any(t.mandatory and t.state not in DONE_TASK for t in m.tasks.values())), 2.0)
        chk("no_unauthorised_execution", not any(t.needs and t.state in (TaskState.RUNNING, TaskState.COMPLETED) and
            any(m.info.get(k) is not None and m.info[k].state not in (InfoState.AVAILABLE_VERIFIED, InfoState.AVAILABLE_UNVERIFIED)
                for k in t.needs) for t in m.tasks.values()), 2.0)
        total = sum(w for _, _, w in checks)
        score = sum(w for _, ok, w in checks if ok) / total if total else 1.0
        flag = None
        if m.external_success is True and score < 0.6:
            flag = "good_outcome_but_weak_process"
        elif m.external_success is False and score >= 0.8:
            flag = "bad_outcome_but_sound_process"
        return {"process_score": round(score, 2), "failed_checks": [n for n, ok, _ in checks if not ok],
                "checks": len(checks), "outcome_independent": True, "outcome_flag": flag,
                "rubric": "weighted share of process checks passed; not a probability and not an outcome measure"}
