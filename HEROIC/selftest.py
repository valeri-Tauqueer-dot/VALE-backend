"""HEROIC self-test.

Run from the repository root:      python -m HEROIC.selftest
For speed numbers as well:         python -m HEROIC.selftest --bench
Every check below actually runs. Nothing is assumed to pass.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain_state import VALEBrainState                      # noqa: E402
from vale_connector import VALEConnector                    # noqa: E402

from HEROIC import HeroicBrain                              # noqa: E402
from HEROIC.core.config import HeroicConfig                 # noqa: E402
from HEROIC.core.enums import MissionState, TaskState       # noqa: E402
from HEROIC.core.models import Mission                      # noqa: E402
from HEROIC.core.statemachine import move_mission          # noqa: E402

BRAINS = ["COGNITIVE", "LEGEND", "ALPHA", "MARCO", "FEELINGS", "HEROIC", "SUPERVISOR", "UNITY"]
BITCOIN = ("Investigate whether Bitcoin is entering a major bearish phase and tell me whether the "
           "evidence supports that conclusion.")


def mk(**cfg) -> HeroicBrain:
    return HeroicBrain(VALEConnector(), HeroicConfig(**cfg))


def state(msg, brains=BRAINS, **shared) -> VALEBrainState:
    st = VALEBrainState(user_message=msg)
    st.set("registered_brains", list(brains))
    for k, v in shared.items():
        st.set(k, v)
    return st


def think(b, msg, brains=BRAINS, **shared):
    return b.think(state(msg, brains, **shared))


def keys(r):
    return [t["key"] for t in r["tasks"]]


def task(r, key):
    return next(t for t in r["tasks"] if t["key"] == key)


def drive(b, mid, verify=True, stop_before=None):
    """Report every READY task as started and finished, like an executor would. Returns the mission."""
    for _ in range(60):
        m = b.get_mission(mid)
        ready = [t for t in m.tasks.values() if t.state == TaskState.READY and t.key != stop_before]
        if not ready:
            break
        for t in ready:
            assert b.report_task_started(mid, t.id)["ok"], t.key
            if t.verification and verify:
                b.report_verification(mid, "all", True, "COGNITIVE", ["ref-1"])
            if t.state != TaskState.COMPLETED:
                assert b.report_task_result(mid, t.id, True, f"{t.key} done")["ok"], t.key
    return b.get_mission(mid)


class PDFScenarios(unittest.TestCase):
    """The validation table from the HEROIC architecture document."""

    def test_simple_request_creates_a_small_mission(self):
        r = think(mk(), "hi")
        self.assertEqual(r["intent"]["mission_type"], "CONVERSATION")
        self.assertEqual(r["plan"]["type"], "SINGLE_TASK")
        self.assertEqual(len(r["tasks"]), 1)
        self.assertEqual(r["activation"]["required_brains"], [])

    def test_complex_request_is_decomposed(self):
        r = think(mk(), BITCOIN)
        self.assertEqual(r["status"], "PLAN_READY")
        self.assertGreaterEqual(len(r["tasks"]), 8)
        self.assertGreaterEqual(len(r["objectives"]), 2)
        self.assertEqual(r["plan"]["type"], "MULTI_TASK")
        self.assertGreaterEqual(len(r["plan"]["layers"]), 5)
        self.assertTrue(r["plan"]["critical_path"])
        for k in ("qualify_market_data", "market_structure", "market_regime", "liquidity_volatility",
                  "competing_hypotheses", "verify_claims", "compose_answer"):
            self.assertIn(k, keys(r))
        self.assertIn("LEGEND", r["activation"]["required_brains"])
        self.assertIn("COGNITIVE", r["activation"]["required_brains"])
        self.assertNotIn("FEELINGS", r["activation"]["required_brains"])
        self.assertNotIn("MARCO", r["activation"]["required_brains"])
        self.assertFalse(r["execution_performed"])
        self.assertEqual(r["stage"], "PLANNED")

    def test_ambiguous_request_asks_for_clarification(self):
        b = mk()
        r = think(b, "explain")
        self.assertEqual(r["status"], "NEEDS_INFORMATION")
        self.assertEqual(r["decision"]["decision"], "CLARIFY")
        self.assertEqual(r["information"]["blocking"], ["subject"])
        self.assertEqual(r["mission"]["escalations"][0]["destination"], "USER")

    def test_missing_critical_data_blocks_a_strong_conclusion(self):
        r = think(mk(), "should I buy BTC now?", internet_available=False, external_information_required=True)
        self.assertEqual(r["decision"]["decision"], "BLOCK")
        self.assertEqual(r["status"], "PLAN_BLOCKED")
        self.assertTrue(any("market data" in x.lower() for x in r["limitations"]))

    def test_conflicting_findings_are_kept_not_averaged(self):
        b = mk()
        r = think(b, BITCOIN)
        out = b.apply_event(r["task_id"], "brain_results", {"results": {
            "LEGEND": {"result": {"direction": "bearish", "timeframe": "4h"}},
            "MARCO": {"result": {"direction": "bullish", "timeframe": "1d"}}}})
        self.assertEqual(len(out["conflicts_found"]), 1)
        self.assertEqual(out["conflicts_found"][0]["cause"], "TIMEFRAME")
        m = b.get_mission(r["task_id"])
        self.assertTrue(any("Unresolved disagreement" in x for x in b._result(m, None, "x")["limitations"]))
        cid = out["conflicts_found"][0]["id"]
        b.apply_event(r["task_id"], "resolve_conflict", {"id": cid, "preserve": True, "basis": "different timeframes"})
        self.assertEqual(m.conflicts[0].status, "PRESERVED")
        self.assertTrue(any("Unresolved disagreement" in x for x in b._result(m, None, "x")["limitations"]))

    def test_failed_task_is_retried_then_escalated_to_supervisor(self):
        b = mk()
        r = think(b, BITCOIN)
        mid, t1 = r["task_id"], task(r, "acquire_information")["id"]
        b.report_task_started(mid, t1)
        out = b.report_task_result(mid, t1, False, failure="search timeout")
        self.assertEqual(b.get_mission(mid).tasks[t1].state, TaskState.READY)       # one retry allowed
        self.assertEqual(out["decision"]["decision"], "PROCEED")
        b.report_task_started(mid, t1)
        out = b.report_task_result(mid, t1, False, failure="search timeout again")
        self.assertEqual(out["decision"]["decision"], "ESCALATE")
        m = b.get_mission(mid)
        self.assertEqual(m.state, MissionState.ESCALATED)
        self.assertEqual(m.escalations[-1].destination, "SUPERVISOR")
        self.assertEqual(m.info["market_data"].state.value, "UNAVAILABLE")

    def test_invalid_dependency_is_caught_and_repaired(self):
        b = mk()
        r = think(b, BITCOIN)
        mid = r["task_id"]
        m = b.get_mission(mid)
        a, c = task(r, "market_structure")["id"], task(r, "competing_hypotheses")["id"]
        m.tasks[a].deps.append(c)                       # competing_hypotheses already depends on market_structure
        issues = b.deps.analyze(m, "test injection")
        self.assertTrue(any(i.startswith("CYCLE") for i in issues))
        out = b.evaluate(mid)
        self.assertEqual(m.replans, 1)
        self.assertEqual(m.plan.issues, [])
        self.assertTrue(out["ok"])
        self.assertTrue(b.audit(mid)["audit"]["ok"])

    def test_unavailable_brain_is_routed_around_or_blocks_honestly(self):
        b = mk()
        r = think(b, "I feel scared about my trade on ETH")
        mid = r["task_id"]
        self.assertEqual(task(r, "market_context")["target"], "LEGEND")
        b.report_brain_unavailable(mid, "LEGEND", "timeout")
        m = b.get_mission(mid)
        mc = m.tasks[task(r, "market_context")["id"]]
        self.assertEqual((mc.target, mc.degraded), ("MARCO", True))          # a stand-in is used and labelled as one
        self.assertNotEqual(m.state, MissionState.BLOCKED)
        self.assertTrue(any("instead of the usual specialist" in x for x in b._result(m, None, "x")["limitations"]))
        self.assertEqual(m.escalations[-1].destination, "SUPERVISOR")
        # a mission that truly needs LEGEND must block instead of pretending
        r2 = think(b, BITCOIN)
        b.report_brain_unavailable(r2["task_id"], "LEGEND", "crashed")
        m2 = b.get_mission(r2["task_id"])
        self.assertEqual(m2.state, MissionState.BLOCKED)
        self.assertTrue(any(t.degraded and t.target == "MARCO" for t in m2.tasks.values()))
        self.assertTrue(m2.decision.reasons[0].startswith("capability_unavailable"))

    def test_full_lifecycle_reaches_completion_with_audit(self):
        b = mk()
        r = think(b, "what is HEROIC?")
        mid = r["task_id"]
        m = drive(b, mid)
        self.assertEqual(m.state, MissionState.COMPLETED)
        self.assertEqual(m.outcome.value, "FULL_COMPLETION")
        self.assertTrue(b.audit(mid)["audit"]["ok"])
        res = b._result(m, None, "x")
        self.assertTrue(res["execution_performed"])
        self.assertEqual(res["stage"], "FINAL")
        self.assertGreaterEqual(res["quality"]["process_score"], 0.8)
        self.assertEqual([h[1] for h in m.history][-1], "VERIFYING->COMPLETED")

    def test_market_lifecycle_completes_with_stated_limitations(self):
        b = mk()
        r = think(b, BITCOIN)
        mid = r["task_id"]
        m = drive(b, mid)
        self.assertEqual(m.state, MissionState.COMPLETED)
        self.assertEqual(m.outcome.value, "PARTIAL_COMPLETION")
        self.assertTrue(any("time horizon" in x for x in b._result(m, None, "x")["limitations"]))
        self.assertTrue(b.audit(mid)["audit"]["ok"])

    def test_completion_is_refused_while_verification_is_missing(self):
        b = mk()
        r = think(b, BITCOIN)
        mid = r["task_id"]
        m = drive(b, mid, verify=False)                 # the verification task "ran" but nothing was verified
        self.assertNotEqual(m.state, MissionState.COMPLETED)           # stopped tasks are not a finished mission
        self.assertEqual(m.state, MissionState.VERIFYING)
        self.assertEqual(m.decision.decision.value, "CONTINUE_INVESTIGATING")
        self.assertTrue(all(e.status == "REQUIRED" for e in m.evidence))
        self.assertFalse(b.completion.evaluate(m).can_complete)
        out = b.evaluate(mid)                           # nothing new arrived: HEROIC stops and states the limit
        self.assertEqual(m.state, MissionState.COMPLETED)
        self.assertEqual(m.outcome.value, "PARTIAL_COMPLETION")
        self.assertTrue(any("not independently verified" in x.lower() for x in b._result(m, None, "x")["limitations"]))
        self.assertTrue(b.audit(mid)["audit"]["ok"])

    def test_changed_objective_replans_and_refined_objective_keeps_work(self):
        b = mk()
        r = think(b, "Analyze BTC market structure")
        mid = r["task_id"]
        drive(b, mid, stop_before="market_structure")
        m = b.get_mission(mid)
        done_before = {t.key for t in m.tasks.values() if t.state == TaskState.COMPLETED}
        self.assertIn("qualify_market_data", done_before)
        out = b.update_request(mid, "Analyze BTC market structure on the 4h chart")
        self.assertEqual(out["update"]["verdict"], "REFINED")
        self.assertIn("qualify_market_data", {t.key for t in m.tasks.values() if t.state == TaskState.COMPLETED})
        self.assertTrue(all(t.preserved for t in m.tasks.values() if t.state == TaskState.COMPLETED))
        out = b.update_request(mid, "What is a stop loss?")
        self.assertEqual(out["update"]["verdict"], "CHANGED")
        self.assertFalse(any(t.state == TaskState.COMPLETED for t in m.tasks.values()))
        self.assertEqual(m.intent.mission_type, "EXPLANATION")
        self.assertTrue(b.audit(mid)["audit"]["ok"])

    def test_duplicate_work_is_flagged(self):
        b = mk()
        r = think(b, BITCOIN)
        m = b.get_mission(r["task_id"])
        dup = Mission  # noqa: F841
        src = m.tasks[task(r, "market_regime")["id"]]
        copy = type(src)(**{f: getattr(src, f) for f in src.__slots__})
        copy.id = "t99"
        m.tasks["t99"] = copy
        kinds = [f.kind for f in b.monitor.check(m)]
        self.assertIn("REPEATED_WORK", kinds)

    def test_many_missions_stay_independent(self):
        b = mk()
        a, c = think(b, BITCOIN), think(b, "hi")
        drive(b, c["task_id"])
        self.assertEqual(b.get_mission(c["task_id"]).state, MissionState.COMPLETED)
        self.assertEqual(b.get_mission(a["task_id"]).state, MissionState.READY)
        self.assertEqual(len(b.registry), 2)


class EngineeringRules(unittest.TestCase):
    def test_self_certification_is_refused(self):
        b = mk()
        r = think(b, BITCOIN)
        out = b.report_verification(r["task_id"], "all", True, "HEROIC")
        self.assertFalse(out["ok"])
        self.assertTrue(all(e.status == "REQUIRED" for e in b.get_mission(r["task_id"]).evidence))

    def test_information_is_never_marked_available_without_a_source(self):
        b = mk()
        for msg in (BITCOIN, "what is HEROIC?", "should I buy ETH now?", "write a message to my friend", "compare BTC vs ETH"):
            r = think(b, msg)
            for i in r["information"]["requirements"]:
                if i["state"].startswith("AVAILABLE"):
                    self.assertTrue(i["source"], (msg, i))
        r = think(b, "should I buy ETH now?")
        self.assertEqual(next(i for i in r["information"]["requirements"] if i["key"] == "market_data")["state"], "MISSING")

    def test_search_results_make_data_available_but_not_verified(self):
        b = mk()
        r = think(b, "should I buy BTC now?", internet_results=[{"title": "x"}], internet_research_performed=True)
        info = next(i for i in r["information"]["requirements"] if i["key"] == "market_data")
        self.assertEqual(info["state"], "AVAILABLE_UNVERIFIED")
        acq = task(r, "acquire_information")
        self.assertEqual(acq["state"], "SKIPPED")
        self.assertTrue(acq["note"].startswith("already satisfied"))
        self.assertTrue(all(e["status"] == "REQUIRED" for e in r["evidence"]))

    def test_execution_needs_explicit_authorisation(self):
        b = mk()
        r = think(b, "deploy to production within 10 minutes")
        mid = r["task_id"]
        self.assertEqual(r["priority"]["level"], "CRITICAL")
        self.assertEqual(task(r, "execute_actions")["state"], "BLOCKED")
        drive(b, mid)
        m = b.get_mission(mid)
        ex = m.task_by_key("execute_actions")
        self.assertEqual(ex.state, TaskState.BLOCKED)
        self.assertIn("info:execution_authorization", ex.blocked_by)
        self.assertEqual(m.decision.decision.value, "WAIT")
        self.assertFalse(b.report_task_result(mid, ex.id, True, "done anyway")["ok"])      # refused
        b.report_information(mid, "execution_authorization", "AVAILABLE_VERIFIED", "USER")
        self.assertEqual(m.task_by_key("execute_actions").state, TaskState.READY)
        drive(b, mid)
        self.assertEqual(m.state, MissionState.COMPLETED)
        self.assertTrue(b.audit(mid)["audit"]["ok"])

    def test_urgency_skips_optional_work_but_never_verification(self):
        r = think(mk(), "Analyze BTC market structure urgently within 10 minutes")
        skipped = [t for t in r["tasks"] if t["state"] == "SKIPPED"]
        self.assertTrue(skipped)
        self.assertTrue(all(not t["mandatory"] for t in skipped))
        v = task(r, "verify_claims")
        self.assertTrue(v["mandatory"])
        self.assertNotEqual(v["state"], "SKIPPED")

    def test_user_beliefs_are_tested_not_assumed(self):
        b = mk()
        r = think(b, "I think Bitcoin will definitely hit 100k, confirm that for me")
        self.assertIn("challenge_hypothesis", keys(r))
        self.assertTrue(any(e["kind"] == "user_hypothesis" for e in r["evidence"]))
        self.assertTrue(any(u["kind"] == "UNVERIFIED" for u in r["uncertainty"]))
        self.assertTrue(b.audit(r["task_id"])["audit"]["ok"])

    def test_state_machine_refuses_illegal_moves(self):
        m = Mission(id="x", request="r")
        self.assertFalse(move_mission(m, MissionState.COMPLETED, "skip everything")[0])
        self.assertTrue(move_mission(m, MissionState.UNDERSTANDING, "ok")[0])
        self.assertTrue(move_mission(m, MissionState.CANCELLED, "ok")[0])
        self.assertFalse(move_mission(m, MissionState.READY, "terminal states do not reopen")[0])

    def test_heroic_is_silent_by_default(self):
        b = mk()
        for msg in ("hi", "explain", BITCOIN, "what is HEROIC?", "I want to kill myself"):
            r = think(b, msg)
            self.assertNotIn("voice", r)
            self.assertNotIn("message", r)
        r = think(mk(speak=True), "explain")
        self.assertIn("voice", r)

    def test_crisis_puts_human_support_first(self):
        r = think(mk(), "I want to kill myself")
        self.assertEqual(r["priority"]["level"], "CRITICAL")
        self.assertEqual(r["tasks"][0]["key"], "human_support")
        self.assertEqual(r["tasks"][0]["target"], "FEELINGS")

    def test_process_quality_is_judged_apart_from_outcome(self):
        b = mk()
        r = think(b, "what is HEROIC?")
        drive(b, r["task_id"])
        out = b.apply_event(r["task_id"], "outcome", {"success": False})
        self.assertEqual(out["quality"]["outcome_flag"], "bad_outcome_but_sound_process")
        self.assertTrue(out["quality"]["outcome_independent"])

    def test_every_planned_mission_passes_its_own_audit(self):
        b = mk()
        for msg in ("hi", BITCOIN, "compare BTC vs ETH", "make a plan to learn python in 30 days",
                    "write a message to apologize to my girlfriend", "monitor ETH every hour and alert me if it drops 5%",
                    "are you working?", "should I buy BTC now?", "what is a stop loss?", "tell me a joke"):
            r = think(b, msg)
            self.assertTrue(b.audit(r["task_id"])["audit"]["ok"], (msg, b.audit(r["task_id"])["audit"]))


class Lifecycle(unittest.TestCase):
    def test_random_missions_run_to_completion_with_a_simulated_executor(self):
        import random
        bits = ["bitcoin", "btc", "eth", "explain", "compare", "vs", "should i", "buy", "now", "plan", "write", "email",
                "to my friend", "deploy", "monitor", "alert me", "why", "is it true", "urgent", "within 5 minutes",
                "i feel sad", "legend", "marco", "heroic", "price", "today", "and then", "1h chart", "kya hai", "NIFTY",
                "short", "tell me whether", "investigate", "i think", "definitely", "confirm that", "analyze",
                "research", "what is", "how to", "make a plan", "draft a", "summarize", "run the", "status", "also"]
        rnd = random.Random(5)
        b = mk(max_missions=1000)
        done = asked = 0
        for _ in range(300):
            msg = " ".join(rnd.choice(bits) for _ in range(rnd.randint(1, 14)))
            r = think(b, msg)
            if r["status"] == "NEEDS_INFORMATION":
                asked += 1
                continue
            mid = r["task_id"]
            for _ in range(40):
                m = b.get_mission(mid)
                if m.state in (MissionState.COMPLETED, MissionState.CANCELLED, MissionState.FAILED):
                    break
                ready = [t for t in m.tasks.values() if t.state == TaskState.READY]
                for t in ready:
                    b.report_task_started(mid, t.id)
                    if t.verification:
                        b.report_verification(mid, "all", True, "COGNITIVE", ["ref"])
                    if t.state != TaskState.COMPLETED:
                        b.report_task_result(mid, t.id, True, "ok")
                if ready:
                    continue
                a = m.info.get("execution_authorization")
                if a is not None and a.state.value == "MISSING":
                    b.report_information(mid, "execution_authorization", "AVAILABLE_VERIFIED", "USER")
                else:
                    b.evaluate(mid)
            m = b.get_mission(mid)
            self.assertEqual(m.state, MissionState.COMPLETED, (msg, m.decision.reasons))
            self.assertTrue(b.audit(mid)["audit"]["ok"], (msg, b.audit(mid)["audit"]))
            done += 1
        self.assertGreater(done, 150)


class Fuzz(unittest.TestCase):
    def test_random_messages_never_break_planning(self):
        import random
        rnd = random.Random(7)
        bits = ["bitcoin", "btc", "eth", "explain", "compare", "vs", "should i", "buy", "now", "plan", "write", "email",
                "to my friend", "deploy", "monitor", "alert me", "why", "is it true", "?", "!", "urgent", "within 5 minutes",
                "i feel sad", "legend", "marco", "heroic", "price", "today", "and then", ";", "1h chart", "बिटकॉइन की कीमत",
                "kya hai", "😀", "\n", "don't", "the", "", "a" * 40, "NIFTY", "AAPL", "short", "in detail"]
        b = mk()
        for i in range(400):
            msg = " ".join(rnd.choice(bits) for _ in range(rnd.randint(0, 14)))
            r = think(b, msg)
            self.assertNotEqual(r["status"], "PLANNING_ERROR", msg)
            self.assertEqual((r["plan"] or {}).get("issues", []), [], msg)
            self.assertTrue(b.audit(r["task_id"])["audit"]["ok"], (msg, b.audit(r["task_id"])["audit"]))
            json.dumps(r)


class Robustness(unittest.TestCase):
    def test_bad_states_never_raise(self):
        b = mk()
        r = b.think(object())
        self.assertIn(r["status"], ("PLAN_READY", "NEEDS_INFORMATION", "PLANNING_ERROR"))
        with self.assertRaises(ValueError):
            b.think(None)
        self.assertEqual(think(b, "")["status"], "NEEDS_INFORMATION")

    def test_huge_media_message_is_cheap(self):
        b = mk()
        blob = "=== VALE MEDIA CONTEXT ===\n" + ("word " * 12000)
        t0 = time.perf_counter()
        r = think(b, "USER QUESTION:\nwhat is this document about?\n\n" + blob)
        self.assertLess(time.perf_counter() - t0, 0.05)
        self.assertEqual(r["intent"]["mission_type"], "EXPLANATION")
        self.assertIn("attachment_content", [i["key"] for i in r["information"]["requirements"]])
        self.assertEqual(think(b, blob)["intent"]["subject"][:10], "understand")

    def test_very_long_text_is_bounded(self):
        t0 = time.perf_counter()
        think(mk(), "analyze bitcoin " + "x " * 200000)
        self.assertLess(time.perf_counter() - t0, 0.1)

    def test_memory_stays_bounded(self):
        b = mk(max_missions=64, archive_size=100)
        ids = []
        for i in range(600):
            r = think(b, f"what is topic number {i}?")
            ids.append(r["task_id"])
        self.assertLessEqual(len(b.registry), 64)
        self.assertGreater(b.registry.evicted, 0)
        self.assertLessEqual(len(b.memory), 100)
        self.assertIsNone(b.get_mission_state("never-existed"))
        self.assertIsNotNone(b.get_mission_state(ids[-1]))

    def test_concurrent_requests_do_not_mix_missions(self):
        b = mk()
        errors, out = [], {}

        def worker(n):
            try:
                for i in range(80):
                    st = state(f"what is topic {n}-{i}?")
                    r = b.think(st)
                    out[st.task_id] = (r["task_id"], r["mission"]["request"])
                    assert r["task_id"] == st.task_id and f"{n}-{i}" in r["mission"]["request"]
            except Exception as exc:                    # pragma: no cover
                errors.append(repr(exc))
        ts = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errors, [])
        self.assertEqual(len(out), 640)

    def test_same_state_twice_is_a_cache_hit_and_new_information_refreshes(self):
        b = mk()
        st = state("should I buy BTC now?")
        r1 = b.think(st)
        self.assertEqual(r1["cache"], "miss")
        r2 = b.think(st)
        self.assertEqual(r2["cache"], "hit")
        st.set("internet_results", [{"title": "x"}])
        st.set("internet_research_performed", True)
        r3 = b.think(st)
        self.assertEqual(next(i for i in r3["information"]["requirements"] if i["key"] == "market_data")["state"], "AVAILABLE_UNVERIFIED")

    def test_results_are_json_serialisable_everywhere(self):
        b = mk()
        for msg in ("hi", BITCOIN, "explain", "deploy to production", "I want to kill myself"):
            r = think(b, msg)
            json.dumps(r)
            for cmd in ("status", "explain", "audit", "evaluate"):
                json.dumps(b.apply_event(r["task_id"], cmd))
        json.dumps(b.health())
        json.dumps(b.contract())
        json.dumps(b.identity())
        json.dumps(b.learning_signals())

    def test_health_and_contract(self):
        b = mk()
        self.assertIsNone(b.health()["last_success_age_s"])           # unknown is reported as unknown
        think(b, "hi")
        h = b.health()
        self.assertTrue(h["live"] and h["ready"])
        self.assertEqual(h["status"], "ONLINE")
        self.assertIsNotNone(h["latency"]["think"]["p50_ms"])
        c = b.contract()
        for k in ("identity", "operations", "events_published", "error_categories", "limits", "recovery"):
            self.assertIn(k, c)
        self.assertFalse(c["writes_user_text"])
        self.assertTrue(b.reset()["ok"])


class RealNetwork(unittest.TestCase):
    def test_runs_inside_the_real_brain_network(self):
        from brain_network import BrainNetwork
        from vale_brain_interface import VALEBrainInterface
        c = VALEConnector()
        n = BrainNetwork(connector=c)
        n.register(HeroicBrain(c, HeroicConfig()))
        for name in ("COGNITIVE", "LEGEND", "ALPHA", "MARCO", "FEELINGS", "SUPERVISOR", "UNITY"):
            n.register(VALEBrainInterface(brain_name=name, connector=c))
        out = n.process(BITCOIN)
        res = out["results"]["HEROIC"]["result"]
        self.assertEqual(res["status"], "PLAN_READY")
        self.assertIn("network_alignment", res["activation"])
        json.dumps(res)
        self.assertNotIn("message", res)
        self.assertNotIn("voice", res)

    def test_received_messages_are_handled(self):
        b = mk()
        r = think(b, BITCOIN)
        st = state("x")
        out = b.receive_message("hello brains", st, "UNITY", None)
        self.assertTrue(out["received"] and out["ok"])
        out = b.receive_message("status please", st, "ALPHA", {"type": "status", "mission_id": r["task_id"]})
        self.assertTrue(out["ok"])
        self.assertEqual(out["mission"]["id"], r["task_id"])
        self.assertFalse(b.receive_message("x", st, "ALPHA", {"type": "nonsense"})["ok"])
        self.assertEqual(b.receive_message("x", st, "ALPHA", {"type": "status", "mission_id": "nope"})["error"], "UNKNOWN_MISSION")


def bench() -> None:
    b = mk()
    msgs = ["hi", "what is HEROIC?", "I feel scared about my trade on ETH", "compare LEGEND and MARCO",
            "should I buy BTC now?", BITCOIN, "make a plan to learn python in 30 days",
            "write a message to apologize to my girlfriend", "deploy to production within 10 minutes"]
    print(f"\n{'request (every call is new text and a new mission)':58} {'p50 ms':>8} {'p95 ms':>8} {'max ms':>8}")
    for m in msgs:
        ts = []
        for i in range(400):
            st = state(m + " " * (i % 50) + "." * (i // 50))
            t0 = time.perf_counter_ns()
            b.think(st)
            ts.append((time.perf_counter_ns() - t0) / 1e6)
        ts.sort()
        print(f"{m[:56]:58} {ts[200]:8.3f} {ts[380]:8.3f} {ts[-1]:8.3f}")


if __name__ == "__main__":
    do_bench = "--bench" in sys.argv
    if do_bench:
        sys.argv.remove("--bench")
    result = unittest.main(exit=False, verbosity=1).result
    if do_bench:
        bench()
    sys.exit(0 if result.wasSuccessful() else 1)
