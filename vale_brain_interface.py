"""Common interface for every VALE brain."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from vale_connector import VALEConnector
if TYPE_CHECKING:
    from brain_network import BrainNetwork
    from brain_state import VALEBrainState

class VALEBrainInterface:
    def __init__(self, brain_name: str, connector: Optional[VALEConnector] = None,
                 network: Optional["BrainNetwork"] = None):
        self.brain_name = str(brain_name).upper()
        self.connector = connector if connector is not None else VALEConnector()
        self.network = network

    def attach_network(self, network: "BrainNetwork") -> None:
        self.network = network

    def identity(self) -> Dict[str, Any]:
        return {"brain": self.brain_name, "interface": "VALE Brain Interface",
                "network_connected": self.network is not None, "connector_version": self.connector.version}

    def think(self, state: "VALEBrainState") -> Dict[str, Any]:
        return {"brain": self.brain_name, "status": "READY", "intelligence_loaded": False,
                "message": f"{self.brain_name} brain is connected to the unified VALE brain network."}

    def receive_message(self, message: str, state: "VALEBrainState", source_brain: str,
                        payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"brain": self.brain_name, "received": True, "from": source_brain,
                "message": message, "payload": payload or {}}

    def ask_brain(self, brain_name: str, message: str, state: "VALEBrainState",
                  payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.network is None:
            return {"success": False, "error": "Brain is not connected to VALE Brain Network."}
        return self.network.ask(self.brain_name, brain_name, message, state, payload)

    def broadcast(self, message: str, state: "VALEBrainState",
                  payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.network is None:
            return {"success": False, "error": "Brain is not connected to VALE Brain Network."}
        return self.network.broadcast(self.brain_name, message, state, payload)

    def set_shared(self, state: "VALEBrainState", key: str, value: Any) -> None:
        state.set(key, value)

    def get_shared(self, state: "VALEBrainState", key: str, default: Any = None) -> Any:
        return state.get(key, default)

    def contribute(self, state: "VALEBrainState", kind: str, content: Any,
                   confidence: float = 0.0, importance: float = 0.5,
                   metadata: Optional[Dict[str, Any]] = None):
        return state.contribute(self.brain_name, kind, content, confidence, importance, metadata)

    def search_web(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        return self.connector.search_web(query, num_results)

    def get_url(self, url: str) -> Optional[Dict[str, Any]]:
        return self.connector.get_url(url)

    def connector_status(self) -> Dict[str, Any]:
        return self.connector.status()

    def capabilities(self) -> Dict[str, bool]:
        return self.connector.capabilities()
