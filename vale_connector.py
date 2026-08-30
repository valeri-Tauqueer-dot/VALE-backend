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
import requests

from typing import Any, Dict, List, Optional


class VALEConnector:

    def __init__(self):

        self.name = "VALE Connector"
        self.version = "2.0"

        # External services

        self.exa_api_url = (
            "https://api.exa.ai/search"
        )

    # ============================================================
    # INTERNET
    # ============================================================

    def internet_available(self) -> bool:
        """
        Check whether the required internet-search
        configuration is available.
        """

        return bool(
            os.environ.get(
                "EXA_API_KEY"
            )
        )

    # ============================================================
    # WEB SEARCH
    # ============================================================

    def search_web(
        self,
        query: str,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search the web through Exa.

        Future brains can request web research
        through this single gateway.
        """

        if not query or not query.strip():

            return []

        api_key = os.environ.get(
            "EXA_API_KEY"
        )

        if not api_key:

            print(
                "VALE CONNECTOR: "
                "EXA_API_KEY is not configured."
            )

            return []

        try:

            response = requests.post(

                self.exa_api_url,

                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                },

                json={
                    "query": query.strip(),
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

                title = item.get(
                    "title",
                    ""
                )

                url = item.get(
                    "url",
                    ""
                )

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

                    "title": title,

                    "url": url,

                    "highlights": highlights
                })

            return results

        except Exception as error:

            print(
                "VALE CONNECTOR "
                "WEB SEARCH ERROR:",
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
