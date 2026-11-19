"""
VALE search providers - batch 8's other half (search providers and
allowance counter).

Everything in source_registry.py is free and unlimited. These two are
different: real search companies with their own, much bigger index of
the whole web, free only up to a monthly amount, then paid. This file
calls them - but only through allowance_counter.py, which is checked
BEFORE every call and updated AFTER every call, so VALE can never go
over the free amount by accident.

Needs an API key to do anything:
    BRAVE_API_KEY   - https://brave.com/search/api/        (free tier: 2,000/month)
    TAVILY_API_KEY  - https://tavily.com                    (free tier: 1,000/month)
Neither is required - a provider with no key configured is simply
skipped, the same safe way every optional piece of search_engine/
behaves when something it needs is missing.

Shares the exact shape every other search_engine piece uses:
    [{"title": str, "url": str, "snippet": str, "source": str}, ...]
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

from search_engine import allowance_counter

TIMEOUT = (5.0, 10.0)
HEADERS_BASE = {"User-Agent": "VALE-research-bot/0.2 (personal learning project)"}


def _brave_configured() -> bool:
    return bool(os.getenv("BRAVE_API_KEY", "").strip())


def _tavily_configured() -> bool:
    return bool(os.getenv("TAVILY_API_KEY", "").strip())


def search_brave(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """Ask Brave's own web index. Never raises; returns [] if not configured, out of allowance, or it fails."""

    key = os.getenv("BRAVE_API_KEY", "").strip()
    if not key or not query:
        return []

    if not allowance_counter.can_use("brave"):
        print("PROVIDERS: brave skipped - this month's free amount is used up", flush=True)
        return []

    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": max(1, min(num_results, 20))},
            headers={**HEADERS_BASE, "Accept": "application/json", "X-Subscription-Token": key},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        allowance_counter.record_use("brave")

        hits = response.json().get("web", {}).get("results", [])
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                "source": "brave",
            }
            for item in hits
        ]

    except Exception as error:
        print("PROVIDERS: brave call failed:", type(error).__name__, flush=True)
        return []


def search_tavily(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """Ask Tavily's search API. Never raises; returns [] if not configured, out of allowance, or it fails."""

    key = os.getenv("TAVILY_API_KEY", "").strip()
    if not key or not query:
        return []

    if not allowance_counter.can_use("tavily"):
        print("PROVIDERS: tavily skipped - this month's free amount is used up", flush=True)
        return []

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={"query": query, "max_results": max(1, min(num_results, 20))},
            headers={**HEADERS_BASE, "Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        allowance_counter.record_use("tavily")

        hits = response.json().get("results", [])
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "source": "tavily",
            }
            for item in hits
        ]

    except Exception as error:
        print("PROVIDERS: tavily call failed:", type(error).__name__, flush=True)
        return []


def search_all(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """Try every configured provider, combine whatever comes back. Never raises."""

    combined: List[Dict[str, Any]] = []
    for search_fn in (search_brave, search_tavily):
        try:
            combined.extend(search_fn(query, num_results))
        except Exception as error:
            print("PROVIDERS: a provider misbehaved:", type(error).__name__, flush=True)
    return combined


def any_configured() -> bool:
    """True if at least one paid-with-free-tier provider has a key set."""
    return _brave_configured() or _tavily_configured()
