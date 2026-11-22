"""Verification engine. A recovery is never called successful because a command returned without an error.

Each action is checked against something observable afterwards. If it cannot be confirmed the answer is
"inconclusive" (ok = None), which keeps the incident open.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..core.enums import ActionKind as AK, Breaker
from ..core.models import ActionRecord, PlannedAction
from ..core.util import iso


class VerificationEngine:
    def __init__(self, sup: Any) -> None:
        self.sup = sup

    def verify(self, rec: ActionRecord, act: PlannedAction) -> Optional[Dict[str, Any]]:
        if not rec.executed:
            return None
        sup = self.sup
        checks: List[str] = []
        ok: Optional[bool] = None
        facts = (rec.verification or {}).get("facts", {})
        kind = AK(rec.kind)
        if not rec.ok and kind in (AK.RESET_BRAIN, AK.ISOLATE_BRAIN, AK.RESTORE_BRAIN, AK.PRUNE_TASKS, AK.GC_COLLECT):
            ok, checks = False, [f"the action itself failed: {rec.detail}"]
        elif kind == AK.RESET_BRAIN:
            brain = sup.registry.brain_object(rec.target)
            res = sup.prober.probe(brain) if brain is not None else None
            if res is None:
                ok, checks = False, ["brain not found after reset"]
            else:
                with sup.lock:
                    sup.registry.record_probe(rec.target, sup.clock(), res)
                if res["how"] == "health":
                    ok = bool(res["ok"] and res["ready"] is not False)
                    checks.append(f"health() after reset: ok={res['ok']} ready={res['ready']}")
                else:
                    ok = None
                    checks.append("the brain has no health(): only liveness is known, so recovery cannot be confirmed")
        elif kind == AK.ISOLATE_BRAIN:
            c = sup.registry.components.get(rec.target)
            ok = bool(c and c.breaker == Breaker.OPEN.value and c.guard and sup.recovery.would_block(rec.target))
            checks.append(f"breaker open={bool(c and c.breaker == Breaker.OPEN.value)}, guard installed={bool(c and c.guard)}, next call would be refused={sup.recovery.would_block(rec.target)}")
        elif kind == AK.RESTORE_BRAIN:
            c = sup.registry.components.get(rec.target)
            ok = bool(c and c.breaker == Breaker.CLOSED.value)
            checks.append(f"breaker closed={ok}")
        elif kind == AK.PRUNE_TASKS:
            closed = facts.get("closed", 0)
            ok = True if closed > 0 and facts.get("after", 0) < facts.get("before", 0) else None
            checks.append(f"task states before={facts.get('before')} after={facts.get('after')} closed={closed}")
            if ok is None:
                checks.append("nothing eligible was closed, so memory use is unchanged")
        elif kind == AK.GC_COLLECT:
            b, a = facts.get("rss_before"), facts.get("rss_after")
            if b is not None and a is not None:
                ok = True if a < b - 0.5 else None
                checks.append(f"memory {b:.1f} MB -> {a:.1f} MB")
            else:
                checks.append("memory use could not be read, so the effect is unknown")
        elif kind in (AK.NOTIFY, AK.ESCALATE):
            ok = rec.ok
            checks.append("delivered to the target's receive_message(); this does not mean anyone has acted on it" if rec.ok
                          else f"not delivered: {rec.detail}")
        elif kind == AK.HOLD:
            ok = rec.target in sup.holds
            checks.append(f"hold present={ok}")
        elif kind == AK.RELEASE_HOLD:
            ok = rec.target not in sup.holds
            checks.append(f"hold removed={ok}")
        return {"at": iso(sup.clock()), "action": rec.id, "kind": rec.kind, "ok": ok, "checks": checks}
