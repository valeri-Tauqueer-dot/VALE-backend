"""
VALE wave runner - batch 6 of the plan.

Does a quick "are you still there?" check across everything the search
engine already knows about, a little bit at a time, forever. This is
"Wave 1": a fast, light check - never downloading a whole page, just
finding out which sources are still alive and worth a closer look later.
Every result is remembered in source_state.py, so the same source is not
re-checked again a moment later.

Runs as one slice of a bigger job. wave.yml starts several of these at
the same time, each one given a different, non-overlapping slice of the
list through SHARD_INDEX / SHARD_COUNT, so the whole list gets covered
without two workers ever checking the same thing twice.

Run one slice by hand (SHARD_COUNT=1 means "I am the only worker, check
everything"):
    SHARD_INDEX=0 SHARD_COUNT=1 python -m search_engine.wave_runner
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

import requests

from search_engine.live_fetch import HEADERS

TIMEOUT = (5.0, 8.0)  # connect, read - light and quick, this is only a liveness check
MAX_AGE_HOURS = 6     # do not re-check something that was already checked this recently
CANDIDATE_SOURCES = ("wikidata-import", "api-directory-import", "link-finder")


def _all_known_sources() -> List[Dict[str, str]]:
    """Every URL the search engine currently knows about, from every importer and the link finder."""

    from search_engine import storage

    seen: Dict[str, Dict[str, str]] = {}

    for tag in CANDIDATE_SOURCES:
        try:
            for doc in storage.list_by_source(tag, limit=2000):
                url = doc.get("url", "")
                if url and url not in seen:
                    seen[url] = {"url": url, "name": doc.get("title", ""), "source": tag}
        except Exception as error:
            print("WAVE RUNNER: could not list a source:", type(error).__name__, flush=True)

    return list(seen.values())


def _todays_work() -> List[Dict[str, str]]:
    """Sources never checked before, plus ones whose last check has gone stale."""

    from search_engine import source_state

    known = _all_known_sources()
    already_tracked = source_state.known_urls()

    never_checked = [item for item in known if item["url"] not in already_tracked]
    stale = [
        {"url": row["url"], "name": row.get("name") or "", "source": row.get("source") or ""}
        for row in source_state.due_for_check(max_age_hours=MAX_AGE_HOURS, limit=2000)
    ]

    print(
        f"WAVE RUNNER: {len(never_checked)} never checked, {len(stale)} due for a re-check",
        flush=True,
    )

    return never_checked + stale


def _my_slice(items: List[Any], shard_index: int, shard_count: int) -> List[Any]:
    """Only the items this one worker is responsible for - every item goes to exactly one worker."""

    if shard_count <= 1:
        return items
    return [item for position, item in enumerate(items) if position % shard_count == shard_index]


def _is_alive(url: str) -> bool:
    """A quick, light check - just "does this still answer?", nothing more. Never raises."""

    try:
        response = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if response.status_code in (405, 403):
            # Some servers reject HEAD outright - fall back to a real GET.
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        return response.status_code < 400

    except Exception:
        return False


def run(limit: int = 0) -> int:
    """
    Check this worker's slice of today's work. Returns how many sources
    were checked.

    limit (optional): check at most this many sources this call, instead
    of the whole slice - for a small caller like the main app's wake-up
    crawler, which only wants to do a little bit at a time, not a full
    wave by itself. 0 (the default) means no limit, which is what
    wave.yml's GitHub Actions shards want.
    """

    shard_index = int(os.environ.get("SHARD_INDEX", "0"))
    shard_count = max(1, int(os.environ.get("SHARD_COUNT", "1")))

    from search_engine import source_state

    work = _todays_work()
    mine = _my_slice(work, shard_index, shard_count)
    if limit > 0:
        mine = mine[:limit]
    print(
        f"WAVE RUNNER: shard {shard_index}/{shard_count} -> {len(mine)} of {len(work)} sources",
        flush=True,
    )

    checked = 0
    for item in mine:
        alive = _is_alive(item["url"])
        source_state.remember(item["url"], name=item["name"], source=item["source"], healthy=alive)
        checked += 1

    print(f"WAVE RUNNER: shard {shard_index}/{shard_count} done - {checked} checked", flush=True)
    return checked


if __name__ == "__main__":
    sys.exit(0 if run() >= 0 else 1)
