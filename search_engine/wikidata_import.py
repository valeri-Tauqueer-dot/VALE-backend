"""
VALE Wikidata importer - batch 3 of the plan.

Finds real organisations with a real official website, straight from
Wikidata's own public data, and saves each one as a small candidate row in
storage (url, title, source="wikidata-import"). Nothing here is marked as a
checked, working feed yet - that is the next batch's job (the link finder
and health checker). This file only answers one question: "what
organisations exist, and where is their homepage?"

Today it covers two groups, chosen because every country has them and they
move markets directly:
    - central banks (one per country - Wikidata property P1582)
    - stock exchanges (Wikidata class Q11691)

More groups can be added later just by adding another entry to QUERIES
below - nothing else needs to change.

Run it on its own:
    python -m search_engine.wikidata_import

Or import and call run() from anywhere else (a GitHub Actions job, a
manual button, a future wave runner).
"""
from __future__ import annotations

import sys
import time
from typing import Any, Dict, List

import requests

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "VALE-research-bot/0.2 (personal learning project; wikidata-import)"
TIMEOUT = (10, 60)  # connect, read - Wikidata's shared query service can be slow
ROW_LIMIT = 500      # a safety cap per group, not a target to reach

# One line per group: a short name, and the SPARQL query that finds it.
# Every query asks for an official website (P856) in the same breath as the
# organisation itself, so a row with no website is simply never returned -
# nothing extra to filter out afterwards. Every query uses the same
# ?item / ?itemLabel / ?website names so one parser works for all of them.
QUERIES: Dict[str, str] = {
    "central bank": f"""
        SELECT DISTINCT ?item ?itemLabel ?website WHERE {{
            ?country wdt:P1582 ?item .
            ?item wdt:P856 ?website .
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT {ROW_LIMIT}
    """,
    "stock exchange": f"""
        SELECT DISTINCT ?item ?itemLabel ?website WHERE {{
            ?item wdt:P31 wd:Q11691 .
            ?item wdt:P856 ?website .
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT {ROW_LIMIT}
    """,
}


def _run_query(sparql: str) -> List[Dict[str, str]]:
    """Ask Wikidata's own query service one question. Never raises."""

    try:
        response = requests.get(
            SPARQL_ENDPOINT,
            params={"query": sparql, "format": "json"},
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/sparql-results+json",
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        bindings = response.json().get("results", {}).get("bindings", [])

        rows: List[Dict[str, str]] = []
        for entry in bindings:
            name = entry.get("itemLabel", {}).get("value", "").strip()
            website = entry.get("website", {}).get("value", "").strip()
            if name and website:
                rows.append({"name": name, "website": website})
        return rows

    except Exception as error:
        print("WIKIDATA IMPORT: query failed:", type(error).__name__, flush=True)
        return []


def run() -> int:
    """
    Run every group's query and save each result as a tiny candidate row.
    Returns how many new rows were actually saved (duplicates don't count).
    """

    saved_total = 0

    for group, sparql in QUERIES.items():
        rows = _run_query(sparql)
        print(f"WIKIDATA IMPORT: {group} -> {len(rows)} found", flush=True)

        docs = [
            {
                "url": row["website"],
                "title": row["name"],
                "body": f"{group} (imported from Wikidata)",
                "source": "wikidata-import",
                "market": "global",
            }
            for row in rows
        ]

        try:
            from search_engine import storage
            saved = storage.save_many(docs)
        except Exception as error:
            print("WIKIDATA IMPORT: storage save failed:", type(error).__name__, flush=True)
            saved = 0

        saved_total += saved
        print(f"WIKIDATA IMPORT: {group} -> {saved} new rows saved", flush=True)

        # Be polite to Wikidata's shared, free query service between groups.
        time.sleep(1)

    print(f"WIKIDATA IMPORT: done, {saved_total} new rows total", flush=True)
    return saved_total


if __name__ == "__main__":
    sys.exit(0 if run() >= 0 else 1)
