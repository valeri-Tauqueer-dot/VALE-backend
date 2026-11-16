"""
VALE link finder - batch 4 of the plan (the "find feeds" half).

wikidata_import.py and api_directory_import.py only ever save an
organisation's plain homepage - a guess, not a confirmed working feed.
This file visits each one, looks for the feed link the website itself
already advertises (the same <link rel="alternate" type="application/
rss+xml"> tag every feed reader looks for), and - only if that feed
actually loads and has real entries in it - saves it as a new, confirmed
row.

Nothing from the importers is ever deleted or changed here; a real,
working feed is simply added alongside it, with source="link-finder" so
later batches can tell a confirmed feed apart from a plain guess.

Run it on its own:
    python -m search_engine.link_finder

The other half of this batch - testing every saved link again and again,
every day, to catch ones that break later - is the health checker, coming
as the next file.
"""
from __future__ import annotations

import sys
import time
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from search_engine.live_fetch import CONNECT_TIMEOUT, HEADERS, READ_TIMEOUT, parse_feed_bytes

IMPORT_SOURCES = ("wikidata-import", "api-directory-import")
MAX_PER_RUN = 200     # a safety cap so one run can't take forever
PAUSE_SECONDS = 0.5   # be polite between different websites


def _find_feed_link(homepage_url: str, html: bytes) -> str:
    """Look for the feed link a page itself advertises. Never raises."""

    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("link", rel="alternate"):
            kind = (tag.get("type") or "").lower()
            href = tag.get("href") or ""
            if href and ("rss" in kind or "atom" in kind or "xml" in kind):
                return urljoin(homepage_url, href)
    except Exception as error:
        print("LINK FINDER: could not read a page's links:", type(error).__name__, flush=True)

    return ""


def _confirmed_feed(feed_url: str) -> bool:
    """True only if the feed actually loads and has real entries inside it."""

    try:
        response = requests.get(feed_url, headers=HEADERS, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        response.raise_for_status()
        return len(parse_feed_bytes(response.content)) > 0

    except Exception as error:
        print("LINK FINDER: feed did not check out:", type(error).__name__, flush=True)
        return False


def _candidates() -> List[Dict[str, Any]]:
    """Every homepage the importers saved, from every shelf. Never raises."""

    try:
        from search_engine import storage
    except Exception as error:
        print("LINK FINDER: storage is not available:", type(error).__name__, flush=True)
        return []

    rows: List[Dict[str, Any]] = []
    for source in IMPORT_SOURCES:
        try:
            rows.extend(storage.list_by_source(source, limit=MAX_PER_RUN))
        except Exception as error:
            print("LINK FINDER: could not read candidates:", type(error).__name__, flush=True)

    return rows[:MAX_PER_RUN]


def run() -> int:
    """
    Visit every importer's candidate homepage, look for a real feed, and
    save only the ones confirmed to actually work.
    Returns how many new, confirmed feeds were saved.
    """

    candidates = _candidates()
    print(f"LINK FINDER: checking {len(candidates)} homepages", flush=True)

    found: List[Dict[str, Any]] = []

    for doc in candidates:
        homepage = doc.get("url", "")
        name = doc.get("title", "")
        if not homepage:
            continue

        feed_url = ""
        try:
            response = requests.get(homepage, headers=HEADERS, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
            response.raise_for_status()
            feed_url = _find_feed_link(homepage, response.content)
        except Exception as error:
            print(f"LINK FINDER: could not open {homepage}:", type(error).__name__, flush=True)

        if feed_url and _confirmed_feed(feed_url):
            found.append(
                {
                    "url": feed_url,
                    "title": name,
                    "body": "confirmed working feed",
                    "source": "link-finder",
                    "market": doc.get("market", ""),
                }
            )
            print(f"LINK FINDER: found a real feed for {name}", flush=True)

        time.sleep(PAUSE_SECONDS)

    try:
        from search_engine import storage
        saved = storage.save_many(found)
    except Exception as error:
        print("LINK FINDER: storage save failed:", type(error).__name__, flush=True)
        saved = 0

    print(f"LINK FINDER: done, {saved} confirmed feeds saved", flush=True)
    return saved


if __name__ == "__main__":
    sys.exit(0 if run() >= 0 else 1)
