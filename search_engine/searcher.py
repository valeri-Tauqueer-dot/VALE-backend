"""
VALE search engine - the searcher (step 2, part 2).

This is VALE's own replacement for Exa. For one question it:
  1. works out the topics (gold, oil, war, rates ...) and picks the right sources,
  2. searches YOUR STORED LINKS and many LIVE SOURCES at the same time,
  3. joins the results, removes duplicates, ranks them,
  4. saves the new links it found (so the next question can be answered from storage),
  5. returns the best results.

search_web(query, num_results) returns the SAME SHAPE that Exa returned
([{"title", "url", "highlights": [...]}]) so the rest of VALE can use it with no other change.

It never raises: if everything fails it returns an empty list.
"""
from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from search_engine import live_fetch, source_registry as registry
from search_engine.live_fetch import Hit

MAX_LIVE_SOURCES = 16
MAX_PER_FAMILY = 3
ALWAYS_TRY = ("gdelt-doc-search", "wikipedia-search")   # text-search APIs worth trying for any question
DONT_SAVE_NOTE_MARKS = ("⚠", "Non-commercial")          # never store results from these sources

_last_report: Dict[str, Any] = {}


def _normalize_url(url: str) -> str:
    try:
        parts = urlparse((url or "").strip())
        query = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_")]
        path = parts.path.rstrip("/") or "/"
        return urlunparse((parts.scheme.lower(), parts.netloc.lower(), path, "", urlencode(query), ""))
    except Exception:
        return (url or "").strip()


GENERIC_TAGS = {"news", "world", "business", "us", "india", "europe", "asia", "africa", "americas", "government"}
GENERIC_TAG_WEIGHT = 0.25


def _choose_live_sources(question: str) -> Dict[str, Any]:
    tags = registry.detect_tags(question)
    wanted = set(tags) | ({"news"} if tags else {"news", "world"})

    scored = []
    for index, source in enumerate(registry.SOURCES):
        if not live_fetch.can_search_live(source):
            continue
        shared = wanted.intersection(source.tags)
        if not shared:
            continue
        # a topic match (gold, oil, war ...) counts much more than a generic tag (news, world ...)
        weight = sum(GENERIC_TAG_WEIGHT if t in GENERIC_TAGS else 1.0 for t in shared)
        scored.append((weight, 1 if source.verified else 0, -index, source))
    scored.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)

    chosen: List[registry.Source] = []
    family: Dict[str, int] = {}
    for _, _, _, source in scored:
        name = source.name.split()[0].lower()
        # no more than 3 sources from the same family (for example BBC), so the list stays varied
        if family.get(name, 0) >= MAX_PER_FAMILY:
            continue
        family[name] = family.get(name, 0) + 1
        chosen.append(source)

    words = live_fetch.query_words(question)
    must: List[registry.Source] = []
    if words:
        for source_id in ALWAYS_TRY:
            source = registry.get(source_id)
            if source and live_fetch.can_search_live(source):
                must.append(source)
    rest = [s for s in chosen if s not in must]
    final = rest[: max(0, MAX_LIVE_SOURCES - len(must))] + must
    return {"tags": tags, "sources": final}


def _stored_hits(question: str, words: List[str], limit: int) -> List[Hit]:
    try:
        from search_engine import storage
        rows = storage.search(question, limit)
    except Exception as error:
        print("SEARCHER: stored search not available:", type(error).__name__, flush=True)
        return []
    hits = []
    for row in rows or []:
        title, body = row.get("title") or "", row.get("body") or ""
        hits.append(Hit(
            title=title, url=row.get("url") or "", snippet=live_fetch.snippet(body),
            source=row.get("source") or "stored", published=row.get("published_at") or "",
            via="stored", score=live_fetch.score_text(title, body, words),
            tags=row.get("market") or "",
        ))
    return [h for h in hits if h.url and h.title]


