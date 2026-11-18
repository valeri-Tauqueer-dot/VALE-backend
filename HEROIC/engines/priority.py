"""Priority engine. Importance and urgency are scored separately, then combined."""
from __future__ import annotations

from typing import Dict, Optional

from ..core.enums import lower_level
from ..core.models import IntentProfile, Mission, PriorityAssessment
from .context import Context

_BASE_IMPORTANCE: Dict[str, float] = {
    "CONVERSATION": 0.10, "EXPLANATION": 0.25, "RESEARCH": 0.40, "ANALYSIS": 0.45, "COMPARISON": 0.40,
    "PLANNING": 0.40, "CREATION": 0.35, "DECISION_SUPPORT": 0.55, "EXECUTION": 0.60, "MONITORING": 0.35,
    "DIAGNOSTIC": 0.50, "OTHER": 0.30,
}
_FINANCIAL = frozenset("invest investment trade trading buy sell loan mortgage money savings retirement leverage "
                       "margin liquidate bet gamble debt credit tax salary".split())
_SAFETY = frozenset("medical doctor medicine dosage overdose symptom symptoms pain emergency accident fire poison "
                    "suicide suicidal harm abuse violence danger dangerous".split())
_LEGAL = frozenset("lawyer legal lawsuit contract court police arrest visa immigration".split())
_OPERATIONAL = frozenset("production prod deploy server database outage downtime backup delete drop migrate "
                         "migration rollback".split())
_UNIT_S = {"s": 1, "sec": 1, "second": 1, "m": 60, "min": 60, "minute": 60, "h": 3600, "hr": 3600, "hour": 3600,
           "d": 86400, "day": 86400, "w": 604800, "week": 604800}


def _deadline_seconds(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    parts = value.split()
    if len(parts) == 2:
        try:
            unit = parts[1].rstrip("s")
            for k, mult in _UNIT_S.items():
                if unit.startswith(k):
                    return float(parts[0]) * mult
        except ValueError:
            return None
    return {"today": 43200.0, "tonight": 43200.0, "tomorrow": 86400.0}.get(value)


class PriorityEngine:
    @staticmethod
    def level_for(imp: float, urg: float, mission_type: str, crisis: bool = False) -> str:
        if crisis:
            return "CRITICAL"
        if imp >= 0.7 and urg >= 0.6:
            return "CRITICAL"
        if imp >= 0.7 or urg >= 0.75:
            return "HIGH"
        if mission_type == "MONITORING" and urg < 0.4:
            return "LOW"
        if imp >= 0.4 or urg >= 0.4:
            return "NORMAL"
        if mission_type == "CONVERSATION" or imp < 0.2:
            return "LOW"
        return "NORMAL"

    @staticmethod
    def urgency_for(kind: str, value: Optional[str]) -> Optional[float]:
        if kind == "urgency":
            return 0.85
        if kind == "deadline":
            secs = _deadline_seconds(value)
            if secs is None:
                return None
            return 0.9 if secs <= 900 else 0.75 if secs <= 3600 else 0.5 if secs <= 86400 else 0.3
        return None

    def assess(self, intent: IntentProfile, ctx: Optional[Context] = None) -> PriorityAssessment:
        reasons = [f"mission_type:{intent.mission_type}"]
        imp = _BASE_IMPORTANCE.get(intent.mission_type, 0.3)
        tk = intent.tokens
        if tk & _FINANCIAL:
            imp += 0.20
            reasons.append("financial_consequence")
            if intent.mission_type in ("DECISION_SUPPORT", "EXECUTION"):
                imp += 0.15
        if tk & _LEGAL:
            imp += 0.25
            reasons.append("legal_consequence")
        if tk & _OPERATIONAL:
            imp += 0.20
            reasons.append("operational_consequence")
        if tk & _SAFETY:
            imp += 0.45
            reasons.append("safety_cue")
        if "HUMAN" in intent.domains:
            imp += 0.10
            reasons.append("human_impact")

        urg = 0.15
        dl = self.urgency_for("deadline", intent.constraint("deadline"))
        if dl is not None:
            urg = dl
            reasons.append(f"deadline:{intent.constraint('deadline')}")
        if intent.constraint("urgency"):
            urg = max(urg, 0.85)
            reasons.append(f"urgency_word:{intent.constraint('urgency')}")
        if intent.time_sensitive:
            urg = max(urg, 0.45)
            reasons.append("time_sensitive")

        if intent.crisis:
            imp, urg = 1.0, 1.0
            reasons.append("crisis_cue")
        imp, urg = min(imp, 1.0), min(urg, 1.0)

        level = self.level_for(imp, urg, intent.mission_type, intent.crisis)
        consequence = {"CRITICAL": "delay could cause serious harm or loss", "HIGH": "delay is costly",
                       "NORMAL": "delay is an inconvenience", "LOW": "delay has little effect",
                       "BACKGROUND": "no effect"}[level]
        return PriorityAssessment(level=level, importance=imp, urgency=urg, reasons=reasons, consequence=consequence)

    def apply_to_tasks(self, m: Mission) -> None:
        """Tasks inherit the mission level. Optional work is one level lower. Verification is never lowered."""
        level = m.priority.level if m.priority else "NORMAL"
        crit = set(m.plan.critical_path) if m.plan else set()
        for t in m.tasks.values():
            if t.verification or t.id in crit or t.mandatory:
                t.priority = level
            else:
                t.priority = lower_level(level)
        for o in m.objectives.values():
            o.priority = level if o.kind != "SECONDARY" else lower_level(level)
