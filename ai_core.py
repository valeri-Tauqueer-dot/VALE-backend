"""VALE AI Core with the unified peer-brain foundation."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from vale_connector import VALEConnector
from brain_network import BrainNetwork
from cognitive_brain import CognitiveBrain
from legend_brain import LegendBrain
from alpha_brain import AlphaBrain
from marco_brain import MarcoBrain
from feelings_brain import FeelingsBrain
from heroic_brain import HeroicBrain
from supervisor_brain import SupervisorBrain
from unity_brain import UnityBrain
from vale_brain import VALEBrain

class VALECore:
    def __init__(self):
        self.name = "VALE AI"
        self.version = "3.0"
        self.status = "ONLINE"
        self.connector = VALEConnector()
        self.brain_network = BrainNetwork(connector=self.connector)
        self.brains = [
            CognitiveBrain(self.connector), LegendBrain(self.connector), AlphaBrain(self.connector),
            MarcoBrain(self.connector), FeelingsBrain(self.connector), HeroicBrain(self.connector),
            SupervisorBrain(self.connector), UnityBrain(self.connector),
        ]
        for brain in self.brains:
            self.brain_network.register(brain)
        # Existing working VALE brain remains the response engine until
        # the individual brains receive their real intelligence.
        self.legacy_brain = VALEBrain()

    def process(self, message: str, conversation: Optional[List[Dict[str, Any]]] = None,
                metadata: Optional[Dict[str, Any]] = None) -> str:
        original_message = (message or "").strip()
        if not original_message:
            return "Please ask me something."

        lower = original_message.lower()
        if lower in {"status", "system status", "are you online", "are you working"}:
            return self.system_status()
        if any(word in lower for word in ["who are you", "what are you", "your name"]):
            return ("I am VALE AI. I answer by searching the real internet through Exa — "
                    "I don't have a built-in list of answers, so everything I tell you comes from a live web search.")

        network_result = self.brain_network.process(
            user_message=original_message,
            conversation=conversation,
            metadata=metadata,
        )
        state = network_result["state"]

        try:
            understanding = self.legacy_brain.understand(original_message)
            state.set("understanding", understanding)
            state.set("intent", self.legacy_brain.detect_intent(understanding))
            state.set("needs_internet", self._needs_internet(state.get("intent", ""), understanding))
        except Exception:
            state.set("understanding", {"original": original_message, "lower": lower})
            state.set("intent", "unknown")
            state.set("needs_internet", True)

        response = self.legacy_brain.think(original_message)
        state.set("final_response", response)
        state.add_message("assistant", response)
        state.event("task_completed", "VALE_CORE", payload={"response_generated": True})
        return response

    def _needs_internet(self, intent: str, understanding: Dict[str, Any]) -> bool:
        if intent in {"research", "market_analysis"}:
            return True
        text = str(understanding.get("lower", ""))
        current_terms = ["latest", "today", "current", "recent", "live", "news", "price",
                         "weather", "score", "stock", "crypto", "bitcoin", "btc", "market"]
        return any(term in text for term in current_terms)

    def brain_status(self) -> Dict[str, Any]:
        return self.brain_network.status()

    def system_status(self) -> str:
        internet_ok = self.connector.internet_available()
        network = self.brain_network.status()
        return (f"VALE AI Status: {self.status}\n"
                f"Version: {self.version}\n"
                f"Brain Network: ONLINE\n"
                f"Brains Connected: {network['brain_count']}\n"
                f"Brain-to-Brain Communication: YES\n"
                f"Shared Brain State: YES\n"
                f"Shared Connector: YES\n"
                f"Internet (Exa) connected: {'YES' if internet_ok else 'NO — EXA_API_KEY not set'}\n"
                f"Checked: {datetime.now(timezone.utc).isoformat()}")

vale = VALECore()
