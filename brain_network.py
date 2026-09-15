"""
VALE Brain Network
==================

Dynamic cognitive orchestration layer for VALE.

Important architectural rule:

    REGISTERED BRAIN != ACTIVE BRAIN

A brain is registered because it exists and is available.
A brain is executed only when the current task requires it.

The network provides:

    - shared task state
    - brain registration
    - brain-to-brain communication
    - capability-aware task planning
    - dynamic brain selection
    - optional Internet research
    - selected-brain execution
    - verification hooks
    - UNITY synthesis hooks
    - operational telemetry

Generation AI OS is NOT treated as a specialized brain here.
It is the operating/infrastructure layer around this network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional, Set


from brain_state import VALEBrainState
from vale_connector import VALEConnector


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BrainNetwork:

    NETWORK_VERSION = "2.0"

    # ------------------------------------------------------------------
    # Brain categories
    # ------------------------------------------------------------------

    CORE_BRAINS = {
        "UNITY",
        "HEROIC",
        "ALPHA",
    }

    SPECIALIZED_BRAINS = {
        "LEGEND",
        "MARCO",
        "FEELING",
        "FEELINGS",
    }

    SUPPORTING_BRAINS = {
        "COGNITIVE",
    }

    OPERATIONAL_BRAINS = {
        "SUPERVISOR",
    }

    # ------------------------------------------------------------------
    # Capability mapping
    # ------------------------------------------------------------------

    CAPABILITY_TO_BRAINS = {
        "integration": {"UNITY"},
        "objective_intelligence": {"HEROIC"},
        "orchestration": {"ALPHA"},
        "performance": {"ALPHA"},
        "market_intelligence": {"LEGEND"},
        "trading_intelligence": {"LEGEND"},
        "market_data": {"LEGEND"},
        "strategy_intelligence": {"LEGEND"},
        "general_reasoning": {"MARCO"},
        "cross_domain_reasoning": {"MARCO"},
        "human_understanding": {"FEELING", "FEELINGS"},
        "emotional_context": {"FEELING", "FEELINGS"},
        "human_perspective": {"FEELING", "FEELINGS"},
        "cognitive_support": {"COGNITIVE"},
        "verification": {"COGNITIVE"},
        "system_monitoring": {"SUPERVISOR"},
    }

    # ------------------------------------------------------------------
    # Keyword routing
    # ------------------------------------------------------------------

    MARKET_KEYWORDS = {
        "btc",
        "bitcoin",
        "crypto",
        "cryptocurrency",
        "ethereum",
        "eth",
        "solana",
        "sol",
        "stock",
        "stocks",
        "share",
        "shares",
        "market",
        "markets",
        "trading",
        "trade",
        "trader",
        "forex",
        "price",
        "prices",
        "chart",
        "technical analysis",
        "market structure",
        "liquidity",
        "volatility",
        "regime",
        "support",
        "resistance",
        "portfolio",
        "strategy",
        "backtest",
        "backtesting",
        "drawdown",
    }

    HUMAN_KEYWORDS = {
        "feel",
        "feeling",
        "feelings",
        "emotion",
        "emotional",
        "relationship",
        "girlfriend",
        "boyfriend",
        "love",
        "romantic",
        "message",
        "apology",
        "apologize",
        "sorry",
        "sad",
        "angry",
        "frustrated",
        "confused",
        "anxious",
        "perspective",
        "empathy",
        "human",
    }

    GENERAL_REASONING_KEYWORDS = {
        "why",
        "explain",
        "compare",
        "reason",
        "reasoning",
        "analyze",
        "analysis",
        "logic",
        "cause",
        "causal",
        "problem",
        "decision",
        "plan",
        "design",
        "architecture",
        "system",
        "research",
        "evaluate",
        "evaluate",
        "pros",
        "cons",
    }

    # Questions that normally require fresh external information.
    EXTERNAL_INFORMATION_KEYWORDS = {
        "today",
        "today's",
        "now",
        "right now",
        "currently",
        "current",
        "latest",
        "recent",
        "news",
        "this week",
        "this month",
        "yesterday",
        "tomorrow",
        "live",
        "real time",
        "realtime",
        "price",
        "prices",
        "weather",
        "score",
        "scores",
        "election",
        "outage",
    }

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        connector: VALEConnector,
        max_brain_rounds: int = 3,
        max_events_per_task: int = 500,
    ):
        self.connector = connector

        self.brains: Dict[str, Any] = {}
        self.tasks: Dict[str, VALEBrainState] = {}

        self.max_brain_rounds = max(1, int(max_brain_rounds))
        self.max_events_per_task = max(50, int(max_events_per_task))

        self._lock = RLock()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, brain: Any) -> Any:
        if brain is None:
            raise ValueError("Cannot register an empty brain.")

        name = str(
            getattr(brain, "brain_name", "")
            or getattr(brain, "name", "")
        ).strip().upper()

        if not name:
            raise ValueError(
                "Brain must expose brain_name or name."
            )

        with self._lock:
            if name in self.brains:
                raise ValueError(
                    f"Brain '{name}' is already registered."
                )

            self.brains[name] = brain

            attach = getattr(brain, "attach_network", None)

            if callable(attach):
                attach(self)

        return brain

    def unregister(self, brain_name: str) -> bool:
        name = brain_name.strip().upper()

        with self._lock:
            return self.brains.pop(name, None) is not None

    def get_brain(
        self,
        brain_name: str,
    ) -> Optional[Any]:

        return self.brains.get(
            brain_name.strip().upper()
        )

    def brain_names(self) -> List[str]:
        with self._lock:
            return list(self.brains.keys())

    # ------------------------------------------------------------------
    # Task state
    # ------------------------------------------------------------------

    def create_task(
        self,
        user_message: str,
        conversation: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VALEBrainState:

        state = VALEBrainState(
            user_message=user_message,
            conversation=conversation,
            metadata=metadata,
        )

        state.set(
            "network_version",
            self.NETWORK_VERSION,
        )

        state.set(
            "registered_brains",
            self.brain_names(),
        )

        state.set(
            "active_brains",
            [],
        )

        state.set(
            "internet_research_performed",
            False,
        )

        state.set(
            "external_information_required",
            False,
        )

        state.event(
            "task_created",
            "VALE_NETWORK",
            payload={
                "task_id": state.task_id,
                "registered_brain_count": len(self.brains),
            },
        )

        with self._lock:
            self.tasks[state.task_id] = state

        return state

    def get_task(
        self,
        task_id: str,
    ) -> Optional[VALEBrainState]:

        with self._lock:
            return self.tasks.get(task_id)

    def close_task(
        self,
        task_id: str,
    ) -> Optional[VALEBrainState]:

        with self._lock:
            return self.tasks.pop(task_id, None)

    # ------------------------------------------------------------------
    # Brain communication
    # ------------------------------------------------------------------

    def ask(
        self,
        source_brain: str,
        target_brain: str,
        message: str,
        state: VALEBrainState,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        source = source_brain.strip().upper()
        target = target_brain.strip().upper()

        target_instance = self.get_brain(target)

        if target_instance is None:

            state.event(
                "brain_message_failed",
                source,
                target,
                {
                    "reason": "target_brain_not_found",
                    "message": message,
                },
            )

            return {
                "success": False,
                "source": source,
                "target": target,
                "error": (
                    f"Brain '{target}' is not registered."
                ),
            }

        state.event(
            "brain_message",
            source,
            target,
            {
                "message": message,
                "data": payload or {},
            },
        )

        receive = getattr(
            target_instance,
            "receive_message",
            None,
        )

        if not callable(receive):

            return {
                "success": False,
                "source": source,
                "target": target,
                "error": (
                    f"Brain '{target}' does not "
                    "implement receive_message()."
                ),
            }

        try:

            result = receive(
                message=message,
                state=state,
                source_brain=source,
                payload=payload or {},
            )

            state.event(
                "brain_message_completed",
                target,
                source,
                {
                    "message": message,
                },
            )

            return {
                "success": True,
                "source": source,
                "target": target,
                "result": result,
            }

        except Exception as exc:

            state.event(
                "brain_message_error",
                target,
                source,
                {
                    "error": str(exc),
                },
            )

            return {
                "success": False,
                "source": source,
                "target": target,
                "error": str(exc),
            }

    def broadcast(
        self,
        source_brain: str,
        message: str,
        state: VALEBrainState,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        source = source_brain.strip().upper()

        return {
            name: self.ask(
                source,
                name,
                message,
                state,
                payload,
            )
            for name in self.brain_names()
            if name != source
        }

    # ------------------------------------------------------------------
    # Brain execution
    # ------------------------------------------------------------------

    def run_brain(
        self,
        brain_name: str,
        state: VALEBrainState,
    ) -> Dict[str, Any]:

        name = brain_name.strip().upper()

        brain = self.get_brain(name)

        if brain is None:

            return {
                "success": False,
                "brain": name,
                "error": "Brain not registered.",
            }

        think = getattr(
            brain,
            "think",
            None,
        )

        if not callable(think):

            return {
                "success": False,
                "brain": name,
                "error": (
                    "Brain does not implement think()."
                ),
            }

        state.event(
            "brain_think_started",
            name,
        )

        try:

            result = think(state)

            state.event(
                "brain_think_completed",
                name,
            )

            return {
                "success": True,
                "brain": name,
                "result": result,
            }

        except Exception as exc:

            state.event(
                "brain_think_error",
                name,
                payload={
                    "error": str(exc),
                },
            )

            return {
                "success": False,
                "brain": name,
                "error": str(exc),
            }

    def run_selected(
        self,
        brain_names: List[str],
        state: VALEBrainState,
    ) -> Dict[str, Any]:

        results: Dict[str, Any] = {}

        active: List[str] = []

        for raw_name in brain_names:

            name = str(raw_name).strip().upper()

            if not name:
                continue

            if name not in self.brains:
                state.event(
                    "brain_selection_skipped",
                    "VALE_NETWORK",
                    payload={
                        "brain": name,
                        "reason": "not_registered",
                    },
                )
                continue

            if name not in active:
                active.append(name)

            results[name] = self.run_brain(
                name,
                state,
            )

        state.set(
            "active_brains",
            active,
        )

        state.event(
            "selected_brains_completed",
            "VALE_NETWORK",
            payload={
                "brains": active,
                "count": len(active),
            },
        )

        return results

    def run_all(
        self,
        state: VALEBrainState,
    ) -> Dict[str, Any]:

        """
        Diagnostic/testing method only.

        This deliberately remains available so existing integration
        tests do not break.

        Production processing MUST use run_selected().
        """

        state.event(
            "run_all_requested",
            "VALE_NETWORK",
            payload={
                "warning": (
                    "run_all is a diagnostic method and is "
                    "not the normal cognitive pipeline."
                ),
            },
        )

        return {
            name: self.run_brain(
                name,
                state,
            )
            for name in self.brain_names()
        }

    # ------------------------------------------------------------------
    # Task understanding
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_text(
        text: str,
    ) -> str:

        return " ".join(
            (text or "").lower().strip().split()
        )

    def _contains_any(
        self,
        text: str,
        keywords: Set[str],
    ) -> bool:

        return any(
            keyword in text
            for keyword in keywords
        )

    def _is_internal_vale_question(
        self,
        text: str,
    ) -> bool:

        internal_terms = {
            "vale",
            "unity",
            "heroic",
            "alpha",
            "legend",
            "marco",
            "feeling",
            "feelings",
            "supervisor",
            "cognitive",
            "generation ai os",
            "ai os",
            "brain network",
            "brain",
            "architecture",
        }

        question_markers = {
            "what is",
            "what does",
            "who is",
            "explain",
            "tell me about",
            "how does",
            "how are",
            "architecture",
            "design",
            "connected",
        }

        return (
            self._contains_any(
                text,
                internal_terms,
            )
            and self._contains_any(
                text,
                question_markers,
            )
        )

    def _requires_external_information(
        self,
        text: str,
    ) -> bool:

        return self._contains_any(
            text,
            self.EXTERNAL_INFORMATION_KEYWORDS,
        )

    def _detect_task_type(
        self,
        text: str,
    ) -> str:

        if self._is_internal_vale_question(text):
            return "VALE_INTERNAL"

        if self._contains_any(
            text,
            self.MARKET_KEYWORDS,
        ):
            return "MARKET_INTELLIGENCE"

        if self._contains_any(
            text,
            self.HUMAN_KEYWORDS,
        ):
            return "HUMAN_CONTEXT"

        if self._contains_any(
            text,
            self.GENERAL_REASONING_KEYWORDS,
        ):
            return "GENERAL_REASONING"

        return "GENERAL"

    # ------------------------------------------------------------------
    # Task planning
    # ------------------------------------------------------------------

    def build_task_plan(
        self,
        state: VALEBrainState,
    ) -> Dict[str, Any]:

        message = state.user_message or ""

        text = self._normalise_text(
            message
        )

        task_type = self._detect_task_type(
            text
        )

        external_required = (
            self._requires_external_information(
                text
            )
        )

        required_capabilities: List[str] = []
        required_brains: List[str] = []
        optional_brains: List[str] = []

        # --------------------------------------------------------------
        # Every normal cognitive task belongs to the unified system.
        # UNITY is therefore the integration entry point.
        # --------------------------------------------------------------

        required_capabilities.append(
            "integration"
        )

        required_brains.append(
            "UNITY"
        )

        # --------------------------------------------------------------
        # Internal VALE questions
        # --------------------------------------------------------------

        if task_type == "VALE_INTERNAL":

            required_capabilities.append(
                "general_reasoning"
            )

            # Internal architecture questions should not need Internet.
            external_required = False

        # --------------------------------------------------------------
        # Market / trading
        # --------------------------------------------------------------

        elif task_type == "MARKET_INTELLIGENCE":

            required_capabilities.extend(
                [
                    "objective_intelligence",
                    "orchestration",
                    "market_intelligence",
                ]
            )

            required_brains.extend(
                [
                    "HEROIC",
                    "ALPHA",
                    "LEGEND",
                ]
            )

            # Cognitive support is useful for evidence,
            # uncertainty and verification.
            optional_brains.append(
                "COGNITIVE"
            )

         # --------------------------------------------------------------
        # Human / emotional context
        # --------------------------------------------------------------

        elif task_type == "HUMAN_CONTEXT":

            required_capabilities.extend(
                [
                    "objective_intelligence",
                    "human_understanding",
                ]
            )

            required_brains.extend(
                [
                    "HEROIC",
                    "FEELING",
                ]
            )

        # --------------------------------------------------------------
        # General reasoning
        # --------------------------------------------------------------

        elif task_type == "GENERAL_REASONING":

            required_capabilities.extend(
                [
                    "objective_intelligence",
                    "general_reasoning",
                ]
            )

            required_brains.extend(
                [
                    "HEROIC",
                    "MARCO",
                ]
            )

        # --------------------------------------------------------------
        # Unknown/general task
        # --------------------------------------------------------------

        else:

            required_capabilities.append(
                "objective_intelligence"
            )

            required_brains.append(
                "HEROIC"
            )

        # --------------------------------------------------------------
        # External information is a capability, not a universal step.
        # --------------------------------------------------------------

        if external_required:

            required_capabilities.append(
                "external_information"
            )

        # --------------------------------------------------------------
        # Verification for information-heavy tasks.
        # --------------------------------------------------------------

        if task_type in {
            "MARKET_INTELLIGENCE",
            "GENERAL_REASONING",
        }:

            required_capabilities.append(
                "verification"
            )

            optional_brains.append(
                "COGNITIVE"
            )

        # --------------------------------------------------------------
        # De-duplicate while preserving order.
        # --------------------------------------------------------------

        required_brains = list(
            dict.fromkeys(
                name.upper()
                for name in required_brains
            )
        )

        optional_brains = list(
            dict.fromkeys(
                name.upper()
                for name in optional_brains
            )
            )

        plan = {
            "task_type": task_type,
            "objective": message,
            "required_capabilities": list(
                dict.fromkeys(
                    required_capabilities
                )
            ),
            "required_brains": required_brains,
            "optional_brains": optional_brains,
            "external_information_required": external_required,
            "verification_required": (
                "verification"
                in required_capabilities
            ),
            "internet_research_allowed": external_required,
            "reasoning_depth": (
                "deep"
                if task_type in {
                    "MARKET_INTELLIGENCE",
                    "GENERAL_REASONING",
                }
                else "normal"
            ),
            "created_at": utc_now(),
        }

        state.set(
            "task_plan",
            plan,
        )

        state.set(
            "task_type",
            task_type,
        )

        state.set(
            "external_information_required",
            external_required,
        )

        state.event(
            "task_plan_created",
            "VALE_NETWORK",
            payload=plan,
        )

        return plan

    # ------------------------------------------------------------------
    # Dynamic selection
    # ------------------------------------------------------------------

    def select_brains(
        self,
        state: VALEBrainState,
        plan: Optional[Dict[str, Any]] = None,
    ) -> List[str]:

        if plan is None:
            plan = state.get(
                "task_plan",
                {},
            )

        selected: List[str] = []

        for name in plan.get(
            "required_brains",
            [],
        ):

            name = str(
                name
            ).strip().upper()

            if (
                name
                and name in self.brains
                and name not in selected
            ):
                selected.append(name)

        # Optional supporting cognition is activated only when available.
        # It is not automatically activated for every task.
        if plan.get(
            "verification_required",
            False,
        ):

            if (
                "COGNITIVE" in self.brains
                and "COGNITIVE" not in selected
            ):
                selected.append(
                    "COGNITIVE"
                )

        state.set(
            "selected_brains",
            selected,
        )

        state.event(
            "brains_selected",
            "VALE_NETWORK",
            payload={
                "selected": selected,
                "count": len(selected),
            },
        )

        return selected

    # ------------------------------------------------------------------
    # Internet / external information
    # ------------------------------------------------------------------

    def research_web(
        self,
        state: VALEBrainState,
        query: str,
        num_results: int = 8,
    ) -> List[Dict[str, Any]]:

        """
        Explicit external-information capability.

        IMPORTANT:

        This function is NOT called automatically for every request.

        The task planner must determine that external information
        is required before production processing calls it.
        """

        if not self.connector.internet_available():

            state.set(
                "internet_available",
                False,
            )

            state.set(
                "internet_research_performed",
                False,
            )

            state.event(
                "internet_research_skipped",
                "VALE_NETWORK",
                payload={
                    "reason": (
                        "connector_not_configured"
                    ),
                },
            )

            return []

        try:

            results = (
                self.connector.search_web(
                    query,
                    num_results=num_results,
                )
                or []
            )

        except Exception as exc:

            state.set(
                "internet_available",
                True,
            )

            state.set(
                "internet_research_performed",
                True,
            )

            state.set(
                "internet_error",
                str(exc),
            )

            state.event(
                "internet_research_error",
                "VALE_NETWORK",
                payload={
                    "error": str(exc),
                },
            )

            return []

        state.set(
            "internet_available",
            True,
        )

        state.set(
            "internet_research_performed",
            True,
        )

        state.set(
            "internet_results",
            results,
        )

        state.set(
            "internet_research_query",
            query,
        )

        state.event(
            "internet_research_completed",
            "VALE_NETWORK",
            payload={
                "result_count": len(results),
                "query": query,
            },
        )

        return results

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify_results(
        self,
        state: VALEBrainState,
        results: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Verification hook.

        The full MCVL system can later replace/extend this method.

        For now it performs structural verification and records
        whether the selected cognitive path completed successfully.
        """

        successful_brains = []
        failed_brains = []

        for name, result in results.items():

            if (
                isinstance(result, dict)
                and result.get("success") is True
            ):
                successful_brains.append(name)
            else:
                failed_brains.append(name)

        verification = {
            "performed": True,
            "verified_brains": successful_brains,
            "failed_brains": failed_brains,
            "all_selected_brains_succeeded": (
                len(failed_brains) == 0
            ),
            "internet_evidence_available": bool(
                state.get(
                    "internet_results",
                    [],
                )
            ),
            "timestamp": utc_now(),
        }

        state.set(
            "verification_result",
            verification,
        )

        state.event(
            "verification_completed",
            "VALE_NETWORK",
            payload=verification,
        )

        return verification

    # ------------------------------------------------------------------
    # Main dynamic process
    # ------------------------------------------------------------------

    def process(
        self,
        user_message: str,
        conversation: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        state = self.create_task(
            user_message,
            conversation,
            metadata,
        )

        state.add_message(
            "user",
            user_message,
        )

        state.set(
            "round",
            1,
        )

        # --------------------------------------------------------------
        # 1. Understand task
        # --------------------------------------------------------------

        plan = self.build_task_plan(
            state
        )

        # --------------------------------------------------------------
        # 2. External information is conditional.
        # --------------------------------------------------------------

        internet_results: List[
            Dict[str, Any]
        ] = []

        if plan.get(
            "external_information_required",
            False,
        ):

            internet_results = self.research_web(
                state,
                user_message,
                num_results=8,
            )

        else:

            state.set(
                "internet_results",
                [],
            )

            state.set(
                "internet_research_performed",
                False,
            )

            state.event(
                "internet_research_not_required",
                "VALE_NETWORK",
                payload={
                    "task_type": plan.get(
                        "task_type"
                    ),
                },
            )

        # --------------------------------------------------------------
        # 3. Select only required brains.
        # --------------------------------------------------------------

        selected_brains = self.select_brains(
            state,
            plan,
        )

        # --------------------------------------------------------------
        # 4. Execute selected brains.
        # --------------------------------------------------------------

        results = self.run_selected(
            selected_brains,
            state,
        )

        # --------------------------------------------------------------
        # 5. Verify selected work when requested.
        # --------------------------------------------------------------

        verification = None

        if plan.get(
            "verification_required",
            False,
        ):

            verification = self.verify_results(
                state,
                results,
            )

        # --------------------------------------------------------------
        # 6. Record pipeline completion.
        # --------------------------------------------------------------

        state.event(
            "network_round_completed",
            "VALE_NETWORK",
            payload={
                "round": 1,
                "task_type": plan.get(
                    "task_type"
                ),
                "selected_brain_count": len(
                    selected_brains
                ),
                "selected_brains": selected_brains,
                "internet_research_performed": state.get(
                    "internet_research_performed",
                    False,
                ),
                "internet_result_count": len(
                    internet_results
                ),
                "verification_performed": (
                    verification is not None
                ),
            },
        )

        return {
            "task_id": state.task_id,
            "success": True,
            "task_plan": plan,
            "selected_brains": selected_brains,
            "results": results,
            "internet_results": internet_results,
            "verification": verification,
            "state": state,
        }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:

        return {
            "network": "VALE Brain Network",
            "version": self.NETWORK_VERSION,
            "status": "ONLINE",
            "brain_count": len(
                self.brains
            ),
            "brains": self.brain_names(),
            "active_tasks": len(
                self.tasks
            ),
            "brain_to_brain_communication": True,
            "shared_state": True,
            "shared_connector": True,
            "dynamic_brain_selection": True,
            "universal_internet_search": False,
            "conditional_external_research": True,
            "run_all_available_for_diagnostics": True,
            "generation_ai_os_as_brain": False,
            "connector": self.connector.status(),
            "checked": utc_now(),
        }