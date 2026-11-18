"""Evidence controller and conflict engine.

HEROIC defines which claims need verification and consumes verification results. It never verifies its own
claims: only a registered verifier (COGNITIVE / MCVL) can mark evidence as verified.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..core.models import Conflict, EvidenceReq, IntentProfile, Mission
from ..core.util import clip, fingerprint, now_ns

VERIFIERS = frozenset({"COGNITIVE", "MCVL"})
_COMPARE_KEYS = ("direction", "trend_direction", "market_direction", "regime", "recommendation", "verdict",
                 "signal", "bias", "conclusion")
_CAUSE_KEYS = (("timeframe", "TIMEFRAME"), ("horizon", "TIMEFRAME"), ("assumptions", "ASSUMPTION"),
               ("data_source", "INPUT"), ("inputs", "INPUT"), ("sources", "INPUT"))


class EvidenceController:
    def derive(self, m: Mission, intent: IntentProfile, verifier_available: bool) -> None:
        m.evidence.clear()
        subj = intent.entity("ASSET") or clip(intent.subject, 60)
        market = "MARKET" in intent.domains
        mt = intent.mission_type
        claimy = mt in ("ANALYSIS", "RESEARCH", "DECISION_SUPPORT", "COMPARISON")

        def add(kind: str, claim: str, provenance: bool = False) -> None:
            m.evidence.append(EvidenceReq(
                m.next_id("e"), claim, kind, "COGNITIVE", "REQUIRED" if verifier_available else "UNVERIFIABLE",
                provenance=provenance,
                note="" if verifier_available else "No verifier (COGNITIVE) is registered; this cannot be independently verified"))

        if market and (claimy or intent.time_sensitive):
            add("market_claim", f"Market observations and conclusions about {subj}", True)
        elif intent.time_sensitive and mt not in ("CONVERSATION", "EXECUTION"):
            add("current_fact", f"Current facts about {subj}", True)
        if mt == "ANALYSIS" and intent.tokens & {"why", "cause", "caused", "because", "reason"}:
            add("causal_claim", f"Causal explanation for {subj}")
        if mt == "DECISION_SUPPORT":
            add("recommendation_basis", f"Basis for any recommendation about {subj}")
        if mt == "COMPARISON":
            add("comparison_claims", f"Factual claims used to compare {subj}")
        if intent.hypotheses:
            add("user_hypothesis", "The user's stated belief is treated as a hypothesis, not a fact")

    def register(self, m: Mission, ref: str, verified: Optional[bool], source: str,
                 refs: Optional[List[str]] = None, note: str = "") -> Tuple[bool, str]:
        if (source or "").upper() not in VERIFIERS:
            m.log("evidence_refused", ref, f"self-certification refused (source={source!r})")
            return False, "HEROIC accepts verification results only from COGNITIVE or MCVL"
        targets = [e for e in m.evidence if e.id == ref or e.kind == ref] or (m.evidence if ref in ("*", "all") else [])
        if not targets:
            return False, f"no evidence requirement matches '{ref}'"
        status = "VERIFIED" if verified is True else "REFUTED" if verified is False else "UNVERIFIABLE"
        for e in targets:
            e.status = status
            e.refs = list(refs or e.refs)
            e.note = note or f"{status.lower()} by {source.upper()}"
        m.log("evidence", ref, f"{status} by {source.upper()}")
        return True, status

    def pending(self, m: Mission) -> List[EvidenceReq]:
        return [e for e in m.evidence if e.status == "REQUIRED"]

    def limited(self, m: Mission) -> List[EvidenceReq]:
        return [e for e in m.evidence if e.status in ("UNVERIFIABLE", "REFUTED")]


class ConflictEngine:
    def report(self, m: Mission, kind: str, parties: List[str], text: str, cause: str = "UNKNOWN") -> Conflict:
        fp = fingerprint(kind, ",".join(sorted(parties)), text.lower())
        for c in m.conflicts:
            if c.fp == fp and c.status != "RESOLVED":
                return c
        c = Conflict(m.next_id("c"), kind, list(parties), clip(text, 240), cause, "OPEN", "", now_ns(), fp)
        m.conflicts.append(c)
        m.log("conflict", c.id, text[:80])
        return c

    def scan_results(self, m: Mission, results: Dict[str, Any]) -> List[Conflict]:
        """Compare what different brains concluded. Disagreement is recorded, never averaged away."""
        found: List[Conflict] = []
        for key in _COMPARE_KEYS:
            seen: Dict[str, str] = {}
            for brain, res in results.items():
                body = res.get("result", res) if isinstance(res, dict) else None
                v = body.get(key) if isinstance(body, dict) else None
                if isinstance(v, (str, int, float, bool)) and str(v).strip():
                    seen[str(brain).upper()] = str(v).strip().lower()
            if len(set(seen.values())) > 1:
                cause = "INTERPRETATION"
                for ck, label in _CAUSE_KEYS:
                    vals = set()
                    for brain in seen:
                        res = results.get(brain) or results.get(brain.lower()) or {}
                        body = res.get("result", res) if isinstance(res, dict) else {}
                        if isinstance(body, dict) and body.get(ck) is not None:
                            vals.add(str(body[ck]))
                    if len(vals) > 1:
                        cause = label
                        break
                found.append(self.report(m, "BRAIN_OUTPUT", sorted(seen),
                                         f"Brains disagree on '{key}': " + ", ".join(f"{b}={v}" for b, v in sorted(seen.items())),
                                         cause))
        return found

    def resolve(self, m: Mission, cid: str, basis: str) -> bool:
        for c in m.conflicts:
            if c.id == cid:
                c.status, c.basis = "RESOLVED", basis
                m.log("conflict_resolved", cid, basis[:80])
                return True
        return False

    def preserve(self, m: Mission, cid: str, reason: str) -> bool:
        for c in m.conflicts:
            if c.id == cid:
                c.status, c.basis = "PRESERVED", reason
                return True
        return False

    def open(self, m: Mission) -> List[Conflict]:
        return [c for c in m.conflicts if c.status == "OPEN"]
