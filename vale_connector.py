"""
VALE CONNECTOR

The shared infrastructure gateway for VALE.

Future brains such as:
- UNITY
- HEROIC
- SUPERVISOR
- ALPHA
- LEGEND
- MARCO
- FEELINGS

can use this connector instead of creating
their own separate internet/API connections.

The connector does NOT decide what a brain should think.

It only provides controlled access to external
and shared capabilities.
"""

import os
import re
import time
import requests

from typing import Any, Dict, List, Optional, Tuple


class VALEConnector:

    def __init__(self):

        self.name = "VALE Connector"
        self.version = "2.0"

        # External services

        self.exa_api_url = (
            "https://api.exa.ai/search"
        )

        # Keyless fallback so internet answers work even before an
        # EXA_API_KEY is configured. Set VALE_FREE_SEARCH=0 to disable it.
        self.wikipedia_api_url = (
            "https://en.wikipedia.org/w/api.php"
        )

        self.user_agent = (
            "VALE-AI/1.0 (learning project; contact: owner of this server)"
        )

        # Small in-memory cache: (provider, query) -> (time, results)
        self._search_cache: Dict[
            Tuple[str, str],
            Tuple[float, List[Dict[str, Any]]],
        ] = {}

        self._cache_seconds = 600
        self._cache_limit = 100

    # ============================================================
    # INTERNET
    # ============================================================

    def exa_configured(self) -> bool:
        """True when an EXA_API_KEY is set on this server."""

        return bool(
            os.environ.get(
                "EXA_API_KEY"
            )
        )

    def free_search_enabled(self) -> bool:
        """The keyless Wikipedia fallback is ON unless VALE_FREE_SEARCH=0."""

        return os.environ.get(
            "VALE_FREE_SEARCH",
            "1",
        ).strip().lower() not in {"0", "false", "off", "no"}

    def search_provider(self) -> str:
        """Which provider search_web() will try first."""

        if self.exa_configured():
            return "exa"

        if self.free_search_enabled():
            return "wikipedia"

        return "none"

    def internet_available(self) -> bool:
        """
        Check whether internet search can be attempted: either an Exa key
        is configured or the free Wikipedia fallback is enabled.
        """

        return self.search_provider() != "none"

    # ============================================================
    # WEB SEARCH
    # ============================================================

    def search_web(
        self,
        query: str,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search the web.

        Order: Exa (when EXA_API_KEY is set) -> Wikipedia (free fallback).
        Every result has the same shape:
            {"title": str, "url": str, "highlights": [str, ...]}

        Future brains can request web research
        through this single gateway.
        """

        if not query or not query.strip():

            return []

        query = query.strip()

        results: List[Dict[str, Any]] = []

        if self.exa_configured():

            results = self._cached(
                "exa",
                query,
                lambda: self._search_exa(
                    query,
                    num_results,
                ),
            )

        if not results and self.free_search_enabled():

            results = self._cached(
                "wikipedia",
                query,
                lambda: self._search_wikipedia(
                    query,
                    min(num_results, 3),
                ),
            )

        if not results and not self.exa_configured():

            if not self.free_search_enabled():

                print(
                    "VALE CONNECTOR: "
                    "EXA_API_KEY is not configured "
                    "and the free search fallback is off."
                )

        return results

    # ------------------------------------------------------------
    # cache
    # ------------------------------------------------------------

    def _cached(
        self,
        provider: str,
        query: str,
        fetch,
    ) -> List[Dict[str, Any]]:

        key = (
            provider,
            query.lower(),
        )

        now = time.time()

        hit = self._search_cache.get(key)

        if hit and now - hit[0] < self._cache_seconds:

            return list(hit[1])

        results = fetch() or []

        # Only cache successful lookups, so a temporary network failure
        # is retried on the next question.
        if results:

            if len(self._search_cache) >= self._cache_limit:

                oldest = min(
                    self._search_cache,
                    key=lambda k: self._search_cache[k][0],
                )

                self._search_cache.pop(
                    oldest,
                    None,
                )

            self._search_cache[key] = (
                now,
                list(results),
            )

        return results

    # ------------------------------------------------------------
    # Exa
    # ------------------------------------------------------------

    def _search_exa(
        self,
        query: str,
        num_results: int,
    ) -> List[Dict[str, Any]]:

        api_key = os.environ.get(
            "EXA_API_KEY"
        )

        if not api_key:

            return []

        try:

            response = requests.post(

                self.exa_api_url,

                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                },

                json={
                    "query": query,
                    "type": "auto",
                    "numResults": num_results,
                    "contents": {
                        "highlights": True,
                    },
                },

                timeout=25,
            )

            response.raise_for_status()

            payload = response.json()

            results = []

            for item in payload.get(
                "results",
                []
            ):

                highlights = item.get(
                    "highlights",
                    []
                )

                if not isinstance(
                    highlights,
                    list
                ):

                    highlights = []

                results.append({

                    "title": item.get(
                        "title",
                        ""
                    ),

                    "url": item.get(
                        "url",
                        ""
                    ),

                    "highlights": highlights,

                    "source": "exa",
                })

            return results

        except Exception as error:

            print(
                "VALE CONNECTOR "
                "WEB SEARCH ERROR (exa):",
                str(error)
            )

            return []

    # ------------------------------------------------------------
    # Wikipedia (free, no key)
    # ------------------------------------------------------------

    @staticmethod
    def _clean_topic(query: str) -> str:
        """'what is a market order?' -> 'market order'."""

        text = re.sub(
            r"[^\w\s'-]",
            " ",
            (query or "").lower(),
        )

        words = text.split()

        drop = {
            "what", "whats", "what's", "who", "whom", "whos", "who's",
            "is", "are", "was", "were", "the", "a", "an", "of", "tell",
            "me", "about", "explain", "define", "describe", "please",
            "does", "do", "did", "how", "why", "when", "where", "give",
            "show", "meaning", "mean", "means", "definition",
        }

        kept = [
            w for w in words
            if w not in drop
        ]

        return " ".join(
            kept or words
        )

    def _search_wikipedia(
        self,
        query: str,
        num_results: int,
    ) -> List[Dict[str, Any]]:

        topic = self._clean_topic(
            query
        )

        if not topic:

            return []

        try:

            response = requests.get(

                self.wikipedia_api_url,

                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": topic,
                    "gsrlimit": max(1, int(num_results)),
                    "prop": "extracts|info",
                    "exintro": 1,
                    "explaintext": 1,
                    "exsentences": 3,
                    "inprop": "url",
                    "redirects": 1,
                    "format": "json",
                    "formatversion": 2,
                },

                headers={
                    "User-Agent": self.user_agent,
                },

                timeout=8,
            )

            response.raise_for_status()

            pages = (
                response.json()
                .get("query", {})
                .get("pages", [])
            )

            if isinstance(pages, dict):

                pages = list(
                    pages.values()
                )

            pages = sorted(
                pages,
                key=lambda page: page.get(
                    "index",
                    999,
                ),
            )

            results = []

            for page in pages:

                extract = str(
                    page.get("extract", "") or ""
                ).strip()

                # Skip empty pages and "X may refer to:" lists.
                if not extract or "may refer to" in extract[:200]:

                    continue

                results.append({

                    "title": page.get(
                        "title",
                        ""
                    ),

                    "url": page.get(
                        "fullurl",
                        "",
                    ),

                    "highlights": [
                        extract[:700]
                    ],

                    "source": "wikipedia",
                })

            return results

        except Exception as error:

            print(
                "VALE CONNECTOR "
                "WEB SEARCH ERROR (wikipedia):",
                str(error)
            )

            return []

    # ============================================================
    # SIMPLE INTERNET REQUEST
    # ============================================================

    def get_url(
        self,
        url: str,
        timeout: int = 15
    ) -> Optional[Dict[str, Any]]:
        """
        Make a controlled GET request.

        This will later allow approved VALE modules
        to access external APIs and websites.
        """

        if not url or not url.strip():

            return None

        try:

            response = requests.get(
                url.strip(),
                timeout=timeout
            )

            return {

                "success": True,

                "status_code":
                    response.status_code,

                "url":
                    response.url,

                "text":
                    response.text
            }

        except Exception as error:

            print(
                "VALE CONNECTOR "
                "GET ERROR:",
                str(error)
            )

            return {

                "success": False,

                "status_code": None,

                "url": url,

                "text": "",

                "error": str(error)
            }

    # ============================================================
    # CONNECTOR STATUS
    # ============================================================

    def status(
        self
    ) -> Dict[str, Any]:
        """
        Return connector health information.
        """

        return {

            "name":
                self.name,

            "version":
                self.version,

            "internet_available":
                self.internet_available(),

            "search_provider":
                self.search_provider(),

            "exa_configured":
                self.exa_configured(),

            "free_search_enabled":
                self.free_search_enabled(),

            "web_search":
                True,

            "url_requests":
                True
        }

    # ============================================================
    # CAPABILITIES
    # ============================================================

    def capabilities(
        self
    ) -> Dict[str, bool]:
        """
        Tell VALE brains what this connector
        currently provides.
        """

        return {

            "internet_search":
                True,

            "external_url_requests":
                True,

            "market_data":
                False,

            "news_data":
                False,

            "database_access":
                False,

            "brain_communication":
                False
        }


# ================================================================
# LOCAL TEST
# ================================================================

if __name__ == "__main__":

    connector = VALEConnector()

    print(
        "VALE CONNECTOR"
    )

    print(
        connector.status()
    )

    print(
        connector.capabilities()
            )
