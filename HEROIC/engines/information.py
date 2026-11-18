"""Information and uncertainty controllers.

Information status is independent of mission status. A state is only AVAILABLE_* when something observable
supports it (the user's own words, search results in the shared state, or a report from another brain).
Anything else is MISSING or UNAVAILABLE. HEROIC never fills a gap with an assumption.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from ..core.config import HeroicConfig
from ..core.enums import OPEN_INFO, Gap, InfoState
from ..core.models import InfoRequirement, IntentProfile, Mission, Uncertainty
from ..core.util import clip, now_ns
from .context import Context
from .intent import comparison_subjects

_AVAILABLE = (InfoState.AVAILABLE_VERIFIED, InfoState.AVAILABLE_UNVERIFIED)
_NEEDS_DATA = ("RESEARCH", "ANALYSIS", "DECISION_SUPPORT", "COMPARISON", "MONITORING")


class InformationController:
    def __init__(self, cfg: HeroicConfig) -> None:
        self.cfg = cfg

    # ------------------------------------------------------------------
    def _tool_state(self, ctx: Context) -> Tuple[InfoState, str, str]:
        if ctx.internet_results > 0:
            return InfoState.AVAILABLE_UNVERIFIED, "internet_search", ""
        if ctx.internet_available is False:
            return InfoState.UNAVAILABLE, "", "internet search is not configured or failed"
        return InfoState.MISSING, "", "not retrieved yet"

    def _add(self, m: Mission, key: str, text: str, state: InfoState, gap: Gap, resolvable: str,
             ttl: float = 0.0, source: str = "", note: str = "", observed: int = 0) -> InfoRequirement:
        r = InfoRequirement(m.next_id("i"), key, text, state, gap, resolvable, ttl, observed, source, note)
        m.info[key] = r
        return r

    def derive(self, m: Mission, intent: IntentProfile, ctx: Context) -> None:
        m.info.clear()
        mt = intent.mission_type
        market = "MARKET" in intent.domains
        live = intent.time_sensitive
        asset = intent.entity("ASSET")
        subj = asset or clip(intent.subject, 60)

        if mt not in ("CONVERSATION", "DIAGNOSTIC", "MONITORING", "EXECUTION") or intent.ambiguity:
            if "no_subject" in intent.ambiguity or "referential_without_antecedent" in intent.ambiguity:
                self._add(m, "subject", "What the request is about", InfoState.MISSING, Gap.CRITICAL, "USER",
                          source="request", note="the request names no subject and no earlier message supplies one")
            elif mt != "CONVERSATION":
                self._add(m, "subject", "What the request is about", InfoState.AVAILABLE_VERIFIED, Gap.CRITICAL,
                          "USER", source="user_request", observed=ctx.now_ns)

        if mt == "COMPARISON" and "needs_two_subjects" in intent.implicit:
            n = len(comparison_subjects(intent.text))
            ok = n >= 2
            self._add(m, "comparison_subjects", "At least two things to compare",
                      InfoState.AVAILABLE_VERIFIED if ok else InfoState.MISSING, Gap.CRITICAL, "USER",
                      source="user_request" if ok else "", note="" if ok else f"only {n} subject found")

        if market and mt != "CONVERSATION" and (live or mt in _NEEDS_DATA or mt == "EXECUTION") \
                and not (mt == "EXPLANATION" and not live):
            need_asset = mt in ("DECISION_SUPPORT", "EXECUTION")
            self._add(m, "instrument", "Which instrument or asset is meant",
                      InfoState.AVAILABLE_VERIFIED if asset else InfoState.MISSING,
                      Gap.CRITICAL if need_asset else Gap.MATERIAL, "USER",
                      source="user_request" if asset else "", observed=ctx.now_ns if asset else 0,
                      note=f"user named {asset}" if asset else "no instrument named")
            st, src, note = self._tool_state(ctx)
            crit = live or mt in ("ANALYSIS", "DECISION_SUPPORT")
            self._add(m, "market_data", f"Current, sourced and timestamped market data for {subj}", st,
                      Gap.CRITICAL if crit else Gap.MATERIAL, "TOOL", self.cfg.ttl_market_s, src, note,
                      ctx.now_ns if st == InfoState.AVAILABLE_UNVERIFIED else 0)
            has_tf = intent.constraint("timeframe") is not None
            self._add(m, "timeframe", "The time horizon of the question",
                      InfoState.AVAILABLE_VERIFIED if has_tf else InfoState.MISSING, Gap.MINOR, "USER",
                      source="user_request" if has_tf else "",
                      note="" if has_tf else "a default horizon will be used and stated")
        elif live and mt not in ("CONVERSATION", "EXECUTION"):
            st, src, note = self._tool_state(ctx)
            self._add(m, "fresh_information", f"Current information about {subj}", st, Gap.MATERIAL, "TOOL",
                      self.cfg.ttl_news_s, src, note, ctx.now_ns if st == InfoState.AVAILABLE_UNVERIFIED else 0)

        if intent.emotional and intent.token_count <= 6 and "HUMAN" in intent.domains and not intent.crisis:
            self._add(m, "situation_details", "What happened and what the person needs", InfoState.INCOMPLETE,
                      Gap.MINOR, "USER", source="user_request", note="the message is short")

        if mt == "CREATION":
            has = bool(intent.constraint("format")) or intent.token_count >= 8
            self._add(m, "content_requirements", "Audience, tone and length of the result",
                      InfoState.AVAILABLE_UNVERIFIED if has else InfoState.MISSING, Gap.MINOR, "USER",
                      source="user_request" if has else "", note="" if has else "sensible defaults will be stated")

        if mt == "EXECUTION":
            self._add(m, "execution_authorization", "Explicit user authorisation to act", InfoState.MISSING,
                      Gap.CRITICAL, "USER", note="HEROIC never treats a request as authorisation to act")

        if ctx.media:
            self._add(m, "attachment_content", "Content of the attached file", InfoState.AVAILABLE_UNVERIFIED,
                      Gap.MATERIAL, "USER", source="user_upload", observed=ctx.now_ns)

    # ------------------------------------------------------------------
    def refresh(self, m: Mission, ctx: Optional[Context] = None) -> bool:
        """Re-read tool state and apply freshness limits. Returns True when anything changed."""
        changed = False
        now = (ctx.now_ns if ctx else now_ns())
        for r in m.info.values():
            if ctx is not None and r.resolvable == "TOOL" and r.state in (InfoState.MISSING, InfoState.UNAVAILABLE):
                st, src, note = self._tool_state(ctx)
                if st != r.state and (st in _AVAILABLE or (st == InfoState.UNAVAILABLE and r.state == InfoState.MISSING)):
                    r.state, r.source, r.note = st, src, note
                    r.observed_ns = now if st in _AVAILABLE else 0
                    changed = True
            if r.state in _AVAILABLE and r.ttl_s > 0 and r.observed_ns and (now - r.observed_ns) / 1e9 > r.ttl_s:
                r.state, r.note = InfoState.STALE, "older than its freshness limit"
                changed = True
        return changed

    def update(self, m: Mission, key: str, state: InfoState, source: str, observed_ns: Optional[int] = None,
               note: str = "") -> Tuple[bool, str]:
        r = m.info.get(key)
        if r is None:
            return False, f"unknown information requirement '{key}'"
        r.state, r.source, r.note = state, source or r.source, note or r.note
        r.observed_ns = (observed_ns or now_ns()) if state in _AVAILABLE else 0
        m.log("info", key, f"{state.value} from {source or 'unknown'}")
        return True, "ok"

    def open_gaps(self, m: Mission) -> List[InfoRequirement]:
        return [r for r in m.info.values() if r.state in OPEN_INFO]

    def blocking(self, m: Mission) -> List[InfoRequirement]:
        return [r for r in m.info.values() if r.state in OPEN_INFO and r.gap == Gap.CRITICAL]

    def summary(self, m: Mission) -> dict:
        gaps = self.open_gaps(m)
        return {"requirements": [r.to_dict() for r in m.info.values()],
                "blocking": [r.key for r in gaps if r.gap == Gap.CRITICAL],
                "material": [r.key for r in gaps if r.gap == Gap.MATERIAL],
                "minor": [r.key for r in gaps if r.gap == Gap.MINOR]}


class UncertaintyController:
    def _add(self, m: Mission, kind: str, source: str, impact: str, text: str) -> Uncertainty:
        for u in m.uncertainties:
            if u.kind == kind and u.source == source and not u.resolved:
                return u
        u = Uncertainty(m.next_id("u"), kind, source, impact, text)
        m.uncertainties.append(u)
        return u

    def derive(self, m: Mission, intent: IntentProfile) -> None:
        m.uncertainties.clear()
        for a in intent.ambiguity:
            self._add(m, "AMBIGUITY", a, "HIGH" if a != "no_clear_request" else "MEDIUM",
                      {"no_subject": "The request does not say what it is about",
                       "referential_without_antecedent": "The request refers to something earlier that is not available",
                       "no_clear_request": "It is not clear what the user wants done"}.get(a, a))
        if intent.clarity < 0.4 and not intent.ambiguity and intent.mission_type != "CONVERSATION":
            self._add(m, "AMBIGUITY", "weak_intent_signal", "LOW",
                      "The request has no explicit intent cue, so the mission type was inferred")
        for h in intent.hypotheses:
            self._add(m, "UNVERIFIED", f"belief:{h}", "MEDIUM", f"The user's stated belief ('{h}') is not assumed to be true")
        self.sync(m)

    def sync(self, m: Mission) -> None:
        """Keep information-gap uncertainties in step with the information state."""
        impact = {Gap.CRITICAL: "HIGH", Gap.MATERIAL: "MEDIUM", Gap.MINOR: "LOW"}
        for r in m.info.values():
            existing = [u for u in m.uncertainties if u.source == f"info:{r.key}"]
            if r.state in OPEN_INFO:
                kind = "STALE" if r.state == InfoState.STALE else "CONFLICTING" if r.state == InfoState.CONTRADICTORY else "INCOMPLETE"
                if not any(not u.resolved for u in existing):
                    self._add(m, kind, f"info:{r.key}", impact[r.gap], f"{r.text} is {r.state.value.lower()}")
            else:
                for u in existing:
                    if not u.resolved:
                        u.resolved, u.resolution = True, "the information became available"

    def resolve(self, m: Mission, uid: str, resolution: str) -> bool:
        for u in m.uncertainties:
            if u.id == uid:
                u.resolved, u.resolution = True, resolution
                return True
        return False

    def visible(self, m: Mission) -> List[Uncertainty]:
        return [u for u in m.uncertainties if not u.resolved]
