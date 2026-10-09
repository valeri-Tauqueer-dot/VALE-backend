"""
VALE search engine - news collector (step 1).

Reads a list of free news RSS feeds, tags each item with the markets it
talks about (gold, oil, crypto, forex, stocks, ...), and saves it with
storage.py.

Run from the main folder of the VALE-backend repo:
    python -m search_engine.collect_news

It never stops on one bad feed. A feed that fails is printed and skipped.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Dict, List

import requests

from search_engine import storage

# (name, link). If a feed stops working, fix or remove its line.
FEEDS = [
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Economic Times Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("US Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("Reserve Bank of India", "https://www.rbi.org.in/pressreleases_rss.xml"),
]

# Words that tell us which market a news item touches.
MARKET_WORDS: Dict[str, List[str]] = {
    "gold": ["gold", "bullion"],
    "silver": ["silver"],
    "oil": ["oil", "crude", "brent", "opec", "petrol", "diesel"],
    "gas": ["natural gas", "lng"],
    "crypto": ["bitcoin", "crypto", "ethereum", "blockchain", "stablecoin"],
    "forex": ["dollar", "rupee", "euro", "yen", "currency", "forex", "exchange rate"],
    "stocks": ["stock", "shares", "sensex", "nifty", "nasdaq", "dow", "s&p", "equity", "ipo"],
    "bonds": ["bond", "yield", "treasury"],
    "rates": ["interest rate", "rate cut", "rate hike", "repo", "inflation", "central bank", "fed "],
    "food": ["wheat", "rice", "sugar", "fish", "fishing", "crop", "harvest", "food price"],
    "weather": ["monsoon", "drought", "flood", "hurricane", "cyclone", "heatwave"],
    "war": ["war", "missile", "invasion", "sanction", "ceasefire", "attack", "conflict"],
}

HEADERS = {"User-Agent": "VALE-research-bot/0.1 (personal learning project)"}
TIMEOUT = 20


def clean(html_text: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", html_text or "")
    return re.sub(r"\s+", " ", unescape(no_tags)).strip()


def tag_markets(title: str, body: str) -> str:
    haystack = f" {title} {body} ".lower()
    found = []
    for market, words in MARKET_WORDS.items():
        if any(w in haystack for w in words):
            found.append(market)
    return ",".join(found)


def parse_date(value: str) -> str:
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).isoformat()
    except Exception:
        return value.strip()


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def parse_feed(xml_bytes: bytes) -> List[Dict[str, str]]:
    """Read RSS (<item>) or Atom (<entry>) and return simple dictionaries."""
    root = ET.fromstring(xml_bytes)
    items = []
    for node in root.iter():
        if _local(node.tag) not in ("item", "entry"):
            continue
        data = {"title": "", "link": "", "summary": "", "date": ""}
        for child in node:
            name = _local(child.tag)
            if name == "title":
                data["title"] = clean(child.text or "")
            elif name == "link":
                data["link"] = (child.attrib.get("href") or child.text or "").strip()
            elif name in ("description", "summary", "content") and not data["summary"]:
                data["summary"] = clean(child.text or "")
            elif name in ("pubDate", "published", "updated", "date") and not data["date"]:
                data["date"] = parse_date(child.text or "")
        if data["link"] and data["title"]:
            items.append(data)
    return items


def collect() -> Dict[str, int]:
    stats = {"feeds_ok": 0, "feeds_failed": 0, "saved": 0, "skipped": 0}
    for name, url in FEEDS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            items = parse_feed(response.content)
        except Exception as error:
            print(f"FEED FAILED: {name} -> {type(error).__name__}", flush=True)
            stats["feeds_failed"] += 1
            continue

        stats["feeds_ok"] += 1
        saved_here = 0
        for item in items:
            market = tag_markets(item["title"], item["summary"])
            ok = storage.save_document(
                url=item["link"],
                title=item["title"],
                body=item["summary"],
                source=name,
                market=market,
                published_at=item["date"],
            )
            if ok:
                saved_here += 1
                stats["saved"] += 1
            else:
                stats["skipped"] += 1
        print(f"FEED OK: {name} -> {len(items)} items, {saved_here} new", flush=True)
    return stats


if __name__ == "__main__":
    result = collect()
    print("DONE:", result, "| total saved in storage:", storage.count(), flush=True)
    # Fail the run only if every feed failed (so GitHub shows a red mark).
    if result["feeds_ok"] == 0:
        sys.exit(1)
