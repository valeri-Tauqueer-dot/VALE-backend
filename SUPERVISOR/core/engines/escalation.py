"""Escalation manager. Sends unresolved or high-impact incidents to the right authority, with limits against floods."""
from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, Optional, Tuple

from ..core.models import Escalation, Incident
from ..core.util import clip

_ALIASES = {"MCVL": "COGNITIVE", "USER": "OPERATOR", "HUMAN": "OPERATOR"}


class EscalationManager:
    def __init__(self, sup: Any) -> None:
        self.sup = sup
        self.sent: Deque[Escalation] = deque(maxlen=200)
        self.outbox: Deque[Escalation] = deque(maxlen=100)       # alerts for a person: read them with the 'outbox' command
        self._last: Dict[Tuple[str, str], float] = {}
        self._times: Deque[float] = deque(maxlen=50)
        self.suppressed = 0

    def deliver(self, inc: Optional[Incident], destination: str, reason: str, now: float, force: bool = False) -> Optional[Escalation]:
        sup, cfg = self.sup, self.sup.cfg
        if inc is None:
            return None
        dest = _ALIASES.get(destination.upper(), destination.upper())
        key = (inc.id, dest)
        last = self._last.get(key)
        if not force and last is not None and now - last < cfg.escalate_cooldown_s:
            self.suppressed += 1
            return None
        recent = sum(1 for t in self._times if now - t <= 60)
        if recent >= 10 and inc.severity != "CRITICAL":
            self.suppressed += 1
            return None
        self._last[key] = now
        self._times.append(now)
        esc = Escalation(id=sup.next_id("esc"), incident=inc.id, destination=dest, severity=inc.severity,
                         summary=clip(inc.summary, 200), at=now)
        message = f"SUPERVISOR ALERT [{inc.severity}] {inc.type} on {inc.component}: {inc.summary}"
        if dest == "OPERATOR":
            esc.delivered, esc.note = True, "recorded for a person and written to the log"
            self.outbox.append(esc)
            sup.log("error" if inc.severity == "CRITICAL" else "warning", f"ESCALATION to a person: {message}")
        else:
            brain = sup.network.get_brain(dest) if sup.network is not None else None
            if brain is None:
                esc.delivered, esc.note = False, f"{dest} is not registered, so the alert could not be delivered"
            elif not cfg.deliver_escalations:
                esc.delivered, esc.note = False, "delivery is switched off (SUPERVISOR_DELIVER_ESCALATIONS=0)"
            else:
                try:
                    brain.receive_message(message=message, state=sup.make_state(), source_brain="SUPERVISOR",
                                          payload={"type": "supervisor_alert", "incident": inc.to_dict(), "reason": reason})
                    esc.delivered, esc.note = True, f"delivered to {dest}"
                except Exception as exc:
                    esc.delivered, esc.note = False, clip(f"{dest} refused the alert: {type(exc).__name__}: {exc}", 160)
        self.sent.append(esc)
        with sup.lock:
            if dest not in inc.escalated_to:
                inc.escalated_to.append(dest)
        sup.audit.add(now, "escalation", inc.id, f"to {dest}: {esc.note}")
        return esc
