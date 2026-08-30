"""
VALE CONNECTOR

The common connection layer between VALE brains/modules
and VALE's shared capabilities.

Brains should use this connector instead of creating
their own separate connections to every service.
"""

import os
import requests
from typing import Any, Dict, List, Optional


class VALEConnector:

    def __init__(self):
        self.name = "VALE Connector"
        self.version = "1.0"

        # Shared external service configuration
        self.exa_api_url = "https://api.exa.ai/search"

    # ============================================================
    # INTERNET
    # ============================================================

    def internet_search(
        self,
        query: str,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Shared VALE internet search.

        Any VALE brain/module that needs internet
        information can use this method.
        """

        api_key = os.environ.get("EXA_API_KEY")

        if not api_key:
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

            for item in payload.get("results", []):

                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "highlights": item.get(
                        "highlights",
                        []
                    ),
                })

            return results

        except Exception as error:

            print(
                "VALE CONNECTOR INTERNET ERROR:",
                str(error)
            )

            return []

    # ============================================================
    # STATUS
    # ============================================================

    def status(self) -> Dict[str, Any]:
        """
        Return connector status.
        """

        return {
            "name": self.name,
            "version": self.version,
            "internet_available": bool(
                os.environ.get("EXA_API_KEY")
            ),
          if __name__ == "__main__":

    connector = VALEConnector()

    print(
        "VALE CONNECTOR STATUS:"
    )

    print(
        connector.status()
                  )
  }
