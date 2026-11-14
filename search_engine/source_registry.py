"""
VALE source registry - batch 2 of the plan.

This is the missing piece search_engine/live_fetch.py and
search_engine/searcher.py have been expecting all along (they both do
`from search_engine import source_registry as registry`). Without this file,
DRIVER's live check ("the eyes") cannot run at all, and falls back to
storage alone - which is exactly what was happening before this file existed.

A Source describes one place VALE can look things up live:
    id        short, unique name used in logs and lookups
    name      a readable name
    kind      "rss" / "atom" (a feed, fetched as-is) or "api" (built from a
              URL template)
    url       for a feed: the feed's address.
              for an api: a template with {query} inside it
    params    which named values this source's URL template needs filled in
              - empty for a plain feed, {"query"} for a question-answering API
    parser    which parser in live_fetch.py understands the reply: one of
              its JSON_PARSERS keys, or "atom_entries" for a feed
    tags      topics this source is good for (used to decide which sources
              are worth trying for a given question)
    note      a short, human description, saved alongside anything found
              through this source so it's clear where a saved link came from
    enabled   turn a source on or off without deleting it
    verified  True once someone has actually seen it return good results

The actual list of sources lives in source_catalog.csv, next to this file,
so more can be added later just by adding a row - nothing else needs to
change when a new source is added.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from urllib.parse import quote

_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_catalog.csv")


@dataclass
class Source:
    id: str
    name: str
    kind: str                       # "rss" | "atom" | "api"
    url: str
    params: Set[str] = field(default_factory=set)
    parser: str = ""
    tags: Set[str] = field(default_factory=set)
    note: str = ""
    enabled: bool = True
    verified: bool = False


def _to_bool(value: str) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes")


def _load(path: str = _CSV_PATH) -> List[Source]:
    """
    Read source_catalog.csv. Never raises: a missing or broken file just
    means an empty source list, so DRIVER still runs fine on storage alone -
    the same safe behaviour as everything else in search_engine/.
    """

    sources: List[Source] = []

    try:
        with open(path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                try:
                    sources.append(
                        Source(
                            id=row["id"].strip(),
                            name=row["name"].strip(),
                            kind=row["kind"].strip(),
                            url=row["url"].strip(),
                            params={p.strip() for p in row.get("params", "").split(";") if p.strip()},
                            parser=row.get("parser", "").strip(),
                            tags={t.strip() for t in row.get("tags", "").split(";") if t.strip()},
                            note=row.get("note", "").strip(),
                            enabled=_to_bool(row.get("enabled", "true")),
                            verified=_to_bool(row.get("verified", "false")),
                        )
                    )
                except Exception as row_error:
                    print("SOURCE REGISTRY: skipped a bad row:", type(row_error).__name__, flush=True)

    except Exception as error:
        print("SOURCE REGISTRY: could not read source_catalog.csv:", type(error).__name__, flush=True)

    return sources


SOURCES: List[Source] = _load()
_BY_ID: Dict[str, Source] = {source.id: source for source in SOURCES}


def get(source_id: str) -> Optional[Source]:
    """Look up one source by its id. Returns None if it is not found."""
    return _BY_ID.get(source_id)


def available(source: Source) -> bool:
    """
    True if this source can be used right now.
    Every source in the catalog today is free and needs no key, so this is
    just `enabled` for now - a later batch can add real outage or rate
    checks here without anything else needing to change.
    """
    return bool(source.enabled)


def render_url(source: Source, **values: str) -> str:
    """Fill a source's URL template with the given values (for example query=...)."""
    safe_values = {key: quote(str(value)) for key, value in values.items()}
    return source.url.format(**safe_values)


_TAG_WORDS: Dict[str, List[str]] = {
    "finance": ["stock", "market", "trading", "trade", "invest", "price", "shares"],
    "crypto": ["crypto", "bitcoin", "btc", "eth", "ethereum", "token", "coin"],
    "mood": ["mood", "sentiment", "feeling", "fear", "greed", "panic", "confidence"],
    "news": ["news", "today", "happened", "latest"],
    "central_bank": ["fed", "federal reserve", "interest rate", "rbi", "ecb"],
    "government": ["government", "regulation", "law", "policy"],
    "world": ["world", "global", "country", "war", "election"],
    "tech": ["tech", "technology", "startup", "software", "ai"],
    "research": ["research", "study", "paper", "science"],
    "history": ["history", "historical", "century"],
    "knowledge": ["what is", "who is", "define", "explain"],
}


def detect_tags(text: str) -> List[str]:
    """
    A small, honest keyword check - not real language understanding, just
    enough to decide which free sources are worth trying for this text.
    """

    text = (text or "").lower()
    found = [tag for tag, words in _TAG_WORDS.items() if any(word in text for word in words)]
    return found or ["general"]