def _save_new(hits: List[Hit], source_notes: Dict[str, str]) -> int:
    docs = []
    seen_links = set()
    for hit in hits:
        if hit.via != "live":
            continue
        link_key = _normalize_url(hit.url)
        if link_key in seen_links:
            continue
        seen_links.add(link_key)
        note = source_notes.get(hit.source, "")
        if any(mark in note for mark in DONT_SAVE_NOTE_MARKS):
            continue
        docs.append({"url": hit.url, "title": hit.title, "body": hit.snippet, "source": hit.source,
                     "market": hit.tags, "published_at": hit.published})
    if not docs:
        return 0
    try:
        from search_engine import storage
        return int(storage.save_many(docs))
    except Exception as error:
        print("SEARCHER: could not save new links:", type(error).__name__, flush=True)
        return 0


def search(
    question: str,
    n: int = 10,
    deadline: float = 8.0,
    live: bool = True,
    save: bool = True,
) -> Dict[str, Any]:
    """Search stored links and live sources at the same time. Returns a dictionary (see keys below)."""
    global _last_report
    started = time.time()
    question = (question or "").strip()
    n = max(1, min(int(n), 50))
    if not question:
        return {"question": "", "tags": [], "words": [], "results": [], "stored_found": 0, "live_found": 0,
                "saved_new": 0, "sources_tried": 0, "reports": [], "elapsed_ms": 0}
    words = live_fetch.query_words(question)

    choice = _choose_live_sources(question) if live else {"tags": registry.detect_tags(question), "sources": []}
    sources = choice["sources"]
    notes = {s.name: s.note for s in sources}

    stored: List[Hit] = []
    stored_box: Dict[str, List[Hit]] = {"hits": []}

    def run_stored() -> None:
        stored_box["hits"] = _stored_hits(question, words, n * 2)

    worker = threading.Thread(target=run_stored, daemon=True)
    worker.start()

    live_hits: List[Hit] = []
    reports: List[live_fetch.SourceReport] = []
    if sources:
        live_hits, reports = live_fetch.fan_out(sources, question, deadline=deadline)

    worker.join(timeout=max(0.1, deadline - (time.time() - started)))
    stored = stored_box["hits"]

    # join, remove duplicates, rank
    best: Dict[str, Hit] = {}
    for hit in stored + live_hits:
        key = _normalize_url(hit.url)
        if not key:
            continue
        current = best.get(key)
        if current is None or hit.score > current.score:
            if current is not None and current.via != hit.via:
                hit.via = "both"
            best[key] = hit
        elif current is not None and current.via != hit.via:
            current.via = "both"
    ranked = sorted(best.values(), key=lambda h: (h.score, 1 if h.via in ("both", "stored") else 0), reverse=True)[:n]

    saved = _save_new(live_hits, notes) if (save and live_hits) else 0

    result = {
        "question": question,
        "tags": choice["tags"],
        "words": words,
        "results": [h.as_dict() for h in ranked],
        "stored_found": len(stored),
        "live_found": len(live_hits),
        "saved_new": saved,
        "sources_tried": len(sources),
        "reports": [r.as_dict() for r in reports],
        "elapsed_ms": int((time.time() - started) * 1000),
    }
    _last_report = {k: result[k] for k in ("question", "stored_found", "live_found", "saved_new", "sources_tried", "elapsed_ms")}
    return result


# ----------------------------------------------------------------------
# drop-in replacement for the Exa gateway
# ----------------------------------------------------------------------
def search_web(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """Same shape Exa returned: [{"title", "url", "highlights": ["..."]}]. Never raises."""
    try:
        found = search(query, n=num_results)
    except Exception as error:
        print("SEARCHER: search failed:", type(error).__name__, flush=True)
        return []
    out = []
    for hit in found["results"]:
        highlights = [hit["snippet"]] if hit.get("snippet") else []
        out.append({"title": hit["title"], "url": hit["url"], "highlights": highlights})
    return out


def is_ready() -> bool:
    """True if the searcher can run (used instead of checking for an Exa key)."""
    return True


def last_report() -> Dict[str, Any]:
    return dict(_last_report)
