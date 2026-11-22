"""SUPERVISOR's own contract and health. The contract says what it watches, what it cannot see, and what it may do."""
from __future__ import annotations

from typing import Any, Dict

from ..core.enums import ActionKind as AK, MUTATING
from ..core.util import iso


def build_contract(sup: Any) -> Dict[str, Any]:
    cfg = sup.cfg
    return {
        "identity": {"brain": sup.brain_name, "version": sup.version, "role": sup.ROLE},
        "watches": {
            "brains": "lifecycle events the network already records (started, completed, error, with timestamps), "
                      "health() when a brain has it, identity() as a liveness check when it does not",
            "network": "number of task states held in memory, request bursts, event loops, failed messages",
            "process": "memory (and its growth), the memory limit when the cgroup file is readable, threads, file handles",
            "data_sources": "search availability and errors, malformed search results, freshness of feeds that a producer registers",
            "state": "required brains that never ran, shared state that disagrees with the lifecycle events",
        },
        "cannot_see": [
            "sessions, credentials or tokens: the system exposes no signals for them",
            "external services beyond what task states show: SUPERVISOR makes no active network probes",
            "a call that hangs cannot be stopped from inside the same process; it can only be detected and escalated",
            "CPU saturation: only the load average is read",
        ],
        "unknown_rule": "a signal that is missing is reported as UNKNOWN or null. It is never reported as healthy.",
        "modes": {"ADVISORY": "observe, classify, record, escalate. Nothing in the system is changed.",
                  "ENFORCE": "also runs the approved recovery actions, within budget and cooldown limits"},
        "actions": {"always_allowed": [a.value for a in AK if a not in MUTATING and a != AK.ROLLBACK and a != AK.RETRY],
                    "enforce_only": sorted(a.value for a in MUTATING),
                    "not_supported": ["ROLLBACK (no versioned rollback controls exist)"],
                    "retry": "inside a guarded call only, for transient errors, at most " + str(cfg.retry_max) + " time(s)"},
        "commands": sorted(sup._COMMANDS),
        "escalation_destinations": {"HEROIC": "mission feasibility, missing brains and data",
                                    "UNITY": "integration, state, communication and core-brain problems",
                                    "COGNITIVE": "evidence and data integrity (MCVL role)",
                                    "OPERATOR": "a person: security, resource and unrecoverable problems (log + outbox)"},
        "writes_user_text": cfg.speak == "on_request",
        "user_text_rule": "only when the user asks about system health, and only from observed facts",
        "limits": {"incidents_kept": cfg.incident_keep, "active_incidents": cfg.max_active, "audit_entries": cfg.audit_keep,
                   "tick_interval_s": cfg.tick_interval_s, "actions_per_window": cfg.action_budget},
        "monitored_component_contract": [
            "identity, version, role", "health() with live / ready / status", "lifecycle events with timestamps",
            "a correlation id (task_id) on every event", "error category and message", "timing (start and end)",
            "resource metrics where relevant", "freshness metadata for data feeds", "recovery hook: reset()"],
        "routine_handling_target": "design target 2-3 s from detection to a recorded response. "
                                   "See health()['routine_handling'] for what was measured. Detection itself waits for the next check.",
    }


def build_health(sup: Any) -> Dict[str, Any]:
    tel, now = sup.telemetry, sup.clock()
    tick = tel.stats("tick")
    thread_alive = bool(sup._thread and sup._thread.is_alive())
    recent_err = sum(1 for e in list(tel.errors) if time_since(e["at"]) < 120)
    total = tel.counters.get("tick", 0) + tel.counters.get("think", 0) + tel.counters.get("receive_message", 0)
    ready = tel.error_count == 0 or (total > 0 and tel.error_count / max(1, total) < 0.2)
    delays = sup.delays
    handling = sup.handling
    return {
        "brain": sup.brain_name, "version": sup.version, "live": True, "ready": bool(ready),
        "status": "DEGRADED" if recent_err >= 3 else "ONLINE", "mode": sup.mode.value,
        "background_thread": thread_alive, "background_enabled": sup.cfg.background,
        "last_tick_age_s": round(now - sup.last_tick, 1) if sup.last_tick else None,
        "ticks": tel.counters.get("tick", 0), "tick": tick,
        "routine_handling": {
            "detect_to_response_ms": {"p50": _ms(handling.pct(50)), "p95": _ms(handling.pct(95)), "samples": len(handling)},
            "evidence_to_detection_s": {"p50": _r(delays.pct(50)), "p95": _r(delays.pct(95)), "samples": len(delays)},
            "note": "measured on real incidents in this process; not a guarantee"},
        "incidents": sup.store.counts(), "holds": sorted(sup.holds),
        "errors": {"total": tel.error_count, "last_two_minutes": recent_err, "recent": list(tel.errors)[-3:]},
        "guards_installed": len(sup.recovery._guards),
    }


def time_since(ts: float) -> float:
    import time
    return time.time() - ts


def _ms(v):
    return None if v is None else round(v * 1000, 3)


def _r(v):
    return None if v is None else round(v, 3)
