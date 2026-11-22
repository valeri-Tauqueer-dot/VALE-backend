"""Conflict manager. Two operational signals disagree: an authority order decides, or the conflict is escalated.

SUPERVISOR detects and records operational conflicts. It does not decide which factual claim is true; that is
for COGNITIVE (MCVL) and the reasoning brains.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Set, Tuple

from ..core.config import SupervisorConfig
from ..core.enums import IncidentType as T
from ..core.models import Observation
from ..core.store import AuditLog
from ..core.util import iso
from .registry import HealthRegistry

# higher wins. Observed behaviour outranks what a component says about itself.
RANK = {"authoritative_state": 4, "probe": 3, "observed_calls": 3, "self_report": 1}


class ConflictManager:
    def __init__(self, cfg: SupervisorConfig, registry: HealthRegistry, audit: AuditLog) -> None:
        self.cfg, self.reg, self.audit = cfg, registry, audit
        self.log: Deque[Dict[str, Any]] = deque(maxlen=100)
        self._seen: Set[Tuple[str, str]] = set()

    def check(self, now: float) -> Tuple[List[Observation], Set[tuple]]:
        """Self-reported health against observed behaviour. This kind is always resolvable by the authority order."""
        cfg = self.cfg
        for c in self.reg.brains():
            if not c.registered or not c.probe_ts or now - c.probe_ts > cfg.probe_ttl_s or c.probe_ok is not True:
                continue
            claims: List[Tuple[str, str, float]] = []
            if c.ready is True:
                claims.append(("self_report", "ready", c.probe_ts))
            elif c.ready is False:
                claims.append(("self_report", "not_ready", c.probe_ts))
            if c.consec_fail >= cfg.fail_high and c.last_error:
                claims.append(("observed_calls", "failing", c.last_error))
            elif c.consec_ok >= cfg.recover_ok and c.last_ok and now - c.last_ok <= 60:
                claims.append(("observed_calls", "working", c.last_ok))
            good = [x for x in claims if x[1] in ("ready", "working")]
            bad = [x for x in claims if x[1] in ("not_ready", "failing")]
            if good and bad:
                key = (c.name, f"{claims[0][1]}|{claims[-1][1]}")
                if key in self._seen:
                    continue
                self._seen.add(key)
                winner = max(claims, key=lambda x: (RANK[x[0]], x[2]))
                rec = {"component": c.name, "at": iso(now), "claims": [{"source": s, "says": v, "at": iso(t)} for s, v, t in claims],
                       "resolved_by": f"{winner[0]} (rank {RANK[winner[0]]})", "outcome": winner[1],
                       "rule": "observed behaviour outranks self-report"}
                self.log.append(rec)
                self.audit.add(now, "conflict_resolved", c.name, f"{rec['outcome']} by {rec['resolved_by']}")
        if len(self._seen) > 500:
            self._seen.clear()
        return [], set()

    def report(self, component: str, claims: List[Dict[str, Any]], now: float) -> Tuple[Dict[str, Any], List[Observation]]:
        """Claims reported by other parts of the system: [{"source": str, "says": str, "rank": int?}, ...]."""
        scored = [(int(c.get("rank", RANK.get(str(c.get("source")), 0))), str(c.get("says")), str(c.get("source"))) for c in claims]
        scored.sort(reverse=True)
        values = {v for _, v, _ in scored}
        evidence = [{"source": s, "says": v, "rank": r} for r, v, s in scored]
        if len(values) <= 1:
            rec = {"component": component, "at": iso(now), "claims": evidence, "resolved_by": "agreement", "outcome": next(iter(values), None)}
            self.log.append(rec)
            return rec, []
        top = scored[0][0]
        leaders = {v for r, v, _ in scored if r == top}
        if len(leaders) == 1:
            rec = {"component": component, "at": iso(now), "claims": evidence, "resolved_by": f"{scored[0][2]} (rank {top})",
                   "outcome": scored[0][1]}
            self.log.append(rec)
            self.audit.add(now, "conflict_resolved", component, f"{rec['outcome']} by {rec['resolved_by']}")
            return rec, []
        rec = {"component": component, "at": iso(now), "claims": evidence, "resolved_by": None, "outcome": None}
        self.log.append(rec)
        self.audit.add(now, "conflict_unresolved", component, "no authoritative source; both positions kept")
        ob = Observation(T.STATE_CONFLICT.value, component, "unresolved_state_conflict", "HIGH",
                         f"Conflicting operational reports about {component} and no authoritative source decides",
                         {"claims": evidence}, [component], "UNITY")
        return rec, [ob]
