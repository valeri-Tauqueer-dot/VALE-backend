"""
VALE search engine - live fetch (step 2, part 1).

Opens many sources AT THE SAME TIME, with short time limits, and turns every answer into the
same simple record (a "hit"): title, link, short snippet, source, date.

Safe by design for a small free server:
  - at most 12 requests at once, one global time limit (a slow source is dropped, not waited for)
  - small download cap per request (1.5 MB), short timeouts
  - polite: a small gap between two requests to the same website
  - a 10 minute memory cache, so the same link is not opened again and again
  - one broken source never breaks the others; every source gives a status report

Only public data. Headlines and short snippets only, never whole pages.
"""
from __future__ import annotations

import json
import re
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass
from html import unescape
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from search_engine import source_registry as registry

HEADERS = {"User-Agent": "VALE-research-bot/0.2 (personal learning project)"}
CONNECT_TIMEOUT = 3.5
READ_TIMEOUT = 6.0
MAX_BYTES = 1_500_000
MAX_WORKERS = 12
CACHE_TTL = 600
CACHE_MAX = 200
HOST_GAP = 0.4          # seconds between two requests to the same website
SNIPPET_CHARS = 300

STOPWORDS = set("""
a an the of in on at to for from with about and or but me my i you we it this that these those is are was were be been being
what whats which who whom whose when where why how do does did can could should would will may might please tell show give
find search look get got any some all latest news today now new update updates happening happened going
""".split())


# ----------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------
def query_words(question: str) -> List[str]:
    """The useful words of a question ('what is the latest gold news' -> ['gold'])."""
    words: List[str] = []
    for raw in re.findall(r"[^\W_]+", (question or "").lower()):
        if len(raw) < 2 or raw in STOPWORDS:
            continue
        if raw not in words:
            words.append(raw)
    return words[:8]


def clean_text(value: Any) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", unescape(text)).strip()


def snippet(value: Any, limit: int = SNIPPET_CHARS) -> str:
    text = clean_text(value)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def score_text(title: str, body: str, words: List[str]) -> float:
    """Title matches count double."""
    if not words:
        return 0.0
    t, b = (title or "").lower(), (body or "").lower()
    return float(sum(2 for w in words if w in t) + sum(1 for w in words if w in b))


@dataclass
class Hit:
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    published: str = ""
    via: str = "live"           # "live" or "stored"
    score: float = 0.0
    tags: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceReport:
    source_id: str
    name: str
    status: str                 # ok | failed | timeout | skipped
    ms: int = 0
    count: int = 0
    error: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ----------------------------------------------------------------------
# safe downloading: cache, politeness, size cap
# ----------------------------------------------------------------------
_cache: Dict[str, Tuple[float, bytes]] = {}
_cache_lock = threading.Lock()
_host_lock = threading.Lock()
_host_next: Dict[str, float] = {}


def _cache_get(url: str) -> Optional[bytes]:
    with _cache_lock:
        item = _cache.get(url)
        if item and time.time() - item[0] < CACHE_TTL:
            return item[1]
        _cache.pop(url, None)
    return None


def _cache_put(url: str, data: bytes) -> None:
    with _cache_lock:
        if len(_cache) >= CACHE_MAX:
            oldest = sorted(_cache.items(), key=lambda kv: kv[1][0])[: CACHE_MAX // 4]
            for key, _ in oldest:
                _cache.pop(key, None)
        _cache[url] = (time.time(), data)


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()
    with _host_lock:
        _host_next.clear()


def _host_wait(url: str) -> None:
    host = urlparse(url).netloc.lower()
    with _host_lock:
        now = time.time()
        slot = max(now, _host_next.get(host, 0.0))
        _host_next[host] = slot + HOST_GAP
    delay = slot - now
    if delay > 0:
        time.sleep(min(delay, 1.5))


def http_get(url: str) -> bytes:
    cached = _cache_get(url)
    if cached is not None:
        return cached
    _host_wait(url)
    response = requests.get(url, headers=HEADERS, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), stream=True)
    try:
        response.raise_for_status()
        data = b""
        for chunk in response.iter_content(65536):
            data += chunk
            if len(data) > MAX_BYTES:
                break
    finally:
        try:
            response.close()
        except Exception:
            pass
    _cache_put(url, data)
    return data


