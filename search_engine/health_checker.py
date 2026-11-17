"""
VALE health checker - batch 4 of the plan (the "test them" half).

link_finder.py confirms a feed works once, the moment it is found. Feeds
break later too - a website redesign, an expired certificate, a renamed
page. This file goes back over every feed link_finder already confirmed
and checks each one again, right now, reporting which ones are still
healthy and which ones have gone bad.

This file only reports - it never deletes or changes a saved row. Deciding
what to do about a broken link (skip it, replace it, remove it) is a
choice for the wave runner, which checks everything on a schedule and
remembers each result over time (the next two files).

Run it on its own:
    python -m search_engine.health_checker
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List

import requests

from search_engine.live_fetch import CONNECT_TIMEOUT, HEADERS, READ_TIMEOUT, parse_feed_bytes

CHECKED_SOURCE = "link-finder"
MAX_PER_RUN = 300


def _still_works(url: str) -> bool:
    """True only if the feed still loads and still has real entries in it."""

    try:
        response = requests.get(url, headers=HEADERS, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        response.raise_for_status()
        return len(parse_feed_bytes(response.content)) > 0

    except Exception:
        return False


def run() -> Dict[str, Any]:
    """
    Re-test every confirmed feed. Returns a small report:
        {"checked", "healthy", "broken": [{"title", "url"}, ...]}
    """

    try:
        from search_engine import storage
        feeds = storage.list_by_source(CHECKED_SOURCE, limit=MAX_PER_RUN)
    except Exception as error:
        print("HEALTH CHECKER: could not read saved feeds:", type(error).__name__, flush=True)
        feeds = []

    print(f"HEALTH CHECKER: re-testing {len(feeds)} confirmed feeds", flush=True)

    broken: List[Dict[str, str]] = []
    healthy_count = 0

    for doc in feeds:
        url = doc.get("url", "")
        if not url:
            continue

        if _still_works(url):
            healthy_count += 1
        else:
            broken.append({"title": doc.get("title", ""), "url": url})
            print(f"HEALTH CHECKER: now broken - {doc.get('title', url)}", flush=True)

    print(
        f"HEALTH CHECKER: done - {healthy_count} healthy, {len(broken)} broken",
        flush=True,
    )

    return {"checked": len(feeds), "healthy": healthy_count, "broken": broken}


if __name__ == "__main__":
    report = run()
    sys.exit(0 if report.get("checked", 0) >= 0 else 1)
