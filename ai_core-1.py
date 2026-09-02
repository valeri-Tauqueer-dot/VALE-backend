"""VALE AI Core — Unified Brain + Shared Internet Coordinator."""

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
    """Coordinates VALE's connected brain modules and shared services."""

    def __init__(self):
        self.name = "VALE AI"
        self.version = "3.1"
        self.status = "ONLINE"

        # One shared connector for all brains.
        self.connector = VALEConnector()

        # Brain-to-brain network.
        self.brain_network = BrainNetwork(
            connector=self.connector
        )

        # Register all brain modules.
        self.brains = [
            CognitiveBrain(self.connector),
            LegendBrain(self.connector),
            AlphaBrain(self.connector),
            MarcoBrain(self.connector),
            FeelingsBrain(self.connector),
            HeroicBrain(self.connector),
            SupervisorBrain(self.connector),
            UnityBrain(self.connector),
        ]

        for brain in self.brains:
            self.brain_network.register(brain)

        # Keep the existing VALE response brain.
        self.legacy_brain = VALEBrain()

    def process(
        self,
        message: str,
        conversation: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process a user message through the unified VALE system."""

        original_message = (message or "").strip()

        if not original_message:
            return {
                "response": "Please ask me something.",
                "internet_used": False,
                "web_results": [],
                "brain_results": {},
            }

        # Create/process shared network state.
        network_result = self.brain_network.process(
            user_message=original_message,
            conversation=conversation,
            metadata=metadata,
        )

        state = network_result["state"]

        # Understand the request using the existing VALE brain.
        try:
            understanding = self.legacy_brain.understand(
                original_message
            )
            intent = self.legacy_brain.detect_intent(
                understanding
            )
        except Exception:
            understanding = {
                "original": original_message,
                "lower": original_message.lower(),
            }
            intent = "unknown"

        state.set("understanding", understanding)
        state.set("intent", intent)

        # Decide whether fresh web information is needed.
        needs_internet = self._needs_internet(
            intent,
            understanding,
            original_message,
        )
        state.set("needs_internet", needs_internet)

        # Shared internet research.
        web_results = []

        if needs_internet:
            try:
                web_results = self.connector.search_web(
                    original_message,
                    num_results=5,
                )
            except Exception as error:
                print(
                    "VALE CORE INTERNET ERROR:",
                    str(error),
                )
                web_results = []

        # Make web results available to every brain.
        state.set("web_results", web_results)
        state.set("internet_used", bool(web_results))

        try:
            state.set(
                "internet_available",
                self.connector.internet_available(),
            )
        except Exception:
            state.set("internet_available", False)

        # Run all brains with the shared state, including web data.
        try:
            brain_results = self.brain_network.run_all(state)
        except Exception as error:
            print(
                "VALE BRAIN NETWORK ERROR:",
                str(error),
            )
            brain_results = {}

        state.set("brain_results", brain_results)

        # Generate the main response using the existing VALE brain.
        try:
            response = self.legacy_brain.think(
                original_message
            )
        except Exception as error:
            print(
                "VALE RESPONSE ERROR:",
                str(error),
            )
            response = (
                "VALE encountered an error while "
                "processing the request."
            )

        # Some existing brain implementations may themselves return
        # a dictionary. Normalize it to the actual text response.
        if isinstance(response, dict):
            response = (
                response.get("response")
                or response.get("answer")
                or response.get("message")
                or str(response)
            )

        response = str(response)

        # Save the final response for future brain interaction.
        state.set("final_response", response)

        try:
            state.add_message("assistant", response)
        except Exception:
            pass

        try:
            state.event(
                "task_completed",
                "VALE_CORE",
                payload={
                    "response_generated": True,
                    "internet_used": bool(web_results),
                    "brains_connected": len(self.brains),
                },
            )
        except Exception:
            pass

        # Return one stable response object to main.py/frontend.
        try:
            brain_names = self.brain_network.brain_names()
        except Exception:
            brain_names = [
                getattr(brain, "brain_name", brain.__class__.__name__)
                for brain in self.brains
            ]

        try:
            internet_available = self.connector.internet_available()
        except Exception:
            internet_available = False

        return {
            "response": response,
            "intent": intent,
            "internet_used": bool(web_results),
            "internet_available": internet_available,
            "web_results": web_results,
            "brain_results": brain_results,
            "brains_connected": brain_names,
        }

    def _needs_internet(
        self,
        intent: str,
        understanding: Dict[str, Any],
        message: str,
    ) -> bool:
        """Return True when fresh/current web information is useful."""

        text = (message or "").lower()

        internet_terms = [
            "latest",
            "today",
            "current",
            "recent",
            "live",
            "news",
            "price",
            "weather",
            "score",
            "market",
            "stock",
            "crypto",
            "bitcoin",
            "btc",
            "eth",
            "ethereum",
            "search",
            "internet",
            "online",
            "web",
            "what happened",
            "what is happening",
        ]

        if intent in {
            "research",
            "market_analysis",
            "current_information",
        }:
            return True

        return any(
            term in text
            for term in internet_terms
        )

    def brain_status(self) -> Dict[str, Any]:
        return self.brain_network.status()

    def system_status(self) -> str:
        try:
            internet_ok = self.connector.internet_available()
        except Exception:
            internet_ok = False

        try:
            network = self.brain_network.status()
            brain_count = network.get(
                "brain_count",
                len(self.brains),
            )
        except Exception:
            brain_count = len(self.brains)

        return (
            f"VALE AI Status: {self.status}\n"
            f"Version: {self.version}\n"
            f"Brain Network: ONLINE\n"
            f"Brains Connected: {brain_count}\n"
            f"Shared Connector: YES\n"
            f"Internet Configuration: "
            f"{'YES' if internet_ok else 'NO'}\n"
            f"Checked: "
            f"{datetime.now(timezone.utc).isoformat()}"
        )


# Global VALE instance used by the backend.
vale = VALECore()