# ----------------------------------------------------------------------
# readers (parsers)
# ----------------------------------------------------------------------
def _local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def parse_feed_bytes(data: bytes) -> List[Dict[str, str]]:
    """RSS (<item>) or Atom (<entry>) -> list of {title, url, summary, date}."""
    root = ET.fromstring(data)
    items: List[Dict[str, str]] = []
    for node in root.iter():
        if _local(node.tag) not in ("item", "entry"):
            continue
        row = {"title": "", "url": "", "summary": "", "date": ""}
        for child in node:
            name = _local(child.tag)
            if name == "title":
                row["title"] = clean_text(child.text)
            elif name == "link":
                row["url"] = (child.attrib.get("href") or child.text or "").strip()
            elif name in ("description", "summary", "content") and not row["summary"]:
                row["summary"] = clean_text(child.text)
            elif name in ("pubDate", "published", "updated", "date") and not row["date"]:
                row["date"] = (child.text or "").strip()
        if row["url"] and row["title"]:
            items.append(row)
    return items


def _rows(items: Any) -> List[Dict[str, Any]]:
    return [x for x in (items or []) if isinstance(x, dict)]


def p_gdelt(obj: Dict[str, Any]) -> List[Dict[str, str]]:
    return [{"title": clean_text(a.get("title")), "url": a.get("url") or "",
             "summary": f"{a.get('domain','')} {a.get('sourcecountry','')} {a.get('language','')}".strip(),
             "date": a.get("seendate") or ""} for a in _rows(obj.get("articles"))]


