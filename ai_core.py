"""
VALE AI CORE
============

Main VALE application/core gateway.

Architecture:

    User
      |
      v
    Generation AI OS
      |
      v
    Brain Network
      |
      v
    UNITY
      |
      v
    HEROIC / ALPHA / required specialized brains
      |
      v
    Verification
      |
      v
    UNITY synthesis
      |
      v
    VALE response

Generation AI OS is infrastructure, NOT a specialized brain.

The AI core deliberately does NOT perform a universal Internet search.
External information is requested only when the task planner determines
that it is required.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


from vale_connector import VALEConnector
from brain_network import BrainNetwork
from AI_OS.ai_osgeneration import GenerationAIOS


from COGNITIVE.cognitive_brain import CognitiveBrain
from LEGEND.legend_brain import LegendBrain
from ALPHA.alpha_brain import AlphaBrain
from MARCO.marco_brain import MarcoBrain
from FEEL.feelings_brain import FeelingsBrain
from HEROIC.heroic_brain import HeroicBrain
from SUPERVISOR.supervisor_brain import SupervisorBrain
from UNITY.unity_brain import UnityBrain


class VALECore:

    VERSION = "4.0"

    def __init__(self):

        self.name = "VALE AI"
        self.version = self.VERSION
        self.status = "ONLINE"

        # --------------------------------------------------------------
        # Shared external connector
        # --------------------------------------------------------------

        self.connector = VALEConnector()

        # --------------------------------------------------------------
        # Generation AI OS
        #
        # This is infrastructure around the brains.
        # It is intentionally NOT registered in BrainNetwork.
        # --------------------------------------------------------------

        self.ai_os = GenerationAIOS(
            connector=self.connector,
        )

        # --------------------------------------------------------------
        # Brain Network
        # --------------------------------------------------------------

        self.brain_network = BrainNetwork(
            connector=self.connector,
        )

        # --------------------------------------------------------------
        # Specialized / cognitive brains
        #
        # These remain separate components.
        # --------------------------------------------------------------

        self.brains = [
            CognitiveBrain(
                self.connector
            ),
            LegendBrain(
                self.connector
            ),
            AlphaBrain(
                self.connector
            ),
            MarcoBrain(
                self.connector
            ),
            FeelingsBrain(
                self.connector
            ),
            HeroicBrain(
                self.connector
            ),
            SupervisorBrain(
                self.connector
            ),
            UnityBrain(
                self.connector
            ),
        ]

        # --------------------------------------------------------------
        # Register available brains.
        #
        # Registration means AVAILABLE.
        # It does NOT mean RUN ON EVERY REQUEST.
        # --------------------------------------------------------------

        for brain in self.brains:
            self.brain_network.register(
                brain
            )

    # ==================================================================
    # PUBLIC PROCESSING
    # ==================================================================

    def process(
        self,
        message: str,
        conversation: Optional[
            List[Dict[str, Any]]
        ] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> str:

        original_message = (
            message or ""
        ).strip()

        if not original_message:
            return "Please ask me something."

        lower = original_message.lower().strip()

        # --------------------------------------------------------------
        # Basic system commands
        # --------------------------------------------------------------

        if lower in {
            "status",
            "system status",
            "are you online",
            "are you working",
        }:

            return self.system_status()

        # --------------------------------------------------------------
        # Identity
        # --------------------------------------------------------------

        if any(
            phrase in lower
            for phrase in [
                "who are you",
                "what are you",
                "your name",
            ]
        ):

            return (
                "I am VALE AI — one coherent AI and cognitive "
                "system. My Generation AI OS provides the operating "
                "architecture around my specialized brains, including "
                "UNITY, HEROIC, ALPHA, LEGEND, MARCO, FEELING, "
                "Supervisor, and the supporting cognitive systems."
            )

        # --------------------------------------------------------------
        # Internal VALE architecture questions
        #
        # These must be answered before external research.
        # --------------------------------------------------------------

        internal_response = (
            self._handle_internal_vale_question(
                original_message
            )
        )

        if internal_response:
            return internal_response

        conversation = (
            conversation or []
        )

        metadata = (
            metadata or {}
        )

        # --------------------------------------------------------------
        # Generation AI OS prepares the lifecycle.
        # --------------------------------------------------------------

        try:

            self.ai_os.begin_task(
                original_message,
                metadata=metadata,
            )

        except Exception:
            # The OS preparation is intentionally non-destructive.
            # The BrainNetwork remains the authoritative task runtime.
            pass

        # --------------------------------------------------------------
        # Dynamic brain-network processing
        # --------------------------------------------------------------

        try:

            network_result = (
                self.brain_network.process(
                    user_message=original_message,
                    conversation=conversation,
                    metadata=metadata,
                )
            )

        except Exception as exc:

            return (
                "VALE encountered an internal processing error. "
                f"Details: {type(exc).__name__}: {exc}"
            )

        state = network_result.get(
            "state"
        )

        # --------------------------------------------------------------
        # Try to obtain a response from the cognitive results.
        # --------------------------------------------------------------

        brain_response = (
            self._extract_brain_response(
                network_result
            )
        )

        if brain_response:

            if state is not None:

                state.set(
                    "answer_source",
                    "brain_network",
                )

                state.set(
                    "final_response",
                    brain_response,
                )

                state.add_message(
                    "assistant",
                    brain_response,
                )

                state.event(
                    "task_completed",
                    "VALE_CORE",
                    payload={
                        "response_generated": True,
                        "source": "brain_network",
                        "active_brains": network_result.get(
                            "selected_brains",
                            [],
                        ),
                    },
                )

            return brain_response

        # --------------------------------------------------------------
        # If selected brains did not generate a final natural-language
        # answer, use external evidence ONLY if the planner requested it.
        # --------------------------------------------------------------

        internet_results = (
            network_result.get(
                "internet_results",
                [],
            )
        )

        if internet_results:

            response = (
                self._internet_evidence_response(
                    original_message,
                    internet_results,
                )

            if state is not None:

                state.set(
                    "answer_source",
                    "external_evidence",
                )

                state.set(
                    "final_response",
                    response,
                )

                state.add_message(
                    "assistant",
                    response,
                )

                state.event(
                    "task_completed",
                    "VALE_CORE",
                    payload={
                        "response_generated": bool(
                            response
                        ),
                        "source": "external_evidence",
                        "active_brains": network_result.get(
                            "selected_brains",
                            [],
                        ),
                    },
                )

            return response

        # --------------------------------------------------------------
        # No brain generated a natural-language answer and no external
        # evidence was requested.
        #
        # Do NOT secretly perform Internet search here.
        # --------------------------------------------------------------

        response = (
            self._build_no_external_answer(
                original_message,
                network_result,
            )
        )

        if state is not None:

            state.set(
                "answer_source",
                "cognitive_pipeline",
            )

            state.set(
                "final_response",
                response,
            )

            state.add_message(
                "assistant",
                response,
            )

            state.event(
                "task_completed",
                "VALE_CORE",
                payload={
                    "response_generated": True,
                    "source": "cognitive_pipeline",
                    "active_brains": network_result.get(
                        "selected_brains",
                        [],
                    ),
                },
            )

        return response

    # ==================================================================
    # RESPONSE EXTRACTION
    # ==================================================================

    def _extract_brain_response(
        self,
        network_result: Dict[str, Any],
    ) -> Optional[str]:

        if not isinstance(
            network_result,
            dict,
        ):
            return None

        # --------------------------------------------------------------
        # Direct response fields
        # --------------------------------------------------------------

        for key in [
            "response",
            "answer",
            "final_response",
            "synthesis",
        ]:

            value = network_result.get(
                key
            )

            if (
                isinstance(
                    value,
                    str,
                )
                and value.strip()
            ):

                return value.strip()

        # --------------------------------------------------------------
        # State-level response
        # --------------------------------------------------------------

        state = network_result.get(
            "state"
        )

        if state is not None:

            try:

                for key in [
                    "final_response",
                    "answer",
                    "response",
                    "synthesis",
                ]:

                    value = state.get(
                        key
                    )

                    if (
                        isinstance(
                            value,
                            str,
                        )
                        and value.strip()
                    ):

                        return value.strip()

            except Exception:
                pass

        # --------------------------------------------------------------
        # Brain-result response extraction
        # --------------------------------------------------------------

        results = network_result.get(
            "results",
            {}
        )

        if isinstance(
            results,
            dict,
        ):

            # UNITY gets highest priority because it is the
            # system-level synthesis layer.
            priority = [
                "UNITY",
                "HEROIC",
                "ALPHA",
                "LEGEND",
                "MARCO",
                "FEELING",
                "FEELINGS",
                "COGNITIVE",
            ]

            ordered_names = []

            for name in priority:

                if name in results:
                    ordered_names.append(
                        name
                    )

            for name in results:

                if name not in ordered_names:
                    ordered_names.append(
                        name
                    )

            for name in ordered_names:

                wrapper = results.get(
                    name
                )

                if not isinstance(
                    wrapper,
                    dict,
                ):
                    continue

                result = wrapper.get(
                    "result"
                )

                if isinstance(
                    result,
                    str,
                ) and result.strip():

                    return result.strip()

                if isinstance(
                    result,
                    dict,
                ):

                    for key in [
                        "response",
                        "answer",
                        "final_response",
                        "synthesis",
                        "message",
                    ]:

                        value = result.get(
                            key
                        )

                        if (
                            isinstance(
                                value,
                                str,
                            )
                            and value.strip()
                        ):

                            # Avoid returning the generic foundation
                            # status message as if it were a real answer.
                            if (
                                key == "message"
                                and "brain is connected"
                                in value.lower()
                            ):
                                continue

                            return value.strip()

        return None

    # ==================================================================
    # EXTERNAL EVIDENCE RESPONSE
    # ==================================================================

    def _internet_evidence_response(
        self,
        message: str,
        results: List[Dict[str, Any]],
    ) -> str:

        if not results:

            return (
                f'VALE determined that fresh external information '
                f'was required for "{message}", but no usable external '
                "evidence was returned."
            )

        lines = [
            f'VALE — external evidence for: "{message}"',
            "",
            (
                "The following information was acquired because "
                "the task required fresh external information:"
            ),
            "",
        ]

        shown = 0

        for item in results:

            if not isinstance(
                item,
                dict,
            ):
                continue

            title = (
                item.get(
                    "title"
                )
                or ""
            ).strip()

            url = (
                item.get(
                    "url"
                )
                or ""
            ).strip()

            highlights = (
                item.get(
                    "highlights"
                )
                or []
            )

            if not title and not url:
                continue

            shown += 1

            lines.append(
                f"{shown}. {title or url}"
            )

            if url:
                lines.append(
                    f"   Source: {url}"
                )

            for highlight in highlights[:3]:

                text = (
                    highlight or ""
                ).strip()

                if text:
                    lines.append(
                        f"   • {text}"
                    )

            lines.append("")

        if shown == 0:

            return (
                f'VALE acquired external information for "{message}", '
                "but the returned evidence was not usable."
            )

        lines.append(
            "Note: external search results are evidence candidates, "
            "not automatically verified truth. Full MCVL/source "
            "verification can be expanded as the verification system "
            "is implemented."
        )

        return "\n".join(
            lines
        ).strip()

    # ==================================================================
    # NO EXTERNAL ANSWER
    # ==================================================================

    def _build_no_external_answer(
        self,
        message: str,
        network_result: Dict[str, Any],
    ) -> str:

        selected = network_result.get(
            "selected_brains",
            [],
        )

        task_plan = network_result.get(
            "task_plan",
            {},
        )

        task_type = task_plan.get(
            "task_type",
            "GENERAL",
        )

        if not selected:

            return (
                "VALE understood the request but no suitable "
                "cognitive capability is currently available for "
                "this task."
            )

        # This is intentionally honest. The current foundation brains
        # may return READY/connected states without producing a real
        # natural-language reasoning answer.
        return (
            "VALE processed the request through its dynamic cognitive "
            "pipeline.\n\n"
            f"Task type: {task_type}\n"
            f"Activated brains: {', '.join(selected)}\n\n"
            "The currently activated brain foundations did not produce "
            "a final natural-language answer. No universal Internet "
            "search was performed because this task was not classified "
            "as requiring external information.\n\n"
            "This is an intentional architectural behavior: VALE does "
            "not manufacture an answer or silently search the Internet "
            "when the required internal intelligence is not yet available."
        )

    # ==================================================================
    # INTERNAL VALE ARCHITECTURE
    # ==================================================================

    def _handle_internal_vale_question(
        self,
        message: str,
    ) -> Optional[str]:

        text = message.lower().strip()

        # --------------------------------------------------------------
        # LEGEND
        # --------------------------------------------------------------

        if (
            "legend" in text
            and any(
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
            )
        ):

            return (
                "LEGEND is VALE's major Market and Trading Intelligence "
                "Brain.\n\n"
                "Its purpose is not simply to predict BUY or SELL. "
                "LEGEND is designed to understand markets using evidence, "
                "market structure, regimes, historical behavior, "
                "participant behavior, strategies, scenarios, "
                "contradictions, uncertainty, risk and decision quality.\n\n"
                "Core LEGEND architecture includes:\n"
                "• Market Data Intelligence\n"
                "• Market DNA Engine\n"
                "• Market Regime Detection\n"
                "• Market Regime Memory\n"
                "• Historical Intelligence\n"
                "• Hypothesis Generation\n"
                "• Market Behavior Engine\n"
                "• Influence Mapping\n"
                "• Market Participant Behavior\n"
                "• Market Wisdom Engine\n"
                "• Trading Wisdom Library\n"
                "• Strategy Intelligence\n"
                "• Backtesting\n"
                "• Stress Testing\n"
                "• Scenario Analysis\n"
                "• Evidence / Provenance\n"
                "• Confidence / Uncertainty\n"
                "• Contradiction Detection\n"
                "• Self-Critique\n"
                "• Decision Quality Analysis\n"
                "• Risk Intelligence\n"
                "• Explainability\n"
                "• Learning / Outcome Analysis\n\n"
                "LEGEND does not manufacture certainty. If critical "
                "market information is missing, stale or contradictory, "
                "the system must explicitly recognize that limitation."
            )

        # --------------------------------------------------------------
        # ALPHA
        # --------------------------------------------------------------

        if (
            "alpha" in text
            and any(
                phrase in text
                for phrase in [
                    "what is alpha",
                    "who is alpha",
                    "alpha brain",
                    "what does alpha do",
                    "explain alpha",
                ]
            )
        ):

            return (
                "ALPHA is VALE's orchestration and performance brain.\n\n"
                "Its role is to execute the cognitive work selected by "
                "the system efficiently, with emphasis on speed, "
                "accuracy, reliability and appropriate reasoning depth.\n\n"
                "ALPHA is not VALE's overall boss. UNITY provides "
                "system-level integration, while HEROIC determines the "
                "mission/objective requirements and specialized brains "
                "provide domain intelligence."
            )

        # --------------------------------------------------------------
        # HEROIC
        # --------------------------------------------------------------

        if (
            "heroic" in text
            and any(
                phrase in text
                for phrase in [
                    "what is heroic",
                    "who is heroic",
                    "heroic brain",
                    "what does heroic do",
                    "explain heroic",
                ]
            )
        ):

            return (
                "HEROIC is VALE's Mission and Objective Intelligence "
                "Brain.\n\n"
                "HEROIC determines what the user is actually trying "
                "to accomplish, including the objective behind the "
                "literal request, the required capabilities, constraints, "
                "priority, urgency, reasoning depth and relevant "
                "intelligence.\n\n"
                "HEROIC is not the overall system boss. UNITY remains "
                "the highest-level integration layer."
            )

        # --------------------------------------------------------------
        # UNITY
        # --------------------------------------------------------------

        if (
            "unity" in text
            and any(
                phrase in text
                for phrase in [
                    "what is unity",
                    "who is unity",
                    "unity brain",
                    "what does unity do",
                    "explain unity",
                ]
            )
        ):

            return (
                "UNITY is VALE's highest-level Integration Brain.\n\n"
                "UNITY exists to make VALE operate as one coherent "
                "cognitive system. It maintains shared context, "
                "coordinates system-level information flow, integrates "
                "different cognitive outputs and produces a coherent "
                "VALE state and final synthesis.\n\n"
                "UNITY is not simply the 'smartest' brain and does not "
                "replace specialized intelligence."
            )

        # --------------------------------------------------------------
        # MARCO
        # --------------------------------------------------------------

        if (
            "marco" in text
            and any(
                phrase in text
                for phrase in [
                    "what is marco",
                    "who is marco",
                    "marco brain",
                    "what does marco do",
                    "explain marco",
                ]
            )
        ):

            return (
                "MARCO is one of VALE's major general and future "
                "intelligence brains.\n\n"
                "Its detailed internal architecture is still being "
                "progressively designed and refined. It remains separate "
                "from UNITY, HEROIC, ALPHA, LEGEND, FEELING and Supervisor."
            )

        # --------------------------------------------------------------
        # FEELING
        # --------------------------------------------------------------

        if (
            (
                "feeling" in text
                or "feelings brain" in text
            )
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
                "FEELING is VALE's Human Experience Brain.\n\n"
                "It is designed to give VALE computational understanding "
                "of human experience, emotional context, empathy, human "
                "perspective, intent context, imagination and idea "
                "creation.\n\n"
                "FEELING does not mean VALE literally becomes human or "
                "claims to experience emotions as a human does."
            )

        # --------------------------------------------------------------
        # SUPERVISOR
        # --------------------------------------------------------------

        if (
            "supervisor" in text
            and any(
                phrase in text
                for phrase in [
                    "what is supervisor",
                    "who is supervisor",
                    "supervisor brain",
                    "what does supervisor do",
                    "explain supervisor",
                ]
            )
        ):

            return (
                "SUPERVISOR is VALE's operational guardian.\n\n"
                "Its responsibility is to monitor system health, brain "
                "activity, failures, dependencies, stale data, invalid "
                "states, communication problems, performance and recovery "
                "conditions.\n\n"
                "Supervisor is not a replacement for UNITY, HEROIC, "
                "ALPHA or the specialized intelligence brains."
            )

        # --------------------------------------------------------------
        # COGNITIVE
        # --------------------------------------------------------------

        if (
            "cognitive" in text
            and any(
                phrase in text
                for phrase in [
                    "what is cognitive",
                    "cognitive brain",
                    "what does cognitive do",
                    "explain cognitive",
                ]
            )
        ):

            return (
                "COGNITIVE is VALE's supporting cognitive-system "
                "foundation.\n\n"
                "It provides infrastructure and capabilities supporting "
                "shared cognitive state, communication, context, "
                "evidence, reasoning foundations, uncertainty and "
                "verification for the wider VALE architecture.\n\n"
                "It is supporting infrastructure rather than the "
                "overall system boss."
            )

        # --------------------------------------------------------------
        # Generation AI OS
        # --------------------------------------------------------------

        if (
            (
                "ai os" in text
                or "ai_os" in text
                or "generation ai os" in text
            )
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
                "Generation AI OS is VALE's underlying cognitive "
                "operating architecture, not another specialized brain.\n\n"
                "It provides the lifecycle and infrastructure through "
                "which VALE's cognitive components operate: "
                "Understand → Think → Verify → Decide → Execute → "
                "Observe → Learn → Evolve.\n\n"
                "It supports shared state, context, routing, communication, "
                "memory, knowledge, reasoning, verification, safety, "
                "observability and evolution around the specialized "
                "brains."
            )

        # --------------------------------------------------------------
        # Brain Network
        # --------------------------------------------------------------

        if (
            "brain network" in text
            and any(
                phrase in text
                for phrase in [
                    "what is brain network",
                    "how does brain network work",
                    "how are brains connected",
                    "how brains are connected",
                    "brain connection",
                    "connect brains",
                ]
            )
        ):

            return (
                "VALE's Brain Network is the shared communication and "
                "execution infrastructure connecting the brains.\n\n"
                "Brains can communicate through shared task state and "
                "brain-to-brain messaging. Importantly, registration does "
                "not mean every brain runs on every request. The network "
                "selects the brains required for the current task.\n\n"
                "The intended flow is UNITY → HEROIC → determine required "
                "capabilities → ALPHA → selected specialized cognition → "
                "verification → UNITY synthesis."
            )

        # --------------------------------------------------------------
        # VALE
        # --------------------------------------------------------------

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
                "VALE is one coherent AI and cognitive system, not a "
                "collection of disconnected chatbots.\n\n"
                "Its architecture combines Generation AI OS, UNITY, "
                "HEROIC, ALPHA, LEGEND, MARCO, FEELING, Supervisor and "
                "supporting cognitive infrastructure such as Cognitive "
                "Fabric, Memory, Knowledge, Reasoning, MCVL, Safety, "
                "Observability, Learning and Evolution.\n\n"
                "The brains are specialized components. Generation AI OS "
                "provides the operating architecture, while UNITY "
                "integrates the system into one coherent VALE state."
            )

        return None

    # ==================================================================
    # STATUS
    # ==================================================================

    def brain_status(
        self,
    ) -> Dict[str, Any]:

        return self.brain_network.status()

    def system_status(
        self,
    ) -> str:

        internet_ok = (
            self.connector.internet_available()
        )

        network = (
            self.brain_network.status()
        )

        return (
            f"VALE AI Status: {self.status}\n"
            f"Version: {self.version}\n"
            f"Generation AI OS: ONLINE\n"
            f"Brain Network: ONLINE\n"
            f"Brains Available: {network['brain_count']}\n"
            f"Brains: {', '.join(network['brains'])}\n"
            f"Dynamic Brain Selection: YES\n"
            f"Universal Internet Search: NO\n"
            f"Conditional External Research: YES\n"
            f"Brain-to-Brain Communication: YES\n"
            f"Shared Brain State: YES\n"
            f"Shared Connector: YES\n"
            f"Generation AI OS Registered As Brain: NO\n"
            f"Internet (Exa) configured: "
            f"{'YES' if internet_ok else 'NO — EXA_API_KEY not set'}\n"
            f"Checked: "
            f"{datetime.now(timezone.utc).isoformat()}"
        )


vale = VALECore()
