"""
VALE UNITY BRAIN
================

UNITY is VALE's system-wide Integration Brain.

Core responsibility
-------------------
UNITY does not replace HEROIC, ALPHA, LEGEND, MARCO, FEELING,
SUPERVISOR, MCVL, Memory, Knowledge, Reasoning, or Evolution.

UNITY's responsibility is to keep those capabilities operating
as one coherent VALE cognitive system.

Architecture position
---------------------

    VALE
      |
      v
    UNITY
      |
      v
    Cognitive Fabric
      |
      +-----------------------------+
      |                             |
      v                             v
    Shared State               Communication
      |
      v
    Routing / Coordination
      |
      v
    HEROIC / ALPHA / Specialized Brains
      |
      v
    Memory / Knowledge / Reasoning
      |
      v
    MCVL
      |
      v
    UNITY Synthesis
      |
      v
    ONE VALE STATE

Important architectural rules
-----------------------------

1. UNITY is the integration brain.
2. Cognitive Fabric is the connective infrastructure.
3. A registered brain is not automatically an active brain.
4. UNITY does not replace specialized intelligence.
5. UNITY does not blindly trust a brain's conclusion.
6. Contradictions must remain visible.
7. Uncertainty must be preserved rather than fabricated away.
8. UNITY should synthesize system state, not simply concatenate answers.
9. Anything not yet finalized remains design-stage/TBD.
10. This file is the first UNITY foundation and will be expanded
    through additional internal modules rather than becoming one
    unmaintainable monolithic brain file.

Current implementation stage
----------------------------

UNITY_INTEGRATION_FOUNDATION

This version establishes:

- UNITY identity
- integration metadata
- shared cognitive-state initialization
- active-brain tracking
- integration lifecycle events
- brain registration visibility
- contribution collection
- contradiction awareness
- verification-state awareness
- synthesis-state preparation
- system-level diagnostics

It intentionally does NOT yet implement the complete future UNITY
architecture.

Future UNITY modules will be added progressively.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from vale_connector import VALEConnector
from vale_brain_interface import VALEBrainInterface


def utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class UnityBrain(VALEBrainInterface):
    """
    VALE's system-wide Integration Brain.

    UNITY sits above the individual specialist brains from an
    integration perspective. It does not perform every form of
    intelligence itself.

    Its job is to maintain the coherence of the whole cognitive
    system and prepare the shared state required for coordinated
    cognition.
    """

    VERSION = "0.1.0"

    ARCHITECTURE_STAGE = "UNITY_INTEGRATION_FOUNDATION"

    BRAIN_NAME = "UNITY"

    # ------------------------------------------------------------------
    # Known VALE architecture
    #
    # These names describe the current master outside architecture.
    # They are intentionally descriptive and do not imply that every
    # brain must run on every request.
    # ------------------------------------------------------------------

    CORE_BRAINS = (
        "UNITY",
        "HEROIC",
        "SUPERVISOR",
        "ALPHA",
    )

    SPECIALIZED_BRAINS = (
        "LEGEND",
        "MARCO",
        "FEELING",
    )

    SUPPORTING_SYSTEMS = (
        "COGNITIVE_FABRIC",
        "MEMORY",
        "KNOWLEDGE",
        "REASONING",
        "EVOLUTION",
        "MCVL",
        "UNITY_CELL_FABRIC",
    )

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        connector: Optional[VALEConnector] = None,
    ):
        super().__init__(
            brain_name=self.BRAIN_NAME,
            connector=connector,
        )

        self.version = self.VERSION
        self.architecture_stage = self.ARCHITECTURE_STAGE

        # Integration runtime counters.
        self.integration_cycles = 0
        self.successful_integrations = 0
        self.failed_integrations = 0

    # ==================================================================
    # IDENTITY
    # ==================================================================

    def identity(self) -> Dict[str, Any]:
        """
        Return UNITY's identity and architectural role.
        """

        base = super().identity()

        base.update(
            {
                "brain": self.BRAIN_NAME,
                "version": self.VERSION,
                "architecture_stage": self.ARCHITECTURE_STAGE,
                "role": "SYSTEM_WIDE_INTEGRATION",
                "mission": (
                    "Keep the VALE cognitive architecture coherent "
                    "and operating as one system."
                ),
                "principle": (
                    "UNITY holds the mind together; "
                    "Cognitive Fabric connects the mind."
                ),
                "registered_as_specialist": False,
            }
        )

        return base

    # ==================================================================
    # SHARED STATE INITIALIZATION
    # ==================================================================

    def initialize_state(
        self,
        state: Any,
    ) -> Dict[str, Any]:
        """
        Initialize the UNITY portion of a VALEBrainState.

        This method does not erase existing state.

        It only establishes missing integration fields.
        """

        existing = state.snapshot_shared()

        if "unity" not in existing:
            state.set(
                "unity",
                {
                    "version": self.VERSION,
                    "architecture_stage": self.ARCHITECTURE_STAGE,
                    "status": "INITIALIZED",
                    "integration_cycle": self.integration_cycles,
                    "created_at": utc_now(),
                },
            )

        if "unity.integration_status" not in existing:
            state.set(
                "unity.integration_status",
                "INITIALIZED",
            )

        if "unity.active_brains" not in existing:
            state.set(
                "unity.active_brains",
                [],
            )

        if "unity.required_capabilities" not in existing:
            state.set(
                "unity.required_capabilities",
                [],
            )

        if "unity.brain_contributions" not in existing:
            state.set(
                "unity.brain_contributions",
                [],
            )

        if "unity.contradictions" not in existing:
            state.set(
                "unity.contradictions",
                [],
            )

        if "unity.verification" not in existing:
            state.set(
                "unity.verification",
                {
                    "status": "NOT_STARTED",
                    "verified": False,
                    "confidence": 0.0,
                },
            )

        if "unity.synthesis" not in existing:
            state.set(
                "unity.synthesis",
                {
                    "status": "NOT_STARTED",
                    "ready": False,
                },
            )

        state.event(
            "unity_state_initialized",
            self.BRAIN_NAME,
            payload={
                "version": self.VERSION,
                "architecture_stage": self.ARCHITECTURE_STAGE,
            },
        )

        return state.get(
            "unity",
            {},
        )

    # ==================================================================
    # ACTIVE BRAIN MANAGEMENT
    # ==================================================================

    def set_active_brains(
        self,
        state: Any,
        brain_names: List[str],
    ) -> List[str]:
        """
        Record which brains are active for the current task.

        Registration and activation remain separate concepts.
        """

        normalized: List[str] = []

        for name in brain_names:
            value = str(name).strip().upper()

            if value and value not in normalized:
                normalized.append(value)

        state.set(
            "unity.active_brains",
            normalized,
        )

        state.set(
            "active_brains",
            normalized,
        )

        state.event(
            "unity_active_brains_updated",
            self.BRAIN_NAME,
            payload={
                "active_brains": normalized,
            },
        )

        return normalized

    def active_brains(
        self,
        state: Any,
    ) -> List[str]:
        """
        Return the current task's active brains.
        """

        value = state.get(
            "unity.active_brains",
            [],
        )

        if not isinstance(value, list):
            return []

        return list(value)

    # ==================================================================
    # REQUIRED CAPABILITIES
    # ==================================================================

    def set_required_capabilities(
        self,
        state: Any,
        capabilities: List[str],
    ) -> List[str]:
        """
        Store capabilities required by the current cognitive task.

        HEROIC will eventually become the authoritative objective/
        capability intelligence layer.

        UNITY currently stores the resulting requirement as shared
        integration state.
        """

        normalized: List[str] = []

        for capability in capabilities:
            value = str(capability).strip().lower()

            if value and value not in normalized:
                normalized.append(value)

        state.set(
            "unity.required_capabilities",
            normalized,
        )

        state.event(
            "unity_capabilities_updated",
            self.BRAIN_NAME,
            payload={
                "required_capabilities": normalized,
            },
        )

        return normalized

    # ==================================================================
    # CONTRIBUTION COLLECTION
    # ==================================================================

    def collect_contributions(
        self,
        state: Any,
    ) -> List[Dict[str, Any]]:
        """
        Collect the current cognitive contributions available in state.

        UNITY does not decide that a contribution is true merely
        because it exists.

        Verification remains a separate responsibility.
        """

        contributions = state.all_contributions()

        result: List[Dict[str, Any]] = []

        for contribution in contributions:
            result.append(
                contribution.to_dict()
            )

        state.set(
            "unity.brain_contributions",
            result,
        )

        state.event(
            "unity_contributions_collected",
            self.BRAIN_NAME,
            payload={
                "contribution_count": len(result),
            },
        )

        return result

    # ==================================================================
    # CONTRADICTION AWARENESS
    # ==================================================================

    def register_contradiction(
        self,
        state: Any,
        contradiction: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Register a contradiction for later verification/resolution.

        UNITY does not silently resolve disagreements here.

        The contradiction remains visible until the appropriate
        verification/reasoning process evaluates it.
        """

        contradictions = state.get(
            "unity.contradictions",
            [],
        )

        if not isinstance(contradictions, list):
            contradictions = []

        item = dict(contradiction)

        item.setdefault(
            "id",
            f"unity-contradiction-{len(contradictions) + 1}",
        )

        item.setdefault(
            "status",
            "OPEN",
        )

        item.setdefault(
            "created_at",
            utc_now(),
        )

        contradictions.append(item)

        state.set(
            "unity.contradictions",
            contradictions,
        )

        state.event(
            "unity_contradiction_registered",
            self.BRAIN_NAME,
            payload=item,
        )

        return item

    def contradictions(
        self,
        state: Any,
    ) -> List[Dict[str, Any]]:
        """
        Return currently registered contradictions.
        """

        value = state.get(
            "unity.contradictions",
            [],
        )

        if not isinstance(value, list):
            return []

        return list(value)

    # ==================================================================
    # VERIFICATION STATE
    # ==================================================================

    def set_verification_state(
        self,
        state: Any,
        status: str,
        verified: bool = False,
        confidence: float = 0.0,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store verification metadata produced by the verification layer.

        UNITY records the state but does not pretend to be MCVL.
        """

        confidence = max(
            0.0,
            min(
                1.0,
                float(confidence),
            ),
        )

        verification = {
            "status": str(status).upper(),
            "verified": bool(verified),
            "confidence": confidence,
            "details": details or {},
            "updated_at": utc_now(),
        }

        state.set(
            "unity.verification",
            verification,
        )

        state.event(
            "unity_verification_state_updated",
            self.BRAIN_NAME,
            payload=verification,
        )

        return verification

    # ==================================================================
    # SYNTHESIS PREPARATION
    # ==================================================================

    def prepare_synthesis(
        self,
        state: Any,
    ) -> Dict[str, Any]:
        """
        Prepare the current shared state for eventual UNITY synthesis.

        This is deliberately preparation only.

        The complete future synthesis engine will be designed as a
        dedicated UNITY subsystem.
        """

        contributions = self.collect_contributions(
            state
        )

        contradictions = self.contradictions(
            state
        )

        verification = state.get(
            "unity.verification",
            {
                "status": "NOT_STARTED",
                "verified": False,
                "confidence": 0.0,
            },
        )

        synthesis = {
            "status": "READY_FOR_SYNTHESIS",
            "ready": True,
            "active_brains": self.active_brains(state),
            "contribution_count": len(contributions),
            "contradiction_count": len(contradictions),
            "verification": verification,
            "prepared_at": utc_now(),
        }

        state.set(
            "unity.synthesis",
            synthesis,
        )

        state.event(
            "unity_synthesis_prepared",
            self.BRAIN_NAME,
            payload={
                "active_brains": synthesis["active_brains"],
                "contribution_count": synthesis["contribution_count"],
                "contradiction_count": synthesis["contradiction_count"],
            },
        )

        return synthesis

    # ==================================================================
    # INTEGRATION CYCLE
    # ==================================================================

    def begin_integration(
        self,
        state: Any,
    ) -> Dict[str, Any]:
        """
        Begin one UNITY integration cycle.

        This is the current foundation lifecycle.

        Future versions will connect this lifecycle to dedicated
        routing, state management, coordination, verification and
        synthesis subsystems.
        """

        self.integration_cycles += 1

        self.initialize_state(
            state
        )

        state.set(
            "unity.integration_status",
            "ACTIVE",
        )

        state.set(
            "unity.integration_cycle",
            self.integration_cycles,
        )

        state.event(
            "unity_integration_started",
            self.BRAIN_NAME,
            payload={
                "cycle": self.integration_cycles,
            },
        )

        return {
            "status": "ACTIVE",
            "cycle": self.integration_cycles,
            "task_id": getattr(
                state,
                "task_id",
                None,
            ),
        }

    def complete_integration(
        self,
        state: Any,
    ) -> Dict[str, Any]:
        """
        Complete the current UNITY integration foundation cycle.

        This does not manufacture a final answer.

        It records the current integration state so later UNITY
        synthesis modules can operate from a stable foundation.
        """

        synthesis = self.prepare_synthesis(
            state
        )

        state.set(
            "unity.integration_status",
            "COMPLETED",
        )

        state.event(
            "unity_integration_completed",
            self.BRAIN_NAME,
            payload={
                "cycle": self.integration_cycles,
                "synthesis_ready": synthesis.get(
                    "ready",
                    False,
                ),
            },
        )

        self.successful_integrations += 1

        return {
            "status": "COMPLETED",
            "cycle": self.integration_cycles,
            "synthesis": synthesis,
        }

    # ==================================================================
    # MAIN BRAIN INTERFACE
    # ==================================================================

    def think(
        self,
        state: Any,
    ) -> Dict[str, Any]:
        """
        Execute the current UNITY integration foundation.

        UNITY currently prepares and maintains integration state.

        It intentionally does not yet implement the complete future
        UNITY synthesis engine.
        """

        try:
            self.begin_integration(
                state
            )

            registered = state.get(
                "registered_brains",
                [],
            )

            if not isinstance(registered, list):
                registered = []

            # Preserve existing active-brain decisions if another
            # orchestration layer has already selected them.
            current_active = self.active_brains(
                state
            )

            if not current_active:
                existing_active = state.get(
                    "active_brains",
                    [],
                )

                if isinstance(existing_active, list):
                    self.set_active_brains(
                        state,
                        existing_active,
                    )

            contributions = self.collect_contributions(
                state
            )

            contradictions = self.contradictions(
                state
            )

            verification = state.get(
                "unity.verification",
                {
                    "status": "NOT_STARTED",
                    "verified": False,
                    "confidence": 0.0,
                },
            )

            result = {
                "brain": self.BRAIN_NAME,
                "status": "READY",
                "version": self.VERSION,
                "architecture_stage": self.ARCHITECTURE_STAGE,
                "role": "SYSTEM_WIDE_INTEGRATION",
                "registered_brains": registered,
                "active_brains": self.active_brains(state),
                "contribution_count": len(
                    contributions
                ),
                "contradiction_count": len(
                    contradictions
                ),
                "verification": verification,
                "integration_status": state.get(
                    "unity.integration_status",
                    "ACTIVE",
                ),
                "synthesis_status": state.get(
                    "unity.synthesis",
                    {},
                ),
                "message": (
                    "UNITY integration foundation is active. "
                    "Complete cognitive synthesis remains a "
                    "dedicated future UNITY subsystem."
                ),
            }

            state.contribute(
                self.BRAIN_NAME,
                "integration_assessment",
                result,
                confidence=1.0,
                importance=1.0,
                metadata={
                    "version": self.VERSION,
                    "architecture_stage": self.ARCHITECTURE_STAGE,
                },
            )

            self.complete_integration(
                state
            )

            return result

        except Exception as exc:
            self.failed_integrations += 1

            try:
                state.set(
                    "unity.integration_status",
                    "FAILED",
                )

                state.event(
                    "unity_integration_failed",
                    self.BRAIN_NAME,
                    payload={
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
            except Exception:
                pass

            return {
                "brain": self.BRAIN_NAME,
                "status": "ERROR",
                "version": self.VERSION,
                "architecture_stage": self.ARCHITECTURE_STAGE,
                "role": "SYSTEM_WIDE_INTEGRATION",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

    # ==================================================================
    # RECEIVE MESSAGE
    # ==================================================================

    def receive_message(
        self,
        message: str,
        state: Any,
        source_brain: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Receive an integration-related message from another VALE brain.

        The current foundation records the message in shared state and
        event history.

        Full UNITY message semantics will be introduced through the
        future Cognitive Fabric communication subsystem.
        """

        source = str(
            source_brain
        ).strip().upper()

        data = payload or {}

        state.event(
            "unity_message_received",
            source,
            self.BRAIN_NAME,
            {
                "message": message,
                "payload": data,
            },
        )

        return {
            "brain": self.BRAIN_NAME,
            "received": True,
            "from": source,
            "message": message,
            "payload": data,
            "integration_status": state.get(
                "unity.integration_status",
                "NOT_INITIALIZED",
            ),
        }

    # ==================================================================
    # DIAGNOSTICS
    # ==================================================================

    def diagnostics(
        self,
        state: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Return UNITY operational and architectural diagnostics.
        """

        result = {
            "brain": self.BRAIN_NAME,
            "version": self.VERSION,
            "architecture_stage": self.ARCHITECTURE_STAGE,
            "role": "SYSTEM_WIDE_INTEGRATION",
            "integration_cycles": self.integration_cycles,
            "successful_integrations": self.successful_integrations,
            "failed_integrations": self.failed_integrations,
            "network_connected": self.network is not None,
            "connector_available": self.connector is not None,
            "core_brains": list(self.CORE_BRAINS),
            "specialized_brains": list(
                self.SPECIALIZED_BRAINS
            ),
            "supporting_systems": list(
                self.SUPPORTING_SYSTEMS
            ),
        }

        if state is not None:
            result["task_id"] = getattr(
                state,
                "task_id",
                None,
            )

            result["integration_status"] = state.get(
                "unity.integration_status",
                "NOT_INITIALIZED",
            )

            result["active_brains"] = self.active_brains(
                state
            )

            result["contradiction_count"] = len(
                self.contradictions(state)
            )

            result["verification"] = state.get(
                "unity.verification",
                {},
            )

            result["synthesis"] = state.get(
                "unity.synthesis",
                {},
            )

        return result
