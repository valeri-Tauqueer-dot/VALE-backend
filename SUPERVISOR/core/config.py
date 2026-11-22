"""SUPERVISOR configuration. Every value can be overridden with a SUPERVISOR_<NAME> environment variable."""
from __future__ import annotations

import os
from dataclasses import dataclass, fields
from typing import Tuple


def _env(name: str, cast, default):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        if cast is bool:
            return raw.strip().lower() in ("1", "true", "yes", "on")
        if cast is tuple:
            return tuple(x.strip().upper() for x in raw.split(",") if x.strip())
        return cast(raw)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class SupervisorConfig:
    mode: str = "ADVISORY"                 # ADVISORY: observe and report only. ENFORCE: may run approved recovery actions.
    background: bool = True                # a small daemon thread that checks the system every tick_interval_s
    tick_interval_s: float = 20.0
    min_tick_gap_s: float = 1.0            # never check more often than this, even when woken early
    probe_interval_s: float = 60.0
    probe_ttl_s: float = 180.0
    scan_tasks: int = 64                   # newest tasks looked at on each tick
    history_window_s: float = 900.0        # older events are ignored
    fresh_evidence_s: float = 900.0        # evidence older than this no longer proves anything
    slow_s: float = 5.0
    timeout_s: float = 30.0
    stall_s: float = 60.0                  # a call that has not finished after this long is a possible hang
    fail_warn: int = 1
    fail_high: int = 3
    fail_critical: int = 5
    recover_ok: int = 3                    # consecutive good signals needed before a component counts as recovered
    clear_ticks: int = 3                   # ticks a problem must be absent before the incident is resolved
    breaker_failures: int = 5
    breaker_open_s: float = 60.0
    breaker_max_open_s: float = 600.0
    retry_max: int = 1
    retry_backoff_s: float = 0.2
    event_storm: int = 400                 # events in one task that look like a loop
    event_repeat: int = 50
    tasks_warn: int = 500
    tasks_high: int = 2000
    tasks_critical: int = 10000
    tasks_keep: int = 200
    tasks_prune_age_s: float = 900.0
    mem_warn_pct: float = 70.0
    mem_high_pct: float = 85.0
    mem_critical_pct: float = 95.0
    mem_growth_mb: float = 50.0            # growth over growth_window_s that counts as a possible leak
    growth_window_s: float = 600.0
    threads_warn: int = 100
    fd_warn_pct: float = 80.0
    burst_warn: int = 20                   # tasks created within 10 s
    burst_high: int = 50
    action_budget: int = 12                # recovery actions allowed per budget_window_s
    budget_window_s: float = 600.0
    cooldown_s: float = 120.0              # minimum gap between the same action on the same target
    startup_grace_s: float = 30.0          # no 'brain missing' incidents while the system is still starting
    unresolved_after_s: float = 3600.0     # an escalated incident with no resolution after this long is marked UNRESOLVED
    warn_escalate_s: float = 600.0         # a WARNING that lasts this long is escalated
    escalate_cooldown_s: float = 300.0
    deliver_escalations: bool = True
    expected_brains: Tuple[str, ...] = ("UNITY", "HEROIC", "ALPHA", "LEGEND", "MARCO", "FEELINGS", "COGNITIVE", "SUPERVISOR")
    incident_keep: int = 500
    max_active: int = 300
    audit_keep: int = 2000
    log: bool = True
    speak: str = "on_request"              # on_request | off. SUPERVISOR only speaks when the user asks about system health

    @classmethod
    def from_env(cls) -> "SupervisorConfig":
        kw = {f.name: _env("SUPERVISOR_" + f.name.upper(), type(f.default), f.default) for f in fields(cls)}
        if kw["mode"] not in ("ADVISORY", "ENFORCE"):
            kw["mode"] = "ADVISORY"
        return cls(**kw)
