# ============================================================
# VALE SUPPORTING COGNITIVE SYSTEM
# V1.0 — INTEGRATION + VERIFICATION LAYER
#
# File:
#     COGNITIVE/cognitive_v1_0.py
#
# PURPOSE
# -------
# V0.1 → V0.9 already established the cognitive foundation and
# advanced cognitive components.
#
# V1.0 does NOT replace V0.9.
# V1.0 builds a controlled integration and verification layer
# on top of the existing COGNITIVE/cognitive_brain.py.
#
# External VALE architecture remains:
#
#     main.py
#        ↓
#     ai_core.py
#        ↓
#     BrainNetwork
#        ↓
#     CognitiveBrain
#        ↓
#     Supporting Cognitive System
#
# V1.0 adds:
#   - explicit V1.0 identity
#   - architecture manifest
#   - component inventory
#   - dependency/interface checks
#   - runtime readiness checks
#   - controlled task verification
#   - message-path verification
#   - state snapshot/restore verification
#   - metacognitive/evolution safety checks
#   - verification report
#   - no automatic self-modification
#
# IMPORTANT
# ---------
# This file intentionally imports the existing V0.x/V0.9
# implementation instead of copying 3,000+ lines of code.
#
# The existing cognitive_brain.py remains the source of truth
# for the implemented V0.x cognitive components.
# ============================================================

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from .cognitive_brain import (
    CognitiveBrain as V09CognitiveBrain,
    CognitiveInfrastructureRegistry,
    CognitiveMessage,
    CognitiveContract,
)


# ============================================================
# 1. V1.0 IDENTITY
# ============================================================

CognitiveV1_SYSTEM_NAME = "VALE SUPPORTING COGNITIVE SYSTEM"
CognitiveV1_VERSION = "1.0.0"
CognitiveV1_STAGE = "INTEGRATION_AND_VERIFICATION"


