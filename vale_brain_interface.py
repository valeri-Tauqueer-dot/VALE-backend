"""
VALE BRAIN INTERFACE

Standard connection interface between VALE brains
and VALE shared infrastructure.

Brains should communicate through this interface
instead of directly controlling infrastructure.
"""

from typing import Any, Dict, List, Optional

from vale_connector import VALEConnector


class VALEBrainInterface:

    def __init__(
        self,
        brain_name: str,
        connector: Optional[VALEConnector] = None
    ):

        self.brain_name = brain_name

        self.connector = (
            connector
            if connector is not None
            else VALEConnector()
        )

    # ============================================================
    # BRAIN INFORMATION
    # ============================================================

    def identity(self) -> Dict[str, Any]:

        return {
            "brain": self.brain_name,
            "interface": "VALE Brain Interface",
            "connector_version":
                self.connector.version
        }

    # ============================================================
    # WEB RESEARCH
    # ============================================================

    def search_web(
        self,
        query: str,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:

        return self.connector.search_web(
            query,
            num_results
        )

    # ============================================================
    # EXTERNAL URL ACCESS
    # ============================================================

    def get_url(
        self,
        url: str
    ) -> Optional[Dict[str, Any]]:

        return self.connector.get_url(
            url
        )

    # ============================================================
    # CONNECTOR STATUS
    # ============================================================

    def connector_status(
        self
    ) -> Dict[str, Any]:

        return self.connector.status()

    # ============================================================
    # AVAILABLE CAPABILITIES
    # ============================================================

    def capabilities(
        self
    ) -> Dict[str, bool]:

        return self.connector.capabilities()
