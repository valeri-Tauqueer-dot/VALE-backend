"""
VALE UNITY — Integration Brain

UNITY is the highest-level integration system of VALE.

Its responsibility is to make the VALE cognitive architecture operate
as one coherent system.

UNITY does NOT replace:

    HEROIC       -> objective / mission intelligence
    SUPERVISOR   -> health, conflict, recovery
    ALPHA        -> execution orchestration / performance
    LEGEND       -> market intelligence
    MARCO        -> general / cross-domain intelligence
    FEELING      -> human experience intelligence
    MCVL         -> verification intelligence

UNITY integrates them.

High-level architecture:

    USER
      │
      ▼
    UNITY
      │
      ├── Integration
      │
      ├── Coordination
      │
      ├── Routing
      │
      ├── Communication
      │
      ├── Contradiction Tracking
      │
      ├── Verification Gateway
      │
      ├── Synthesis
      │
      └── Diagnostics
              │
              ▼
        COHERENT VALE STATE

This file is the runtime integration boundary.

Important architectural principle:

    "A brain is not a button."

UNITY therefore does not simply call every brain and concatenate their
answers. It maintains shared state, task context, communication,
verification state, contradiction state, and synthesis state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from vale_brain_interface import VALEBrainInterface

from .integration_state import UnityIntegrationState
from .cognitive_fabric import CognitiveFabric

from .routing.routing_engine import RoutingEngine
from .routing.routing_policy import RoutingPolicy

from .coordination.coordination_engine import CoordinationEngine

from .integration.brain_registry import BrainRegistry
from .integration.capability_registry import CapabilityRegistry
from .integration.brain_activation import BrainActivationManager

from .synthesis.synthesis_engine import SynthesisEngine

from .contradiction.contradiction_engine import ContradictionEngine

from .verification.verification_gateway import VerificationGateway

from .communication.message_router import MessageRouter
from .communication.event_dispatcher import EventDispatcher
from .communication.communication_protocol import CommunicationProtocol

from .diagnostics.integration_diagnostics import IntegrationDiagnostics
from .diagnostics.fabric_diagnostics import FabricDiagnostics
from .diagnostics.system_diagnostics import SystemDiagnostics


VERSION = "0.2.0"
ARCHITECTURE_STAGE = "UNITY_INTEGRATION_RUNTIME_FOUNDATION"


class UnityBrain(VALEBrainInterface):
    """
    Central UNITY integration brain.

    This class owns the runtime relationship between UNITY's integration
    subsystems.

    It intentionally does not contain the intelligence of the other VALE
    brains.
    """

    BRAIN_NAME = "UNITY"

    CORE_BRAINS = {
        "UNITY",
        "HEROIC",
        "SUPERVISOR",
        "ALPHA",
    }

    SPECIALIZED_BRAINS = {
        "LEGEND",
        "MARCO",
        "FEELING",
    }

    SUPPORTING_SYSTEMS = {
        "COGNITIVE_FABRIC",
        "MEMORY",
        "KNOWLEDGE",
        "REASONING",
        "EVOLUTION",
        "MCVL",
        "UNITY_CELL_FABRIC",
    }

    def __init__(
        self,
        connector: Optional[Any] = None,
        network: Optional[Any] = None,
        state: Optional[Any] = None,
        auto_initialize: bool = True,
    ) -> None:
        """
        Create the UNITY runtime.

        Parameters
        ----------
        connector:
            Optional VALE external connector.

        network:
            Optional existing VALE BrainNetwork.

        state:
            Optional existing VALEBrainState.

        auto_initialize:
            If True, UNITY initializes its structural foundation immediately.
        """

        super().__init__(
            brain_name=self.BRAIN_NAME,
            connector=connector,
            network=network,
        )

        # --------------------------------------------------------------
        # Base state
        # --------------------------------------------------------------

        self.state = UnityIntegrationState(
            state=state
        )

        # --------------------------------------------------------------
        # Communication / Fabric
        # --------------------------------------------------------------

        self.cognitive_fabric = CognitiveFabric()

        self.message_router = MessageRouter(
            fabric=self.cognitive_fabric
        )

        self.event_dispatcher = EventDispatcher(
            state=self.state
        )

        self.communication_protocol = CommunicationProtocol(
            state=self.state
        )

        # --------------------------------------------------------------
        # Integration
        # --------------------------------------------------------------

        self.brain_registry = BrainRegistry()

        self.capability_registry = CapabilityRegistry()

        self.activation_manager = BrainActivationManager(
            registry=self.brain_registry,
            state=self.state,
        )

        # --------------------------------------------------------------
        # Coordination
        # --------------------------------------------------------------

        self.coordination_engine = CoordinationEngine(
            state=self.state
        )

        # --------------------------------------------------------------
        # Routing
        # --------------------------------------------------------------

        self.routing_policy = RoutingPolicy()

        self.routing_engine = RoutingEngine(
            fabric=self.cognitive_fabric,
            policy=self.routing_policy,
            state=self.state,
        )

        # --------------------------------------------------------------
        # Contradiction management
        # --------------------------------------------------------------

        self.contradiction_engine = ContradictionEngine(
            state=self.state
        )

        # --------------------------------------------------------------
        # Verification boundary
        # --------------------------------------------------------------

        self.verification_gateway = VerificationGateway(
            state=self.state
        )

        # --------------------------------------------------------------
        # Synthesis
        # --------------------------------------------------------------

        self.synthesis_engine = SynthesisEngine(
            state=self.state
        )

        # --------------------------------------------------------------
        # Diagnostics
        # --------------------------------------------------------------

        self.integration_diagnostics = IntegrationDiagnostics(
            brain_registry=self.brain_registry,
            capability_registry=self.capability_registry,
            activation_manager=self.activation_manager,
            state=self.state,
        )

        self.fabric_diagnostics = FabricDiagnostics(
            cognitive_fabric=self.cognitive_fabric,
            message_router=self.message_router,
            event_dispatcher=self.event_dispatcher,
            communication_protocol=self.communication_protocol,
            state=self.state,
        )

        self.system_diagnostics = SystemDiagnostics(
            integration_diagnostics=self.integration_diagnostics,
            fabric_diagnostics=self.fabric_diagnostics,
            state=self.state,
        )

        self._initialized = False
        self._last_task_id: Optional[str] = None
        self._last_integration: Optional[Dict[str, Any]] = None

        if auto_initialize:
            self.initialize()

    # ==================================================================
    # INITIALIZATION
    # ==================================================================

    def initialize(self) -> Dict[str, Any]:
        """
        Initialize the complete UNITY structural foundation.

        Initialization is intentionally deterministic.

        It registers the VALE architecture but does not execute cognitive
        reasoning.
        """

        if self._initialized:
            return self.runtime_status()

        # --------------------------------------------------------------
        # Register VALE brain/system identities
        # --------------------------------------------------------------

        self.brain_registry.register_vaIe_foundation()

        # --------------------------------------------------------------
        # Register foundation capabilities
        # --------------------------------------------------------------

        self.capability_registry.register_foundation_capabilities()

        # --------------------------------------------------------------
        # Connect capability providers
        # --------------------------------------------------------------

        self._connect_foundation_capabilities()

        # --------------------------------------------------------------
        # Synchronize activation records
        # --------------------------------------------------------------

        self.activation_manager.synchronize_registry()

        # UNITY itself is structurally active.
        self.activation_manager.activate(
            "UNITY",
            reason="UNITY runtime initialization",
        )

        # --------------------------------------------------------------
        # Register communication nodes
        # --------------------------------------------------------------

        self._register_communication_nodes()

        # --------------------------------------------------------------
        # Publish UNITY state
        # --------------------------------------------------------------

        self.state.set_status("INITIALIZED")

        self.state.set_registered_brains(
            self.brain_registry.names()
        )

        self.state.set_active_brains(
            self.activation_manager.active_names()
        )

        self.state.event(
            event_type="UNITY_INITIALIZED",
            source="UNITY",
            payload={
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
            },
        )

        self._initialized = True

        return self.runtime_status()

    def _connect_foundation_capabilities(self) -> None:
        """
        Connect known architectural providers to foundation capabilities.

        This is structural registration only.

        It does not mean that every provider is currently instantiated or
        available at runtime.
        """

        mappings = {
            "integration": ["UNITY"],
            "objective_intelligence": ["HEROIC"],
            "orchestration": ["ALPHA"],
            "market_intelligence": ["LEGEND"],
            "general_intelligence": ["MARCO"],
            "human_experience": ["FEELING"],
            "system_supervision": ["SUPERVISOR"],
            "memory": ["MEMORY"],
            "knowledge": ["KNOWLEDGE"],
            "reasoning": ["REASONING"],
            "verification": ["MCVL"],
            "communication": ["COGNITIVE_FABRIC"],
            "routing": ["UNITY"],
            "coordination": ["UNITY"],
            "evolution": ["EVOLUTION"],
            "cell_fabric": ["UNITY_CELL_FABRIC"],
        }

        for capability, providers in mappings.items():
            for provider in providers:
                try:
                    self.capability_registry.connect_provider(
                        capability,
                        provider,
                    )
                except Exception:
                    # Provider registration must not prevent UNITY from
                    # initializing. The diagnostic layer will expose the
                    # resulting structural problem.
                    pass

    def _register_communication_nodes(self) -> None:
        """
        Register the known UNITY communication nodes.

        Registration creates communication endpoints only. It does not
        instantiate or activate the corresponding brains.
        """

        nodes = (
            self.CORE_BRAINS
            | self.SPECIALIZED_BRAINS
            | self.SUPPORTING_SYSTEMS
        )

        for node in sorted(nodes):
            try:
                self.cognitive_fabric.register_node(
                    node,
                    handler=None,
                )
            except TypeError:
                try:
                    self.cognitive_fabric.register_node(node)
                except Exception:
                    pass
            except Exception:
                pass

    # ==================================================================
    # IDENTITY
    # ==================================================================

    def identity(self) -> Dict[str, Any]:
        """
        Return UNITY identity and architectural role.
        """

        base = {}

        try:
            base = super().identity()
        except Exception:
            base = {
                "brain": self.BRAIN_NAME,
            }

        base.update(
            {
                "brain": self.BRAIN_NAME,
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "role": "SYSTEM_INTEGRATION",
                "integration_brain": True,
                "initialized": self._initialized,
                "core_brains": sorted(self.CORE_BRAINS),
                "specialized_brains": sorted(
                    self.SPECIALIZED_BRAINS
                ),
                "supporting_systems": sorted(
                    self.SUPPORTING_SYSTEMS
                ),
            }
        )

        return base

    # ==================================================================
    # TASK MANAGEMENT
    # ==================================================================

    def create_task(
        self,
        user_message: str,
        objective: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Create a UNITY task context.
        """

        if not self._initialized:
            self.initialize()

        task = self.coordination_engine.create_task(
            user_message=user_message,
            objective=objective,
            metadata=metadata,
        )

        self._last_task_id = getattr(
            task,
            "task_id",
            None,
        )

        return task

    def create_execution(
        self,
        task_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Create a live execution context for a task.
        """

        return self.coordination_engine.create_execution(
            task_id=task_id,
            metadata=metadata,
        )

    # ==================================================================
    # BRAIN REGISTRATION / ACTIVATION
    # ==================================================================

    def register_brain(
        self,
        name: str,
        system_type: str = "BRAIN",
        role: str = "",
        version: str = "unknown",
        capabilities: Optional[Iterable[str]] = None,
        available: bool = True,
        active: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Register a runtime brain or system with UNITY.
        """

        record = self.brain_registry.register(
            name=name,
            system_type=system_type,
            role=role,
            version=version,
            capabilities=capabilities,
            available=available,
            active=active,
            metadata=metadata,
        )

        self.activation_manager.synchronize_registry()

        self.state.set_registered_brains(
            self.brain_registry.names()
        )

        return record

    def activate_brain(
        self,
        name: str,
        reason: str = "",
    ) -> Any:
        """
        Activate a registered brain structurally.
        """

        result = self.activation_manager.activate(
            name=name,
            reason=reason,
        )

        self.state.set_active_brains(
            self.activation_manager.active_names()
        )

        return result

    def deactivate_brain(
        self,
        name: str,
        reason: str = "",
    ) -> Any:
        """
        Deactivate a brain structurally.
        """

        # UNITY itself should not be casually deactivated.
        if str(name).upper() == "UNITY":
            raise ValueError(
                "UNITY cannot be deactivated through the normal "
                "brain activation interface."
            )

        result = self.activation_manager.deactivate(
            name=name,
            reason=reason,
        )

        self.state.set_active_brains(
            self.activation_manager.active_names()
        )

        return result

    # ==================================================================
    # CAPABILITIES
    # ==================================================================

    def require_capabilities(
        self,
        capabilities: Iterable[str],
    ) -> None:
        """
        Record capabilities required for the current UNITY task.

        Capability selection itself belongs to HEROIC/other higher-level
        intelligence. UNITY stores and coordinates the requirement.
        """

        normalized = [
            str(capability).strip().lower()
            for capability in capabilities
            if str(capability).strip()
        ]

        self.state.set_required_capabilities(
            normalized
        )

    # ==================================================================
    # CONTRIBUTIONS
    # ==================================================================

    def collect_contribution(
        self,
        brain: str,
        kind: str,
        content: Any,
        confidence: float = 0.0,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record a cognitive contribution into UNITY state.
        """

        contribution = self.state.record_contribution(
            brain=brain,
            kind=kind,
            content=content,
            confidence=confidence,
            importance=importance,
            metadata=metadata,
        )

        return contribution

    def collect_contributions(
        self,
        contributions: Optional[Iterable[Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Collect multiple already-produced contributions.

        This method does not generate or modify the substantive content.
        """

        collected: List[Dict[str, Any]] = []

        if contributions is None:
            return self.state.contributions()

        for contribution in contributions:
            if isinstance(contribution, dict):
                brain = contribution.get("brain", "UNKNOWN")
                kind = contribution.get("kind", "UNKNOWN")
                content = contribution.get("content")
                confidence = contribution.get(
                    "confidence",
                    0.0,
                )
                importance = contribution.get(
                    "importance",
                    0.5,
                )
                metadata = contribution.get(
                    "metadata",
                    {},
                )
            else:
                brain = getattr(
                    contribution,
                    "brain",
                    "UNKNOWN",
                )
                kind = getattr(
                    contribution,
                    "kind",
                    "UNKNOWN",
                )
                content = getattr(
                    contribution,
                    "content",
                    None,
                )
                confidence = getattr(
                    contribution,
                    "confidence",
                    0.0,
                )
                importance = getattr(
                    contribution,
                    "importance",
                    0.5,
                )
                metadata = getattr(
                    contribution,
                    "metadata",
                    {},
                )

            collected.append(
                self.collect_contribution(
                    brain=brain,
                    kind=kind,
                    content=content,
                    confidence=confidence,
                    importance=importance,
                    metadata=metadata,
                )
            )

        return collected

    # ==================================================================
    # CONTRADICTIONS
    # ==================================================================

    def register_contradiction(
        self,
        conflict_type: str,
        sources: Optional[Iterable[str]] = None,
        claims: Optional[Iterable[Any]] = None,
        evidence: Optional[Iterable[Any]] = None,
        assumptions: Optional[Iterable[Any]] = None,
        severity: str = "MEDIUM",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Register a contradiction for later investigation.
        """

        return self.contradiction_engine.create_conflict(
            conflict_type=conflict_type,
            sources=sources,
            claims=claims,
            evidence=evidence,
            assumptions=assumptions,
            severity=severity,
            metadata=metadata,
        )

    # ==================================================================
    # VERIFICATION
    # ==================================================================

    def request_verification(
        self,
        claim: Any,
        requested_by: str = "UNITY",
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Create a verification request.

        Actual verification belongs to MCVL.
        """

        return self.verification_gateway.create_request(
            claim=claim,
            requested_by=requested_by,
            task_id=task_id,
            metadata=metadata,
        )

    # ==================================================================
    # ROUTING
    # ==================================================================

    def create_route(
        self,
        source: str,
        destination: str,
        capability: str,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        priority: int = 5,
        reason: str = "",
        required_inputs: Optional[Iterable[str]] = None,
        expected_outputs: Optional[Iterable[str]] = None,
        dependencies: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Create a structural route.

        Intelligent destination selection remains outside this method.
        """

        return self.routing_engine.create_route(
            source=source,
            destination=destination,
            capability=capability,
            task_id=task_id,
            correlation_id=correlation_id,
            priority=priority,
            reason=reason,
            required_inputs=required_inputs,
            expected_outputs=expected_outputs,
            dependencies=dependencies,
            metadata=metadata,
        )

    # ==================================================================
    # COMMUNICATION
    # ==================================================================

    def send_message(
        self,
        source: str,
        destination: str,
        message_type: str,
        payload: Any = None,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Send a structured communication message through UNITY.
        """

        envelope = self.communication_protocol.create(
            source=source,
            destination=destination,
            message_type=message_type,
            payload=payload,
            task_id=task_id,
            correlation_id=correlation_id,
            provenance=provenance,
            metadata=metadata,
        )

        return self.message_router.send(
            envelope
        )

    def broadcast_message(
        self,
        source: str,
        message_type: str,
        payload: Any = None,
        targets: Optional[Iterable[str]] = None,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Broadcast structured communication.
        """

        envelope = self.communication_protocol.create(
            source=source,
            destination="*",
            message_type=message_type,
            payload=payload,
            task_id=task_id,
            correlation_id=correlation_id,
            provenance=provenance,
            metadata=metadata,
        )

        return self.message_router.broadcast(
            envelope,
            targets=targets,
        )

    # ==================================================================
    # SYNTHESIS
    # ==================================================================

    def synthesize(
        self,
        task_id: Optional[str] = None,
        user_message: Optional[str] = None,
        additional_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Produce a UNITY synthesis from current cognitive state.

        This is structural synthesis.

        The synthesis engine must not manufacture substantive information
        that was not provided by the cognitive system.
        """

        result = self.synthesis_engine.synthesize(
            task_id=task_id,
            user_message=user_message,
            additional_state=additional_state,
        )

        self._last_integration = result

        self.state.set_synthesis(
            result
        )

        return result

    # ==================================================================
    # DIAGNOSTICS
    # ==================================================================

    def run_diagnostics(self) -> Dict[str, Any]:
        """
        Run complete UNITY system diagnostics.
        """

        return self.system_diagnostics.run()

    def integration_health(self) -> Dict[str, Any]:
        return self.integration_diagnostics.run()

    def fabric_health(self) -> Dict[str, Any]:
        return self.fabric_diagnostics.run()

    # ==================================================================
    # STATE / SNAPSHOT
    # ==================================================================

    def active_brains(self) -> List[str]:
        return self.activation_manager.active_names()

    def registered_brains(self) -> List[str]:
        return self.brain_registry.names()

    def required_capabilities(self) -> List[str]:
        return self.state.required_capabilities()

    def contradictions(self) -> List[Dict[str, Any]]:
        return self.contradiction_engine.to_dict().get(
            "conflicts",
            [],
        )

    def runtime_status(self) -> Dict[str, Any]:
        """
        Return the current UNITY runtime status.
        """

        return {
            "brain": self.BRAIN_NAME,
            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
            "initialized": self._initialized,
            "state_status": self.state.status(),
            "registered_brains": self.registered_brains(),
            "active_brains": self.active_brains(),
            "required_capabilities": (
                self.required_capabilities()
            ),
            "last_task_id": self._last_task_id,
            "has_last_integration": (
                self._last_integration is not None
            ),
        }

    def snapshot(self) -> Dict[str, Any]:
        """
        Return a complete structural UNITY snapshot.
        """

        return {
            "identity": self.identity(),
            "runtime": self.runtime_status(),
            "state": self.state.snapshot(),
            "brain_registry": self.brain_registry.to_dict(),
            "capability_registry": (
                self.capability_registry.to_dict()
            ),
            "activation": (
                self.activation_manager.to_dict()
            ),
            "routing": self.routing_engine.to_dict(),
            "coordination": (
                self.coordination_engine.to_dict()
            ),
            "contradictions": (
                self.contradiction_engine.to_dict()
            ),
            "verification": (
                self.verification_gateway.to_dict()
            ),
            "communication": {
                "fabric": self.cognitive_fabric.diagnostics(),
                "router": self.message_router.diagnostics(),
                "events": self.event_dispatcher.diagnostics(),
                "protocol": (
                    self.communication_protocol.diagnostics()
                ),
            },
            "synthesis": (
                self.synthesis_engine.diagnostics()
            ),
            "diagnostics": (
                self.system_diagnostics.diagnostics()
            ),
        }

    # ==================================================================
    # VALIDATION
    # ==================================================================

    def validate(self) -> Dict[str, Any]:
        """
        Validate the structural UNITY runtime.

        Validation checks architecture integrity only.
        """

        errors: List[str] = []
        warnings: List[str] = []

        components = {
            "state": self.state,
            "brain_registry": self.brain_registry,
            "capability_registry": self.capability_registry,
            "activation_manager": self.activation_manager,
            "routing_engine": self.routing_engine,
            "coordination_engine": self.coordination_engine,
            "contradiction_engine": self.contradiction_engine,
            "verification_gateway": self.verification_gateway,
            "synthesis_engine": self.synthesis_engine,
            "cognitive_fabric": self.cognitive_fabric,
            "message_router": self.message_router,
            "event_dispatcher": self.event_dispatcher,
            "communication_protocol": (
                self.communication_protocol
            ),
            "system_diagnostics": self.system_diagnostics,
        }

        for name, component in components.items():
            if component is None:
                errors.append(
                    f"UNITY component is missing: {name}"
                )
                continue

            validator = getattr(
                component,
                "validate",
                None,
            )

            if not callable(validator):
                warnings.append(
                    f"{name} does not expose validate()."
                )
                continue

            try:
                result = validator()

                if isinstance(result, dict):
                    errors.extend(
                        result.get("errors", [])
                    )

            except Exception as exc:
                errors.append(
                    f"{name} validation failed: {exc}"
                )

        # --------------------------------------------------------------
        # Architecture identity checks
        # --------------------------------------------------------------

        registered = set(
            self.brain_registry.names()
        )

        required_architecture = (
            self.CORE_BRAINS
            | self.SPECIALIZED_BRAINS
            | self.SUPPORTING_SYSTEMS
        )

        missing = sorted(
            required_architecture - registered
        )

        if missing:
            errors.append(
                "Required VALE architecture nodes are missing "
                f"from the registry: {missing}"
            )

        # --------------------------------------------------------------
        # UNITY activation check
        # --------------------------------------------------------------

        if self._initialized:
            active = set(
                self.activation_manager.active_names()
            )

            if "UNITY" not in active:
                errors.append(
                    "UNITY runtime is initialized but UNITY "
                    "is not active."
                )

        return {
            "valid": not errors,
            "status": (
                "INVALID"
                if errors
                else (
                    "VALID_WITH_WARNINGS"
                    if warnings
                    else "VALID"
                )
            ),
            "errors": errors,
            "warnings": warnings,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    # ==================================================================
    # MAIN BRAIN INTERFACE
    # ==================================================================

    def think(
        self,
        state: Any = None,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        UNITY cognitive entry point.

        Compatibility is intentionally broad because the existing
        VALEBrainInterface / BrainNetwork may call think(state), while
        direct runtime callers may provide user_message/context.

        IMPORTANT:

        UNITY does not perform the substantive reasoning of HEROIC,
        ALPHA, LEGEND, MARCO, FEELING, or MCVL here.

        This method establishes the shared task/integration context and
        returns the resulting UNITY integration state.
        """

        if not self._initialized:
            self.initialize()

        # --------------------------------------------------------------
        # Resolve incoming state
        # --------------------------------------------------------------

        incoming_state = state

        if incoming_state is not None:
            # If an external VALEBrainState was supplied, keep it as the
            # underlying state when possible.
            try:
                if hasattr(
                    incoming_state,
                    "user_message",
                ):
                    if not user_message:
                        user_message = (
                            incoming_state.user_message
                        )
            except Exception:
                pass

        if not user_message:
            user_message = kwargs.get(
                "message",
                "",
            )

        if user_message is None:
            user_message = ""

        # --------------------------------------------------------------
        # Create task
        # --------------------------------------------------------------

        task = self.create_task(
            user_message=str(user_message),
            objective=(
                context.get("objective")
                if isinstance(context, dict)
                else None
            ),
            metadata=(
                context
                if isinstance(context, dict)
                else {}
            ),
        )

        task_id = getattr(
            task,
            "task_id",
            None,
        )

        # --------------------------------------------------------------
        # Shared state
        # --------------------------------------------------------------

        self.state.set(
            "unity.runtime.last_user_message",
            str(user_message),
        )

        if context:
            self.state.set(
                "unity.runtime.request_context",
                dict(context),
            )

        # --------------------------------------------------------------
        # Start task if supported
        # --------------------------------------------------------------

        try:
            self.coordination_engine.start_task(
                task_id
            )
        except Exception:
            pass

        # --------------------------------------------------------------
        # Current structural state
        # --------------------------------------------------------------

        integration_state = self.state.snapshot()

        diagnostics = self.run_diagnostics()

        result = {
            "brain": "UNITY",
            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
            "task_id": task_id,
            "status": "INTEGRATION_READY",
            "user_message": str(user_message),
            "active_brains": self.active_brains(),
            "required_capabilities": (
                self.required_capabilities()
            ),
            "integration_state": integration_state,
            "diagnostics": diagnostics,
        }

        self._last_integration = result

        return result

    # ==================================================================
    # MESSAGE RECEIVING
    # ==================================================================

    def receive_message(
        self,
        message: Any,
        state: Any = None,
        source_brain: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Receive a structured message into UNITY.

        The message is recorded as integration/communication state.

        UNITY does not automatically interpret the substantive meaning of
        the message here.
        """

        if not self._initialized:
            self.initialize()

        source = (
            str(source_brain).upper()
            if source_brain
            else "UNKNOWN"
        )

        self.state.event(
            event_type="UNITY_MESSAGE_RECEIVED",
            source=source,
            target="UNITY",
            payload={
                "message": message,
                "payload": payload or {},
            },
        )

        self.state.set(
            "unity.runtime.last_message",
            {
                "source": source,
                "message": message,
                "payload": payload or {},
            },
        )

        return {
            "status": "RECEIVED",
            "source": source,
            "destination": "UNITY",
            "message": message,
            "payload": payload or {},
        }

    # ==================================================================
    # FINAL DIAGNOSTIC SUMMARY
    # ==================================================================

    def diagnostics(self) -> Dict[str, Any]:
        """
        Return a compact but complete UNITY diagnostic representation.
        """

        system_health = self.system_diagnostics.run()

        return {
            "brain": self.BRAIN_NAME,
            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
            "initialized": self._initialized,
            "runtime": self.runtime_status(),
            "validation": self.validate(),
            "system_health": system_health,
            "integration": (
                self.integration_diagnostics.diagnostics()
            ),
            "fabric": (
                self.fabric_diagnostics.diagnostics()
            ),
        }


# ----------------------------------------------------------------------
# Compatibility alias
# ----------------------------------------------------------------------

UnityIntegrationBrain = UnityBrain


__all__ = [
    "UnityBrain",
    "UnityIntegrationBrain",
    "VERSION",
    "ARCHITECTURE_STAGE",
]
