"""HEROIC - VALE's Mission Intelligence brain.

HEROIC turns a request into a structured mission: objectives, information needs, evidence requirements, a
dependency-safe plan, the smallest sufficient set of capabilities, priorities and a decision about what to do next.
It plans and coordinates. It does not execute tasks, verify its own claims or replace UNITY, ALPHA, SUPERVISOR or
MCVL. Planned work is never reported as done. See the HEROIC/engines package for each capability.
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from vale_brain_interface import VALEBrainInterface

from .core.config import HeroicConfig
from .core.enums import (DONE_TASK, LEVELS, OPEN_INFO, TERMINAL_MISSION, Decision, InfoState,
                         MissionState as MS, Outcome, PlanState as PS, TaskState as TS)
from .core.models import DecisionRecord, Mission
from .core.registry import MissionRegistry
from .core.statemachine import move_mission, move_plan, move_task
from .core.telemetry import Telemetry
from .core.util import clip, mono_ns, norm, now_ns
from .engines.capabilities import CapabilityRegistry, CapabilitySelector
from .engines.context import Context, ContextController
from .engines.decision import DecisionQualityAnalyzer, SufficiencyEngine
from .engines.evidence import ConflictEngine, EvidenceController
from .engines.information import InformationController, UncertaintyController
from .engines.intent import IntentEngine
from .engines.interfaces import EvolutionInterface, MissionMemory, build_contract, build_health
from .engines.monitor import InterruptController, MissionMonitor, Replanner
from .engines.objectives import ObjectiveEngine
from .engines.outcome import CompletionController, EscalationController, ResponseController, collect_limitations
from .engines.planning import DependencyPlanner, ExecutionPlanBuilder, TaskPlanner
from .engines.priority import PriorityEngine

_AVAILABLE = (InfoState.AVAILABLE_VERIFIED, InfoState.AVAILABLE_UNVERIFIED)


class HeroicBrain(VALEBrainInterface):
    VERSION = "1.0.0"
    ROLE = "MISSION_INTELLIGENCE"
    ARCHITECTURE_STAGE = "HEROIC_MISSION_ENGINE"
    RULES = (
        "No fabricated information, evidence, capabilities, results or system states.",
        "No blind agreement: a user's belief is a hypothesis until evidence supports it.",
        "No artificial balance: conclusions follow the evidence.",
        "No unnecessary activation: use the smallest sufficient set of capabilities.",
        "No premature completion: a stopped task is not a finished mission.",
        "No hidden uncertainty: critical uncertainty stays visible.",
        "No invalid dependencies: prerequisites come first.",
        "No uncontrolled replanning: valid work is kept and changes are explained.",
        "No role confusion: HEROIC is not UNITY, ALPHA, SUPERVISOR or MCVL.",
        "No unsupported execution claims: a planned action is not a completed action.",
        "No objective drift: every task serves a live objective.",
        "No forced conclusions: HEROIC can wait, ask, block or escalate.",
        "No unnecessary rewrites: working components and interfaces are preserved.",
    )

    def __init__(self, connector: Any = None, config: Optional[HeroicConfig] = None) -> None:
        super().__init__(brain_name="HEROIC", connector=connector)
        self.version = self.VERSION
        self.cfg = config or HeroicConfig.from_env()
        self.lock = threading.RLock()
        self.telemetry = Telemetry()
        self.memory = MissionMemory(self.cfg.archive_size)
        self.evolution = EvolutionInterface(self.cfg.learning_buffer)
        self.registry = MissionRegistry(self.cfg.max_missions, on_evict=self._on_evict)
        self.context = ContextController()
        self.intent = IntentEngine(self.cfg.intent_cache_size, self.cfg.max_request_chars)
        self.priority = PriorityEngine()
        self.objectives = ObjectiveEngine()
        self.info = InformationController(self.cfg)
        self.uncertainty = UncertaintyController()
        self.evidence = EvidenceController()
        self.conflicts = ConflictEngine()
        self.planner = TaskPlanner(self.cfg)
        self.deps = DependencyPlanner()
        self.exec_plan = ExecutionPlanBuilder()
        self.selector = CapabilitySelector()
        self.sufficiency = SufficiencyEngine(self.cfg, self.info, self.evidence, self.conflicts)
        self.quality = DecisionQualityAnalyzer()
        self.monitor = MissionMonitor(self.cfg)
        self.replanner = Replanner(self.cfg, self.planner, self.deps)
        self.interrupts = InterruptController()
        self.completion = CompletionController(self.objectives, self.evidence, self.conflicts, self.info)
        self.escalation = EscalationController()
        self.response = ResponseController(self.cfg, self.info)

    # ================================================================== helpers
    def _capabilities(self, ctx: Optional[Context] = None, m: Optional[Mission] = None) -> CapabilityRegistry:
        brains = ctx.registered if ctx is not None and ctx.registered else ()
        if not brains and m is not None and m.registered:
            brains = m.registered                      # what the network had registered when the mission started
        if not brains and self.network is not None:
            try:
                brains = self.network.brain_names()
            except Exception:
                brains = ()
        internet = ctx.internet_available if ctx is not None else None
        if internet is None and m is not None:
            internet = m.internet
        if internet is None:
            try:
                internet = bool(self.connector.internet_available())
            except Exception:
                internet = None
        if m is not None:
            if brains:
                m.registered = [str(b).upper() for b in brains]
            m.internet = internet
        return CapabilityRegistry(brains, internet, exclude=m.down if m is not None else ())

    def _guard(self, m: Mission, to: MS):
        if to == MS.COMPLETED:
            rep = self.completion.evaluate(m)
            return (True, "ok") if rep.can_complete else (False, "completion conditions not met: " + ", ".join(rep.unmet[:4]))
        if to == MS.READY:
            if m.plan is not None and m.plan.issues:
                return False, "the plan has structural issues"
        if to == MS.REPLANNING and m.replans >= self.cfg.max_replans:
            return False, "replan limit reached"
        return True, "ok"

    def _move(self, m: Mission, to: MS, reason: str) -> bool:
        ok, _ = move_mission(m, to, reason, self._guard)
        return ok

    def _sync_plan_state(self, m: Mission) -> None:
        if m.plan is None:
            return
        target = {MS.BLOCKED: PS.BLOCKED, MS.ESCALATED: PS.BLOCKED, MS.READY: PS.READY, MS.EXECUTING: PS.EXECUTING,
                  MS.VERIFYING: PS.EXECUTING, MS.COMPLETED: PS.COMPLETED, MS.FAILED: PS.FAILED,
                  MS.CANCELLED: PS.CANCELLED, MS.REPLANNING: PS.REPLANNING}.get(m.state)
        if target is not None:
            move_plan(m, m.plan, target, f"mission {m.state.value}")

    def _on_evict(self, m: Mission) -> None:
        if m.state in TERMINAL_MISSION and not m.quality:
            m.quality = self.quality.analyze(m)
        self.memory.archive(m)

    def _finalize(self, m: Mission) -> None:
        m.quality = self.quality.analyze(m)
        self.evolution.record(m)
        self.memory.archive(m)
        m.log("finalized", m.state.value, m.outcome.value if m.outcome else "")

    # ================================================================== pipeline
    def _understand(self, m: Mission, ctx: Context, caps: CapabilityRegistry, intent, carry: bool = False) -> None:
        old_info = dict(m.info) if carry else {}
        old_ev = {e.kind: e for e in m.evidence} if carry else {}
        m.intent = intent
        m.constraints = list(intent.constraints)
        m.media = ctx.media
        m.conflicts = [c for c in m.conflicts if c.kind != "OBJECTIVE"]
        m.priority = self.priority.assess(intent, ctx)
        self.objectives.build(m, intent)
        self.info.derive(m, intent, ctx)
        self.evidence.derive(m, intent, caps.resolve("verification").available)
        self.uncertainty.derive(m, intent)
        if carry:
            for k, r in m.info.items():
                o = old_info.get(k)
                if o is not None and o.resolvable == "TOOL" and o.state in _AVAILABLE and r.state in OPEN_INFO:
                    r.state, r.source, r.observed_ns, r.note = o.state, o.source, o.observed_ns, o.note
            for e in m.evidence:
                o = old_ev.get(e.kind)
                if o is not None and o.status in ("VERIFIED", "REFUTED", "UNVERIFIABLE") and e.status == "REQUIRED":
                    e.status, e.refs, e.note = o.status, o.refs, o.note
            self.uncertainty.sync(m)

    def _build_plan(self, m: Mission, ctx: Context, caps: CapabilityRegistry, reason: str) -> None:
        self.planner.build(m, m.intent, ctx, caps)
        self.deps.analyze(m, reason)
        self.priority.apply_to_tasks(m)
        self.deps.refresh_readiness(m)
        m.activation = self.selector.select(m, ctx.network_plan, caps)

    def _plan(self, m: Mission, ctx: Context) -> None:
        t0 = mono_ns()
        caps = self._capabilities(ctx, m)
        self._move(m, MS.UNDERSTANDING, "analyse the request")
        if not ctx.request:
            self._plan_empty(m, ctx, caps)
            return
        intent = self.intent.analyze(ctx.request, ctx.has_history)
        self._understand(m, ctx, caps, intent)
        t1 = mono_ns()
        self._move(m, MS.PLANNING, "build the plan")
        self._build_plan(m, ctx, caps, "initial")
        t2 = mono_ns()
        self._advance(m, ctx)
        m.stage_ms = {"understand": (t1 - t0) / 1e6, "plan": (t2 - t1) / 1e6, "decide": (mono_ns() - t2) / 1e6}

    def _plan_empty(self, m: Mission, ctx: Context, caps: CapabilityRegistry) -> None:
        intent = self.intent.analyze("", False)
        m.intent, m.constraints, m.plan = intent, [], None
        m.priority = self.priority.assess(intent, ctx)
        self.info.derive(m, intent, ctx)
        self.evidence.derive(m, intent, caps.resolve("verification").available)
        self.uncertainty.derive(m, intent)
        m.decision = self.sufficiency.decide(m, True)
        self._settle(m, m.decision)
        m.progress_marker = self.sufficiency.marker(m)

    def _advance(self, m: Mission, ctx: Optional[Context] = None, depth: int = 0) -> None:
        """Re-evaluate a mission after any change and move its state to match the facts."""
        if m.state in TERMINAL_MISSION:
            return
        caps = self._capabilities(ctx, m)
        self.deps.refresh_readiness(m)
        self.info.refresh(m, ctx)
        self.uncertainty.sync(m)
        self.objectives.refresh(m)
        rec = self.sufficiency.decide(m, caps.resolve("verification").available)
        m.decision = rec
        m.log("decision", rec.decision.value, ",".join(rec.reasons)[:120])
        if rec.decision == Decision.REPLAN and depth < 2 and m.intent is not None:
            reason = "plan invalid: " + "; ".join(m.plan.issues)[:100] if m.plan else "plan invalid"
            out = self._replan(m, reason, ctx or self.context.from_text(m.request), caps)
            if out.get("replanned"):
                return self._advance(m, ctx, depth + 1)
            rec = DecisionRecord(Decision.ESCALATE, ["replan_refused"], {}, now_ns())
            m.decision = rec
        self._settle(m, rec)
        m.progress_marker = self.sufficiency.marker(m)
        m.touch()

    def _settle(self, m: Mission, rec: DecisionRecord) -> None:
        d = rec.decision
        started = any(t.state in (TS.RUNNING, TS.COMPLETED, TS.FAILED) for t in m.tasks.values())
        if d == Decision.ESCALATE:
            self.escalation.escalate(m, self.escalation.reason_for(rec.reasons), "; ".join(rec.reasons)[:200])
            self._move(m, MS.ESCALATED, ",".join(rec.reasons)[:100])
        elif d in (Decision.CLARIFY, Decision.BLOCK):
            if d == Decision.CLARIFY:
                self.escalation.escalate(m, "NEEDS_USER", "; ".join(rec.detail.get("questions", []))[:200], "MEDIUM")
            self._move(m, MS.BLOCKED, ",".join(rec.reasons)[:100])
        else:
            if m.state in (MS.BLOCKED, MS.ESCALATED):
                self._move(m, MS.EXECUTING if started else MS.READY, "recovered")
            elif m.state == MS.UNDERSTANDING:
                self._move(m, MS.PLANNING, "plan built")
            if m.state in (MS.PLANNING, MS.REPLANNING):
                self._move(m, MS.READY, "plan ready")
            if started and m.state == MS.READY:
                self._move(m, MS.EXECUTING, "work started")
            if d == Decision.CONTINUE_INVESTIGATING:
                m.rounds += 1
            mand = [t for t in m.tasks.values() if t.mandatory]
            work = [t for t in mand if not t.verification and t.kind != "COMMUNICATION"]
            all_done = bool(mand) and all(t.state in DONE_TASK for t in mand)
            work_done = bool(work) and all(t.state in DONE_TASK for t in work)
            if m.state == MS.EXECUTING and (work_done or all_done):
                self._move(m, MS.VERIFYING, "work finished; checking evidence")
            if m.state == MS.VERIFYING and all_done and d in (Decision.COMPLETE, Decision.COMPLETE_WITH_LIMITATIONS):
                if d == Decision.COMPLETE_WITH_LIMITATIONS:
                    self._accept_limitations(m, rec)
                if self._move(m, MS.COMPLETED, d.value):
                    for t in m.tasks.values():
                        if t.state not in (TS.COMPLETED, TS.SKIPPED, TS.CANCELLED, TS.FAILED, TS.RUNNING):
                            move_task(m, t, TS.SKIPPED, "optional; the mission completed without it")
                            t.note = t.note or "optional; the mission completed without it"
                    rep = self.completion.evaluate(m)
                    m.outcome = rep.outcome or Outcome.PARTIAL_COMPLETION
                    self._finalize(m)
        self._sync_plan_state(m)

    def _accept_limitations(self, m: Mission, rec: DecisionRecord) -> None:
        """Completing with limitations means saying so: unmet checks become explicit, visible limitations."""
        for e in m.evidence:
            if e.status == "REQUIRED":
                e.status, e.note = "UNVERIFIABLE", "verification was not obtained within the investigation limit"
        for c in m.conflicts:
            if c.status == "OPEN":
                self.conflicts.preserve(m, c.id, "left unresolved; both positions are kept")
        m.log("limitations_accepted", ",".join(rec.reasons)[:80], "completing with stated limitations")

    def _replan(self, m: Mission, reason: str, ctx: Context, caps: CapabilityRegistry) -> Dict[str, Any]:
        if m.state in (MS.READY, MS.EXECUTING, MS.VERIFYING, MS.BLOCKED, MS.ESCALATED):
            if not self._move(m, MS.REPLANNING, reason):
                return {"replanned": False, "refused": "replan_not_allowed", "reason": reason}
        out = self.replanner.replan(m, reason, m.intent, ctx, caps)
        if out.get("replanned"):
            self.priority.apply_to_tasks(m)
            self.deps.refresh_readiness(m)
            m.activation = self.selector.select(m, ctx.network_plan, caps)
            self.uncertainty.sync(m)
        return out

    def _apply_update(self, m: Mission, ctx: Context) -> Dict[str, Any]:
        """The user changed the request while the mission was live."""
        intent = self.intent.analyze(ctx.request, ctx.has_history)
        verdict = self.objectives.reconcile(m, intent)
        action = self.interrupts.classify(m, "USER_UPDATE", {"verdict": verdict})
        m.log("user_update", verdict, clip(ctx.request, 80))
        if action.action == "NONE":
            m.request = ctx.request
            return {"verdict": verdict}
        caps = self._capabilities(ctx, m)
        if m.state != MS.UNDERSTANDING:
            self._move(m, MS.UNDERSTANDING, f"request {verdict.lower()}")
        m.request = ctx.request
        self._understand(m, ctx, caps, intent, carry=(verdict == "REFINED"))
        self._move(m, MS.PLANNING, "replan after the request changed")
        out = self.replanner.replan(m, f"request {verdict.lower()}", intent, ctx, caps, keep_valid=(verdict == "REFINED"))
        if out.get("replanned"):
            self.priority.apply_to_tasks(m)
            self.deps.refresh_readiness(m)
            m.activation = self.selector.select(m, ctx.network_plan, caps)
        else:
            self.escalation.escalate(m, "OPERATIONAL", "the request changed but the replan limit was reached")
        self._advance(m, ctx)
        out["verdict"] = verdict
        return out

    def _refresh(self, m: Mission, ctx: Context) -> None:
        """Same request, new information in the shared state (for example search results arrived)."""
        self.info.refresh(m, ctx)
        self._advance(m, ctx)

    # ================================================================== VALE interface
    def think(self, state: Any) -> Dict[str, Any]:
        if state is None:
            raise ValueError("HEROIC.think() requires a VALEBrainState")
        t0 = mono_ns()
        try:
            with self.lock:
                ctx = self.context.build(state)
                mid = str(getattr(state, "task_id", "") or "") or f"m-{self.telemetry.counters.get('missions', 0) + 1}"
                m = self.registry.get(mid)
                cache = "miss"
                changed = bool(m is not None and ctx.request and norm(ctx.request) != norm(m.request))
                if m is not None and m.state in TERMINAL_MISSION and changed:
                    self.registry.remove(mid)
                    m = None
                if m is None:
                    m = Mission(id=mid, request=ctx.request, media=ctx.media)
                    self.registry.put(m)
                    self.telemetry.count("missions")
                    self._plan(m, ctx)
                elif changed:
                    self._apply_update(m, ctx)
                elif ctx.sig != m.last_ctx_sig:
                    self._refresh(m, ctx)
                else:
                    cache = "hit"
                result = self._result(m, ctx, cache)
                m.last_ctx_sig = ctx.sig
            result["timing_ms"]["total"] = round((mono_ns() - t0) / 1e6, 4)
            self._publish(state, m, result)
        except Exception as exc:
            self.telemetry.error("think", exc)
            result = self._error_result(state, exc)
        finally:
            self.telemetry.observe("think", mono_ns() - t0)
        return result

    def _publish(self, state: Any, m: Mission, result: Dict[str, Any]) -> None:
        try:
            state.set("heroic_status", result["status"])
            state.set("heroic_mission", result["mission"])
            state.set("heroic_result", result)
            state.set("heroic_activation", m.activation)
            state.event("heroic_mission_state_updated", self.brain_name, payload={
                "mission_id": m.id, "mission_state": m.state.value,
                "plan_state": m.plan.state.value if m.plan else None,
                "decision": m.decision.decision.value if m.decision else None})
        except Exception as exc:                      # publishing must never break planning
            self.telemetry.error("publish", exc)

    def _status(self, m: Mission) -> str:
        if m.state == MS.BLOCKED:
            return "NEEDS_INFORMATION" if m.decision and m.decision.decision == Decision.CLARIFY else "PLAN_BLOCKED"
        if m.state in (MS.ESCALATED, MS.COMPLETED, MS.FAILED, MS.CANCELLED):
            return m.state.value
        return "PLAN_READY" if m.state in (MS.READY, MS.EXECUTING, MS.VERIFYING, MS.REPLANNING) else "PLAN_DRAFT"

    def _result(self, m: Mission, ctx: Optional[Context], cache: str) -> Dict[str, Any]:
        rep = self.completion.evaluate(m)
        quality = self.quality.analyze(m)
        m.quality = quality
        self.monitor.check(m)
        plan = m.plan
        primary = m.primary()
        started = any(t.state in (TS.RUNNING, TS.COMPLETED, TS.FAILED) for t in m.tasks.values())
        verified = any(e.status in ("VERIFIED", "REFUTED") for e in m.evidence)
        out: Dict[str, Any] = {
            "brain": self.brain_name, "version": self.VERSION, "role": self.ROLE, "status": self._status(m),
            "planning_status": plan.state.value if plan else None, "task_id": m.id, "mission_id": m.id,
            "mission": m.to_dict(), "intent": m.intent.to_dict() if m.intent else None,
            "objective": primary.to_dict() if primary else None,
            "objectives": [o.to_dict() for o in m.objectives.values()],
            "tasks": [t.to_dict() for t in m.tasks.values()],
            "plan": plan.to_dict() if plan else None,
            "execution_plan": self.exec_plan.build(m) if plan else None,
            "activation": m.activation, "priority": m.priority.to_dict() if m.priority else None,
            "information": self.info.summary(m),
            "uncertainty": [u.to_dict() for u in m.uncertainties if not u.resolved],
            "evidence": [e.to_dict() for e in m.evidence], "conflicts": [c.to_dict() for c in m.conflicts],
            "decision": m.decision.to_dict() if m.decision else None, "limitations": rep.limitations,
            "response": self.response.build(m, rep), "findings": [f.to_dict() for f in m.findings],
            "quality": {k: quality[k] for k in ("process_score", "failed_checks", "outcome_flag")},
            "stage": ("FINAL" if m.state in TERMINAL_MISSION else "IN_PROGRESS" if started else "PLANNED"),
            "planning_performed": plan is not None, "execution_performed": started,
            "verification_performed": verified, "planning_error": None,
            "timing_ms": {k: round(v, 4) for k, v in m.stage_ms.items()}, "cache": cache,
        }
        v = self.response.voice(m)
        if v:
            out["voice"] = v
        return out

    def _error_result(self, state: Any, exc: BaseException) -> Dict[str, Any]:
        return {"brain": self.brain_name, "version": self.VERSION, "role": self.ROLE, "status": "PLANNING_ERROR",
                "planning_status": None, "task_id": str(getattr(state, "task_id", "")), "mission": None,
                "objective": None, "tasks": [], "plan": None, "execution_plan": None,
                "planning_performed": False, "execution_performed": False, "verification_performed": False,
                "planning_error": f"{type(exc).__name__}: {str(exc)[:200]}"}

    # ================================================================== mission API
    def create_mission(self, request: str, mission_id: Optional[str] = None, parent_id: Optional[str] = None) -> Dict[str, Any]:
        t0 = mono_ns()
        try:
            with self.lock:
                ctx = self.context.from_text(request)
                mid = mission_id or f"m-{self.telemetry.counters.get('missions', 0) + 1}"
                old = self.registry.get(mid)
                if old is not None:
                    return {"ok": False, "error": "MISSION_EXISTS", "mission_id": mid}
                m = Mission(id=mid, request=ctx.request, parent_id=parent_id, media=ctx.media)
                self.registry.put(m)
                self.telemetry.count("missions")
                self._plan(m, ctx)
                return self._result(m, ctx, "miss")
        except Exception as exc:
            self.telemetry.error("create_mission", exc)
            return {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}
        finally:
            self.telemetry.observe("create_mission", mono_ns() - t0)

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        return self.registry.get(mission_id, touch=False)

    def get_mission_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        m = self.registry.get(task_id, touch=False)
        if m is not None:
            d = m.to_dict()
            d["tasks"] = [t.to_dict() for t in m.tasks.values()]
            d["plan"] = m.plan.to_dict() if m.plan else None
            return d
        return self.memory.recall(task_id)

    def _ok(self, m: Mission, **extra: Any) -> Dict[str, Any]:
        d = {"ok": True, "mission": m.summary(), "decision": m.decision.to_dict() if m.decision else None}
        d.update(extra)
        return d

    def _api(self, op: str, mission_id: str, fn: Callable[[Mission], Dict[str, Any]]) -> Dict[str, Any]:
        t0 = mono_ns()
        try:
            with self.lock:
                m = self.registry.get(mission_id)
                if m is None:
                    return {"ok": False, "error": "UNKNOWN_MISSION", "mission_id": mission_id}
                return fn(m)
        except Exception as exc:
            self.telemetry.error(op, exc)
            return {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}
        finally:
            self.telemetry.observe(op, mono_ns() - t0)

    # ---- handlers (used by the public methods and by receive_message) -----------
    def _h_task_started(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        t = m.find_task(str(p.get("task", "")))
        if t is None:
            return {"ok": False, "error": "UNKNOWN_TASK", "task": p.get("task")}
        if m.state in TERMINAL_MISSION:
            return {"ok": False, "error": "MISSION_FINISHED"}
        if t.state != TS.READY:
            return {"ok": False, "error": "TASK_NOT_READY", "state": t.state.value, "blocked_by": list(t.blocked_by)}
        move_task(m, t, TS.RUNNING, f"started by {src or 'executor'}")
        self._advance(m)
        return self._ok(m, task=t.to_dict())

    def _h_task_result(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        t = m.find_task(str(p.get("task", "")))
        if t is None:
            return {"ok": False, "error": "UNKNOWN_TASK", "task": p.get("task")}
        if m.state in TERMINAL_MISSION:
            return {"ok": False, "error": "MISSION_FINISHED"}
        if t.state in (TS.PENDING, TS.BLOCKED):
            return {"ok": False, "error": "PREREQUISITES_INCOMPLETE", "blocked_by": list(t.blocked_by)}
        if t.state in (TS.COMPLETED, TS.SKIPPED, TS.CANCELLED):
            return {"ok": False, "error": "TASK_ALREADY_FINAL", "state": t.state.value}
        if t.state == TS.FAILED:
            move_task(m, t, TS.READY, "retry")
        if t.state == TS.READY:
            move_task(m, t, TS.RUNNING, f"started by {src or 'executor'}")
        who = str(p.get("brain") or src or t.target or "")
        if bool(p.get("success", True)):
            move_task(m, t, TS.COMPLETED, f"result reported by {who}")
            t.result, t.failure = clip(str(p.get("summary", "")), 500), None
            for k in t.produces:
                r = m.info.get(k)
                if r is not None and r.state in OPEN_INFO:
                    self.info.update(m, k, InfoState.AVAILABLE_UNVERIFIED, who or f"task:{t.id}", note=f"produced by task {t.id}")
        else:
            t.failure = clip(str(p.get("failure") or "failed"), 200)
            move_task(m, t, TS.FAILED, t.failure)
            if t.attempts < self.cfg.max_attempts:
                move_task(m, t, TS.READY, "retry allowed")
            else:
                for k in t.produces:
                    r = m.info.get(k)
                    if r is not None and r.state in OPEN_INFO:
                        self.info.update(m, k, InfoState.UNAVAILABLE, who, note=f"task {t.id} failed")
        self._advance(m)
        return self._ok(m, task=t.to_dict())

    def _h_info_update(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        try:
            st = InfoState(str(p.get("state", "")).upper())
        except ValueError:
            return {"ok": False, "error": "INVALID_STATE", "allowed": [s.value for s in InfoState]}
        ok, why = self.info.update(m, str(p.get("key", "")), st, str(p.get("source") or src), p.get("observed_at_ns"), str(p.get("note", "")))
        if not ok:
            return {"ok": False, "error": "UNKNOWN_REQUIREMENT", "detail": why}
        self._advance(m)
        return self._ok(m)

    def _h_verification(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        ok, why = self.evidence.register(m, str(p.get("claim", "all")), p.get("verified"), str(p.get("source") or src),
                                         list(p.get("refs") or []), str(p.get("note", "")))
        if not ok:
            return {"ok": False, "error": "REJECTED", "detail": why}
        if not self.evidence.pending(m):
            for t in m.tasks.values():
                if t.verification and t.state in (TS.READY, TS.RUNNING):
                    if t.state == TS.READY:
                        move_task(m, t, TS.RUNNING, "verification reported")
                    move_task(m, t, TS.COMPLETED, "verification reported")
                    t.result = f"verification reported by {str(p.get('source') or src).upper()}"
        self._advance(m)
        return self._ok(m, status=why)

    def _h_brain_results(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        found = self.conflicts.scan_results(m, p.get("results") or {})
        for c in found:
            self.uncertainty._add(m, "CONFLICTING", f"conflict:{c.id}", "HIGH", c.text)
        self._advance(m)
        return self._ok(m, conflicts_found=[c.to_dict() for c in found])

    def _h_conflict(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        c = self.conflicts.report(m, str(p.get("kind", "BRAIN_OUTPUT")), list(p.get("parties") or [src]), str(p.get("text", "")), str(p.get("cause", "UNKNOWN")))
        self.uncertainty._add(m, "CONFLICTING", f"conflict:{c.id}", "HIGH", c.text)
        self._advance(m)
        return self._ok(m, conflict=c.to_dict())

    def _h_resolve_conflict(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        cid, basis = str(p.get("id", "")), str(p.get("basis", ""))
        ok = self.conflicts.preserve(m, cid, basis) if p.get("preserve") else self.conflicts.resolve(m, cid, basis)
        if ok:
            self.uncertainty.resolve(m, next((u.id for u in m.uncertainties if u.source == f"conflict:{cid}"), ""), basis)
        self._advance(m)
        return self._ok(m) if ok else {"ok": False, "error": "UNKNOWN_CONFLICT"}

    def _h_brain_unavailable(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        brain = str(p.get("brain", "")).upper()
        action = self.interrupts.classify(m, "BRAIN_UNAVAILABLE", {"brain": brain})
        if brain and brain not in m.down:
            m.down.append(brain)
        out = {}
        if action.replan:
            out = self._replan(m, f"{brain} is unavailable", self.context.from_text(m.request), self._capabilities(None, m))
        self.escalation.escalate(m, "OPERATIONAL", f"{brain} is unavailable: {p.get('reason', 'no reason given')}", "HIGH")
        self._advance(m)
        return self._ok(m, replan=out, affected_tasks=action.notes)

    def _h_constraint(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        kind, value = str(p.get("kind", "")), str(p.get("value", ""))
        m.constraints.append((kind, value))
        action = self.interrupts.classify(m, "NEW_CONSTRAINT", {"kind": kind})
        urg = self.priority.urgency_for(kind, value)
        if urg is not None and m.priority is not None:
            m.priority.urgency = max(m.priority.urgency, urg)
            m.priority.level = self.priority.level_for(m.priority.importance, m.priority.urgency,
                                                       m.intent.mission_type if m.intent else "OTHER", bool(m.intent and m.intent.crisis))
            m.priority.reasons.append(f"{kind}:{value}")
        out = {}
        if action.replan and m.intent is not None:
            out = self._replan(m, f"new constraint {kind}", self.context.from_text(m.request), self._capabilities(None, m))
        self.priority.apply_to_tasks(m)
        self._advance(m)
        return self._ok(m, replan=out)

    def _h_priority(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        level = str(p.get("level", "")).upper()
        if level not in LEVELS or m.priority is None:
            return {"ok": False, "error": "INVALID_LEVEL", "allowed": list(LEVELS)}
        m.priority.level = level
        m.priority.reasons.append(f"changed_by:{src or 'api'}")
        self.priority.apply_to_tasks(m)
        m.touch()
        return self._ok(m)

    def _h_update_request(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        if m.state in TERMINAL_MISSION:
            return {"ok": False, "error": "MISSION_FINISHED"}
        ctx = self.context.from_text(str(p.get("text", "")))
        if not ctx.request:
            return {"ok": False, "error": "EMPTY_REQUEST"}
        out = self._apply_update(m, ctx)
        return self._ok(m, update=out)

    def _h_cancel(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        if m.state in TERMINAL_MISSION:
            return {"ok": False, "error": "MISSION_FINISHED"}
        for t in m.tasks.values():
            if t.state not in (TS.COMPLETED, TS.CANCELLED, TS.SKIPPED, TS.FAILED):
                move_task(m, t, TS.CANCELLED, "mission cancelled")
        if self._move(m, MS.CANCELLED, str(p.get("reason", "cancelled"))):
            m.outcome = Outcome.CANCELLED
            m.decision = DecisionRecord(Decision.BLOCK, ["mission_cancelled"], {}, now_ns())
            self._sync_plan_state(m)
            self._finalize(m)
        return self._ok(m)

    def _h_evaluate(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        self._advance(m)
        return self._ok(m, completion=self.completion.evaluate(m).to_dict())

    def _h_replan(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        if m.intent is None:
            return {"ok": False, "error": "NOTHING_TO_REPLAN"}
        out = self._replan(m, str(p.get("reason", "requested")), self.context.from_text(m.request), self._capabilities(None, m))
        self._advance(m)
        return self._ok(m, replan=out)

    def _h_status(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        return self._ok(m, tasks=[{"id": t.id, "key": t.key, "state": t.state.value, "target": t.target} for t in m.tasks.values()])

    def _h_explain(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        subject = str(p.get("subject", "")).lower()
        rows = [{"at_ns": a, "kind": k, "subject": s, "reason": r} for a, k, s, r in m.ledger
                if not subject or subject in s.lower() or subject in r.lower() or subject in k.lower()]
        return self._ok(m, explanation=rows[-60:])

    def _h_audit(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        return self._ok(m, audit=self.audit_mission(m))

    def _h_outcome(self, m: Mission, p: Dict[str, Any], src: str) -> Dict[str, Any]:
        m.external_success = bool(p.get("success"))
        m.quality = self.quality.analyze(m)
        return self._ok(m, quality=m.quality)

    _COMMANDS = {
        "task_started": "_h_task_started", "task_result": "_h_task_result", "info_update": "_h_info_update",
        "verification_result": "_h_verification", "brain_results": "_h_brain_results", "conflict": "_h_conflict",
        "resolve_conflict": "_h_resolve_conflict", "brain_unavailable": "_h_brain_unavailable",
        "constraint": "_h_constraint", "priority": "_h_priority", "update_request": "_h_update_request",
        "cancel": "_h_cancel", "evaluate": "_h_evaluate", "replan": "_h_replan", "status": "_h_status",
        "explain": "_h_explain", "audit": "_h_audit", "outcome": "_h_outcome",
    }

    def apply_event(self, mission_id: str, command: str, payload: Optional[Dict[str, Any]] = None, source: str = "") -> Dict[str, Any]:
        name = self._COMMANDS.get(str(command).lower())
        if name is None:
            return {"ok": False, "error": "UNKNOWN_COMMAND", "allowed": sorted(self._COMMANDS)}
        fn = getattr(self, name)
        return self._api(str(command).lower(), mission_id, lambda m: fn(m, payload or {}, source))

    # convenience wrappers
    def report_task_started(self, mission_id: str, task: str, source: str = "") -> Dict[str, Any]:
        return self.apply_event(mission_id, "task_started", {"task": task}, source)

    def report_task_result(self, mission_id: str, task: str, success: bool = True, summary: str = "",
                           failure: str = "", source: str = "") -> Dict[str, Any]:
        return self.apply_event(mission_id, "task_result", {"task": task, "success": success, "summary": summary, "failure": failure}, source)

    def report_information(self, mission_id: str, key: str, state: str, source: str = "", note: str = "") -> Dict[str, Any]:
        return self.apply_event(mission_id, "info_update", {"key": key, "state": state, "source": source, "note": note}, source)

    def report_verification(self, mission_id: str, claim: str, verified: Optional[bool], source: str, refs: Optional[List[str]] = None) -> Dict[str, Any]:
        return self.apply_event(mission_id, "verification_result", {"claim": claim, "verified": verified, "source": source, "refs": refs or []}, source)

    def report_brain_unavailable(self, mission_id: str, brain: str, reason: str = "") -> Dict[str, Any]:
        return self.apply_event(mission_id, "brain_unavailable", {"brain": brain, "reason": reason})

    def update_request(self, mission_id: str, text: str) -> Dict[str, Any]:
        return self.apply_event(mission_id, "update_request", {"text": text})

    def cancel_mission(self, mission_id: str, reason: str = "") -> Dict[str, Any]:
        return self.apply_event(mission_id, "cancel", {"reason": reason})

    def evaluate(self, mission_id: str) -> Dict[str, Any]:
        return self.apply_event(mission_id, "evaluate")

    def explain(self, mission_id: str, subject: str = "") -> Dict[str, Any]:
        return self.apply_event(mission_id, "explain", {"subject": subject})

    def audit(self, mission_id: str) -> Dict[str, Any]:
        return self.apply_event(mission_id, "audit")

    def receive_message(self, message: str, state: Any, source_brain: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload if isinstance(payload, dict) else {}
        cmd = str(payload.get("type") or payload.get("command") or "").lower()
        mid = str(payload.get("mission_id") or getattr(state, "task_id", "") or "")
        base: Dict[str, Any] = {"brain": self.brain_name, "received": True, "from": source_brain, "message": message,
                                "command": cmd or None}
        if not cmd:
            return {**base, "ok": True, "note": "message recorded; no command was given"}
        return {**base, **self.apply_event(mid, cmd, payload, str(source_brain or ""))}

    # ================================================================== audit, health, identity
    def audit_mission(self, m: Mission) -> Dict[str, Any]:
        """Check a mission against HEROIC's own engineering rules. Returns the violations found."""
        v: List[str] = []
        tasks = list(m.tasks.values())
        for r in m.info.values():
            if r.state in _AVAILABLE and not r.source:
                v.append(f"fabricated_information: '{r.key}' is marked available with no source")
        if m.intent and m.intent.hypotheses and not any(t.key == "challenge_hypothesis" for t in tasks):
            v.append("blind_agreement: a user belief has no task that tests it")
        if m.state == MS.COMPLETED and any(t.mandatory and t.state not in DONE_TASK for t in tasks):
            v.append("premature_completion: mandatory work is not done")
        lim = " ".join(collect_limitations(m)).lower()
        for r in m.info.values():
            if r.state in OPEN_INFO and r.gap.value in ("CRITICAL", "MATERIAL") and r.text.lower() not in lim:
                v.append(f"hidden_uncertainty: '{r.key}' gap is not in the limitations")
        if m.plan is not None and m.plan.issues:
            v.append("invalid_dependencies: " + "; ".join(m.plan.issues[:3]))
        for t in tasks:
            if t.state in (TS.RUNNING, TS.COMPLETED) and any(m.tasks[d].state not in DONE_TASK for d in t.deps if d in m.tasks):
                v.append(f"invalid_readiness: {t.id} ran before its prerequisites")
            if t.state in (TS.RUNNING, TS.COMPLETED) and any(
                    (m.info.get(k) is not None and m.info[k].state not in _AVAILABLE) for k in t.needs):
                v.append(f"unauthorised_execution: {t.id} ran without its required information")
            if t.target == "HEROIC":
                v.append(f"role_confusion: {t.id} is assigned to HEROIC")
            if t.state == TS.COMPLETED and not t.started_ns and not t.preserved:
                v.append(f"unsupported_execution_claim: {t.id} is completed but was never started")
        if m.replans > self.cfg.max_replans:
            v.append("uncontrolled_replanning")
        live = {o.id for o in m.objectives.values() if o.status != "DROPPED"}
        for t in tasks:
            if t.state not in (TS.CANCELLED, TS.SKIPPED) and live and not (set(t.serves) & live):
                v.append(f"objective_drift: {t.id} serves no live objective")
        tgt = {t.target for t in tasks if t.target}
        for b in m.activation.get("required_brains", []):
            if b not in tgt and b != "ALPHA":
                v.append(f"unnecessary_activation: {b}")
        return {"ok": not v, "violations": v, "rules_checked": 11}

    def health(self) -> Dict[str, Any]:
        return build_health(self)

    def contract(self) -> Dict[str, Any]:
        return build_contract(self)

    def learning_signals(self) -> Dict[str, Any]:
        return self.evolution.signals()

    def status(self) -> Dict[str, Any]:
        h = self.health()
        return {"brain": self.brain_name, "version": self.VERSION, "status": h["status"], "ready": h["ready"],
                "missions_live": h["missions"]["live"], "think_p50_ms": h["latency"]["think"]["p50_ms"],
                "think_p95_ms": h["latency"]["think"]["p95_ms"]}

    def reset(self) -> Dict[str, Any]:
        with self.lock:
            n = self.registry.clear()
            self.intent._cached.cache_clear()
        return {"ok": True, "missions_cleared": n}

    def identity(self) -> Dict[str, Any]:
        base = super().identity()
        base.update({
            "version": self.VERSION, "role": self.ROLE, "architecture_stage": self.ARCHITECTURE_STAGE,
            "central_question": "WHAT ACTUALLY NEEDS TO BE ACCOMPLISHED?",
            "principle": "Never optimise for producing an answer. Optimise for the best justified outcome.",
            "engines": ["intent", "context", "objectives", "information", "uncertainty", "capabilities", "task_planner",
                        "dependency_planner", "priority", "evidence", "conflict", "sufficiency", "decision_quality",
                        "monitor", "replanner", "interrupts", "completion", "escalation", "response", "mission_memory",
                        "evolution_interface", "health_contract"],
            "rules": list(self.RULES), "executes_tasks": False, "writes_user_text": self.cfg.speak,
            "limits": {"max_missions": self.cfg.max_missions, "max_tasks": self.cfg.max_tasks,
                       "max_replans": self.cfg.max_replans, "max_rounds": self.cfg.max_rounds}})
        return base
