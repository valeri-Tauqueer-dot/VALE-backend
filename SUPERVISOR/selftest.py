"""SUPERVISOR self-test.

Run from the repository root:      python -m SUPERVISOR.selftest
Every check runs for real, with a simulated clock, so nothing here waits for minutes to pass.
"""
from __future__ import annotations

import json
import random
import sys
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain_network import BrainNetwork                      # noqa: E402
from brain_state import BrainEvent, VALEBrainState          # noqa: E402
from vale_brain_interface import VALEBrainInterface         # noqa: E402
from vale_connector import VALEConnector                    # noqa: E402

from SUPERVISOR import SupervisorBrain                      # noqa: E402
from SUPERVISOR.core.config import SupervisorConfig         # noqa: E402
from SUPERVISOR.core.enums import ActionKind, ComponentState as CS, IncidentStatus as IS, Mode  # noqa: E402
from SUPERVISOR.core.models import Observation, PlannedAction  # noqa: E402
from SUPERVISOR.engines.recovery import BrainIsolatedError  # noqa: E402


class Clock:
    def __init__(self) -> None:
        self.t = 1_800_000_000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


def iso_at(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


class Stub(VALEBrainInterface):
    """A brain whose behaviour the tests control."""

    def __init__(self, name, connector, health=False, reset=False, heal=True):
        super().__init__(name, connector)
        self.fail, self.fail_n, self.calls, self.resets, self.ready, self.heal = None, 0, 0, 0, True, heal
        self.messages = []
        if health:
            self.health = self._health
        if reset:
            self.reset = self._reset

    def _health(self):
        return {"live": True, "ready": self.ready, "status": "ONLINE" if self.ready else "DEGRADED"}

    def _reset(self):
        self.resets += 1
        if self.heal:
            self.ready, self.fail = True, None
        return "reset done"

    def think(self, state):
        self.calls += 1
        if self.fail_n > 0:
            self.fail_n -= 1
            raise TimeoutError("upstream timeout")
        if self.fail == "error":
            raise RuntimeError("boom")
        if self.fail == "timeout":
            raise TimeoutError("upstream timeout")
        if self.fail == "value":
            raise ValueError("bad input")
        return {"brain": self.brain_name, "ok": True}

    def receive_message(self, message, state, source_brain, payload=None):
        self.messages.append((message, payload))
        return {"ok": True}


class World:
    def __init__(self, names=("HEROIC", "LEGEND", "ALPHA", "UNITY", "COGNITIVE"), mode="ADVISORY", health=(), reset=(),
                 heal=True, **cfg):
        self.clock = Clock()
        self.metrics = {"rss_mb": 100.0, "mem_limit_mb": 512.0, "mem_pct": 19.5, "threads": 10.0}
        c = VALEConnector()
        base = dict(background=False, mode=mode, expected_brains=tuple(names) + ("SUPERVISOR",), startup_grace_s=0.0,
                    retry_backoff_s=0.0, min_tick_gap_s=0.0, log=False)
        base.update(cfg)
        self.sup = SupervisorBrain(c, SupervisorConfig(**base), clock=self.clock, metrics=lambda: dict(self.metrics))
        self.net = BrainNetwork(connector=c)
        self.brains = {n: Stub(n, c, health=n in health, reset=n in reset, heal=heal) for n in names}
        for b in self.brains.values():
            self.net.register(b)
        self.net.register(self.sup)

    def tick(self, advance: float = 20.0, **kw):
        self.clock.advance(advance)
        return self.sup.tick(**kw)

    def task(self, brains=("HEROIC",), fail=None, slow=None, required=None, active=None, finished=True,
             internet=None, age=1.0, unfinished=(), skipped=None, extra_events=0, created_age=None):
        fail, slow = fail or {}, slow or {}
        st = VALEBrainState(user_message="x")
        t0 = self.clock.t - age
        st.created_at = iso_at(t0 if created_age is None else self.clock.t - created_age)
        ts = t0
        for b in brains:
            st.events.append(BrainEvent("brain_think_started", b, timestamp=iso_at(ts)))
            if b in unfinished:
                continue
            ts += slow.get(b, 0.05)
            if b in fail:
                st.events.append(BrainEvent("brain_think_error", b, payload={"error": fail[b]}, timestamp=iso_at(ts)))
            else:
                st.events.append(BrainEvent("brain_think_completed", b, timestamp=iso_at(ts)))
        for brain, reason in (skipped or []):
            st.events.append(BrainEvent("brain_selection_skipped", "VALE_NETWORK", payload={"brain": brain, "reason": reason}, timestamp=iso_at(ts)))
        for i in range(extra_events):
            st.events.append(BrainEvent("noise", "X", payload={"i": i}, timestamp=iso_at(ts)))
        if finished:
            st.events.append(BrainEvent("selected_brains_completed", "VALE_NETWORK", payload={}, timestamp=iso_at(ts)))
        st.set("task_plan", {"required_brains": list(required if required is not None else brains), "optional_brains": []})
        st.set("active_brains", list(active if active is not None else [b for b in brains if b not in unfinished]))
        for k, v in (internet or {}).items():
            st.set(k, v)
        self.net.tasks[st.task_id] = st
        return st

    def incident(self, component, signature=None):
        for i in self.sup.store.active():
            if i.component == component and (signature is None or i.signature == signature):
                return i
        return None


def codes(w):
    return sorted((i.type, i.component, i.signature, i.severity) for i in w.sup.store.active())


class Detection(unittest.TestCase):
    def test_dead_brain_is_detected_classified_and_escalated(self):
        w = World()
        for _ in range(3):
            w.task(("LEGEND",), fail={"LEGEND": "boom"})
        w.tick()
        i = w.incident("LEGEND", "consecutive_failures")
        self.assertEqual((i.severity, i.type), ("HIGH", "HEALTH"))
        self.assertEqual(w.sup.registry.components["LEGEND"].state, CS.UNHEALTHY)
        self.assertEqual(i.status, IS.ESCALATED)
        self.assertIn("HEROIC", i.escalated_to)
        msg, payload = w.brains["HEROIC"].messages[-1]
        self.assertEqual(payload["type"], "supervisor_alert")
        self.assertEqual(payload["incident"]["component"], "LEGEND")
        self.assertIsNotNone(i.to_dict()["detection_delay_s"])

    def test_one_failure_is_a_warning_and_recovery_needs_several_good_signals(self):
        w = World()
        w.task(("LEGEND",), fail={"LEGEND": "boom"})
        w.tick()
        self.assertEqual(w.incident("LEGEND").severity, "WARNING")
        self.assertEqual(w.sup.registry.components["LEGEND"].state, CS.DEGRADED)
        self.assertEqual(w.brains["HEROIC"].messages, [])                       # a warning is not escalated at once
        w.task(("LEGEND",))
        w.tick()
        self.assertEqual(w.sup.registry.components["LEGEND"].state, CS.DEGRADED)  # one good call is not recovery
        w.task(("LEGEND",)); w.task(("LEGEND",))
        w.tick()
        self.assertEqual(w.sup.registry.components["LEGEND"].state, CS.HEALTHY)
        for _ in range(3):
            w.tick()
        self.assertIsNone(w.incident("LEGEND"))
        resolved = w.sup.store.recent_resolved()[-1]
        self.assertEqual(resolved.status, IS.RESOLVED)
        self.assertEqual(resolved.verification[-1]["check"], "condition_absent")

    def test_a_call_that_never_finishes_is_a_critical_possible_hang(self):
        w = World()
        w.task(("LEGEND",), unfinished=("LEGEND",), finished=False, age=120)
        w.tick()
        i = w.incident("LEGEND", "stalled_call")
        self.assertEqual((i.severity, i.type), ("CRITICAL", "TIMEOUT"))
        self.assertEqual(w.sup.registry.components["LEGEND"].state, CS.UNHEALTHY)
        self.assertTrue(w.brains["UNITY"].messages)
        self.assertEqual(w.sup.escalation.outbox[-1].destination, "OPERATOR")     # it cannot be killed from here: a person is told

    def test_slow_calls_are_warnings_and_timeouts_are_high(self):
        w = World()
        w.task(("LEGEND",), slow={"LEGEND": 8.0})
        w.tick()
        self.assertEqual(w.incident("LEGEND", "slow_call").severity, "WARNING")
        w.task(("ALPHA",), slow={"ALPHA": 45.0})
        w.tick()
        self.assertEqual(w.incident("ALPHA", "slow_call").severity, "HIGH")

    def test_unknown_stays_unknown_and_is_never_called_healthy(self):
        w = World()
        w.tick(force_probe=True)
        w.tick()
        s = w.sup.status()
        for n in ("LEGEND", "ALPHA", "COGNITIVE"):
            c = w.sup.registry.components[n]
            self.assertEqual(c.state, CS.UNKNOWN, n)
            self.assertIn("readiness", c.reason)
        self.assertNotEqual(s["overall"], "OK")
        self.assertIn("LEGEND", s["no_evidence_yet"])
        self.assertIsNone(w.sup.availability("LEGEND"))

    def test_a_missing_brain_is_an_incident_only_after_the_start_up_grace_period(self):
        w = World(names=("HEROIC", "LEGEND"), startup_grace_s=30.0)
        w.sup.cfg.__class__  # frozen config: build a new supervisor that expects ALPHA as well
        w2 = World(names=("HEROIC", "LEGEND"), startup_grace_s=30.0, expected_brains=("HEROIC", "LEGEND", "ALPHA", "SUPERVISOR"))
        w2.tick(10)
        self.assertIsNone(w2.incident("ALPHA"))
        w2.tick(40)
        i = w2.incident("ALPHA", "not_registered")
        self.assertEqual(i.severity, "HIGH")                                        # ALPHA is a core brain
        self.assertEqual(w2.sup.availability("ALPHA"), False)

    def test_required_brains_that_never_ran_and_unregistered_selections(self):
        w = World()
        w.task(("LEGEND",), required=["LEGEND", "ALPHA"])
        w.task(("LEGEND",), required=["LEGEND", "COGNITIVE"], skipped=[("COGNITIVE", "not_registered")])
        w.tick()
        self.assertEqual(w.incident("ALPHA", "required_not_run").type, "COMMUNICATION")
        self.assertIsNone(w.incident("COGNITIVE", "required_not_run"))             # the network said why it skipped it
        self.assertEqual(w.incident("COGNITIVE", "selected_but_unregistered").type, "HEALTH")

    def test_shared_state_that_disagrees_with_the_events(self):
        w = World()
        w.task(("LEGEND", "ALPHA"), active=["LEGEND"])
        w.tick()
        i = w.incident("NETWORK", "active_brains_mismatch")
        self.assertEqual(i.type, "STATE_CONFLICT")
        self.assertEqual(i.evidence[-1]["state_says"], ["LEGEND"])

    def test_search_provider_failures_and_bad_results(self):
        w = World()
        for _ in range(3):
            w.task(("LEGEND",), internet={"external_information_required": True, "internet_available": False})
        w.task(("LEGEND",), internet={"external_information_required": True, "internet_available": True,
                                      "internet_research_performed": True, "internet_results": [{"title": "t"}, {"url": "u", "title": "t"}]})
        w.tick()
        self.assertEqual(w.incident("SEARCH", "provider_unavailable").severity, "HIGH")
        self.assertEqual(w.incident("SEARCH", "malformed_results").severity, "WARNING")
        self.assertTrue(w.brains["COGNITIVE"].messages)                             # evidence quality goes to COGNITIVE (MCVL)
        self.assertTrue(any(p["type"] == "supervisor_alert" for _, p in w.brains["HEROIC"].messages))

    def test_loops_and_request_bursts(self):
        w = World()
        w.task(("LEGEND",), extra_events=500)
        for _ in range(25):
            w.task(("HEROIC",), created_age=1.0)
        w.tick(1)
        self.assertTrue(any(i.signature == "event_storm" and i.severity == "HIGH" for i in w.sup.store.active()))
        self.assertEqual(w.incident("NETWORK", "request_burst").type, "SECURITY")
        self.assertEqual(w.sup.escalation.outbox[-1].destination, "OPERATOR")      # security events are escalated, never acted on

    def test_memory_pressure_memory_growth_and_task_registry_growth(self):
        w = World(tasks_warn=500)
        w.metrics["mem_pct"] = 72.0
        w.tick()
        self.assertEqual(w.incident("PROCESS", "memory_pressure").severity, "WARNING")
        w.metrics["mem_pct"] = 90.0
        w.tick()
        self.assertEqual(w.incident("PROCESS", "memory_pressure").severity, "HIGH")
        w.metrics["mem_pct"] = 30.0
        for rss in (100, 115, 130, 145, 160, 175, 190, 205, 220, 235, 250):       # +150 MB over 10 minutes
            w.metrics["rss_mb"] = float(rss)
            w.tick(60)
        self.assertEqual(w.incident("PROCESS", "memory_growth").severity, "HIGH")
        for i in range(600):
            w.net.tasks[f"t{i}"] = SimpleNamespace(task_id=f"t{i}", events=[], created_at=iso_at(w.clock.t - 5000))
        w.tick()
        self.assertEqual(w.incident("NETWORK", "task_registry_growth").severity, "WARNING")

    def test_stale_feed_puts_a_hold_on_dependents_and_releases_it_when_fresh(self):
        w = World()
        w.sup.register_feed("market_data", 60, critical=True, dependents=("LEGEND",))
        w.sup.report_feed("market_data")
        w.tick(30)
        self.assertIsNone(w.incident("market_data"))
        w.tick(100)                                                                  # 130 s old, limit 60 s
        i = w.incident("market_data", "stale_feed")
        self.assertEqual((i.severity, i.type), ("HIGH", "DATA_INTEGRITY"))
        self.assertTrue(w.sup.is_held("market_data"))
        self.assertTrue(w.brains["COGNITIVE"].messages and w.brains["HEROIC"].messages)
        w.sup.report_feed("market_data")
        for _ in range(3):
            w.tick(10)
        self.assertIsNone(w.incident("market_data"))
        self.assertFalse(w.sup.is_held("market_data"))
        w.sup.register_feed("never", 10)
        w.tick(30)
        self.assertEqual(w.incident("never", "never_reported").severity, "WARNING")  # unknown is not "stale" and not "fresh"

    def test_self_report_versus_behaviour_is_resolved_by_authority_and_unresolvable_conflicts_escalate(self):
        w = World(health=("LEGEND",))
        for _ in range(3):
            w.task(("LEGEND",), fail={"LEGEND": "boom"})
        w.tick(force_probe=True)                                                    # LEGEND says "ready" but its calls fail
        self.assertEqual(w.sup.registry.components["LEGEND"].state, CS.UNHEALTHY)
        rec = w.sup.conflicts.log[-1]
        self.assertEqual(rec["rule"], "observed behaviour outranks self-report")
        self.assertFalse(any(i.type == "STATE_CONFLICT" for i in w.sup.store.active()))
        out = w.sup.receive_message("x", None, "UNITY", {"type": "conflict", "component": "MARCO", "claims": [
            {"source": "A", "says": "up", "rank": 2}, {"source": "B", "says": "down", "rank": 2}]})
        self.assertTrue(out["escalated"])
        w.tick()
        i = w.incident("MARCO", "unresolved_state_conflict")
        self.assertEqual(len(i.evidence[-1]["claims"]), 2)                          # both positions are kept

    def test_repeats_of_one_problem_make_one_incident_not_many(self):
        w = World()
        for _ in range(6):
            w.task(("LEGEND",), fail={"LEGEND": "boom"})
            w.tick(5)
        same = [i for i in w.sup.store.active() if i.component == "LEGEND" and i.signature == "consecutive_failures"]
        self.assertEqual(len(same), 1)
        self.assertGreaterEqual(same[0].occurrences, 5)
        self.assertEqual(same[0].severity, "CRITICAL")                              # severity only goes up while it is open

    def test_every_incident_has_a_timestamped_trail_and_a_clear_status(self):
        w = World()
        for _ in range(3):
            w.task(("LEGEND",), fail={"LEGEND": "boom"})
        w.task(("ALPHA",), unfinished=("ALPHA",), finished=False, age=100)
        w.tick()
        for i in w.sup.store.active():
            d = i.to_dict(full=True)
            self.assertIn(d["status"], [s.value for s in IS])
            self.assertTrue(d["audit_trail"] and d["audit_trail"][0]["at"])
            self.assertTrue(d["evidence"])
            self.assertIsNotNone(d["detected_at"])
        self.assertGreater(len(w.sup.audit), 0)
        self.assertTrue(w.sup.explain(w.incident("LEGEND").id)["audit_trail"])


class Actions(unittest.TestCase):
    def test_advisory_changes_nothing_and_records_what_it_would_do(self):
        w = World(health=("LEGEND",), reset=("LEGEND",), heal=True)
        for _ in range(5):
            w.task(("LEGEND",), fail={"LEGEND": "boom"})
        for _ in range(5):
            w.tick()
        self.assertEqual(w.brains["LEGEND"].resets, 0)
        self.assertNotIn("think", w.brains["LEGEND"].__dict__)                       # no guard was installed
        self.assertFalse(w.sup.registry.components["LEGEND"].guard)
        i = w.incident("LEGEND", "consecutive_failures")
        refused = [a for a in i.actions if not a.allowed]
        self.assertEqual(sorted({a.kind for a in refused}), ["ISOLATE_BRAIN", "RESET_BRAIN"])
        self.assertEqual(len(refused), 2)                                           # each recommendation is recorded once
        self.assertTrue(all("ADVISORY" in a.detail for a in refused))

    def test_reset_is_run_and_then_verified_against_the_brains_own_health(self):
        w = World(mode="ENFORCE", health=("LEGEND",), reset=("LEGEND",), heal=True)
        for _ in range(3):
            w.task(("LEGEND",), fail={"LEGEND": "boom"})
        w.brains["LEGEND"].ready = False
        w.tick()
        i = w.incident("LEGEND", "consecutive_failures")
        reset = [a for a in i.actions if a.kind == "RESET_BRAIN"][0]
        self.assertEqual((reset.executed, reset.ok, reset.verification["ok"]), (True, True, True))
        self.assertEqual(w.brains["LEGEND"].resets, 1)
        self.assertIn("health() after reset", reset.verification["checks"][0])

    def test_a_reset_that_does_not_heal_is_not_called_success_and_is_not_repeated_forever(self):
        w = World(mode="ENFORCE", health=("LEGEND",), reset=("LEGEND",), heal=False)
        w.brains["LEGEND"].ready = False
        for _ in range(3):
            w.task(("LEGEND",), fail={"LEGEND": "boom"})
        for _ in range(8):
            w.tick(130)                                                               # past the cooldown every time
        i = w.incident("LEGEND", "consecutive_failures")
        runs = [a for a in i.actions if a.kind == "RESET_BRAIN" and a.executed]
        self.assertTrue(all(a.verification["ok"] is False for a in runs))
        self.assertEqual(len(runs), 3)                                               # bounded: three tries, then it stops
        self.assertEqual(i.status, IS.UNRESOLVED)
        self.assertEqual(w.brains["LEGEND"].resets, 3)
        self.assertTrue(w.sup.escalation.outbox)

    def test_a_recovery_that_cannot_be_confirmed_stays_open(self):
        w = World(mode="ENFORCE", reset=("LEGEND",))                                  # a reset hook but no health()
        for _ in range(3):
            w.task(("LEGEND",), fail={"LEGEND": "boom"})
        w.tick()
        i = w.incident("LEGEND", "consecutive_failures")
        a = [x for x in i.actions if x.kind == "RESET_BRAIN"][0]
        self.assertIsNone(a.verification["ok"])
        self.assertIn("no health()", a.verification["checks"][0])
        self.assertIn(i.status, (IS.RECOVERING, IS.ESCALATED))                         # open, never "resolved" on a guess
        self.assertIsNone(w.sup.store.get(i.id).resolved_at or None)

    def test_circuit_breaker_isolates_a_failing_brain_and_lets_one_trial_call_through_later(self):
        w = World(mode="ENFORCE")
        legend, st = w.brains["LEGEND"], VALEBrainState(user_message="x")
        w.tick()                                                                      # installs the guards
        self.assertIn("think", legend.__dict__)
        legend.fail = "error"
        for _ in range(5):
            with self.assertRaises(RuntimeError):
                legend.think(st)
        self.assertEqual(w.sup.registry.components["LEGEND"].breaker, "OPEN")
        calls = legend.calls
        with self.assertRaises(BrainIsolatedError):
            legend.think(st)
        self.assertEqual(legend.calls, calls)                                         # refused without calling the brain
        w.clock.advance(61)
        with self.assertRaises(RuntimeError):
            legend.think(st)                                                          # the trial call fails: open again, longer
        self.assertEqual(w.sup.registry.components["LEGEND"].breaker, "OPEN")
        self.assertGreater(w.sup.registry.components["LEGEND"].breaker_open_s, 60)
        legend.fail = None
        w.clock.advance(w.sup.registry.components["LEGEND"].breaker_open_s + 1)
        self.assertEqual(legend.think(st)["ok"], True)
        self.assertEqual(w.sup.registry.components["LEGEND"].breaker, "CLOSED")

    def test_retry_is_bounded_and_only_for_transient_errors(self):
        w = World(mode="ENFORCE")
        w.tick()
        legend, st = w.brains["LEGEND"], VALEBrainState(user_message="x")
        legend.fail_n = 1
        self.assertTrue(legend.think(st)["ok"])
        self.assertEqual((legend.calls, w.sup.recovery.retries), (2, 1))
        legend.calls, legend.fail = 0, "value"
        with self.assertRaises(ValueError):
            legend.think(st)
        self.assertEqual(legend.calls, 1)                                             # not transient: no retry
        legend.calls, legend.fail = 0, "timeout"
        with self.assertRaises(TimeoutError):
            legend.think(st)
        self.assertEqual(legend.calls, 2)                                             # one try plus retry_max = 1

    def test_the_action_budget_and_cooldown_stop_runaway_recovery(self):
        w = World(mode="ENFORCE", health=("LEGEND", "ALPHA"), reset=("LEGEND", "ALPHA"), heal=False, action_budget=2)
        for b in ("LEGEND", "ALPHA"):
            w.brains[b].ready = False
            for _ in range(3):
                w.task((b,), fail={b: "boom"})
        for _ in range(40):
            w.tick(30)
        total = w.brains["LEGEND"].resets + w.brains["ALPHA"].resets
        self.assertLessEqual(total, 2 + 2)                                            # budget of 2 per window, at most a second window
        refused = [a for i in w.sup.store.active() for a in i.actions if not a.allowed and "budget" in a.detail]
        self.assertTrue(refused or total <= 2)

    def test_task_registry_pruning_keeps_the_newest_and_never_touches_work_in_flight(self):
        w = World(mode="ENFORCE", tasks_warn=500, tasks_keep=200)
        old = w.clock.t - 7200
        for i in range(800):
            w.net.tasks[f"old{i}"] = SimpleNamespace(task_id=f"old{i}", events=[], created_at=iso_at(old + i))
        busy = w.net.tasks["old3"]
        w.sup.registry.ensure("LEGEND").inflight["old3"] = w.clock.t - 5
        for i in range(100):
            w.net.tasks[f"new{i}"] = SimpleNamespace(task_id=f"new{i}", events=[], created_at=iso_at(w.clock.t - i))
        w.tick()
        i = w.incident("NETWORK", "task_registry_growth")
        prune = [a for a in i.actions if a.kind == "PRUNE_TASKS"][0]
        self.assertTrue(prune.verification["ok"])
        self.assertIn("old3", w.net.tasks)                                            # in flight: left alone
        self.assertIn("new99", w.net.tasks)
        self.assertLess(len(w.net.tasks), 900)
        self.assertLessEqual(len(w.net.tasks), 201 + 1)
        for _ in range(4):
            w.tick()
        self.assertIsNone(w.incident("NETWORK", "task_registry_growth"))              # it clears and is resolved with evidence

    def test_freeing_memory_is_not_called_a_success_unless_memory_actually_dropped(self):
        w = World(mode="ENFORCE")
        w.metrics["mem_pct"] = 75.0
        w.tick()
        i = w.incident("PROCESS", "memory_pressure")
        gc = [a for a in i.actions if a.kind == "GC_COLLECT"][0]
        self.assertTrue(gc.executed)
        self.assertIsNone(gc.verification["ok"])                                      # memory reading did not drop: inconclusive

    def test_rollback_is_refused_because_nothing_can_be_rolled_back(self):
        w = World(mode="ENFORCE")
        ok, why = w.sup.policy.authorize(PlannedAction("ROLLBACK", "X", "y"), Mode.ENFORCE, w.clock())
        self.assertFalse(ok)
        self.assertIn("no versioned rollback", why)

    def test_switching_modes_installs_and_removes_guards_and_restores_the_original_method(self):
        w = World()
        legend = w.brains["LEGEND"]
        original = legend.think
        out = w.sup.set_mode("ENFORCE")
        self.assertGreaterEqual(out["guards"], 3)
        self.assertIn("think", legend.__dict__)
        w.sup.set_mode("ADVISORY")
        self.assertNotIn("think", legend.__dict__)
        self.assertEqual(legend.think, original)
        self.assertFalse(any(c.guard or c.breaker != "CLOSED" for c in w.sup.registry.components.values()))

    def test_a_guard_is_transparent(self):
        w = World(mode="ENFORCE")
        w.tick()
        legend, st = w.brains["LEGEND"], VALEBrainState(user_message="x")
        self.assertEqual(legend.think(st), {"brain": "LEGEND", "ok": True})
        legend.think = legend.think  # still callable
        legend.fail = "error"
        with self.assertRaises(RuntimeError) as cm:
            legend.think(st)
        self.assertEqual(str(cm.exception), "boom")
        self.assertEqual(w.sup.registry.components["LEGEND"].inflight, {})

    def test_authorised_recovery_requests_only(self):
        w = World(mode="ENFORCE", health=("LEGEND",), reset=("LEGEND",))
        out = w.sup.receive_message("x", None, "MARCO", {"type": "recover", "component": "LEGEND"})
        self.assertEqual(out["error"], "NOT_AUTHORISED")
        out = w.sup.receive_message("x", None, "HEROIC", {"type": "recover", "component": "LEGEND"})
        self.assertTrue(out["ok"])
        self.assertEqual(w.brains["LEGEND"].resets, 1)
        adv = World(health=("LEGEND",), reset=("LEGEND",))
        self.assertEqual(adv.sup.receive_message("x", None, "HEROIC", {"type": "recover", "component": "LEGEND"})["error"], "REFUSED")


class RealNetworkModes(unittest.TestCase):
    def _run(self, mode):
        try:
            from HEROIC import HeroicBrain
        except Exception:                                                              # pragma: no cover
            self.skipTest("HEROIC is not installed")
        c = VALEConnector()
        sup = SupervisorBrain(c, SupervisorConfig(background=False, mode=mode, startup_grace_s=0.0, log=False,
                                                  expected_brains=("HEROIC", "UNITY", "SUPERVISOR")))
        net = BrainNetwork(connector=c)
        for b in (HeroicBrain(c), Stub("UNITY", c), sup):
            net.register(b)
        sup.tick()
        out = [net.process(q)["results"]["HEROIC"]["result"] for q in ("hi", "what is a stop loss?")]
        sup.tick()
        return sup, out

    def test_enforce_mode_is_invisible_to_a_healthy_system(self):
        adv_sup, adv = self._run("ADVISORY")
        enf_sup, enf = self._run("ENFORCE")
        self.assertEqual([r["status"] for r in adv], [r["status"] for r in enf])
        self.assertEqual([len(r["tasks"]) for r in adv], [len(r["tasks"]) for r in enf])
        h = enf_sup.registry.components["HEROIC"]
        self.assertTrue(h.guard and h.calls >= 2 and h.state == CS.HEALTHY)
        self.assertFalse(adv_sup.registry.components["HEROIC"].guard)
        self.assertFalse(enf_sup.incidents())
        enf_sup.set_mode("ADVISORY")
        self.assertNotIn("think", enf_sup.registry.brain_object("HEROIC").__dict__)


class Robustness(unittest.TestCase):
    def test_garbage_in_never_raises(self):
        w = World()
        w.net.tasks["g1"] = SimpleNamespace(task_id="g1", events="not a list", created_at="nonsense")
        w.net.tasks["g2"] = SimpleNamespace(task_id="g2")
        w.net.tasks["g3"] = SimpleNamespace(task_id="g3", events=[SimpleNamespace(), object(), BrainEvent("brain_think_error", "X", payload=None, timestamp="bad")], created_at=None)
        w.brains["LEGEND"].identity = lambda: (_ for _ in ()).throw(RuntimeError("identity exploded"))
        w.brains["ALPHA"].health = lambda: "not a dict"
        w.brains["COGNITIVE"].health = lambda: (_ for _ in ()).throw(ValueError("health exploded"))
        rep = w.tick(force_probe=True)
        self.assertIsInstance(rep, dict)
        self.assertNotIn("error", rep)
        self.assertEqual(w.sup.registry.components["COGNITIVE"].probe_ok, False)
        self.assertEqual(w.sup.think(object())["brain"], "SUPERVISOR")
        self.assertIn("error", w.sup.receive_message("x", None, "A", {"type": "signal", "kind": "nonsense"}) | {"error": 1})
        with self.assertRaises(ValueError):
            w.sup.think(None)
        w.sup.network.tasks = None
        self.assertNotIn("error", w.tick())

    def test_memory_is_bounded(self):
        w = World(max_active=50, incident_keep=40, audit_keep=300)
        for r in range(6):
            w.sup._pending.extend(Observation("OTHER", f"C{r}-{i}", "x", "INFORMATIONAL", "noise") for i in range(300))
            w.tick(5)
        self.assertLessEqual(len(w.sup.store), 50)
        self.assertGreater(w.sup.store.dropped, 0)
        self.assertLessEqual(len(w.sup.audit), 300)
        for _ in range(8):
            w.tick(5)
        self.assertLessEqual(len(w.sup.store.recent_resolved(1000)), 40)

    def test_a_check_stays_cheap_even_with_a_huge_task_registry(self):
        w = World()
        for i in range(30000):
            w.net.tasks[f"t{i}"] = SimpleNamespace(task_id=f"t{i}", events=[], created_at=iso_at(w.clock.t - 9999))
        w.tick()
        t0 = time.perf_counter()
        w.tick()
        self.assertLess(time.perf_counter() - t0, 0.1)

    def test_threads_can_call_brains_and_check_at_the_same_time(self):
        w = World(mode="ENFORCE")
        w.tick()
        errors, n = [], 300

        def caller(name):
            try:
                st = VALEBrainState(user_message="x")
                for _ in range(n):
                    w.brains[name].think(st)
            except Exception as exc:                                                # pragma: no cover
                errors.append(repr(exc))

        def ticker():
            try:
                for _ in range(40):
                    w.sup.tick()
            except Exception as exc:                                                # pragma: no cover
                errors.append(repr(exc))
        ts = [threading.Thread(target=caller, args=(b,)) for b in ("LEGEND", "ALPHA", "HEROIC")] + [threading.Thread(target=ticker)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errors, [])
        for b in ("LEGEND", "ALPHA", "HEROIC"):
            self.assertEqual(w.brains[b].calls, n)
            self.assertEqual(w.sup.registry.components[b].calls, n)
            self.assertEqual(w.sup.registry.components[b].inflight, {})

    def test_the_background_thread_runs_and_stops(self):
        c = VALEConnector()
        sup = SupervisorBrain(c, SupervisorConfig(background=True, tick_interval_s=0.05, startup_grace_s=0.0,
                                                  min_tick_gap_s=0.0, log=False, expected_brains=("SUPERVISOR",)))
        net = BrainNetwork(connector=c)
        net.register(sup)
        deadline = time.time() + 3
        while sup.telemetry.counters.get("tick", 0) < 3 and time.time() < deadline:
            time.sleep(0.02)
        self.assertGreaterEqual(sup.telemetry.counters.get("tick", 0), 3)
        self.assertTrue(sup.health()["background_thread"])
        sup.stop()
        self.assertFalse(sup._thread.is_alive())

    def test_outputs_are_json_serialisable(self):
        w = World(health=("LEGEND",))
        for _ in range(3):
            w.task(("LEGEND",), fail={"LEGEND": "boom"})
        w.tick(force_probe=True)
        for obj in (w.sup.status(), w.sup.incidents(False), w.sup.export(), w.sup.health(), w.sup.contract(), w.sup.identity(),
                    w.sup.think(VALEBrainState(user_message="hi")), w.sup.explain(w.incident("LEGEND").id)):
            json.dumps(obj)
        for cmd in ("status", "incidents", "audit", "outbox", "health", "contract", "tick", "probe"):
            json.dumps(w.sup.receive_message("x", None, "UNITY", {"type": cmd, "component": "LEGEND"}))

    def test_think_commands_and_the_voice_rule(self):
        w = World()
        w.tick(force_probe=True)
        w.tick()
        r = w.sup.think(VALEBrainState(user_message="what is bitcoin?"))
        self.assertNotIn("voice", r)
        self.assertNotIn("message", r)
        r = w.sup.think(VALEBrainState(user_message="is the vale system healthy?"))
        self.assertIn("voice", r)
        self.assertNotIn("everything is fine", r["voice"].lower())
        self.assertEqual(r["status"], "OK_PARTIAL")
        silent = World(speak="off")
        self.assertNotIn("voice", silent.sup.think(VALEBrainState(user_message="is the vale system healthy?")))
        self.assertEqual(w.sup.receive_message("m", None, "X", {"type": "nonsense"})["error"], "UNKNOWN_COMMAND")
        self.assertTrue(w.sup.receive_message("m", None, "X", None)["ok"])
        self.assertTrue(w.sup.receive_message("m", None, "LEGEND", {"type": "signal", "kind": "heartbeat"})["ok"])
        self.assertEqual(w.sup.receive_message("m", None, "LEGEND", {"type": "signal", "component": "ALPHA", "kind": "ok"})["error"], "NOT_AUTHORISED")
        self.assertFalse(w.sup.contract()["writes_user_text"] is False)

    def test_routine_handling_is_measured_and_well_inside_the_two_to_three_second_target(self):
        w = World()
        for _ in range(3):
            w.task(("LEGEND",), fail={"LEGEND": "boom"})
        w.tick()
        h = w.sup.health()["routine_handling"]
        self.assertGreater(h["detect_to_response_ms"]["samples"], 0)
        self.assertLess(h["detect_to_response_ms"]["p95"], 2000)

    def test_it_works_inside_the_real_network_and_watches_the_real_heroic(self):
        try:
            from HEROIC import HeroicBrain
        except Exception:                                                              # pragma: no cover
            self.skipTest("HEROIC is not installed")
        c = VALEConnector()
        clock = Clock()
        sup = SupervisorBrain(c, SupervisorConfig(background=False, startup_grace_s=0.0, log=False, expected_brains=("HEROIC", "UNITY", "SUPERVISOR")), clock=clock)
        net = BrainNetwork(connector=c)
        for b in (HeroicBrain(c), Stub("UNITY", c), sup):
            net.register(b)
        real_now = time.time()
        clock.t = real_now
        out = net.process("what is a stop loss?")
        self.assertIn("HEROIC", out["results"])
        sup.tick(force_probe=True)
        h = sup.registry.components["HEROIC"]
        self.assertEqual((h.state, h.ready), (CS.HEALTHY, True))
        self.assertGreaterEqual(h.calls, 1)
        self.assertTrue(h.coverage["health"] and h.coverage["contract"] and h.coverage["recovery_hook"])
        self.assertEqual(sup.status()["overall"] in ("OK", "OK_PARTIAL"), True)
        self.assertFalse(sup.incidents())


class Fuzz(unittest.TestCase):
    def test_random_event_streams_never_break_the_invariants(self):
        rnd = random.Random(11)
        names = ["HEROIC", "LEGEND", "ALPHA", "UNITY", "COGNITIVE"]
        w = World(health=("LEGEND", "ALPHA"), reset=("LEGEND",), max_active=80, tasks_warn=40)
        for step in range(250):
            for _ in range(rnd.randint(0, 4)):
                bs = tuple(rnd.sample(names, rnd.randint(1, 4)))
                w.task(bs, fail={b: "e" for b in bs if rnd.random() < 0.3}, slow={b: rnd.choice([0.05, 6, 40]) for b in bs},
                       required=list(rnd.sample(names, rnd.randint(0, 3))), finished=rnd.random() < 0.8,
                       unfinished=tuple(b for b in bs if rnd.random() < 0.1), age=rnd.choice([1, 30, 400, 2000]),
                       internet=rnd.choice([None, {"external_information_required": True, "internet_available": rnd.random() < 0.5}]))
            if rnd.random() < 0.1:
                w.metrics["mem_pct"] = rnd.choice([20.0, 75.0, 90.0, 97.0])
            if rnd.random() < 0.1:
                w.brains[rnd.choice(names)].ready = rnd.random() < 0.5
            rep = w.tick(rnd.choice([1, 20, 70]), force_probe=rnd.random() < 0.2)
            self.assertNotIn("error", rep)
            self.assertLessEqual(len(w.sup.store), 80)
            for i in w.sup.store.active():
                self.assertIn(i.status, [s for s in IS if s != IS.RESOLVED])
                self.assertIn(i.severity, ("INFORMATIONAL", "WARNING", "HIGH", "CRITICAL"))
        self.assertEqual(w.brains["LEGEND"].resets, 0)                                 # ADVISORY never acted
        self.assertFalse(any(c.guard for c in w.sup.registry.components.values()))
        json.dumps(w.sup.export())


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    sys.exit(0 if result.wasSuccessful() else 1)
