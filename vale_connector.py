"""
VALE CONNECTOR

Shared connection layer for VALE brains and modules.

This is the first foundation layer.
Brains will use this connector to access
shared VALE capabilities.
"""

import os
import requests
from typing import Any, Dict, List


class VALEConnector:

    def __init__(self):

        self.name = "VALE Connector"
        self.version = "1.0"

        self.exa_api_url = (
            "https://api.exa.ai/search"
        )

    # ============================================================
    # INTERNET SEARCH
    # ============================================================

    def internet_search(
        self,
        query: str,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:

        api_key = os.environ.get(
            "EXA_API_KEY"
        )

        if not api_key:

            print(
                "VALE CONNECTOR: "
                "EXA_API_KEY is not configured."
            )

            return []

        if not query or not query.strip():

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

                results.append({

                    "title": item.get(
                        "title",
                        ""
                    ),

                    "url": item.get(
                        "url",
                        ""
                    ),

                    "highlights": item.get(
                        "highlights",
                        []
                    ),
                })

            return results

        except Exception as error:

            print(
                "VALE CONNECTOR "
                "INTERNET ERROR:",
                str(error)
            )

            return []

    # ============================================================
    # CONNECTOR STATUS
    # ============================================================

    def status(
        self
    ) -> Dict[str, Any]:

        return {

            "name": self.name,

            "version": self.version,

            "internet_available": bool(
                os.environ.get(
                    "EXA_API_KEY"
                )
            )
        }


# ================================================================
# LOCAL TEST
# ================================================================

if __name__ == "__main__":

    connector = VALEConnector()

    print(
        "VALE CONNECTOR STATUS:"
    )

    print(
        connector.status()
    )
