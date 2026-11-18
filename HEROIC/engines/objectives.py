"""Objective engine: primary, secondary and prerequisite objectives with testable success conditions."""
from __future__ import annotations

from ..core.enums import DONE_TASK, OPEN_INFO, Gap, InfoState
from ..core.models import Conflict, IntentProfile, Mission, Objective, SuccessCondition
from ..core.util import clip, content_tokens, fingerprint, jaccard

_CLAIMY = ("ANALYSIS", "RESEARCH", "DECISION_SUPPORT", "COMPARISON")


def _fp(text: str) -> str:
    return fingerprint(*sorted(set(content_tokens(text))))


class ObjectiveEngine:
    def build(self, m: Mission, intent: IntentProfile) -> None:
        m.objectives.clear()
        pri = m.priority.level if m.priority else "NORMAL"
        mt = intent.mission_type
        market = "MARKET" in intent.domains

        prereq_ids = []
        if intent.time_sensitive and mt != "CONVERSATION":
            o = Objective(m.next_id("o"), "Use current information, not remembered information", "PREREQUISITE", pri,
                          [SuccessCondition("INFO_OK", "Critical information is available and fresh")])
            m.objectives[o.id] = o
            prereq_ids.append(o.id)
        if mt == "EXECUTION":
            o = Objective(m.next_id("o"), "Obtain explicit user authorisation before any action", "PREREQUISITE", pri,
                          [SuccessCondition("AUTHORIZED", "The user has authorised the execution")])
            m.objectives[o.id] = o
            prereq_ids.append(o.id)

        conds = [SuccessCondition("TASKS_DONE", "All mandatory tasks are completed")]
        if mt in _CLAIMY or (market and intent.time_sensitive):
            conds += [SuccessCondition("INFO_OK", "Critical information requirements are resolved"),
                      SuccessCondition("CLAIMS_VERIFIED", "Material claims are verified, or their limits are stated"),
                      SuccessCondition("NO_OPEN_CONFLICT", "No conflict is left open or hidden")]
        if mt == "EXECUTION":
            conds.append(SuccessCondition("AUTHORIZED", "Execution was authorised"))
        conds.append(SuccessCondition("DELIVERED", "A response that addresses the request is delivered"))
        primary = Objective(m.next_id("o"), clip(intent.text or m.request, 240), "PRIMARY", pri, conds,
                            prereq=prereq_ids, fp=_fp(intent.text))
        m.objectives[primary.id] = primary

        if len(intent.sub_intents) >= 2:
            for _, seg in intent.sub_intents[1:]:
                o = Objective(m.next_id("o"), clip(seg, 200), "SECONDARY", pri,
                              [SuccessCondition("DELIVERED", "This part of the request is answered")], fp=_fp(seg))
                m.objectives[o.id] = o
        if intent.hypotheses:
            o = Objective(m.next_id("o"), "Test the user's stated belief against evidence instead of assuming it",
                          "SECONDARY", pri, [SuccessCondition("CLAIMS_VERIFIED", "The belief is verified, refuted, or its limits are stated")])
            m.objectives[o.id] = o
        for code in intent.conflicts:
            m.conflicts.append(Conflict(m.next_id("c"), "OBJECTIVE", ["request"], f"The request contains competing instructions ({code})",
                                        cause="INTERPRETATION", status="OPEN", created_ns=m.updated_ns))

    def reconcile(self, m: Mission, new_intent: IntentProfile) -> str:
        """Compare a changed request with the current objective: SAME, REFINED or CHANGED."""
        old = m.intent
        if old is None or " ".join(old.text.lower().split()) == " ".join(new_intent.text.lower().split()):
            return "SAME"
        sim = jaccard(set(content_tokens(old.text)), set(content_tokens(new_intent.text)))
        return "REFINED" if sim >= 0.6 and old.mission_type == new_intent.mission_type else "CHANGED"

    def refresh(self, m: Mission) -> None:
        mand = [t for t in m.tasks.values() if t.mandatory]
        mand_done = bool(mand) and all(t.state in DONE_TASK for t in mand)
        info_ok = not any(i.gap == Gap.CRITICAL and i.state in OPEN_INFO for i in m.info.values())
        claims_ok = all(e.status in ("VERIFIED", "WAIVED") or (e.status in ("UNVERIFIABLE", "REFUTED") and e.note)
                        for e in m.evidence)
        no_conflict = not any(c.status == "OPEN" for c in m.conflicts)
        comm = [t for t in m.tasks.values() if t.kind == "COMMUNICATION"]
        delivered = m.delivered or (mand_done and bool(comm) and all(t.state in DONE_TASK for t in comm))
        auth = m.info.get("execution_authorization")
        authorized = auth is not None and auth.state in (InfoState.AVAILABLE_VERIFIED, InfoState.AVAILABLE_UNVERIFIED)
        checks = {"TASKS_DONE": mand_done, "INFO_OK": info_ok, "CLAIMS_VERIFIED": claims_ok,
                  "NO_OPEN_CONFLICT": no_conflict, "DELIVERED": delivered, "AUTHORIZED": authorized}
        for o in m.objectives.values():
            if o.status == "DROPPED":
                continue
            for c in o.success:
                c.met = checks.get(c.kind, False)
            o.status = "MET" if o.success and all(c.met for c in o.success) else "OPEN"
