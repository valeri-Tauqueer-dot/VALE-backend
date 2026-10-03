"""
VALE UNITY — State Integrator

The State Integrator converts validated cognitive contributions and integration
state into one coherent UNITY cognitive state representation.

Responsibilities:
    - collect relevant cognitive state
    - normalize contributions
    - preserve provenance
    - preserve confidence and importance
    - preserve contradictions
    - preserve verification status
    - build a unified state snapshot

The State Integrator does NOT:
    - perform independent reasoning
    - decide which brain is correct
    - fabricate missing information
    - silently resolve contradictions
    - replace MCVL
    - generate the final user-facing response

Version: 0.1.0
Architecture Stage: UNITY_STATE_INTEGRATION_FOUNDATION
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_STATE_INTEGRATION_FOUNDATION"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(value: Any, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = minimum

    return max(minimum, min(maximum, value))


class StateIntegrator:
    """
    Builds a coherent structural representation of VALE cognitive state.

    This class intentionally preserves uncertainty rather than forcing
    conflicting information into a single conclusion.
    """

    def __init__(self, state: Optional[Any] = None) -> None:
        self.state = state
        self._lock = RLock()

        self._last_integrated: Optional[Dict[str, Any]] = None
        self._integration_count = 0

    # ------------------------------------------------------------------
    # Contribution normalization
    # ------------------------------------------------------------------

    def normalize_contribution(
        self,
        contribution: Any,
    ) -> Dict[str, Any]:
        """
        Convert a BrainContribution or dictionary into a stable structure.
        """

        if hasattr(contribution, "to_dict"):
            raw = contribution.to_dict()
        elif isinstance(contribution, dict):
            raw = dict(contribution)
        else:
            raw = {
                "content": str(contribution),
            }

        brain = str(
            raw.get("brain", "UNKNOWN")
        ).strip().upper()

        kind = str(
            raw.get("kind", "unknown")
        ).strip().lower()

        content = raw.get("content")

        confidence = _clamp(
            raw.get("confidence", 0.0)
        )

        importance = _clamp(
            raw.get("importance", 0.5)
        )

        timestamp = raw.get(
            "timestamp",
            _utc_now(),
        )

        metadata = raw.get(
            "metadata",
            {},
        )

        if not isinstance(metadata, dict):
            metadata = {
                "raw_metadata": metadata,
            }

        return {
            "brain": brain,
            "kind": kind,
            "content": content,
            "confidence": confidence,
            "importance": importance,
            "timestamp": timestamp,
            "metadata": metadata,
        }

    def normalize_contributions(
        self,
        contributions: Iterable[Any],
    ) -> List[Dict[str, Any]]:
        return [
            self.normalize_contribution(item)
            for item in contributions
        ]

    # ------------------------------------------------------------------
    # Integration
    # ------------------------------------------------------------------

    def integrate(
        self,
        contributions: Optional[Iterable[Any]] = None,
        active_brains: Optional[Iterable[str]] = None,
        required_capabilities: Optional[Iterable[str]] = None,
        contradictions: Optional[Iterable[Any]] = None,
        verification: Optional[Dict[str, Any]] = None,
        shared_state: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Construct a unified cognitive-state representation.

        No conclusion is selected merely because one contribution has higher
        confidence. Confidence remains provenance metadata for later reasoning
        and verification.
        """

        with self._lock:
            normalized_contributions = self.normalize_contributions(
                contributions or []
            )

            normalized_brains = sorted(
                {
                    str(brain).strip().upper()
                    for brain in (active_brains or [])
                    if str(brain).strip()
                }
            )

            normalized_capabilities = sorted(
                {
                    str(capability).strip().lower()
                    for capability in (required_capabilities or [])
                    if str(capability).strip()
                }
            )

            normalized_contradictions = list(
                contradictions or []
            )

            verification_state = dict(
                verification or {}
            )

            shared = dict(
                shared_state or {}
            )

            contribution_by_brain: Dict[str, List[Dict[str, Any]]] = {}

            for contribution in normalized_contributions:
                brain = contribution["brain"]

                contribution_by_brain.setdefault(
                    brain,
                    [],
                ).append(contribution)

            integrated = {
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "integrated_at": _utc_now(),
                "integration_count": self._integration_count + 1,

                "task_id": task_id,

                "active_brains": normalized_brains,
                "required_capabilities": normalized_capabilities,

                "contributions": normalized_contributions,
                "contributions_by_brain": contribution_by_brain,

                "contradictions": normalized_contradictions,

                "verification": verification_state,

                "shared_state": shared,

                "metadata": dict(metadata or {}),

                "quality": {
                    "contribution_count": len(
                        normalized_contributions
                    ),
                    "brain_count": len(
                        {
                            item["brain"]
                            for item in normalized_contributions
                        }
                    ),
                    "contradiction_count": len(
                        normalized_contradictions
                    ),
                    "verification_available": bool(
                        verification_state
                    ),
                },
            }

            self._integration_count += 1
            self._last_integrated = integrated

            self._publish(integrated)

            return integrated

    # ------------------------------------------------------------------
    # State-based integration
    # ------------------------------------------------------------------

    def integrate_state(
        self,
        state: Any,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Integrate directly from UnityIntegrationState-like objects.
        """

        if state is None:
            raise ValueError("State cannot be None.")

        if hasattr(state, "snapshot"):
            snapshot = state.snapshot()
        elif hasattr(state, "to_dict"):
            snapshot = state.to_dict()
        elif isinstance(state, dict):
            snapshot = dict(state)
        else:
            raise TypeError(
                "State must provide snapshot(), to_dict(), or be a dictionary."
            )

        unity_state = snapshot.get(
            "unity",
            snapshot,
        )

        integration = unity_state.get(
            "integration",
            {},
        )

        return self.integrate(
            contributions=unity_state.get(
                "brain_contributions",
                [],
            ),
            active_brains=unity_state.get(
                "active_brains",
                [],
            ),
            required_capabilities=unity_state.get(
                "required_capabilities",
                [],
            ),
            contradictions=unity_state.get(
                "contradictions",
                [],
            ),
            verification=unity_state.get(
                "verification",
                {},
            ),
            shared_state=unity_state.get(
                "shared",
                integration.get(
                    "shared",
                    {},
                ),
            ),
            task_id=task_id,
            metadata={
                "source": "UNITY_STATE",
            },
        )

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def last_integrated(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._last_integrated is None:
                return None

            return dict(self._last_integrated)

    def clear(self) -> None:
        with self._lock:
            self._last_integrated = None

    # ------------------------------------------------------------------
    # State publication
    # ------------------------------------------------------------------

    def _publish(
        self,
        integrated: Dict[str, Any],
    ) -> None:
        if self.state is None:
            return

        try:
            if hasattr(self.state, "set"):
                self.state.set(
                    "unity.synthesis.integrated_state",
                    integrated,
                )

            if hasattr(self.state, "set_synthesis"):
                self.state.set_synthesis(
                    {
                        "status": "INTEGRATED",
                        "integrated_at": integrated["integrated_at"],
                        "contribution_count": integrated[
                            "quality"
                        ]["contribution_count"],
                        "contradiction_count": integrated[
                            "quality"
                        ]["contradiction_count"],
                    }
                )

        except Exception:
            # Integration state remains locally valid even if publication
            # into a shared state object fails.
            return

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def validate(
        self,
        integrated: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        target = integrated or self._last_integrated

        errors: List[str] = []
        warnings: List[str] = []

        if target is None:
            warnings.append(
                "No integrated cognitive state currently exists."
            )

            return {
                "valid": True,
                "errors": errors,
                "warnings": warnings,
            }

        if "contributions" not in target:
            errors.append(
                "Integrated state is missing contributions."
            )

        if "contradictions" not in target:
            errors.append(
                "Integrated state is missing contradictions."
            )

        if "verification" not in target:
            errors.append(
                "Integrated state is missing verification state."
            )

        if target.get("quality", {}).get(
            "contradiction_count",
            0,
        ) > 0:
            warnings.append(
                "Integrated state contains unresolved contradictions."
            )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    def diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            validation = self.validate()

            return {
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "integration_count": self._integration_count,
                "has_integrated_state": (
                    self._last_integrated is not None
                ),
                "validation": validation,
  }
