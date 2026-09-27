"""
VALE UNITY — INTEGRATION STATE
==============================

This module provides UNITY's system-wide integration state layer.

Important architectural distinction
------------------------------------

VALEBrainState
    Generic shared working state for one VALE task.

UNITY Integration State
    Structured system-level integration state maintained by UNITY.

UNITY does not replace VALEBrainState.

Instead:

    VALEBrainState
          |
          v
    UNITY Integration State
          |
    +-----+------+----------------+
    |            |                |
    State      Coordination    Verification
    |            |                |
    +------------+----------------+
                 |
                 v
            ONE VALE STATE

Design principles
-----------------

1. The state belongs to the current cognitive task.
2. UNITY maintains integration metadata around that state.
3. Brain registration is different from brain activation.
4. Contributions are different from verified conclusions.
5. Contradictions are preserved instead of hidden.
6. Verification status is explicitly tracked.
7. Synthesis status is explicitly tracked.
8. State updates are observable through events.
9. No final answer is fabricated by this layer.
10. Future Cognitive Fabric modules will build on this state layer.

Current stage
-------------

UNITY_INTEGRATION_STATE_FOUNDATION

This module intentionally does not implement:

- final synthesis
- MCVL verification logic
- HEROIC objective reasoning
- ALPHA execution orchestration
- Supervisor health logic
- Memory implementation
- Knowledge implementation
- Evolution implementation

Those remain separate systems.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def utc_now() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class UnityIntegrationState:
    """
    Structured UNITY state for one VALE cognitive task.

    This class wraps the existing VALEBrainState rather than replacing it.
    """

    VERSION = "0.1.0"

    ARCHITECTURE_STAGE = "UNITY_INTEGRATION_STATE_FOUNDATION"

    def __init__(self, state: Any):
        self.state = state

        self._ensure_foundation()

    # ==================================================================
    # FOUNDATION
    # ==================================================================

    def _ensure_foundation(self) -> None:
        """
        Create UNITY integration fields if they do not already exist.
        """

        if self.state.get("unity.integration", None) is None:
            self.state.set(
                "unity.integration",
                {
                    "version": self.VERSION,
                    "architecture_stage": self.ARCHITECTURE_STAGE,
                    "status": "INITIALIZED",
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                },
            )

        defaults = {
            "unity.active_brains": [],
            "unity.registered_brains": [],
            "unity.required_capabilities": [],
            "unity.brain_contributions": [],
            "unity.contradictions": [],
            "unity.verification": {
                "status": "NOT_STARTED",
                "verified": False,
                "confidence": 0.0,
                "details": {},
            },
            "unity.synthesis": {
                "status": "NOT_STARTED",
                "ready": False,
                "result_available": False,
            },
            "unity.routing": {
                "status": "NOT_STARTED",
                "routes": [],
            },
            "unity.coordination": {
                "status": "NOT_STARTED",
                "active": False,
            },
        }

        for key, value in defaults.items():
            if self.state.get(key, None) is None:
                self.state.set(key, value)

    # ==================================================================
    # GENERIC ACCESS
    # ==================================================================

    def get(self, key: str, default: Any = None) -> Any:
        """
        Read a UNITY integration field.
        """

        return self.state.get(
            f"unity.{key}",
            default,
        )

    def set(self, key: str, value: Any) -> None:
        """
        Set a UNITY integration field.
        """

        self.state.set(
            f"unity.{key}",
            value,
        )

        self._touch()

    def _touch(self) -> None:
        """
        Update integration metadata timestamp.
        """

        integration = self.state.get(
            "unity.integration",
            {},
        )

        if not isinstance(integration, dict):
            integration = {}

        integration["updated_at"] = utc_now()

        self.state.set(
            "unity.integration",
            integration,
        )

    # ==================================================================
    # STATUS
    # ==================================================================

    def status(self) -> str:
        """
        Return current UNITY integration status.
        """

        integration = self.state.get(
            "unity.integration",
            {},
        )

        if not isinstance(integration, dict):
            return "UNKNOWN"

        return str(
            integration.get(
                "status",
                "UNKNOWN",
            )
        )

    def set_status(self, status: str) -> str:
        """
        Update UNITY integration status.
        """

        value = str(status).upper()

        integration = self.state.get(
            "unity.integration",
            {},
        )

        if not isinstance(integration, dict):
            integration = {}

        integration["status"] = value
        integration["updated_at"] = utc_now()

        self.state.set(
            "unity.integration",
            integration,
        )

        self.event(
            "unity_integration_status_changed",
            payload={
                "status": value,
            },
        )

        return value

    # ==================================================================
    # BRAIN REGISTRY
    # ==================================================================

    def set_registered_brains(
        self,
        brain_names: Iterable[str],
    ) -> List[str]:
        """
        Record brains known to the current VALE runtime.

        Registration does not mean activation.
        """

        normalized = self._normalize_names(
            brain_names
        )

        self.set(
            "registered_brains",
            normalized,
        )

        self.event(
            "unity_brain_registry_updated",
            payload={
                "registered_brains": normalized,
            },
        )

        return normalized

    def registered_brains(self) -> List[str]:
        """
        Return registered brains.
        """

        value = self.get(
            "registered_brains",
            [],
        )

        return list(value) if isinstance(value, list) else []

    # ==================================================================
    # ACTIVE BRAINS
    # ==================================================================

    def set_active_brains(
        self,
        brain_names: Iterable[str],
    ) -> List[str]:
        """
        Record brains participating in the current cognitive task.
        """

        normalized = self._normalize_names(
            brain_names
        )

        self.set(
            "active_brains",
            normalized,
        )

        self.event(
            "unity_active_brains_changed",
            payload={
                "active_brains": normalized,
            },
        )

        return normalized

    def active_brains(self) -> List[str]:
        """
        Return currently active brains.
        """

        value = self.get(
            "active_brains",
            [],
        )

        return list(value) if isinstance(value, list) else []

    # ==================================================================
    # CAPABILITIES
    # ==================================================================

    def set_required_capabilities(
        self,
        capabilities: Iterable[str],
    ) -> List[str]:
        """
        Record capabilities required for the current task.

        HEROIC will eventually determine these requirements.
        UNITY stores them as shared integration state.
        """

        normalized: List[str] = []

        for capability in capabilities:
            value = str(
                capability
            ).strip().lower()

            if value and value not in normalized:
                normalized.append(value)

        self.set(
            "required_capabilities",
            normalized,
        )

        self.event(
            "unity_required_capabilities_changed",
            payload={
                "required_capabilities": normalized,
            },
        )

        return normalized

    def required_capabilities(self) -> List[str]:
        """
        Return current required capabilities.
        """

        value = self.get(
            "required_capabilities",
            [],
        )

        return list(value) if isinstance(value, list) else []

    # ==================================================================
    # CONTRIBUTIONS
    # ==================================================================

    def record_contribution(
        self,
        brain: str,
        kind: str,
        content: Any,
        confidence: float = 0.0,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record a brain contribution in UNITY state.

        A contribution is NOT automatically a verified conclusion.
        """

        item = {
            "brain": str(brain).upper(),
            "kind": str(kind),
            "content": content,
            "confidence": self._clamp(confidence),
            "importance": self._clamp(importance),
            "metadata": metadata or {},
            "timestamp": utc_now(),
        }

        contributions = self.get(
            "brain_contributions",
            [],
        )

        if not isinstance(contributions, list):
            contributions = []

        contributions.append(item)

        self.set(
            "brain_contributions",
            contributions,
        )

        self.event(
            "unity_contribution_recorded",
            source=item["brain"],
            payload={
                "kind": item["kind"],
                "confidence": item["confidence"],
                "importance": item["importance"],
            },
        )

        return item

    def contributions(self) -> List[Dict[str, Any]]:
        """
        Return all recorded brain contributions.
        """

        value = self.get(
            "brain_contributions",
            [],
        )

        return list(value) if isinstance(value, list) else []

    def contributions_from(
        self,
        brain: str,
    ) -> List[Dict[str, Any]]:
        """
        Return contributions from one brain.
        """

        target = str(
            brain
        ).upper()

        return [
            item
            for item in self.contributions()
            if str(
                item.get(
                    "brain",
                    "",
                )
            ).upper()
            == target
        ]

    # ==================================================================
    # CONTRADICTIONS
    # ==================================================================

    def add_contradiction(
        self,
        left_source: str,
        right_source: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Register an unresolved contradiction.

        UNITY preserves the disagreement.

        It does not decide which side is correct.
        """

        contradictions = self.get(
            "contradictions",
            [],
        )

        if not isinstance(contradictions, list):
            contradictions = []

        item = {
            "id": f"contradiction-{len(contradictions) + 1}",
            "left_source": str(
                left_source
            ).upper(),
            "right_source": str(
                right_source
            ).upper(),
            "description": str(
                description
            ),
            "details": details or {},
            "status": "OPEN",
            "created_at": utc_now(),
            "resolved_at": None,
        }

        contradictions.append(item)

        self.set(
            "contradictions",
            contradictions,
        )

        self.event(
            "unity_contradiction_detected",
            payload=item,
        )

        return item

    def contradictions(
        self,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return contradictions, optionally filtered by status.
        """

        items = self.get(
            "contradictions",
            [],
        )

        if not isinstance(items, list):
            return []

        if status is None:
            return list(items)

        target = str(
            status
        ).upper()

        return [
            item
            for item in items
            if str(
                item.get(
                    "status",
                    "",
                )
            ).upper()
            == target
        ]

    def resolve_contradiction(
        self,
        contradiction_id: str,
        resolution: Optional[str] = None,
    ) -> bool:
        """
        Mark a contradiction as resolved.

        The actual reasoning/verifying system must determine the
        resolution before this method is called.
        """

        contradictions = self.contradictions()

        changed = False

        for item in contradictions:
            if item.get("id") == contradiction_id:
                item["status"] = "RESOLVED"
                item["resolution"] = resolution
                item["resolved_at"] = utc_now()
                changed = True
                break

        if changed:
            self.set(
                "contradictions",
                contradictions,
            )

            self.event(
                "unity_contradiction_resolved",
                payload={
                    "contradiction_id": contradiction_id,
                    "resolution": resolution,
                },
            )

        return changed

    # ==================================================================
    # VERIFICATION
    # ==================================================================

    def set_verification(
        self,
        status: str,
        verified: bool = False,
        confidence: float = 0.0,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store verification metadata.

        MCVL owns verification intelligence.

        UNITY stores the resulting verification state.
        """

        result = {
            "status": str(
                status
            ).upper(),
            "verified": bool(
                verified
            ),
            "confidence": self._clamp(
                confidence
            ),
            "details": details or {},
            "updated_at": utc_now(),
        }

        self.set(
            "verification",
            result,
        )

        self.event(
            "unity_verification_updated",
            payload=result,
        )

        return result

    def verification(self) -> Dict[str, Any]:
        """
        Return current verification state.
        """

        value = self.get(
            "verification",
            {},
        )

        return dict(value) if isinstance(value, dict) else {}

    # ==================================================================
    # ROUTING STATE
    # ==================================================================

    def set_routing(
        self,
        status: str,
        routes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Store routing metadata.

        This is state only.

        The future Cognitive Fabric routing engine will perform
        actual routing intelligence.
        """

        result = {
            "status": str(
                status
            ).upper(),
            "routes": list(
                routes or []
            ),
            "updated_at": utc_now(),
        }

        self.set(
            "routing",
            result,
        )

        self.event(
            "unity_routing_state_updated",
            payload=result,
        )

        return result

    def routing(self) -> Dict[str, Any]:
        """
        Return routing state.
        """

        value = self.get(
            "routing",
            {},
        )

        return dict(value) if isinstance(value, dict) else {}

    # ==================================================================
    # COORDINATION STATE
    # ==================================================================

    def set_coordination(
        self,
        status: str,
        active: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store system-wide coordination metadata.
        """

        result = {
            "status": str(
                status
            ).upper(),
            "active": bool(
                active
            ),
            "details": details or {},
            "updated_at": utc_now(),
        }

        self.set(
            "coordination",
            result,
        )

        self.event(
            "unity_coordination_state_updated",
            payload=result,
        )

        return result

    def coordination(self) -> Dict[str, Any]:
        """
        Return coordination state.
        """

        value = self.get(
            "coordination",
            {},
        )

        return dict(value) if isinstance(value, dict) else {}

    # ==================================================================
    # SYNTHESIS STATE
    # ==================================================================

    def set_synthesis(
        self,
        status: str,
        ready: bool = False,
        result_available: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store synthesis lifecycle state.

        This does NOT perform synthesis.
        """

        result = {
            "status": str(
                status
            ).upper(),
            "ready": bool(
                ready
            ),
            "result_available": bool(
                result_available
            ),
            "metadata": metadata or {},
            "updated_at": utc_now(),
        }

        self.set(
            "synthesis",
            result,
        )

        self.event(
            "unity_synthesis_state_updated",
            payload=result,
        )

        return result

    def synthesis(self) -> Dict[str, Any]:
        """
        Return current synthesis state.
        """

        value = self.get(
            "synthesis",
            {},
        )

        return dict(value) if isinstance(value, dict) else {}

    # ==================================================================
    # EVENTS
    # ==================================================================

    def event(
        self,
        event_type: str,
        source: str = "UNITY",
        target: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record an integration event in the underlying VALEBrainState.
        """

        self.state.event(
            event_type=event_type,
            source=str(
                source
            ).upper(),
            target=(
                str(target).upper()
                if target is not None
                else None
            ),
            payload=payload or {},
        )

    # ==================================================================
    # SNAPSHOT
    # ==================================================================

    def snapshot(self) -> Dict[str, Any]:
        """
        Return a complete UNITY integration snapshot.
        """

        return {
            "version": self.VERSION,
            "architecture_stage": self.ARCHITECTURE_STAGE,
            "task_id": getattr(
                self.state,
                "task_id",
                None,
            ),
            "status": self.status(),
            "registered_brains": self.registered_brains(),
            "active_brains": self.active_brains(),
            "required_capabilities": self.required_capabilities(),
            "brain_contributions": self.contributions(),
            "contradictions": self.contradictions(),
            "verification": self.verification(),
            "routing": self.routing(),
            "coordination": self.coordination(),
            "synthesis": self.synthesis(),
            "captured_at": utc_now(),
        }

    # ==================================================================
    # VALIDATION
    # ==================================================================

    def validate(self) -> Dict[str, Any]:
        """
        Validate the structural integrity of UNITY state.

        This is not MCVL verification.

        It checks whether required UNITY state structures exist and
        have the expected basic types.
        """

        errors: List[str] = []

        if not isinstance(
            self.registered_brains(),
            list,
        ):
            errors.append(
                "registered_brains must be a list"
            )

        if not isinstance(
            self.active_brains(),
            list,
        ):
            errors.append(
                "active_brains must be a list"
            )

        if not isinstance(
            self.required_capabilities(),
            list,
        ):
            errors.append(
                "required_capabilities must be a list"
            )

        if not isinstance(
            self.contributions(),
            list,
        ):
            errors.append(
                "brain_contributions must be a list"
            )

        if not isinstance(
            self.contradictions(),
            list,
        ):
            errors.append(
                "contradictions must be a list"
            )

        if not isinstance(
            self.verification(),
            dict,
        ):
            errors.append(
                "verification must be a dictionary"
            )

        if not isinstance(
            self.routing(),
            dict,
        ):
            errors.append(
                "routing must be a dictionary"
            )

        if not isinstance(
            self.coordination(),
            dict,
        ):
            errors.append(
                "coordination must be a dictionary"
            )

        if not isinstance(
            self.synthesis(),
            dict,
        ):
            errors.append(
                "synthesis must be a dictionary"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "checked_at": utc_now(),
        }

    # ==================================================================
    # HELPERS
    # ==================================================================

    @staticmethod
    def _normalize_names(
        values: Iterable[str],
    ) -> List[str]:
        """
        Normalize brain/system names.
        """

        result: List[str] = []

        for value in values:
            normalized = str(
                value
            ).strip().upper()

            if normalized and normalized not in result:
                result.append(normalized)

        return result

    @staticmethod
    def _clamp(
        value: float,
    ) -> float:
        """
        Clamp numeric confidence/importance values to [0, 1].
        """

        try:
            numeric = float(value)
        except (
            TypeError,
            ValueError,
        ):
            numeric = 0.0

        return max(
            0.0,
            min(
                1.0,
                numeric,
            ),
        )
