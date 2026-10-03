"""
VALE UNITY — Synthesis Engine

The Synthesis Engine is the structural coordinator for UNITY synthesis.

Pipeline:

    cognitive contributions
            ↓
    StateIntegrator
            ↓
    integrated UNITY state
            ↓
    ResponseIntegrator
            ↓
    structured UNITY response

Important architectural boundary:

The Synthesis Engine does NOT:
    - replace HEROIC
    - replace ALPHA
    - perform specialized brain reasoning
    - perform MCVL verification
    - force consensus
    - select a winner from contradictory brains
    - fabricate missing evidence

Its responsibility is to make the transition from distributed cognitive
information to one coherent UNITY representation explicit and traceable.

Version: 0.1.0
Architecture Stage: UNITY_SYNTHESIS_ENGINE_FOUNDATION
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional

from .response_integrator import ResponseIntegrator
from .state_integrator import StateIntegrator


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_SYNTHESIS_ENGINE_FOUNDATION"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SynthesisEngine:
    """
    Structural synthesis coordinator for UNITY.
    """

    def __init__(
        self,
        state: Optional[Any] = None,
        state_integrator: Optional[StateIntegrator] = None,
        response_integrator: Optional[ResponseIntegrator] = None,
    ) -> None:
        self.state = state

        self.state_integrator = (
            state_integrator
            if state_integrator is not None
            else StateIntegrator(state=state)
        )

        self.response_integrator = (
            response_integrator
            if response_integrator is not None
            else ResponseIntegrator()
        )

        self._lock = RLock()

        self._synthesis_count = 0
        self._last_synthesis: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Main synthesis pipeline
    # ------------------------------------------------------------------

    def synthesize(
        self,
        contributions: Optional[Iterable[Any]] = None,
        active_brains: Optional[Iterable[str]] = None,
        required_capabilities: Optional[Iterable[str]] = None,
        contradictions: Optional[Iterable[Any]] = None,
        verification: Optional[Dict[str, Any]] = None,
        shared_state: Optional[Dict[str, Any]] = None,
        answer: Any = None,
        summary: Optional[str] = None,
        uncertainty: Optional[Iterable[str]] = None,
        limitations: Optional[Iterable[str]] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the structural UNITY synthesis pipeline.
        """

        with self._lock:
            integrated_state = self.state_integrator.integrate(
                contributions=contributions,
                active_brains=active_brains,
                required_capabilities=required_capabilities,
                contradictions=contradictions,
                verification=verification,
                shared_state=shared_state,
                task_id=task_id,
                metadata=metadata,
            )

            integrated_response = (
                self.response_integrator.integrate(
                    integrated_state=integrated_state,
                    answer=answer,
                    summary=summary,
                    uncertainty=uncertainty,
                    limitations=limitations,
                    metadata={
                        **dict(metadata or {}),
                        "synthesis_engine": "UNITY",
                    },
                )
            )

            self._synthesis_count += 1

            synthesis = {
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "synthesis_id": (
                    f"UNITY-SYNTHESIS-{self._synthesis_count}"
                ),
                "created_at": _utc_now(),

                "status": integrated_response.get(
                    "status",
                    "STRUCTURED",
                ),

                "task_id": task_id,

                "integrated_state": integrated_state,

                "response": integrated_response,

                "verification": dict(
                    verification or {}
                ),

                "contradictions": list(
                    contradictions or []
                ),

                "metadata": dict(
                    metadata or {}
                ),
            }

            self._last_synthesis = synthesis

            self._publish(synthesis)

            return synthesis

    # ------------------------------------------------------------------
    # State-driven synthesis
    # ------------------------------------------------------------------

    def synthesize_from_state(
        self,
        state: Optional[Any] = None,
        answer: Any = None,
        summary: Optional[str] = None,
        uncertainty: Optional[Iterable[str]] = None,
        limitations: Optional[Iterable[str]] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize directly from UnityIntegrationState-like state.
        """

        source_state = state or self.state

        if source_state is None:
            raise ValueError(
                "No UNITY state is available for synthesis."
            )

        integrated_state = (
            self.state_integrator.integrate_state(
                source_state,
                task_id=task_id,
            )
        )

        return self.synthesize(
            contributions=integrated_state.get(
                "contributions",
                [],
            ),
            active_brains=integrated_state.get(
                "active_brains",
                [],
            ),
            required_capabilities=integrated_state.get(
                "required_capabilities",
                [],
            ),
            contradictions=integrated_state.get(
                "contradictions",
                [],
            ),
            verification=integrated_state.get(
                "verification",
                {},
            ),
            shared_state=integrated_state.get(
                "shared_state",
                {},
            ),
            answer=answer,
            summary=summary,
            uncertainty=uncertainty,
            limitations=limitations,
            task_id=task_id or integrated_state.get(
                "task_id"
            ),
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def last_synthesis(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._last_synthesis is None:
                return None

            return dict(self._last_synthesis)

    def clear(self) -> None:
        with self._lock:
            self._last_synthesis = None

    # ------------------------------------------------------------------
    # State publication
    # ------------------------------------------------------------------

    def _publish(
        self,
        synthesis: Dict[str, Any],
    ) -> None:
        if self.state is None:
            return

        try:
            if hasattr(self.state, "set_synthesis"):
                self.state.set_synthesis(
                    {
                        "status": synthesis["status"],
                        "synthesis_id": synthesis[
                            "synthesis_id"
                        ],
                        "created_at": synthesis[
                            "created_at"
                        ],
                        "response_status": synthesis[
                            "response"
                        ].get("status"),
                    }
                )

            if hasattr(self.state, "set"):
                self.state.set(
                    "unity.synthesis.last_result",
                    synthesis,
                )

            if hasattr(self.state, "event"):
                self.state.event(
                    event_type="UNITY_SYNTHESIS_COMPLETED",
                    source="UNITY",
                    target=None,
                    payload={
                        "synthesis_id": synthesis[
                            "synthesis_id"
                        ],
                        "status": synthesis[
                            "status"
                        ],
                    },
                )

        except Exception:
            # Synthesis itself remains available even if state publication
            # fails.
            return

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(
        self,
        synthesis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        target = synthesis or self._last_synthesis

        errors: List[str] = []
        warnings: List[str] = []

        if target is None:
            warnings.append(
                "No synthesis result currently exists."
            )

            return {
                "valid": True,
                "errors": errors,
                "warnings": warnings,
            }

        if "integrated_state" not in target:
            errors.append(
                "Synthesis is missing integrated_state."
            )

        if "response" not in target:
            errors.append(
                "Synthesis is missing response."
            )

        if "verification" not in target:
            errors.append(
                "Synthesis is missing verification state."
            )

        if target.get("contradictions"):
            warnings.append(
                "Synthesis contains unresolved contradictions."
            )

        if target.get("response", {}).get("answer") is None:
            warnings.append(
                "Synthesis does not contain a substantive answer."
            )

        state_validation = (
            self.state_integrator.validate(
                target.get("integrated_state")
            )
        )

        response_validation = (
            self.response_integrator.validate(
                target.get("response")
            )
        )

        errors.extend(
            f"state_integrator: {error}"
            for error in state_validation["errors"]
        )

        errors.extend(
            f"response_integrator: {error}"
            for error in response_validation["errors"]
        )

        warnings.extend(
            f"state_integrator: {warning}"
            for warning in state_validation["warnings"]
        )

        warnings.extend(
            f"response_integrator: {warning}"
            for warning in response_validation["warnings"]
        )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "synthesis_count": self._synthesis_count,
                "has_last_synthesis": (
                    self._last_synthesis is not None
                ),
                "state_integrator": (
                    self.state_integrator.diagnostics()
                ),
                "response_integrator": (
                    self.response_integrator.diagnostics()
                ),
                "validation": self.validate(),
  }
