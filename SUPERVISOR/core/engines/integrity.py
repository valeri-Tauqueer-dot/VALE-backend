"""State consistency, communication and data integrity monitors, plus freshness tracking for data feeds."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from ..core.config import SupervisorConfig
from ..core.enums import IncidentType as T
from ..core.models import Observation
from ..core.util import iso
from .collector import TaskDigest


class IntegrityMonitor:
    def __init__(self, cfg: SupervisorConfig) -> None:
        self.cfg = cfg
        self.recent_search: Deque[bool] = deque(maxlen=5)
        self.no_results = 0

    def analyze(self, digests: List[TaskDigest], now: float) -> Tuple[List[Observation], Set[tuple]]:
        obs: List[Observation] = []
        checked: Set[tuple] = set()
        if not digests:
            return obs, checked
        checked.add((T.COMMUNICATION.value, "*", "required_not_run"))
        checked.add((T.HEALTH.value, "*", "selected_but_unregistered"))
        checked.add((T.STATE_CONFLICT.value, "*", "active_brains_mismatch"))
        for d in digests:
            skipped = {b for b, _ in d.skipped}
            for r in d.required:
                if r not in d.started and r not in skipped:
                    obs.append(Observation(T.COMMUNICATION.value, r, "required_not_run", "WARNING",
                                           f"{r} was required for a task but never ran",
                                           {"task": d.task_id, "required": d.required, "ran": sorted(d.started)},
                                           [r], "UNITY", first_evidence_ts=d.created))
            for b, reason in d.skipped:
                if reason == "not_registered":
                    obs.append(Observation(T.HEALTH.value, b, "selected_but_unregistered", "WARNING",
                                           f"{b} was selected for a task but is not registered",
                                           {"task": d.task_id}, [b], "UNITY", first_evidence_ts=d.created))
            if d.active is not None and set(d.active) != set(d.started):
                obs.append(Observation(T.STATE_CONFLICT.value, "NETWORK", "active_brains_mismatch", "WARNING",
                                       "The shared state lists different active brains than the lifecycle events show",
                                       {"task": d.task_id, "state_says": sorted(d.active), "events_say": sorted(d.started)},
                                       ["NETWORK"], "UNITY", first_evidence_ts=d.created))
            if d.external_required:
                checked.add((T.DATA_INTEGRITY.value, "SEARCH"))
                bad = d.internet_available is False or bool(d.internet_error)
                self.recent_search.append(bad)
                sev = "HIGH" if sum(self.recent_search) >= 3 else "WARNING"
                if d.internet_available is False:
                    obs.append(Observation(T.DATA_INTEGRITY.value, "SEARCH", "provider_unavailable", sev,
                                           "Internet search was needed but is not available",
                                           {"task": d.task_id}, ["MARKET_INTELLIGENCE", "HEROIC"], "COGNITIVE",
                                           first_evidence_ts=d.created))
                if d.internet_error:
                    obs.append(Observation(T.DATA_INTEGRITY.value, "SEARCH", "search_error", sev,
                                           f"Internet search failed: {d.internet_error}", {"task": d.task_id},
                                           ["MARKET_INTELLIGENCE", "HEROIC"], "COGNITIVE", first_evidence_ts=d.created))
                if d.results_bad:
                    obs.append(Observation(T.DATA_INTEGRITY.value, "SEARCH", "malformed_results", "WARNING",
                                           f"{d.results_bad} of {d.results_n} search results had no source or no text",
                                           {"task": d.task_id, "bad": d.results_bad, "total": d.results_n},
                                           ["COGNITIVE"], "COGNITIVE", first_evidence_ts=d.created))
                if d.internet_performed and d.results_n == 0 and not d.internet_error:
                    self.no_results += 1
                    if self.no_results >= 3:
                        obs.append(Observation(T.DATA_INTEGRITY.value, "SEARCH", "no_results", "INFORMATIONAL",
                                               f"{self.no_results} searches in a row returned nothing", {"streak": self.no_results},
                                               [], "COGNITIVE"))
                elif d.results_n > 0:
                    self.no_results = 0
        return obs, checked


@dataclass
class Feed:
    name: str
    max_age_s: float
    critical: bool
    dependents: Tuple[str, ...]
    registered_at: float
    last_observed: Optional[float] = None


class FeedMonitor:
    """Freshness of data that a producer (for example LEGEND's market data) reports. Unknown stays unknown."""

    def __init__(self, cfg: SupervisorConfig) -> None:
        self.cfg = cfg
        self.feeds: Dict[str, Feed] = {}

    def register(self, name: str, max_age_s: float, critical: bool, dependents: Tuple[str, ...], now: float) -> Feed:
        f = self.feeds.get(name)
        if f is None:
            f = self.feeds[name] = Feed(name, float(max_age_s), bool(critical), tuple(dependents), now)
        else:
            f.max_age_s, f.critical, f.dependents = float(max_age_s), bool(critical), tuple(dependents)
        return f

    def report(self, name: str, observed_at: float) -> bool:
        f = self.feeds.get(name)
        if f is None:
            return False
        f.last_observed = max(f.last_observed or 0.0, observed_at)
        return True

    def age(self, name: str, now: float) -> Optional[float]:
        f = self.feeds.get(name)
        return None if f is None or f.last_observed is None else max(0.0, now - f.last_observed)

    def check(self, now: float) -> Tuple[List[Observation], Set[tuple]]:
        obs: List[Observation] = []
        checked: Set[tuple] = set()
        for f in self.feeds.values():
            checked.add((T.DATA_INTEGRITY.value, f.name))
            if f.last_observed is None:
                if now - f.registered_at > f.max_age_s:
                    obs.append(Observation(T.DATA_INTEGRITY.value, f.name, "never_reported", "WARNING",
                                           f"Feed '{f.name}' has never reported an observation time (freshness is unknown)",
                                           {"max_age_s": f.max_age_s}, list(f.dependents), "COGNITIVE"))
                continue
            age = now - f.last_observed
            if age > f.max_age_s:
                obs.append(Observation(T.DATA_INTEGRITY.value, f.name, "stale_feed", "HIGH" if f.critical else "WARNING",
                                       f"Feed '{f.name}' is stale: last data {age:.0f}s old, limit {f.max_age_s:.0f}s",
                                       {"age_s": round(age, 1), "max_age_s": f.max_age_s, "last_observed": iso(f.last_observed)},
                                       list(f.dependents), "COGNITIVE", first_evidence_ts=f.last_observed + f.max_age_s))
        return obs, checked
