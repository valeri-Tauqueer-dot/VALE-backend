"""Mission memory, evolution and health/contract interfaces.

These are interfaces, not systems. Mission memory keeps per-mission history only and never replaces VALE's
global Memory. The evolution interface only COLLECTS verified-outcome signals; it never changes HEROIC itself.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional

from ..core.enums import MissionState, OPEN_INFO
from ..core.models import Mission
from ..core.util import content_tokens, jaccard, now_ns


class MissionMemory:
    def __init__(self, size: int = 512) -> None:
        self._items: Deque[Dict[str, Any]] = deque(maxlen=max(16, size))

    def archive(self, m: Mission) -> None:
        item = {"id": m.id, "request": m.request[:160], "state": m.state.value,
                "outcome": m.outcome.value if m.outcome else None,
                "mission_type": m.intent.mission_type if m.intent else None,
                "domains": list(m.intent.domains) if m.intent else [], "tasks": len(m.tasks),
                "replans": m.replans, "process_score": m.quality.get("process_score"),
                "limitations": len([1 for r in m.info.values() if r.state in OPEN_INFO]),
                "archived_ns": now_ns(), "tokens": frozenset(content_tokens(m.request)[:16])}
        for i, x in enumerate(self._items):
            if x["id"] == m.id:
                del self._items[i]
                break
        self._items.append(item)

    def recall(self, mission_id: str) -> Optional[Dict[str, Any]]:
        for x in reversed(self._items):
            if x["id"] == mission_id:
                return {k: (sorted(v) if isinstance(v, frozenset) else v) for k, v in x.items()}
        return None

    def similar(self, text: str, k: int = 3) -> List[Dict[str, Any]]:
        q = set(content_tokens(text)[:16])
        scored = sorted(((jaccard(q, x["tokens"]), x) for x in self._items), key=lambda p: -p[0])
        return [{"id": x["id"], "similarity": round(s, 2), "request": x["request"], "outcome": x["outcome"]}
                for s, x in scored[:k] if s > 0.3]

    def __len__(self) -> int:
        return len(self._items)


class EvolutionInterface:
    def __init__(self, size: int = 500) -> None:
        self._items: Deque[Dict[str, Any]] = deque(maxlen=max(16, size))

    def record(self, m: Mission) -> None:
        if m.outcome is None and m.state not in (MissionState.FAILED, MissionState.CANCELLED):
            return
        self._items.append({
            "mission_type": m.intent.mission_type if m.intent else None,
            "domains": list(m.intent.domains) if m.intent else [], "plan_tasks": len(m.tasks),
            "replans": m.replans, "rounds": m.rounds, "outcome": m.outcome.value if m.outcome else m.state.value,
            "process_score": m.quality.get("process_score"),
            "failed_capabilities": sorted({t.capability for t in m.tasks.values() if t.state.value == "FAILED"}),
            "duration_s": round((m.updated_ns - m.created_ns) / 1e9, 3)})

    def signals(self) -> Dict[str, Any]:
        items = list(self._items)
        by: Dict[str, Dict[str, Any]] = {}
        caps: Dict[str, int] = {}
        for x in items:
            b = by.setdefault(x["mission_type"] or "UNKNOWN", {"count": 0, "score": 0.0, "scored": 0, "replans": 0, "partial": 0})
            b["count"] += 1
            b["replans"] += 1 if x["replans"] else 0
            b["partial"] += 1 if x["outcome"] == "PARTIAL_COMPLETION" else 0
            if x["process_score"] is not None:
                b["score"] += x["process_score"]
                b["scored"] += 1
            for c in x["failed_capabilities"]:
                caps[c] = caps.get(c, 0) + 1
        return {"missions_recorded": len(items), "note": "read-only signals; HEROIC never changes itself from them",
                "by_mission_type": {k: {"count": v["count"],
                                        "avg_process_score": round(v["score"] / v["scored"], 2) if v["scored"] else None,
                                        "replan_rate": round(v["replans"] / v["count"], 2),
                                        "partial_rate": round(v["partial"] / v["count"], 2)} for k, v in by.items()},
                "capability_failures": caps}


def build_contract(brain: Any) -> Dict[str, Any]:
    """The minimum operational contract SUPERVISOR needs to watch HEROIC."""
    return {
        "identity": {"brain": brain.brain_name, "version": brain.version, "role": brain.ROLE},
        "dependencies": ["vale_brain_interface.VALEBrainInterface", "brain_state.VALEBrainState (duck-typed)",
                         "connector.internet_available() (optional)", "network.brain_names() (optional)"],
        "health": {"method": "health()", "liveness": "live", "readiness": "ready",
                   "rule": "a signal that is not available is reported as null, never as healthy"},
        "operations": ["think(state)", "receive_message(...)", "create_mission", "report_task_started",
                       "report_task_result", "report_information", "report_verification", "report_brain_results",
                       "report_brain_unavailable", "add_constraint", "change_priority", "update_request",
                       "cancel_mission", "evaluate", "replan", "explain", "audit", "learning_signals", "reset"],
        "commands": sorted(brain._COMMANDS),
        "events_published": ["heroic_mission_state_updated"],
        "shared_state_keys_written": ["heroic_status", "heroic_mission", "heroic_result", "heroic_activation"],
        "correlation_ids": ["mission_id (equals the network task_id)", "task_id", "plan_id"],
        "state_models": {"mission": [s.value for s in MissionState]},
        "error_categories": ["PLANNING_ERROR", "INVALID_TRANSITION", "GUARD_REFUSED", "UNKNOWN_MISSION", "REJECTED"],
        "timing": ["timing_ms (per stage, every result)", "telemetry latency p50/p95/max"],
        "limits": {"max_missions": brain.cfg.max_missions, "max_tasks": brain.cfg.max_tasks,
                   "max_replans": brain.cfg.max_replans, "max_rounds": brain.cfg.max_rounds},
        "recovery": ["reset() clears live missions and caches; telemetry is kept"],
        "writes_user_text": brain.cfg.speak,
    }


def build_health(brain: Any) -> Dict[str, Any]:
    tel = brain.telemetry
    now = now_ns()
    last_ok = tel.last_ok_ns
    recent_err = sum(1 for e in list(tel.errors) if (now - e["at_ns"]) / 1e9 < 60)
    total = tel.counters.get("think", 0) + tel.counters.get("receive_message", 0)
    ready = tel.error_count == 0 or (total > 0 and tel.error_count / max(1, total) < 0.2)
    return {
        "brain": brain.brain_name, "version": brain.version, "live": True, "ready": bool(ready),
        "status": "DEGRADED" if recent_err >= 3 else "ONLINE",
        "uptime_s": round((now - tel.started_ns) / 1e9, 1),
        "last_success_age_s": round((now - last_ok) / 1e9, 1) if last_ok else None,
        "missions": {"live": len(brain.registry), "limit": brain.cfg.max_missions, "evicted": brain.registry.evicted,
                     "by_state": brain.registry.counts_by_state(), "archived": len(brain.memory)},
        "latency": {"think": tel.stats("think"), "receive_message": tel.stats("receive_message")},
        "errors": {"total": tel.error_count, "last_minute": recent_err, "recent": list(tel.errors)[-3:]},
        "intent_cache": dict(brain.intent._cached.cache_info()._asdict()),
        "network_attached": brain.network is not None,
    }
