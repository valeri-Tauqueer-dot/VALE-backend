"""
VALE DRIVER - the brain that connects storage to the brains.

What DRIVER does, for one question:
  1. looks at everything already stored (the search_engine database can hold
     tens of thousands of small link-rows - url, title, a short snippet,
     nothing more),
  2. picks a wide pool of candidates that could answer the question
     (up to `pool`, 200 by default),
  3. sends the question to search_engine.searcher, which sends the most
     promising live sources to "the eyes" (search_engine.live_fetch) for a
     fresh look, and saves anything new it finds back into storage,
  4. joins the wide stored pool with the fresh live-checked results, removes
     duplicates, and narrows everything down to a short evidence list
     (up to `n`, 30 by default) for the thinking brains (ALPHA, LEGEND, ...).

search_web(query, num_results) keeps the SAME SHAPE Exa used to return
([{"title", "url", "highlights": [...]}]), so VALEConnector can call DRIVER
exactly like it used to call Exa, with no other change needed anywhere else.

It never raises: if anything fails, it returns an empty list / empty evidence,
the same way search_engine.searcher already does.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from vale_brain_interface import VALEBrainInterface


def _candidates(question: str, pool: int) -> List[Dict[str, Any]]:
    """Steps 1 + 2: the wide pool from storage alone - no live check yet."""

    try:
        from search_engine import storage

        return storage.search(question, limit=pool)

    except Exception as error:
        print("DRIVER: storage search failed:", type(error).__name__, flush=True)
        return []


def _live_checked(question: str, n: int, deadline: float) -> List[Dict[str, Any]]:
    """Step 3: hand the question to searcher, which uses "the eyes" (live_fetch)."""

    try:
        from search_engine import searcher

        found = searcher.search(question, n=n, deadline=deadline, live=True, save=True)
        return found.get("results", [])

    except Exception as error:
        print("DRIVER: live check (the eyes) failed:", type(error).__name__, flush=True)
        return []


def gather_evidence(
    question: str,
    n: int = 30,
    pool: int = 200,
    deadline: float = 8.0,
) -> Dict[str, Any]:
    """
    The full funnel: wide stored candidates -> the eyes (live check) -> a
    short, ranked evidence list. Returns a dict a brain can read right away:

        {"question", "evidence": [...], "candidates_seen", "evidence_count",
         "elapsed_ms"}

    Each evidence item has the same fields as a search_engine Hit:
    title, url, snippet, source, published, via ("stored"/"live"/"both"), score.
    """

    started = time.time()
    question = (question or "").strip()

    if not question:
        return {
            "question": "",
            "evidence": [],
            "candidates_seen": 0,
            "evidence_count": 0,
            "elapsed_ms": 0,
        }

    n = max(1, min(int(n), 100))
    pool = max(n, min(int(pool), 500))

    wide = _candidates(question, pool)
    fresh = _live_checked(question, n, deadline)

    # Fresh, live-checked results come first (they are already ranked by
    # searcher). Any remaining room is filled from the wider stored pool,
    # skipping anything already picked up.
    seen_urls = set()
    evidence: List[Dict[str, Any]] = []

    for hit in fresh:
        url = hit.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            evidence.append(hit)

    for doc in wide:
        if len(evidence) >= n:
            break
        url = doc.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            evidence.append(
                {
                    "title": doc.get("title", ""),
                    "url": url,
                    "snippet": doc.get("body", ""),
                    "source": doc.get("source", ""),
                    "published": doc.get("published_at", ""),
                    "via": "stored",
                    "score": 0.0,
                }
            )

    evidence = evidence[:n]

    return {
        "question": question,
        "evidence": evidence,
        "candidates_seen": len(wide),
        "evidence_count": len(evidence),
        "elapsed_ms": int((time.time() - started) * 1000),
    }


def search_web(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """
    Drop-in replacement for the old Exa gateway, built on the funnel above.
    Same shape Exa returned: [{"title", "url", "highlights": ["..."]}].
    """

    try:
        found = gather_evidence(query, n=num_results)
    except Exception as error:
        print("DRIVER: search_web failed:", type(error).__name__, flush=True)
        return []

    out = []
    for item in found["evidence"]:
        highlights = [item["snippet"]] if item.get("snippet") else []
        out.append({"title": item.get("title", ""), "url": item.get("url", ""), "highlights": highlights})
    return out


def is_ready() -> bool:
    """True if DRIVER can run (used instead of checking for an Exa key)."""
    return True


class DriverBrain(VALEBrainInterface):
    """
    DRIVER as a full brain, so other brains can ask it directly later
    (through the brain network) instead of only going through the connector.

    `think()` is left as the plain default for now - we have not yet wired
    up exactly how the brain network hands a question to a brain, so this
    will be connected properly in the batch that joins DRIVER to the network.
    Until then, call gather_evidence() directly with the question.
    """

    def __init__(self, connector=None, network=None):
        super().__init__(brain_name="DRIVER", connector=connector, network=network)

    def gather_evidence(self, question: str, n: int = 30, pool: int = 200) -> Dict[str, Any]:
        """The same funnel as the module-level function, callable on the brain."""
        return gather_evidence(question, n=n, pool=pool)