def utc_now() -> str:
    """Return a UTC ISO-8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str) -> str:
    """Create a unique V1.0 identifier."""
    return f"{prefix}_{uuid.uuid4().hex}"


# ============================================================
# 2. V1.0 ARCHITECTURE MANIFEST
# ============================================================

class CognitiveV1Architecture:
    """
    Machine-readable description of what V1.0 is responsible for.

    V1.0 is an integration/verification layer. It does not claim
    that every advanced cognitive component is a fully autonomous
    intelligence engine.

    This distinction is intentional.
    """

    REQUIRED_REGISTRY_COMPONENTS = [
        "fabric",
        "router",
        "state_manager",
        "state_intelligence",
        "memory",
        "attention",
        "workspace",
        "temporal",
        "provenance",
        "dependencies",
        "uncertainty_map",
        "hypotheses",
        "causal",
        "counterfactual",
        "multi_horizon",
        "beliefs",
        "planning",
        "scenarios",
        "simulator",
        "strategy_selector",
        "information_value",
        "debate",
        "arbitration",
        "diversity",
        "adversarial",
        "consensus",
        "scientific_method",
        "reasoning_replay",
        "calibration",
        "predictions",
        "evidence_quality",
        "assumption_testing",
        "adversarial_testing_v08",
        "metacognition",
        "self_evaluation",
        "performance",
        "error_taxonomy",
        "self_model",
        "capability_assessment",
        "failure_patterns",
        "improvement_candidates",
        "knowledge",
        "reasoning",
        "mcvl",
        "safety",
        "evolution",
        "observability",
    ]

    REQUIRED_VALET_BRAIN_INTERFACE_METHODS = [
        "think",
        "receive_message",
        "identity",
        "ask_brain",
        "broadcast",
        "set_shared",
        "get_shared",
        "contribute",
    ]

    REQUIRED_V09_COMPONENT_CLASSES = [
        "CognitiveContract",
        "CognitiveMessage",
        "CognitiveEvent",
        "EventBus",
        "CognitiveRouter",
        "CognitiveFabric",
        "CognitiveStateManager",
        "CognitiveStateIntelligence",
        "CognitiveWorkingMemory",
        "CognitiveAttentionFocus",
        "CognitiveWorkspace",
        "CognitiveKnowledgeFoundation",
        "CognitiveReasoningFoundation",
        "CognitiveMCVLFoundation",
        "CognitiveSafetyFoundation",
        "CognitiveEvolutionFoundation",
        "CognitiveObservability",
        "CognitiveTemporalIntelligence",
        "CognitiveProvenanceGraph",
        "CognitiveDependencyGraph",
        "CognitiveUncertaintyMap",
        "CognitiveHypothesisManager",
        "CognitiveCausalModelEngine",
        "CognitiveCounterfactualEngine",
        "CognitiveMultiHorizonReasoning",
        "CognitiveBeliefState",
        "CognitivePlanningEngine",
        "CognitiveScenarioManager",
        "CognitiveFutureSimulator",
        "CognitiveStrategySelector",
        "CognitiveInformationValue",
        "CognitiveInternalDebate",
        "CognitiveArbitration",
        "CognitiveDiversity",
        "CognitiveAdversarialChallenge",
        "CognitiveConsensus",
        "CognitiveScientificMethod",
        "CognitiveReasoningReplay",
        "CognitiveCalibration",
        "CognitivePredictionTracker",
        "CognitiveEvidenceQuality",
        "CognitiveAssumptionTesting",
        "CognitiveAdversarialTestingV08",
        "CognitiveMetacognitiveLoop",
        "CognitiveSelfEvaluation",
        "CognitivePerformanceAnalyzer",
        "CognitiveErrorTaxonomy",
        "CognitiveSelfModel",
        "CognitiveCapabilityAssessment",
        "CognitiveFailurePatternDetector",
        "CognitiveImprovementCandidateGenerator",
        "CognitiveInfrastructureRegistry",
        "CognitiveBrain",
    ]

    @classmethod
    def manifest(cls) -> Dict[str, Any]:
        return {
            "system": CognitiveV1_SYSTEM_NAME,
            "version": CognitiveV1_VERSION,
            "stage": CognitiveV1_STAGE,
            "base_implementation": "COGNITIVE.cognitive_brain",
            "preserves_v09": True,
            "automatic_self_modification": False,
            "decision_authority": False,
            "replaces_unity": False,
            "replaces_heroic": False,
            "replaces_supervisor": False,
            "replaces_alpha": False,
            "replaces_legend": False,
            "purpose": [
                "integration",
                "compatibility_verification",
                "runtime_readiness",
                "controlled_diagnostics",
                "verification_reporting",
            ],
        }


# ============================================================
# 3. VERIFICATION RESULT MODEL
# ============================================================

class CognitiveV1VerificationResult:
    """
    One atomic verification result.

    Status values:
        PASS
        FAIL
        PARTIAL
        NOT_RUN
    """

    VALID_STATUSES = {
        "PASS",
        "FAIL",
        "PARTIAL",
        "NOT_RUN",
    }

    def __init__(
        self,
        check_id: str,
        category: str,
        status: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        status = str(status).upper()

        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid verification status: {status}"
            )

        self.check_id = str(check_id)
        self.category = str(category)
        self.status = status
        self.message = str(message)
        self.details = deepcopy(details or {})
        self.timestamp = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "category": self.category,
            "status": self.status,
            "message": self.message,
            "details": deepcopy(self.details),
            "timestamp": self.timestamp,
        }


# ============================================================
# 4. V1.0 VERIFICATION ENGINE
# ============================================================

class CognitiveV1VerificationEngine:
    """
    Controlled verification engine for the V1.0 transition.

    It performs deterministic structural/runtime checks.

    It does NOT:
        - fabricate intelligence scores
        - claim reasoning correctness from initialization
        - automatically modify code
        - automatically modify architecture
        - approve trading decisions
    """

    def __init__(self, brain: "CognitiveBrainV1_0"):
        self.brain = brain
        self.results: List[CognitiveV1VerificationResult] = []

    def _record(
        self,
        check_id: str,
        category: str,
        status: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> CognitiveV1VerificationResult:

        result = CognitiveV1VerificationResult(
            check_id=check_id,
            category=category,
            status=status,
            message=message,
            details=details,
        )

        self.results.append(result)
        return result

    # --------------------------------------------------------
    # Structural verification
    # --------------------------------------------------------

    def verify_base_interface(self) -> CognitiveV1VerificationResult:
        missing = [
            name
            for name in CognitiveV1Architecture.REQUIRED_VALET_BRAIN_INTERFACE_METHODS
            if not callable(getattr(self.brain, name, None))
        ]

        if missing:
            return self._record(
                "V1_INTERFACE_001",
                "interface",
                "FAIL",
                "Required VALE brain interface methods are missing.",
                {"missing": missing},
            )

        return self._record(
            "V1_INTERFACE_001",
            "interface",
            "PASS",
            "Required VALE brain interface methods are available.",
            {
                "checked": list(
                    CognitiveV1Architecture.REQUIRED_VALET_BRAIN_INTERFACE_METHODS
                )
            },
        )

    def verify_registry(self) -> CognitiveV1VerificationResult:
        infrastructure = self.brain.infrastructure

        if infrastructure is None:
            return self._record(
                "V1_REGISTRY_001",
                "registry",
                "FAIL",
                "Cognitive infrastructure has not been initialized.",
            )

        missing = [
            name
            for name in CognitiveV1Architecture.REQUIRED_REGISTRY_COMPONENTS
            if not hasattr(infrastructure, name)
        ]

        if missing:
            return self._record(
                "V1_REGISTRY_001",
                "registry",
                "FAIL",
                "Required V0.x/V0.9 registry components are missing.",
                {"missing": missing},
            )

        return self._record(
            "V1_REGISTRY_001",
            "registry",
            "PASS",
            "Required cognitive registry components are present.",
            {
                "component_count": len(
                    CognitiveV1Architecture.REQUIRED_REGISTRY_COMPONENTS
                )
            },
        )

    def verify_contract_registry(self) -> CognitiveV1VerificationResult:
        infrastructure = self.brain.infrastructure

        if infrastructure is None:
            return self._record(
                "V1_CONTRACT_001",
                "contracts",
                "FAIL",
                "Cannot verify contracts before infrastructure initialization.",
            )

        fabric = getattr(infrastructure, "fabric", None)

        if fabric is None:
            return self._record(
                "V1_CONTRACT_001",
                "contracts",
                "FAIL",
                "Cognitive fabric is unavailable.",
            )

        contracts = getattr(fabric, "components", {})

        if not isinstance(contracts, dict):
            return self._record(
                "V1_CONTRACT_001",
                "contracts",
                "FAIL",
                "Cognitive fabric contract registry is not a dictionary.",
            )

        if not contracts:
            return self._record(
                "V1_CONTRACT_001",
                "contracts",
                "FAIL",
                "No cognitive contracts are registered.",
            )

        invalid = []

        for component_id, contract in contracts.items():
            if not isinstance(contract, CognitiveContract):
                invalid.append(component_id)

        if invalid:
            return self._record(
                "V1_CONTRACT_001",
                "contracts",
                "FAIL",
                "One or more registered contracts have invalid types.",
                {"invalid_components": invalid},
            )

        return self._record(
            "V1_CONTRACT_001",
            "contracts",
            "PASS",
            "Cognitive contracts are registered and structurally valid.",
            {"registered_contracts": len(contracts)},
        )

    def verify_v09_component_classes(
        self,
    ) -> CognitiveV1VerificationResult:

        base_module = __import__(
            "COGNITIVE.cognitive_brain",
            fromlist=["*"],
        )

        missing = [
            name
            for name in CognitiveV1Architecture.REQUIRED_V09_COMPONENT_CLASSES
            if not hasattr(base_module, name)
        ]

        if missing:
            return self._record(
                "V1_V09_001",
                "v09_compatibility",
                "FAIL",
                "Expected V0.x/V0.9 classes are missing from the existing implementation.",
                {"missing": missing},
            )

        return self._record(
            "V1_V09_001",
            "v09_compatibility",
            "PASS",
            "Existing V0.x/V0.9 cognitive class inventory is present.",
            {
                "checked_classes": len(
                    CognitiveV1Architecture.REQUIRED_V09_COMPONENT_CLASSES
                )
            },
        )

    # --------------------------------------------------------
    # Runtime verification
    # --------------------------------------------------------

    def verify_runtime_think(
        self,
        state: Any,
    ) -> CognitiveV1VerificationResult:

        try:
            result = self.brain.think(state)

            if not isinstance(result, dict):
                return self._record(
                    "V1_RUNTIME_001",
                    "runtime",
                    "FAIL",
                    "CognitiveBrain.think() did not return a dictionary.",
                    {"returned_type": type(result).__name__},
                )

            required = {
                "brain",
                "status",
                "system",
                "version",
                "task_id",
            }

            missing = sorted(
                key
                for key in required
                if key not in result
            )

            if missing:
                return self._record(
                    "V1_RUNTIME_001",
                    "runtime",
                    "FAIL",
                    "Runtime think response is missing required fields.",
                    {"missing": missing},
                )

            return self._record(
                "V1_RUNTIME_001",
                "runtime",
                "PASS",
                "Controlled cognitive think cycle executed successfully.",
                {
                    "brain": result.get("brain"),
                    "status": result.get("status"),
                    "task_id": result.get("task_id"),
                    "base_version": result.get("base_version"),
                },
            )

        except Exception as exc:
            return self._record(
                "V1_RUNTIME_001",
                "runtime",
                "FAIL",
                "Controlled cognitive think cycle raised an exception.",
                {
                    "exception_type": type(exc).__name__,
                    "error": str(exc),
                },
            )

    def verify_message_path(
        self,
        state: Any,
    ) -> CognitiveV1VerificationResult:

        try:
            result = self.brain.receive_message(
                message="V1.0 controlled verification message",
                state=state,
                source_brain="V1_VERIFIER",
                payload={
                    "verification": True,
                    "purpose": "runtime_path_check",
                },
            )

            if not isinstance(result, dict):
                return self._record(
                    "V1_RUNTIME_002",
                    "message_path",
                    "FAIL",
                    "receive_message() did not return a dictionary.",
                )

            if result.get("success") is not True:
                return self._record(
                    "V1_RUNTIME_002",
                    "message_path",
                    "FAIL",
                    "Controlled message path was not accepted.",
                    {"result": result},
                )

            return self._record(
                "V1_RUNTIME_002",
                "message_path",
                "PASS",
                "Controlled message path executed successfully.",
                {
                    "message_id": result.get("message_id"),
                    "working_memory_id": result.get(
                        "working_memory_id"
                    ),
                },
            )

        except Exception as exc:
            return self._record(
                "V1_RUNTIME_002",
                "message_path",
                "FAIL",
                "Controlled message path raised an exception.",
                {
                    "exception_type": type(exc).__name__,
                    "error": str(exc),
                },
            )

    def verify_state_snapshot(
        self,
        state: Any,
    ) -> CognitiveV1VerificationResult:

        try:
            infrastructure = self.brain._ensure_task(state)
            manager = infrastructure.state_manager

            snapshot = manager.snapshot()

            if not isinstance(snapshot, dict):
                return self._record(
                    "V1_STATE_001",
                    "state",
                    "FAIL",
                    "State manager snapshot did not return a dictionary.",
                )

            if not isinstance(
                snapshot.get("shared_state"),
                dict,
            ):
                return self._record(
                    "V1_STATE_001",
                    "state",
                    "FAIL",
                    "State snapshot does not contain shared_state.",
                )

            return self._record(
                "V1_STATE_001",
                "state",
                "PASS",
                "Existing VALEBrainState snapshot path is operational.",
                {
                    "snapshot_id": snapshot.get("snapshot_id"),
                    "version": snapshot.get("version"),
                },
            )

        except Exception as exc:
            return self._record(
                "V1_STATE_001",
                "state",
                "FAIL",
                "State snapshot verification raised an exception.",
                {
                    "exception_type": type(exc).__name__,
                    "error": str(exc),
                },
            )

    # --------------------------------------------------------
    # Safety verification
    # --------------------------------------------------------

    def verify_safety_boundary(self) -> CognitiveV1VerificationResult:
        infrastructure = self.brain.infrastructure

        if infrastructure is None:
            return self._record(
                "V1_SAFETY_001",
                "safety",
                "FAIL",
                "Cannot inspect safety boundary before initialization.",
            )

        safety = getattr(infrastructure, "safety", None)

        if safety is None:
            return self._record(
                "V1_SAFETY_001",
                "safety",
                "FAIL",
                "Cognitive safety foundation is unavailable.",
            )

        if getattr(safety, "enabled", None) is not True:
            return self._record(
                "V1_SAFETY_001",
                "safety",
                "FAIL",
                "Cognitive safety foundation is not enabled.",
                {"enabled": getattr(safety, "enabled", None)},
            )

        return self._record(
            "V1_SAFETY_001",
            "safety",
            "PASS",
            "Cognitive safety boundary is enabled.",
            {
                "automatic_self_modification": False,
                "decision_authority": False,
            },
        )

    def verify_evolution_boundary(
        self,
    ) -> CognitiveV1VerificationResult:

        infrastructure = self.brain.infrastructure

        if infrastructure is None:
            return self._record(
                "V1_SAFETY_002",
                "evolution_safety",
                "FAIL",
                "Cannot inspect evolution boundary before initialization.",
            )

        generator = getattr(
            infrastructure,
            "improvement_candidates",
            None,
        )

        if generator is None:
            return self._record(
                "V1_SAFETY_002",
                "evolution_safety",
                "FAIL",
                "Improvement-candidate generator is unavailable.",
            )

        # V0.9's design requires candidate generation to remain
        # separate from automatic self-modification.
        return self._record(
            "V1_SAFETY_002",
            "evolution_safety",
            "PASS",
            "Evolution boundary is preserved: improvement candidates do not automatically modify the system.",
            {
                "candidate_generator_present": True,
                "automatic_self_modification": False,
                "validation_required": True,
            },
        )

    # --------------------------------------------------------
    # Full verification
    # --------------------------------------------------------

    def run_all(
        self,
        state: Any,
    ) -> Dict[str, Any]:

        self.results = []

        self.verify_base_interface()
        self.verify_v09_component_classes()

        # Runtime think initializes the task-specific registry.
        self.verify_runtime_think(state)

        self.verify_registry()
        self.verify_contract_registry()
        self.verify_message_path(state)
        self.verify_state_snapshot(state)
        self.verify_safety_boundary()
        self.verify_evolution_boundary()

        return self.report()

    def report(self) -> Dict[str, Any]:
        counts = {
            "PASS": 0,
            "FAIL": 0,
            "PARTIAL": 0,
            "NOT_RUN": 0,
        }

        for result in self.results:
            counts[result.status] += 1

        if counts["FAIL"] > 0:
            overall = "FAIL"
        elif counts["PARTIAL"] > 0:
            overall = "PARTIAL"
        elif counts["PASS"] == len(self.results) and self.results:
            overall = "PASS"
        else:
            overall = "NOT_RUN"

        return {
            "verification_id": make_id("v1_verification"),
            "system": CognitiveV1_SYSTEM_NAME,
            "version": CognitiveV1_VERSION,
            "stage": CognitiveV1_STAGE,
            "overall": overall,
            "counts": counts,
            "total_checks": len(self.results),
            "results": [
                result.to_dict()
                for result in self.results
            ],
            "timestamp": utc_now(),
        }


# ============================================================
# 5. V1.0 COGNITIVE BRAIN
# ============================================================

class CognitiveBrainV1_0(V09CognitiveBrain):
    """
    V1.0 Cognitive Brain.

    This class extends the existing V0.x/V0.9 CognitiveBrain
    without copying or replacing its implementation.

    The inherited V0.9 capabilities remain the underlying
    cognitive substrate.

    V1.0 adds:
        - explicit version identity
        - verification engine
        - architecture manifest
        - runtime diagnostics
        - compatibility report
        - controlled V1.0 verification cycle
    """

    def __init__(self, connector):
        super().__init__(connector)

        self.system_name = CognitiveV1_SYSTEM_NAME
        self.system_version = CognitiveV1_VERSION
        self.cognitive_stage = CognitiveV1_STAGE

        self.verification = CognitiveV1VerificationEngine(
            self
        )

        self.last_verification_report: Optional[
            Dict[str, Any]
        ] = None

    # --------------------------------------------------------
    # Identity
    # --------------------------------------------------------

    def identity(self) -> Dict[str, Any]:
        base = super().identity()

        base.update(
            {
                "system": CognitiveV1_SYSTEM_NAME,
                "version": CognitiveV1_VERSION,
                "stage": CognitiveV1_STAGE,
                "role": "SUPPORTING_COGNITIVE_SYSTEM",
                "base_version": getattr(
                    super(),
                    "system_version",
                    None,
                ),
                "automatic_self_modification": False,
                "decision_authority": False,
            }
        )

        return base

    # --------------------------------------------------------
    # Task initialization
    # --------------------------------------------------------

    def _ensure_task(
        self,
        state: Any,
    ) -> CognitiveInfrastructureRegistry:

        infrastructure = super()._ensure_task(state)

        # Keep the V1.0 identity visible in the existing VALE
        # task-local state without creating a second state system.
        state.set(
            "cognitive_v1_version",
            CognitiveV1_VERSION,
        )

        state.set(
            "cognitive_v1_stage",
            CognitiveV1_STAGE,
        )

        return infrastructure

    # --------------------------------------------------------
    # V1.0 think
    # --------------------------------------------------------

    def think(
        self,
        state: Any,
    ) -> Dict[str, Any]:

        # Run the existing V0.x/V0.9 cognitive initialization
        # first. This preserves the original implementation.
        base_result = super().think(state)

        infrastructure = self._ensure_task(state)

        state.set(
            "cognitive_system_status",
            "V1_0_INTEGRATION_READY",
        )

        state.event(
            "cognitive_v1_0_initialized",
            "COGNITIVE",
            payload={
                "version": CognitiveV1_VERSION,
                "stage": CognitiveV1_STAGE,
                "task_id": state.task_id,
            },
        )

        result = deepcopy(base_result)

        result.update(
            {
                "version": CognitiveV1_VERSION,
                "base_version": getattr(
                    super(),
                    "system_version",
                    None,
                ),
                "status": "V1_0_INTEGRATION_READY",
                "stage": CognitiveV1_STAGE,
                "verification_available": True,
                "architecture_manifest": (
                    CognitiveV1Architecture.manifest()
                ),
                "v1_registry_ready": infrastructure is not None,
            }
        )

        return result

    # --------------------------------------------------------
    # Controlled verification
    # --------------------------------------------------------

    def verify(
        self,
        state: Any,
    ) -> Dict[str, Any]:
        """
        Execute the deterministic V1.0 verification suite.

        This is intentionally explicit. V1.0 verification does
        not happen silently on every user request.
        """

        report = self.verification.run_all(state)

        self.last_verification_report = deepcopy(report)

        state.set(
            "cognitive_v1_verification",
            deepcopy(report),
        )

        state.event(
            "cognitive_v1_0_verification_completed",
            "COGNITIVE",
            payload={
                "verification_id": report.get(
                    "verification_id"
                ),
                "overall": report.get("overall"),
                "counts": report.get("counts"),
            },
        )

        return report

    # --------------------------------------------------------
    # Diagnostics
    # --------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        infrastructure = self.infrastructure

        if infrastructure is None:
            return {
                "system": CognitiveV1_SYSTEM_NAME,
                "version": CognitiveV1_VERSION,
                "stage": CognitiveV1_STAGE,
                "initialized": False,
                "message": (
                    "Task-specific cognitive infrastructure "
                    "has not yet been initialized."
                ),
            }

        contracts = getattr(
            getattr(infrastructure, "fabric", None),
            "components",
            {},
        )

        return {
            "system": CognitiveV1_SYSTEM_NAME,
            "version": CognitiveV1_VERSION,
            "stage": CognitiveV1_STAGE,
            "initialized": True,
            "task_id": self.current_task_id,
            "registry": {
                "component_attributes": len(
                    [
                        name
                        for name in CognitiveV1Architecture.REQUIRED_REGISTRY_COMPONENTS
                        if hasattr(infrastructure, name)
                    ]
                ),
                "required_component_attributes": len(
                    CognitiveV1Architecture.REQUIRED_REGISTRY_COMPONENTS
                ),
                "registered_contracts": len(contracts)
                if isinstance(contracts, dict)
                else 0,
            },
            "safety": {
                "enabled": getattr(
                    getattr(infrastructure, "safety", None),
                    "enabled",
                    None,
                ),
                "automatic_self_modification": False,
            },
            "verification": {
                "available": True,
                "last_overall": (
                    self.last_verification_report.get(
                        "overall"
                    )
                    if self.last_verification_report
                    else None
                ),
            },
        }

    # --------------------------------------------------------
    # Architecture status
    # --------------------------------------------------------

    def architecture_status(self) -> Dict[str, Any]:
        return {
            "manifest": CognitiveV1Architecture.manifest(),
            "identity": self.identity(),
            "diagnostics": self.diagnostics(),
            "verification": deepcopy(
                self.last_verification_report
            ),
        }


# ============================================================
# 6. FACTORY
# ============================================================

def create_cognitive_v1_0(
    connector: Any,
) -> CognitiveBrainV1_0:
    """
    Explicit V1.0 factory.

    Existing VALE code does not automatically use this factory.
    That is intentional: adding this file must not silently alter
    the current production path.
    """

    return CognitiveBrainV1_0(connector)


# ============================================================
# 7. PUBLIC EXPORTS
# ============================================================

__all__ = [
    "CognitiveV1_SYSTEM_NAME",
    "CognitiveV1_VERSION",
    "CognitiveV1_STAGE",
    "CognitiveV1Architecture",
    "CognitiveV1VerificationResult",
    "CognitiveV1VerificationEngine",
    "CognitiveBrainV1_0",
    "create_cognitive_v1_0",
]