def p_wikipedia(obj: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for r in _rows(((obj.get("query") or {}).get("search"))):
        pid = r.get("pageid")
        if pid:
            out.append({"title": clean_text(r.get("title")), "url": f"https://en.wikipedia.org/?curid={pid}",
                        "summary": clean_text(r.get("snippet")), "date": r.get("timestamp") or ""})
    return out


def p_wikidata(obj: Dict[str, Any]) -> List[Dict[str, str]]:
    return [{"title": clean_text(r.get("label")), "url": r.get("concepturi") or (f"https://www.wikidata.org/wiki/{r.get('id')}" if r.get("id") else ""),
             "summary": clean_text(r.get("description")), "date": ""} for r in _rows(obj.get("search"))]


def p_openalex(obj: Dict[str, Any]) -> List[Dict[str, str]]:
    return [{"title": clean_text(r.get("title") or r.get("display_name")), "url": r.get("doi") or r.get("id") or "",
             "summary": f"Research paper, {r.get('publication_year') or ''}".strip(", "), "date": r.get("publication_date") or ""}
            for r in _rows(obj.get("results"))]


def p_crossref(obj: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for r in _rows(((obj.get("message") or {}).get("items"))):
        title = (r.get("title") or [""])[0] if isinstance(r.get("title"), list) else r.get("title")
        container = (r.get("container-title") or [""])[0] if isinstance(r.get("container-title"), list) else ""
        out.append({"title": clean_text(title), "url": r.get("URL") or "", "summary": clean_text(container), "date": ""})
    return out


def p_openlibrary(obj: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for r in _rows(obj.get("docs")):
        key = r.get("key")
        if key:
            authors = ", ".join(r.get("author_name") or [])[:120]
            out.append({"title": clean_text(r.get("title")), "url": f"https://openlibrary.org{key}",
                        "summary": f"{authors} {r.get('first_publish_year') or ''}".strip(), "date": ""})
    return out


def p_gutendex(obj: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for r in _rows(obj.get("results")):
        if r.get("id"):
            authors = ", ".join(a.get("name", "") for a in _rows(r.get("authors")))[:120]
            out.append({"title": clean_text(r.get("title")), "url": f"https://www.gutenberg.org/ebooks/{r['id']}",
                        "summary": f"Public-domain book. {authors}".strip(), "date": ""})
    return out


def p_federal_register(obj: Dict[str, Any]) -> List[Dict[str, str]]:
    return [{"title": clean_text(r.get("title")), "url": r.get("html_url") or "",
             "summary": clean_text(r.get("abstract")), "date": r.get("publication_date") or ""} for r in _rows(obj.get("results"))]


def p_hn(obj: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for r in _rows(obj.get("hits")):
        url = r.get("url") or (f"https://news.ycombinator.com/item?id={r['objectID']}" if r.get("objectID") else "")
        out.append({"title": clean_text(r.get("title")), "url": url, "summary": "", "date": r.get("created_at") or ""})
    return out


JSON_PARSERS: Dict[str, Callable[[Dict[str, Any]], List[Dict[str, str]]]] = {
    "gdelt_doc": p_gdelt, "wikipedia_search": p_wikipedia, "wikidata_search": p_wikidata,
    "openalex": p_openalex, "crossref": p_crossref, "openlibrary": p_openlibrary,
    "gutendex": p_gutendex, "federal_register": p_federal_register, "hn_algolia": p_hn,
}


def can_search_live(source: "registry.Source") -> bool:
    """True if this source can answer a text question by itself."""
    if not source.enabled or not registry.available(source):
        return False
    if source.kind in ("rss", "atom") and not source.params:
        return True
    if source.params and set(source.params) <= {"query"}:
        return source.parser in JSON_PARSERS or source.parser == "atom_entries"
    return False


# ----------------------------------------------------------------------
# one source
# ----------------------------------------------------------------------
def fetch_source(source: "registry.Source", question: str, words: List[str]) -> Tuple[List[Hit], SourceReport]:
    started = time.time()

    def done(status: str, hits: List[Hit], error: str = "") -> Tuple[List[Hit], SourceReport]:
        return hits, SourceReport(source.id, source.name, status, int((time.time() - started) * 1000), len(hits), error)

    if not can_search_live(source):
        return done("skipped", [], "needs more than a question, or needs a key")

    try:
        if source.params:
            api_query = " ".join(words) if words else (question or "")[:80]
            url = registry.render_url(source, query=api_query)
        else:
            url = source.url

        data = http_get(url)

        if source.kind in ("rss", "atom") or source.parser == "atom_entries":
            rows = parse_feed_bytes(data)
        else:
            rows = JSON_PARSERS[source.parser](json.loads(data.decode("utf-8", "replace")))

        hits: List[Hit] = []
        for row in rows:
            if not row.get("url") or not row.get("title"):
                continue
            body = snippet(row.get("summary"))
            score = score_text(row["title"], body, words)
            # a feed has no search box: keep only items that match; an API already matched
            if words and not source.params and score == 0:
                continue
            hits.append(Hit(title=row["title"], url=row["url"], snippet=body, source=source.name,
                            published=row.get("date", ""), via="live", score=score,
                            tags=",".join(registry.detect_tags(f"{row['title']} {body}"))))

        if not words and not source.params:
            hits = hits[:10]          # no useful words: just the newest items of the feed
        return done("ok", hits)

    except requests.exceptions.Timeout:
        return done("timeout", [], "Timeout")
    except Exception as error:
        return done("failed", [], type(error).__name__)


# ----------------------------------------------------------------------
# many sources at the same time
# ----------------------------------------------------------------------
def fan_out(
    sources: List["registry.Source"],
    question: str,
    deadline: float = 8.0,
    max_workers: int = MAX_WORKERS,
) -> Tuple[List[Hit], List[SourceReport]]:
    words = query_words(question)
    sources = [s for s in sources]
    if not sources:
        return [], []

    pool = ThreadPoolExecutor(max_workers=max(1, min(len(sources), max_workers)))
    futures = {pool.submit(fetch_source, s, question, words): s for s in sources}
    done, not_done = wait(list(futures), timeout=deadline)

    hits: List[Hit] = []
    reports: List[SourceReport] = []
    for future in done:
        try:
            got, report = future.result()
            hits.extend(got)
            reports.append(report)
        except Exception as error:
            source = futures[future]
            reports.append(SourceReport(source.id, source.name, "failed", 0, 0, type(error).__name__))
    for future in not_done:
        source = futures[future]
        future.cancel()
        reports.append(SourceReport(source.id, source.name, "timeout", int(deadline * 1000), 0, "too slow"))

    pool.shutdown(wait=False, cancel_futures=True)
    return hits, reports
