"""Explicit state machines for missions, plans and tasks. Every transition is checked and recorded."""
from __future__ import annotations

from typing import Callable, Dict, FrozenSet, Optional, Tuple

from .enums import MissionState as M, PlanState as P, TaskState as T
from .models import Mission, Plan, Task
from .util import now_ns

MISSION_TRANSITIONS: Dict[M, FrozenSet[M]] = {
    M.NEW: frozenset({M.UNDERSTANDING, M.BLOCKED, M.ESCALATED, M.CANCELLED}),
    M.UNDERSTANDING: frozenset({M.PLANNING, M.BLOCKED, M.ESCALATED, M.CANCELLED}),
    M.PLANNING: frozenset({M.READY, M.BLOCKED, M.ESCALATED, M.CANCELLED, M.UNDERSTANDING}),
    M.READY: frozenset({M.EXECUTING, M.REPLANNING, M.BLOCKED, M.ESCALATED, M.CANCELLED, M.UNDERSTANDING}),
    M.EXECUTING: frozenset({M.VERIFYING, M.REPLANNING, M.BLOCKED, M.ESCALATED, M.FAILED, M.CANCELLED, M.UNDERSTANDING}),
    M.VERIFYING: frozenset({M.COMPLETED, M.REPLANNING, M.EXECUTING, M.BLOCKED, M.ESCALATED, M.FAILED, M.CANCELLED, M.UNDERSTANDING}),
    M.REPLANNING: frozenset({M.READY, M.BLOCKED, M.ESCALATED, M.CANCELLED, M.FAILED, M.UNDERSTANDING}),
    M.BLOCKED: frozenset({M.UNDERSTANDING, M.PLANNING, M.READY, M.REPLANNING, M.EXECUTING, M.ESCALATED,
                          M.CANCELLED, M.FAILED}),
    M.ESCALATED: frozenset({M.UNDERSTANDING, M.PLANNING, M.READY, M.REPLANNING, M.BLOCKED, M.CANCELLED, M.FAILED}),
    M.COMPLETED: frozenset(),
    M.FAILED: frozenset(),
    M.CANCELLED: frozenset(),
}

PLAN_TRANSITIONS: Dict[P, FrozenSet[P]] = {
    P.CREATED: frozenset({P.DRAFT, P.READY, P.BLOCKED, P.CANCELLED}),
    P.DRAFT: frozenset({P.READY, P.BLOCKED, P.CANCELLED, P.FAILED}),
    P.READY: frozenset({P.EXECUTING, P.REPLANNING, P.BLOCKED, P.CANCELLED}),
    P.EXECUTING: frozenset({P.COMPLETED, P.BLOCKED, P.REPLANNING, P.FAILED, P.CANCELLED}),
    P.BLOCKED: frozenset({P.DRAFT, P.READY, P.REPLANNING, P.EXECUTING, P.FAILED, P.CANCELLED}),
    P.REPLANNING: frozenset({P.DRAFT, P.READY, P.BLOCKED, P.FAILED, P.CANCELLED}),
    P.COMPLETED: frozenset(),
    P.FAILED: frozenset(),
    P.CANCELLED: frozenset(),
}

TASK_TRANSITIONS: Dict[T, FrozenSet[T]] = {
    T.PENDING: frozenset({T.READY, T.BLOCKED, T.CANCELLED, T.SKIPPED}),
    T.BLOCKED: frozenset({T.PENDING, T.READY, T.CANCELLED, T.SKIPPED, T.FAILED}),
    T.READY: frozenset({T.RUNNING, T.BLOCKED, T.PENDING, T.CANCELLED, T.SKIPPED}),
    T.RUNNING: frozenset({T.COMPLETED, T.FAILED, T.CANCELLED, T.READY}),
    T.FAILED: frozenset({T.READY, T.CANCELLED, T.SKIPPED}),
    T.COMPLETED: frozenset(),
    T.CANCELLED: frozenset(),
    T.SKIPPED: frozenset(),
}

Guard = Callable[[Mission, M], Tuple[bool, str]]


def move_mission(m: Mission, to: M, reason: str, guard: Optional[Guard] = None) -> Tuple[bool, str]:
    """Move a mission to a new state if the transition is legal and its guard (if any) passes."""
    frm = m.state
    if frm == to:
        return True, "unchanged"
    if to not in MISSION_TRANSITIONS[frm]:
        m.log("transition_refused", f"{frm.value}->{to.value}", "illegal transition")
        return False, f"illegal transition {frm.value}->{to.value}"
    if guard is not None:
        ok, why = guard(m, to)
        if not ok:
            m.log("guard_refused", f"{frm.value}->{to.value}", why)
            return False, why
    ts = now_ns()
    m.state = to
    m.state_since_ns = ts
    m.history.append((ts, f"{frm.value}->{to.value}", reason))
    m.log("state", f"{frm.value}->{to.value}", reason)
    m.updated_ns = ts
    return True, "ok"


def move_plan(m: Mission, plan: Plan, to: P, reason: str) -> bool:
    if plan.state == to:
        return True
    if to not in PLAN_TRANSITIONS[plan.state]:
        m.log("plan_transition_refused", f"{plan.state.value}->{to.value}", reason)
        return False
    m.log("plan_state", f"{plan.state.value}->{to.value}", reason)
    plan.state = to
    return True


def move_task(m: Mission, t: Task, to: T, reason: str = "") -> bool:
    if t.state == to:
        return True
    if to not in TASK_TRANSITIONS[t.state]:
        m.log("task_transition_refused", f"{t.id}:{t.state.value}->{to.value}", reason)
        return False
    ts = now_ns()
    if to == T.RUNNING:
        t.started_ns = ts
        t.attempts += 1
    elif to in (T.COMPLETED, T.FAILED, T.CANCELLED, T.SKIPPED):
        t.ended_ns = ts
    t.state = to
    m.log("task_state", f"{t.id}->{to.value}", reason)
    return True
