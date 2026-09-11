"""VALE AI CORE — unified brains with universal Internet fallback.

Every normal user question first gets a live Internet evidence pass through the
single shared VALEConnector. The nine brains then receive the same task state.
VALE-internal architecture questions are handled internally before Internet
research so names such as LEGEND, ALPHA, HEROIC, UNITY, MARCO, FEELING and
SUPERVISOR are not incorrectly interpreted as ordinary web-search terms.

As brain intelligence is added, those brains can refine, verify, rank and
synthesize the same evidence without changing the API gateway.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from vale_connector import VALEConnector
from brain_network import BrainNetwork

from COGNITIVE.cognitive_brain import CognitiveBrain
from LEGEND.legend_brain import LegendBrain
from ALPHA.alpha_brain import AlphaBrain
from MARCO.marco_brain import MarcoBrain
from FEEL.feelings_brain import FeelingsBrain
from HEROIC.heroic_brain import HeroicBrain
from SUPERVISOR.supervisor_brain import SupervisorBrain
from UNITY.unity_brain import UnityBrain
from AI_OS.ai_osgeneration import AiOsGenerationBrain


class VALECore:
    def __init__(self):
        self.name = "VALE AI"
        self.version = "3.1"
        self.status = "ONLINE"

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
        """Main VALE processing pipeline."""

        original_message = (message or "").strip()

        if not original_message:
            return "Please ask me something."

        lower = original_message.lower()

        if lower in {
            "status",
            "system status",
            "are you online",
            "are you working",
        }:
            return self.system_status()

        if any(
            word in lower
            for word in ["who are you", "what are you", "your name"]
        ):
            return (
                "I am VALE AI. My unified brain network is online, and I can use "
                "live Internet research through the shared VALE connector."
            )

        # VALE's own architecture must be answered internally.
        internal_response = self._handle_internal_vale_question(
            original_message
        )

        if internal_response:
            return internal_response

        conversation = conversation or []
        metadata = metadata or {}

        try:
            network_result = self.brain_network.process(
                user_message=original_message,
                conversation=conversation,
                metadata=metadata,
            )
        except Exception as exc:
            return (
                "VALE encountered an internal processing error. "
                f"Details: {type(exc).__name__}: {exc}"
            )

        state = network_result["state"]

        # Future-proof hook: if a brain/synthesis layer produces a final
        # response, use it before the Internet fallback.
        brain_response = self._extract_brain_response(network_result)

        if brain_response:
            state.set("answer_source", "brain_network")
            state.set("final_response", brain_response)
            state.add_message("assistant", brain_response)

            state.event(
                "task_completed",
                "VALE_CORE",
                payload={
                    "response_generated": True,
                    "source": "brain_network",
                    "brain_count": len(self.brains),
                },
            )

            return brain_response

        response = self._internet_fallback(
            original_message,
            network_result.get("internet_results", []),
        )

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

    def _internet_fallback(
        self,
        message: str,
        results: List[Dict[str, Any]],
    ) -> str:
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

        lines = [
            f'VALE — live Internet research for: "{message}"',
            "",
        ]

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

    def _handle_internal_vale_question(
        self,
        message: str,
    ) -> Optional[str]:
        """Answer questions about VALE's own architecture internally."""

        text = message.lower().strip()

        if "legend" in text and any(
            phrase in text
            for phrase in [
                "what is legend",
                "who is legend",
                "tell me about legend",
                "explain legend",
                "legend brain",
                "what does legend do",
                "what is the legend brain",
            ]
        ):
            return (
                "LEGEND is VALE's major Market and Trading Intelligence Brain.\n\n"
                "Its purpose is not simply to predict BUY or SELL. LEGEND "
                "analyzes market conditions, evidence, regimes, historical "
                "behavior, strategies, scenarios, contradictions, confidence, "
                "uncertainty, risk, and decision quality.\n\n"
                "Core LEGEND capabilities include:\n"
                "• Market Data Intelligence\n"
                "• Market DNA Engine\n"
                "• Market Regime Detection\n"
                "• Market Regime Memory\n"
                "• Historical Intelligence\n"
                "• AI Hypothesis Generation\n"
                "• Missing Information Detection\n"
                "• Market Influence Mapping\n"
                "• Market Participant Behavior Analysis\n"
                "• Market Wisdom Engine\n"
                "• Trading Wisdom Library\n"
                "• Strategy Intelligence\n"
                "• Backtesting\n"
                "• Strategy Stress Testing\n"
                "• Scenario Analysis\n"
                "• Evidence and Confidence Analysis\n"
                "• Contradiction Detection\n"
                "• Self-Critique\n"
                "• Decision Quality Analysis\n"
                "• Risk Intelligence\n"
                "• Explainability Timeline\n"
                "• Outcome and Learning Interface\n\n"
                "LEGEND does not guess when critical market information is "
                "missing. Evidence comes before speculation."
            )

        if "alpha" in text and any(
            phrase in text
            for phrase in [
                "what is alpha",
                "who is alpha",
                "alpha brain",
                "what does alpha do",
                "explain alpha",
            ]
        ):
            return (
                "ALPHA is VALE's orchestration and performance brain.\n\n"
                "Its primary responsibility is coordinating cognition "
                "efficiently across VALE's brains while prioritizing:\n"
                "1. Speed and low latency\n"
                "2. Accuracy\n"
                "3. Quality and reliability\n\n"
                "ALPHA is not the overall boss of VALE. It helps coordinate "
                "and optimize the execution of the cognitive system."
            )

        if "heroic" in text and any(
            phrase in text
            for phrase in [
                "what is heroic",
                "who is heroic",
                "heroic brain",
                "what does heroic do",
                "explain heroic",
            ]
        ):
            return (
                "HEROIC is VALE's mission and objective intelligence brain.\n\n"
                "Its role is to understand what the user is actually trying "
                "to accomplish, including the objective behind the literal "
                "request, determine which intelligence is required, and "
                "coordinate the appropriate cognitive capabilities.\n\n"
                "HEROIC is not the overall system boss and does not replace "
                "UNITY, ALPHA, LEGEND, MARCO, FEELING, Supervisor, or the "
                "other specialized systems."
            )

        if "unity" in text and any(
            phrase in text
            for phrase in [
                "what is unity",
                "who is unity",
                "unity brain",
                "what does unity do",
                "explain unity",
            ]
        ):
            return (
                "UNITY is VALE's highest-level integration brain.\n\n"
                "It connects and synthesizes the outputs of VALE's different "
                "cognitive systems into one coherent VALE state and one final "
                "answer.\n\n"
                "UNITY is the integration layer, not a replacement for "
                "specialized intelligence such as LEGEND, MARCO, FEELING, "
                "or the Reasoning and Knowledge systems."
            )

        if "marco" in text and any(
            phrase in text
            for phrase in [
                "what is marco",
                "who is marco",
                "marco brain",
                "what does marco do",
                "explain marco",
            ]
        ):
            return (
                "MARCO is one of VALE's major general and future-intelligence "
                "brains.\n\n"
                "Its detailed internal architecture is still being "
                "progressively designed and refined. It is separate from "
                "LEGEND, ALPHA, HEROIC, UNITY, FEELING, and Supervisor."
            )

        if (
            ("feeling" in text or "feelings brain" in text)
            and any(
                phrase in text
                for phrase in [
                    "what is feeling",
                    "what is feelings",
                    "who is feeling",
                    "feeling brain",
                    "what does feeling do",
                    "explain feeling",
                ]
            )
        ):
            return (
                "FEELING is VALE's human-oriented cognitive intelligence.\n\n"
                "It is designed to help VALE understand human experience, "
                "emotional context, perspective, imagination, intent, and "
                "human-centered meaning.\n\n"
                "FEELING does not mean VALE literally becomes human or "
                "claims to experience emotions as a human does."
            )

        if "supervisor" in text and any(
            phrase in text
            for phrase in [
                "what is supervisor",
                "who is supervisor",
                "supervisor brain",
                "what does supervisor do",
                "explain supervisor",
            ]
        ):
            return (
                "SUPERVISOR is VALE's continuous supervision and system-health "
                "intelligence.\n\n"
                "It monitors brain behavior, failures, conflicts, coordination "
                "problems, dependencies, and recovery conditions.\n\n"
                "SUPERVISOR is not a replacement for UNITY, HEROIC, ALPHA, "
                "LEGEND, MARCO, or FEELING."
            )

        if "cognitive" in text and any(
            phrase in text
            for phrase in [
                "what is cognitive",
                "cognitive brain",
                "what does cognitive do",
                "explain cognitive",
            ]
        ):
            return (
                "COGNITIVE is VALE's supporting cognitive-system foundation.\n\n"
                "It provides shared cognitive infrastructure such as state, "
                "communication, context, evidence, reasoning foundations, "
                "and coordination support for the larger VALE architecture."
            )

        if (
            ("ai os" in text or "ai_os" in text or "generation ai os" in text)
            and any(
                phrase in text
                for phrase in [
                    "what is ai os",
                    "what is ai_os",
                    "what is generation ai os",
                    "ai os brain",
                    "what does ai os do",
                    "explain ai os",
                ]
            )
        ):
            return (
                "The Generation AI OS layer is VALE's broader operating "
                "foundation for the cognitive lifecycle: Understand, Think, "
                "Verify, Decide, Execute, Observe, Learn, and Evolve."
            )

        if any(
            phrase in text
            for phrase in [
                "what is vale",
                "who is vale",
                "what is vale ai",
                "vale ai",
                "vale architecture",
            ]
        ):
            return (
                "VALE is one coherent AI and cognitive system, not a collection "
                "of disconnected chatbots. Its architecture combines UNITY, "
                "HEROIC, Supervisor, ALPHA, LEGEND, MARCO, FEELING, and shared "
                "supporting systems such as Cognitive Fabric, Memory, Knowledge, "
                "Reasoning, Evolution, MCVL, and the Unity Cell Fabric."
            )

        return None

    def _extract_brain_response(
        self,
        network_result: Dict[str, Any],
    ) -> Optional[str]:
        """Extract a final response if a brain/synthesis layer provides one."""

        if not isinstance(network_result, dict):
            return None

        for key in [
            "response",
            "answer",
            "final_response",
            "synthesis",
        ]:
            value = network_result.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        state = network_result.get("state")

        if state is not None:
            try:
                for key in [
                    "final_response",
                    "answer",
                    "response",
                ]:
                    value = state.get(key)

                    if isinstance(value, str) and value.strip():
                        return value.strip()
            except Exception:
                pass

        return None

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
            f"Internet (Exa) configured: "
            f"{'YES' if internet_ok else 'NO — EXA_API_KEY not set'}\n"
            f"Checked: {datetime.now(timezone.utc).isoformat()}"
        )


vale = VALECore()
