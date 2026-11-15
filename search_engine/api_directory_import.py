"""
VALE API-directory importer - batch 3 of the plan.

Reads the free, public APIs.guru directory (https://apis.guru - no key
needed, no sign-up) and saves each relevant provider as a small candidate
row in storage, the same way wikidata_import.py does. Like that file, this
one only answers "what organisations exist, and where is their homepage or
API?" - the next batch (the link finder and health checker) is what
actually tests and confirms a real working feed from each one.

The APIs.guru list covers 2,500+ APIs for every kind of software tool, so
this file keeps only the entries whose name or description matches a
market-relevant word (finance, bank, currency, crypto, government,
weather, news, and so on) - not the whole directory.

Run it on its own:
    python -m search_engine.api_directory_import
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List

import requests

LIST_URL = "https://api.apis.guru/v2/list.json"
USER_AGENT = "VALE-research-bot/0.2 (personal learning project; api-directory-import)"
TIMEOUT = (10, 60)

# Only entries whose id, title or description mention one of these are
# kept - the full directory is mostly unrelated developer tools. Add a
# word here any time and more of the directory opens up - nothing else
# needs to change.
KEYWORDS = [
    "bank", "finance", "financial", "currency", "exchange rate", "forex",
    "stock", "market", "trading", "invest", "crypto", "bitcoin", "economy",
    "economic", "government", "treasury", "central bank", "regulator",
    "weather", "climate", "commodity", "news", "statistics",
]


def _fetch_directory() -> Dict[str, Any]:
    """Download the whole APIs.guru directory once. Never raises."""

    try:
        response = requests.get(
            LIST_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    except Exception as error:
        print("API DIRECTORY IMPORT: download failed:", type(error).__name__, flush=True)
        return {}


def _matches(text: str) -> bool:
    """A small, honest keyword check - good enough to skip unrelated tools."""
    text = (text or "").lower()
    return any(word in text for word in KEYWORDS)


def _candidate_rows(directory: Dict[str, Any]) -> List[Dict[str, str]]:
    """Pick out the market-relevant entries and shape them as save_many() rows."""

    rows: List[Dict[str, str]] = []

    for api_id, entry in (directory or {}).items():
        try:
            preferred = entry.get("preferred", "")
            versions = entry.get("versions", {})
            info = versions.get(preferred, {}).get("info", {}) if preferred else {}

            title = info.get("title") or api_id
            description = info.get("description") or ""

            if not _matches(f"{api_id} {title} {description}"):
                continue

            provider = api_id.split(":")[0]
            contact = info.get("contact") or {}
            website = contact.get("url") or f"https://{provider}"

            rows.append(
                {
                    "url": website,
                    "title": str(title)[:200],
                    "body": str(description)[:500],
                    "source": "api-directory-import",
                    "market": "global",
                }
            )

        except Exception as row_error:
            print(
                "API DIRECTORY IMPORT: skipped a bad entry:",
                type(row_error).__name__,
                flush=True,
            )
            continue

    return rows


def run() -> int:
    """Download the directory, keep the relevant entries, save them.
    Returns the number of new rows saved (duplicates don't count)."""

    directory = _fetch_directory()
    print(f"API DIRECTORY IMPORT: {len(directory)} total APIs in the directory", flush=True)

    rows = _candidate_rows(directory)
    print(f"API DIRECTORY IMPORT: {len(rows)} match a market keyword", flush=True)

    try:
        from search_engine import storage
        saved = storage.save_many(rows)
    except Exception as error:
        print("API DIRECTORY IMPORT: storage save failed:", type(error).__name__, flush=True)
        saved = 0

    print(f"API DIRECTORY IMPORT: {saved} new rows saved", flush=True)
    return saved


if __name__ == "__main__":
    sys.exit(0 if run() >= 0 else 1)
