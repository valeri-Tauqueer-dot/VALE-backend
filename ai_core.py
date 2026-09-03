"""VALE AI CORE — unified brains with universal Internet fallback.

Every normal user question first gets a live Internet evidence pass through the
single shared VALEConnector. The eight brains then receive the same task state.
Today the brains are still foundation shells, so VALE falls back to the cleaned
Internet evidence. As brain intelligence is added, those brains can refine,
verify, rank and synthesize the same evidence without changing the API gateway.
"""
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
from ai_osgeneration import AiOsGenerationBrain


class VALECore:
    def __init__(self):
        self.name = "VALE AI"
        self.version = "3.1"
        self.status = "ONLINE"

        # One connector is shared by the entire unified brain.
        self.connector = VALEConnector()
        self.brain_network = BrainNetwork(connector=self.connector)

        self.brains = [
            CognitiveBrain(self.connector),
            LegendBrain(self.connector),
            AlphaBrain(self.connector),
            MarcoBrain(self.connector),
            FeelingsBrain(self.connector),
            HeroicBrain(self.connector),
            SupervisorBrain(self.connector),
            UnityBrain(self.connector),
            AiOsGenerationBrain(self.connector),
        ]

        for brain in self.brains:
            self.brain_network.register(brain)

    def process(
        self,
        message: str,
        conversation: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        original_message = (message or "").strip()
        if not original_message:
            return "Please ask me something."

        lower = original_message.lower()
        if lower in {"status", "system status", "are you online", "are you working"}:
            return self.system_status()

        if any(word in lower for word in ["who are you", "what are you", "your name"]):
            return (
                "I am VALE AI. My unified brain network is online, and I can use "
                "live Internet research through the shared VALE connector."
            )

        network_result = self.brain_network.process(
            user_message=original_message,
            conversation=conversation,
            metadata=metadata,
        )
        state = network_result["state"]

        # Foundation-stage fallback: until specialized brain intelligence is loaded,
        # return the live Internet evidence instead of saying "I don't know".
        response = self._internet_fallback(original_message, network_result.get("internet_results", []))

        state.set("answer_source", "internet_fallback")
        state.set("final_response", response)
        state.add_message("assistant", response)
        state.event(
            "task_completed",
            "VALE_CORE",
            payload={
                "response_generated": bool(response),
                "source": "internet_fallback",
                "brain_count": len(self.brains),
            },
        )
        return response

    def _internet_fallback(self, message: str, results: List[Dict[str, Any]]) -> str:
        if not self.connector.internet_available():
            return (
                "VALE cannot use the Internet right now because EXA_API_KEY is not "
                "configured on the server. Once the key is configured, every normal "
                "question will automatically receive a live Internet research pass."
            )

        if not results:
            return (
                f'VALE searched the Internet for "{message}" but did not receive usable '
                "results. Try rephrasing the question or making it more specific."
            )

        lines = [f'VALE — live Internet research for: "{message}"', ""]
        shown = 0

        for item in results:
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            highlights = item.get("highlights") or []
            if not title and not url:
                continue

            shown += 1
            lines.append(f"{shown}. {title or url}")
            if url:
                lines.append(f"   Source: {url}")
            for highlight in highlights[:3]:
                text = (highlight or "").strip()
                if text:
                    lines.append(f"   • {text}")
            lines.append("")

        if shown == 0:
            return (
                f'VALE searched the Internet for "{message}" but the returned data '
                "was not usable. Try rephrasing the question."
            )

        lines.append(
            "Brain status: connected. The current brains are foundation modules; "
            "their refinement/verification layer will be applied as their intelligence "
            "is added."
        )
        return "\n".join(lines).strip()

    def brain_status(self) -> Dict[str, Any]:
        return self.brain_network.status()

    def system_status(self) -> str:
        internet_ok = self.connector.internet_available()
        network = self.brain_network.status()
        return (
            f"VALE AI Status: {self.status}\n"
            f"Version: {self.version}\n"
            f"Brain Network: ONLINE\n"
            f"Brains Connected: {network['brain_count']}\n"
            f"Brain-to-Brain Communication: YES\n"
            f"Shared Brain State: YES\n"
            f"Shared Connector: YES\n"
            f"Internet (Exa) configured: {'YES' if internet_ok else 'NO — EXA_API_KEY not set'}\n"
            f"Checked: {datetime.now(timezone.utc).isoformat()}"
        )


vale = VALECore()
