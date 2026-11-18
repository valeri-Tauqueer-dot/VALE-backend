"""Task planner, dependency planner and execution-plan builder.

The planner builds the smallest plan that fully covers the mission. The dependency planner validates the graph
in O(V+E): topological order, cycle detection, parallel layers, critical path and readiness. The execution plan
is a hand-over document for ALPHA. HEROIC never executes tasks and never marks planned work as done.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..core.config import HeroicConfig
from ..core.enums import DONE_TASK, OPEN_INFO, InfoState, PlanState, PlanType, TaskState
from ..core.models import IntentProfile, Mission, Plan, Task
from ..core.statemachine import move_task
from ..core.util import clip, fingerprint, now_ns
from .capabilities import CapabilityRegistry
from .context import Context
from .intent import comparison_subjects

_AVAILABLE = (InfoState.AVAILABLE_VERIFIED, InfoState.AVAILABLE_UNVERIFIED)


@dataclass(slots=True)
class _Spec:
    key: str
    kind: str
    cap: str
    name: str
    desc: str
    after: List[str]
    soft: List[str]
    cost: float
    mandatory: bool
    role: str
    out: str
    criteria: Tuple[str, ...]
    verification: bool
    produces: Tuple[str, ...]
    needs: Tuple[str, ...]


class _B:
    def __init__(self) -> None:
        self.specs: Dict[str, _Spec] = {}

    def add(self, key, kind, cap, name, desc, after=(), soft=(), cost=1.0, mandatory=True, role="primary",
            out="", criteria=(), verification=False, produces=(), needs=()) -> str:
        if key not in self.specs:
            self.specs[key] = _Spec(key, kind, cap, name, desc, [a for a in after if a], [s for s in soft if s],
                                    cost, mandatory, role, out or "Result that satisfies the objective",
                                    tuple(criteria) or ("Output is produced and consistent with the objective",),
                                    verification, tuple(produces), tuple(needs))
        return key

    def split_leaves(self) -> Tuple[List[str], List[str]]:
        """What the next step must wait for.

        hard: mandatory tasks that no other mandatory task builds on. soft: optional tasks nothing builds on.
        An optional task hanging off a mandatory one never hides that mandatory task from the next step."""
        ref_any, ref_hard = set(), set()
        for s in self.specs.values():
            ref_any.update(s.after)
            ref_any.update(s.soft)
            if s.mandatory:
                ref_hard.update(s.after)          # only a hard link from a mandatory task counts as "built upon"
        hard = [k for k, s in self.specs.items() if s.mandatory and k not in ref_hard and k != "compose_answer"]
        soft = [k for k, s in self.specs.items() if not s.mandatory and k not in ref_any and k != "compose_answer"]
        return hard, soft


def _cap_for(mtype: str, domains: Tuple[str, ...]) -> str:
    if mtype == "EXECUTION" or mtype == "MONITORING":
        return "orchestration"
    if mtype == "DIAGNOSTIC":
        return "system_monitoring"
    if mtype == "EXPLANATION" and "VALE" in domains:
        return "knowledge"
    if "MARKET" in domains and mtype in ("ANALYSIS", "RESEARCH", "DECISION_SUPPORT", "COMPARISON", "PLANNING", "EXPLANATION"):
        return "market_intelligence"
    if "HUMAN" in domains and mtype in ("CREATION", "CONVERSATION"):
        return "human_perspective"
    return "general_reasoning"


class TaskPlanner:
    def __init__(self, cfg: HeroicConfig) -> None:
        self.cfg = cfg

    def build(self, m: Mission, intent: IntentProfile, ctx: Context, caps: CapabilityRegistry,
              reuse: Optional[Dict[str, str]] = None) -> None:
        m.tasks.clear()
        b = _B()
        subj = clip(intent.subject or intent.text, 80)
        self._chain(b, m, intent, subj)
        self._finish(b, m, intent, subj)
        self._instantiate(b, m, intent, caps, ctx, reuse or {})
        m.baseline_tasks = len(m.tasks)

    # ------------------------------------------------------------------ mission chains
    def _chain(self, b: _B, m: Mission, I: IntentProfile, subj: str) -> None:
        mt, dom = I.mission_type, I.domains
        market, human, vale = "MARKET" in dom, "HUMAN" in dom, "VALE" in dom
        live_key = "market_data" if "market_data" in m.info else "fresh_information" if "fresh_information" in m.info else None
        support = None
        if human and (I.emotional or mt in ("CONVERSATION", "CREATION", "DECISION_SUPPORT", "PLANNING", "ANALYSIS")):
            support = b.add("human_support" if I.crisis else "understand_human_context", "REASONING", "human_understanding",
                            "Provide human support first" if I.crisis else "Understand the human context",
                            f"Recognise the emotion and what the person needs in: {subj}", cost=1.2,
                            out="Emotional context and the person's needs",
                            criteria=("The emotion and need are identified",))
        acq = None
        if live_key and mt not in ("CONVERSATION", "MONITORING"):
            acq = b.add("acquire_information", "DATA", "external_information", "Acquire current information",
                        f"Retrieve current, sourced information about {subj}", cost=1.5, produces=(live_key,),
                        role="fresh" if any(o.text.startswith("Use current") for o in m.objectives.values()) else "primary",
                        out="Sourced, timestamped information", criteria=("Sources and retrieval time are recorded",))

        if mt == "CONVERSATION":
            if market and I.emotional:
                b.add("market_context", "REASONING", "market_intelligence", "Check the market context the person mentions",
                      f"Look at the market situation behind: {subj}", after=[support], cost=2.0, mandatory=False)
        elif mt == "EXPLANATION":
            k = b.add("recall_knowledge", "KNOWLEDGE", "knowledge", "Recall stored knowledge",
                      f"Find what VALE already knows about {subj}", after=[acq], cost=0.6,
                      out="Relevant stored knowledge")
            complex_q = I.token_count >= 9 or bool(I.tokens & {"how", "why"}) or bool(I.secondary_types)
            if complex_q and not vale:
                b.add("reason_about_topic", "REASONING", "market_intelligence" if market else "general_reasoning",
                      "Reason about the topic", f"Work out a clear explanation of {subj}", after=[acq], soft=[k], cost=1.8)
        elif mt in ("RESEARCH", "ANALYSIS") and market:
            self._market_chain(b, I, subj, acq, deep=True, risk=False)
            if mt == "ANALYSIS":
                b.add("challenge_findings", "REASONING", "market_intelligence", "Challenge the findings",
                      f"Look for counter-evidence and alternative explanations for {subj}",
                      after=["competing_hypotheses"], cost=1.5, mandatory=False)
        elif mt in ("RESEARCH", "ANALYSIS", "OTHER"):
            k = b.add("recall_knowledge", "KNOWLEDGE", "knowledge", "Recall stored knowledge",
                      f"Find what VALE already knows about {subj}", after=[acq], cost=0.6)
            a = b.add("analyze_findings", "REASONING", "general_reasoning",
                      "Analyse the evidence" if mt != "OTHER" else "Understand the request",
                      f"Reason about {subj} using the information gathered", after=[acq, k], cost=2.0)
            if mt == "ANALYSIS":
                b.add("challenge_findings", "REASONING", "general_reasoning", "Challenge the findings",
                      f"Look for counter-evidence and alternative explanations for {subj}", after=[a], cost=1.5, mandatory=False)
        elif mt == "COMPARISON":
            cap = "market_intelligence" if market else "general_reasoning"
            subs = comparison_subjects(I.text)[:4] or [subj]
            profs = [b.add(f"profile_{i + 1}", "REASONING", cap, f"Profile: {s}", f"Gather the key facts about {s}",
                           after=[acq], cost=1.5) for i, s in enumerate(subs)]
            b.add("compare", "REASONING", cap, "Compare against shared criteria",
                  f"Compare {', '.join(subs)} on the same criteria and state the trade-offs", after=profs, cost=2.0)
        elif mt == "DECISION_SUPPORT":
            if market:
                self._market_chain(b, I, subj, acq, deep=False, risk=True)
                b.add("challenge_findings", "REASONING", "market_intelligence", "Challenge the recommendation basis",
                      f"Look for counter-evidence before any recommendation about {subj}",
                      after=["risk_assessment"], cost=1.5)
            else:
                o = b.add("gather_options", "REASONING", "general_reasoning", "Gather the options", f"List the real options for {subj}",
                          after=[acq, support], cost=1.5)
                t = b.add("evaluate_tradeoffs", "REASONING", "general_reasoning", "Evaluate trade-offs",
                          f"Weigh benefits, costs and risks of each option for {subj}", after=[o], cost=2.0)
                r = b.add("risk_check", "REASONING", "general_reasoning", "Check risks", f"Identify the main risks of {subj}",
                          after=[o], cost=1.2)
                b.add("challenge_findings", "REASONING", "general_reasoning", "Challenge the recommendation basis",
                      "Look for counter-evidence and what would change the answer", after=[t, r], cost=1.2)
        elif mt == "PLANNING":
            cap = "strategy_intelligence" if market else "general_reasoning"
            c = b.add("define_constraints", "REASONING", "general_reasoning", "Define goal and constraints",
                      f"State the goal, limits and success measure for {subj}", after=[support], cost=1.0)
            o = b.add("generate_options", "REASONING", cap, "Generate options", f"Generate workable ways to achieve {subj}",
                      after=[c], cost=2.0)
            b.add("evaluate_tradeoffs", "REASONING", cap, "Evaluate trade-offs", "Compare the options and pick a sensible path",
                  after=[o], cost=1.8)
        elif mt == "CREATION":
            cl = b.add("clarify_requirements", "REASONING", "general_reasoning", "Clarify requirements",
                       f"Work out audience, tone and length for {subj}", after=[support], cost=0.8, mandatory=False)
            persp = None
            if human:
                persp = b.add("human_perspective", "REASONING", "human_perspective", "Consider the other person's view",
                              "Think about how the message will be received", after=[support], cost=1.2)
            d = b.add("draft_content", "REASONING", "general_reasoning", "Draft the content", f"Write: {subj}",
                      after=[cl, persp or support], cost=2.0, out="A complete draft")
            b.add("review_content", "REASONING", "general_reasoning", "Review the draft", "Check accuracy, tone and fit with the request",
                  after=[d], cost=1.0)
        elif mt == "EXECUTION":
            f = b.add("assess_feasibility", "REASONING", "general_reasoning", "Assess feasibility and risk",
                      f"Check that {subj} can be done safely", after=[acq], cost=1.2)
            p = b.add("prepare_actions", "SYSTEM", "orchestration", "Prepare the actions",
                      "Prepare the exact steps without performing them", after=[f], cost=1.2)
            a = b.add("request_authorization", "COMMUNICATION", "conversation", "Ask the user to authorise",
                      "Show the prepared steps and ask for explicit confirmation before anything is done",
                      after=[p], cost=0.4, role="auth", out="The user's explicit yes or no")
            e = b.add("execute_actions", "SYSTEM", "orchestration", "Perform the actions",
                      "Perform the prepared steps. Only after explicit user authorisation.", after=[a], cost=2.5,
                      needs=("execution_authorization",), role="auth", out="Action results reported by the executor")
            b.add("verify_outcome", "VERIFICATION", "verification", "Verify the outcome", "Check the real result of the actions",
                  after=[e], cost=1.2, verification=True)
        elif mt == "MONITORING":
            c = b.add("define_conditions", "REASONING", "general_reasoning", "Define what to watch",
                      f"State the exact condition, threshold and frequency for {subj}", cost=1.0)
            f = b.add("establish_data_feed", "DATA", "market_data" if market else "external_information",
                      "Establish the data feed", "Confirm a reliable, timestamped data source", after=[c], cost=1.5,
                      produces=(live_key,) if live_key else ())
            s = b.add("schedule_checks", "SYSTEM", "orchestration", "Schedule the checks", "Schedule recurring checks",
                      after=[f], cost=1.0)
            b.add("define_alerts", "COMMUNICATION", "conversation", "Define the alerts", "Decide how and when the user is told",
                  after=[s], cost=0.5)
        elif mt == "DIAGNOSTIC":
            c = b.add("collect_health", "SYSTEM", "system_monitoring", "Collect health signals",
                      f"Collect health, error and timing signals for {subj}", cost=1.2)
            b.add("analyze_findings", "REASONING", "general_reasoning", "Analyse the findings",
                  "Explain what the signals mean", after=[c], cost=1.5)

    def _market_chain(self, b: _B, I: IntentProfile, subj: str, acq, deep: bool, risk: bool) -> None:
        d = b.add("qualify_market_data", "DATA", "market_data", "Qualify the market data",
                  f"Check provenance, timestamps, freshness and gaps of the data for {subj}", after=[acq], cost=1.5,
                  out="Qualified market data state", criteria=("Source and timestamp stated", "Gaps and staleness listed"))
        s = b.add("market_structure", "REASONING", "market_intelligence", "Analyse market structure",
                  f"Trend, range, swings and structural change for {subj}", after=[d], cost=2.0)
        r = b.add("market_regime", "REASONING", "market_intelligence", "Classify the market regime",
                  f"Regime and regime transition for {subj}", after=[d], cost=2.0)
        l = b.add("liquidity_volatility", "REASONING", "market_intelligence", "Assess liquidity and volatility",
                  f"Liquidity, volatility and shock behaviour for {subj}", after=[d], cost=2.0)
        h = b.add("historical_context", "REASONING", "market_intelligence", "Compare historical analogues",
                  f"Compare comparable historical periods for {subj} and state where comparison stops being valid",
                  after=[d], cost=2.5, mandatory=False) if deep else None
        hyp = b.add("competing_hypotheses", "REASONING", "market_intelligence", "Generate and test competing hypotheses",
                    f"Build competing explanations for {subj} and the evidence each one needs",
                    after=[s, r, l], soft=[h], cost=3.0, out="Competing hypotheses with supporting and opposing evidence")
        if risk:
            b.add("risk_assessment", "REASONING", "market_intelligence", "Assess risk and invalidation",
                  f"Risks, drawdown exposure and what would invalidate each view on {subj}", after=[hyp], cost=1.5)

    # ------------------------------------------------------------------ modifiers shared by every mission
    def _finish(self, b: _B, m: Mission, I: IntentProfile, subj: str) -> None:
        roots = [k for k, s in b.specs.items() if not s.after and k == "acquire_information"]
        if len(I.sub_intents) >= 2:
            sec = [o for o in m.objectives.values() if o.kind == "SECONDARY"][: len(I.sub_intents) - 1]
            for i, ((stype, seg), obj) in enumerate(zip(I.sub_intents[1:], sec), start=1):
                if stype == I.mission_type:
                    continue                      # the main chain already covers it; compose_answer serves it
                cap = _cap_for(stype, I.domains)
                kind = "KNOWLEDGE" if cap == "knowledge" else "SYSTEM" if cap in ("orchestration", "system_monitoring") else "REASONING"
                b.add(f"follow_up_{i}", kind, cap, f"Address part {i + 1} of the request", clip(seg, 120), after=roots,
                      cost=1.5, role=f"sec:{obj.id}")
        if I.hypotheses:
            hard, soft = b.split_leaves()
            b.add("challenge_hypothesis", "REASONING", "general_reasoning", "Test the user's stated belief",
                  "Check the belief against evidence and say plainly whether it holds. Do not assume it is true.",
                  after=hard or roots, soft=soft, cost=1.5, role="hyp")
        if any(e.status == "REQUIRED" for e in m.evidence):
            hard, soft = b.split_leaves()
            b.add("verify_claims", "VERIFICATION", "verification", "Verify the material claims",
                  "Check evidence, provenance and contradictions behind the claims before they are stated",
                  after=hard, soft=soft, cost=2.0, verification=True, out="Verification result per claim")
        # the final reply is always added last, so it can never start before the work it depends on
        hard, soft = b.split_leaves()
        if I.mission_type == "CONVERSATION":
            b.add("compose_answer", "COMMUNICATION", "conversation", "Respond conversationally",
                  "Reply in a natural, human way", after=hard, soft=soft, cost=0.4, role="all")
        else:
            b.add("compose_answer", "COMMUNICATION", "conversation", "Compose the answer",
                  "Write the answer: findings, evidence, uncertainty and limitations stated plainly",
                  after=hard, soft=soft, cost=0.8, role="all", out="Final answer for the user")

    # ------------------------------------------------------------------ build Task objects
    def _instantiate(self, b: _B, m: Mission, I: IntentProfile, caps: CapabilityRegistry, ctx: Context,
                     reuse: Dict[str, str]) -> None:
        specs = list(b.specs.values())
        if len(specs) > self.cfg.max_tasks:
            keep = [s for s in specs if s.mandatory] + [s for s in specs if not s.mandatory]
            specs = [s for s in specs if s in keep[: self.cfg.max_tasks]]
        fresh = next((o.id for o in m.objectives.values() if o.text.startswith("Use current")), None)
        auth = next((o.id for o in m.objectives.values() if o.text.startswith("Obtain explicit")), None)
        hyp = next((o.id for o in m.objectives.values() if o.text.startswith("Test the user")), None)
        primary = m.primary()
        pid = primary.id if primary else ""
        urgent = bool(m.priority and m.priority.urgency >= 0.85)

        ids = {s.key: reuse.get(fingerprint(s.kind, s.cap, s.key, s.name)) or m.next_id("t") for s in specs}
        for s in specs:
            serves = [pid]
            if s.role == "fresh" and fresh:
                serves.append(fresh)
            elif s.role == "auth" and auth:
                serves.append(auth)
            elif s.role == "hyp" and hyp:
                serves = [hyp]
            elif s.role.startswith("sec:"):
                serves = [s.role[4:]]
            elif s.role == "all":
                serves = [o.id for o in m.objectives.values()
                          if o.kind in ("PRIMARY", "SECONDARY") and not o.text.startswith("Test the user")]
            r = caps.resolve(s.cap)
            t = Task(id=ids[s.key], key=s.key, name=s.name, description=s.desc, kind=s.kind, capability=s.cap,
                     target=r.provider, degraded=r.degraded, serves=tuple(x for x in serves if x),
                     deps=[ids[a] for a in s.after if a in ids], soft_deps=[ids[a] for a in s.soft if a in ids],
                     needs=s.needs, produces=s.produces, mandatory=s.mandatory, cost=s.cost,
                     expected_output=s.out, criteria=s.criteria, verification=s.verification,
                     fp=fingerprint(s.kind, s.cap, s.key, s.name))
            if r.degraded:
                t.note = f"using {r.provider}: {r.reason}"
            if not r.available:
                if s.mandatory:
                    t.state, t.blocked_by, t.note = TaskState.BLOCKED, [f"capability:{s.cap}"], r.reason
                else:
                    t.state, t.note, t.ended_ns = TaskState.SKIPPED, f"optional capability unavailable: {r.reason}", now_ns()
            elif s.produces and all(k in m.info and m.info[k].state in _AVAILABLE for k in s.produces):
                t.state, t.note, t.ended_ns = TaskState.SKIPPED, "already satisfied: information is present in the shared state", now_ns()
            elif urgent and not s.mandatory:
                t.state, t.note, t.ended_ns = TaskState.SKIPPED, "optional work skipped to meet the deadline", now_ns()
            m.tasks[t.id] = t


class DependencyPlanner:
    """Validates the task graph and computes everything derived from it."""

    def analyze(self, m: Mission, reason: str = "initial") -> List[str]:
        tasks = list(m.tasks.values())
        n = len(tasks)
        idx = {t.id: i for i, t in enumerate(tasks)}
        issues: List[str] = []
        preds: List[List[int]] = [[] for _ in range(n)]
        succ: List[List[int]] = [[] for _ in range(n)]
        edges = 0
        for i, t in enumerate(tasks):
            for d in t.deps:
                j = idx.get(d)
                if j is None:
                    issues.append(f"UNKNOWN_DEPENDENCY: {t.id} needs {d}")
                elif j == i:
                    issues.append(f"SELF_DEPENDENCY: {t.id}")
                else:
                    preds[i].append(j)
                    succ[j].append(i)
                    edges += 1
        indeg = [len(p) for p in preds]
        queue = [i for i in range(n) if indeg[i] == 0]
        head = 0
        while head < len(queue):
            u = queue[head]
            head += 1
            for v in succ[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    queue.append(v)
        if len(queue) < n:
            issues.append("CYCLE: " + self._cycle(tasks, preds, indeg))
        order = queue if len(queue) == n else queue + [i for i in range(n) if i not in set(queue)]

        level = [0] * n
        dist = [0.0] * n
        prev = [-1] * n
        for u in order:
            cost = 0.0 if tasks[u].state == TaskState.SKIPPED else tasks[u].cost
            best, bd = -1, 0.0
            for p in preds[u]:
                if level[p] + 1 > level[u]:
                    level[u] = level[p] + 1
                if best == -1 or dist[p] > bd:
                    best, bd = p, dist[p]
            dist[u] = cost + (bd if best != -1 else 0.0)
            prev[u] = best
        layers: List[List[str]] = []
        for u in order:
            tasks[u].level = level[u]
            while len(layers) <= level[u]:
                layers.append([])
            layers[level[u]].append(tasks[u].id)
        path: List[str] = []
        end = max(range(n), key=lambda i: dist[i]) if n else -1
        crit = dist[end] if n else 0.0
        while end != -1:
            path.append(tasks[end].id)
            end = prev[end]
        path.reverse()

        width = max((len(x) for x in layers), default=0)
        ptype = (PlanType.SINGLE_TASK if n <= 1 else PlanType.PARALLEL if edges == 0
                 else PlanType.SEQUENTIAL if width == 1 else PlanType.MULTI_TASK)
        for r in m.info.values():
            if r.resolvable == "TOOL" and r.state in OPEN_INFO and not any(r.key in t.produces for t in tasks):
                issues.append(f"UNPRODUCIBLE_INFORMATION: nothing in the plan can produce '{r.key}'")
        final = next((i for i, t in enumerate(tasks) if t.key == "compose_answer"), -1)
        if final >= 0 and not any(i.startswith("CYCLE") for i in issues):
            anc, stack = set(), [final]
            while stack:
                u = stack.pop()
                for p in preds[u]:
                    if p not in anc:
                        anc.add(p)
                        stack.append(p)
            for i, t in enumerate(tasks):
                if i != final and t.mandatory and i not in anc:
                    issues.append(f"UNJOINED_WORK: {t.id} ({t.key}) is not a prerequisite of the final answer")
        old = m.plan
        # derived state is reset before it is rebuilt, so old values can never leak into a new plan
        m.plan = Plan(id=old.id if old else m.next_id("p"), version=(old.version + 1) if old else 1, type=ptype,
                      state=PlanState.DRAFT, order=[tasks[i].id for i in order], layers=layers, critical_path=path,
                      critical_cost=crit, total_cost=sum(t.cost for t in tasks if t.state != TaskState.SKIPPED),
                      issues=issues, edges=edges, reason=reason, created_ns=now_ns())
        return issues

    @staticmethod
    def _cycle(tasks: List[Task], preds: List[List[int]], indeg: List[int]) -> str:
        remaining = {i for i, d in enumerate(indeg) if d > 0}
        if not remaining:
            return "unknown"
        cur = next(iter(remaining))
        seen: Dict[int, int] = {}
        chain: List[int] = []
        while cur not in seen:
            seen[cur] = len(chain)
            chain.append(cur)
            nxt = [p for p in preds[cur] if p in remaining]
            if not nxt:
                break
            cur = nxt[0]
        loop = chain[seen[cur]:] if cur in seen else chain
        names = [tasks[i].id for i in reversed(loop)]
        return " -> ".join(names + names[:1])

    def refresh_readiness(self, m: Mission) -> List[str]:
        """Set PENDING / READY / BLOCKED for every task that has not started. Returns the ids that changed."""
        if m.plan is None:
            return []
        changed: List[str] = []
        for tid in m.plan.order:
            t = m.tasks[tid]
            if t.state in (TaskState.RUNNING, TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.SKIPPED):
                continue
            blockers = [b for b in t.blocked_by if b.startswith("capability:")]
            waiting = False
            for d in t.deps:
                ds = m.tasks[d].state
                if ds in (TaskState.FAILED, TaskState.CANCELLED):
                    blockers.append(f"failed:{d}")
                elif ds == TaskState.BLOCKED:
                    blockers.append(f"upstream:{d}")
                elif ds not in DONE_TASK:
                    waiting = True
            for k in t.needs:
                info = m.info.get(k)
                if info is not None and info.state not in _AVAILABLE:
                    blockers.append(f"info:{k}")
            new = TaskState.BLOCKED if blockers else TaskState.PENDING if waiting else TaskState.READY
            if new != t.state:
                if move_task(m, t, new, ",".join(blockers) or "dependencies satisfied"):
                    changed.append(tid)
            t.blocked_by = blockers
        return changed


class ExecutionPlanBuilder:
    _RES = ((1.5, "LIGHT"), (3.0, "MEDIUM"), (99.0, "HEAVY"))

    def build(self, m: Mission) -> Dict[str, Any]:
        plan = m.plan
        if plan is None:
            return {}
        primary = m.primary()
        tasks, a_tasks, a_deps = [], [], []
        for tid in plan.order:
            t = m.tasks[tid]
            res = next(r for c, r in self._RES if t.cost <= c)
            tasks.append({"id": t.id, "name": t.key, "title": t.name, "kind": t.kind, "capability": t.capability,
                          "target": t.target, "degraded": t.degraded, "priority": t.priority, "state": t.state.value,
                          "mandatory": t.mandatory, "deps": list(t.deps), "soft_deps": list(t.soft_deps),
                          "needs_information": list(t.needs), "serves": list(t.serves), "level": t.level,
                          "relative_cost": t.cost, "expected_output": t.expected_output, "criteria": list(t.criteria)})
            a_tasks.append({"name": t.key, "task_kind": t.kind, "description": t.description, "target": t.target,
                            "capability": t.capability, "priority": t.priority, "resource_class": res,
                            "input_data": {"objective": primary.text if primary else m.request, "mission_id": m.id},
                            "metadata": {"source": "HEROIC", "task_id": t.id, "serves": list(t.serves),
                                         "mandatory": t.mandatory, "verification": t.verification,
                                         "needs_information": list(t.needs), "expected_output": t.expected_output,
                                         "state_at_handover": t.state.value}})
            for d in t.deps:
                dep = m.tasks[d]
                a_deps.append({"dependent_task_name": t.key, "prerequisite_task_name": dep.key,
                               "dependency_type": "VERIFICATION" if t.verification else "DATA" if dep.kind == "DATA" else "REQUIRES",
                               "required": True, "description": f"{t.name} needs {dep.name}"})
            for d in t.soft_deps:
                dep = m.tasks[d]
                a_deps.append({"dependent_task_name": t.key, "prerequisite_task_name": dep.key,
                               "dependency_type": "ORDER", "required": False, "description": f"{t.name} should follow {dep.name}"})
        return {
            "plan_id": plan.id, "mission_id": m.id, "version": plan.version, "type": plan.type.value,
            "state": plan.state.value, "order": list(plan.order), "layers": [list(x) for x in plan.layers],
            "critical_path": list(plan.critical_path), "critical_relative_cost": round(plan.critical_cost, 2),
            "total_relative_cost": round(plan.total_cost, 2), "max_parallelism": plan.max_parallelism(),
            "tasks": tasks,
            "requires_verification": any(t.verification for t in m.tasks.values()),
            "authorization_required": any(t.needs for t in m.tasks.values()),
            "constraints": [list(c) for c in m.constraints],
            "alpha_blueprint": {"tasks": a_tasks, "dependencies": a_deps,
                                "metadata": {"source": "HEROIC", "mission_id": m.id, "plan_version": plan.version}},
            "handoff": {"to": "ALPHA", "executed": False,
                        "note": "HEROIC prepared this plan. No task has been executed by HEROIC."},
        }
