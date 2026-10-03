"""
VALE UNITY — Verification Gateway

Version:
    0.1.0

Architecture Stage:
    UNITY_VERIFICATION_GATEWAY_FOUNDATION

Purpose
-------
Provides the controlled structural boundary between UNITY and MCVL.

Architecture:

    UNITY
      │
      ▼
    VerificationGateway
      │
      ▼
    MCVL
      │
      ▼
    VerificationGateway
      │
      ▼
    UNITY VerificationState

The gateway manages:

    - verification requests
    - verification state
    - verifier registration
    - result ingestion
    - provenance
    - confidence
    - uncertainty
    - contradiction references
    - lifecycle events

It does NOT:

    - independently verify claims
    - replace MCVL
    - invent evidence
    - resolve contradictions
    - select truth through voting
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable, Dict, List, Optional

from .verification_state import VerificationState


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_VERIFICATION_GATEWAY_FOUNDATION"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class VerificationGateway:
    """
    Structural verification gateway for UNITY.

    A verifier may be connected through `register_verifier()`.

    The verifier is external to this class and is expected to represent
    MCVL or another explicitly authorized verification implementation.

    This gateway does not assume that a verifier exists.
    """

    def __init__(
        self,
        state: Any = None,
        verifier: Optional[Any] = None,
    ) -> None:
        self.state = state

        self._verifier = verifier
        self._verifiers: Dict[str, Any] = {}

        self._requests: Dict[str, VerificationState] = {}
        self._counter = 0

        self._events: List[Dict[str, Any]] = []

        self._lock = RLock()

        if verifier is not None:
            self.register_verifier("MCVL", verifier)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _next_id(self) -> str:
        self._counter += 1
        return f"verification-{self._counter:06d}"

    def _record_event(
        self,
        event_type: str,
        verification_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        event = {
            "event_type": str(event_type),
            "source": "UNITY_VERIFICATION_GATEWAY",
            "verification_id": verification_id,
            "payload": deepcopy(payload or {}),
            "timestamp": _utc_now(),
        }

        self._events.append(event)

        if self.state is not None:
            try:
                if hasattr(self.state, "event"):
                    self.state.event(
                        event_type=event["event_type"],
                        source=event["source"],
                        target="MCVL",
                        payload=event["payload"],
                    )
            except Exception:
                # Verification state must not fail because event publication
                # to a broader state implementation is unavailable.
                pass

        return event

    def _publish(self, verification: VerificationState) -> None:
        if self.state is None:
            return

        payload = verification.to_dict()

        try:
            if hasattr(self.state, "set"):
                self.state.set(
                    f"unity.verification.requests."
                    f"{verification.verification_id}",
                    payload,
                )

                self.state.set(
                    "unity.verification.latest",
                    payload,
                )

            if hasattr(self.state, "set_verification"):
                self.state.set_verification(payload)

        except Exception:
            # The gateway remains operational even if a broader state
            # implementation does not expose every optional method.
            pass

    # ------------------------------------------------------------------
    # Verifier registration
    # ------------------------------------------------------------------

    def register_verifier(
        self,
        name: str,
        verifier: Any,
    ) -> Dict[str, Any]:
        """
        Register a verification implementation.

        Normally this will be MCVL.

        Supported verifier interfaces are intentionally flexible.
        The gateway can work with:

            verify(...)
            verify_claim(...)
            callable objects

        The gateway does not assume a specific MCVL implementation yet.
        """
        normalized = str(name).strip().upper()

        if not normalized:
            raise ValueError("Verifier name cannot be empty.")

        if verifier is None:
            raise ValueError("Verifier cannot be None.")

        with self._lock:
            self._verifiers[normalized] = verifier

            if normalized == "MCVL":
                self._verifier = verifier

            self._record_event(
                "UNITY_VERIFIER_REGISTERED",
                payload={
                    "verifier": normalized,
                },
            )

        return {
            "registered": True,
            "verifier": normalized,
        }

    def unregister_verifier(self, name: str) -> bool:
        normalized = str(name).strip().upper()

        with self._lock:
            existed = normalized in self._verifiers

            if existed:
                del self._verifiers[normalized]

                if normalized == "MCVL":
                    self._verifier = None

                self._record_event(
                    "UNITY_VERIFIER_UNREGISTERED",
                    payload={
                        "verifier": normalized,
                    },
                )

            return existed

    def verifier_names(self) -> List[str]:
        with self._lock:
            return sorted(self._verifiers.keys())

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------

    def create_request(
        self,
        claim: Any,
        task_id: Optional[str] = None,
        requested_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VerificationState:
        """
        Create a verification request.

        Creating a request does not perform verification.
        """
        with self._lock:
            verification_id = self._next_id()

            request = VerificationState(
                verification_id=verification_id,
                task_id=task_id,
                claim=claim,
                requested_by=requested_by,
                metadata=metadata,
            )

            request.request()

            self._requests[verification_id] = request

            self._publish(request)

            self._record_event(
                "UNITY_VERIFICATION_REQUESTED",
                verification_id,
                {
                    "task_id": task_id,
                    "requested_by": requested_by,
                },
            )

            return request

    def get_request(
        self,
        verification_id: str,
    ) -> Optional[VerificationState]:
        with self._lock:
            return self._requests.get(str(verification_id))

    def require_request(
        self,
        verification_id: str,
    ) -> VerificationState:
        request = self.get_request(verification_id)

        if request is None:
            raise KeyError(
                f"Unknown verification request: {verification_id}"
            )

        return request

    def has_request(self, verification_id: str) -> bool:
        return self.get_request(verification_id) is not None

    def requests(self) -> List[VerificationState]:
        with self._lock:
            return list(self._requests.values())

    # ------------------------------------------------------------------
    # Verification execution
    # ------------------------------------------------------------------

    def execute(
        self,
        verification_id: str,
        verifier_name: str = "MCVL",
        payload: Optional[Dict[str, Any]] = None,
    ) -> VerificationState:
        """
        Send a verification request to a registered verifier.

        The verifier's result is ingested structurally.

        No verifier means no verification is fabricated.
        """
        request = self.require_request(verification_id)

        normalized_verifier = str(verifier_name).strip().upper()

        with self._lock:
            verifier = self._verifiers.get(normalized_verifier)

        if verifier is None:
            request.complete(
                status="FAILED",
                result={
                    "error": (
                        f"Verifier '{normalized_verifier}' "
                        "is not registered."
                    )
                },
                confidence=0.0,
                uncertainty=1.0,
            )

            self._publish(request)

            self._record_event(
                "UNITY_VERIFICATION_FAILED",
                verification_id,
                {
                    "reason": "verifier_not_registered",
                    "verifier": normalized_verifier,
                },
            )

            return request

        request.start(verifier=normalized_verifier)
        self._publish(request)

        self._record_event(
            "UNITY_VERIFICATION_STARTED",
            verification_id,
            {
                "verifier": normalized_verifier,
            },
        )

        try:
            result = self._invoke_verifier(
                verifier=verifier,
                request=request,
                payload=payload,
            )

            self.ingest_result(
                verification_id=verification_id,
                result=result,
                verifier=normalized_verifier,
            )

        except Exception as exc:
            request.complete(
                status="FAILED",
                result={
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                confidence=0.0,
                uncertainty=1.0,
            )

            self._publish(request)

            self._record_event(
                "UNITY_VERIFICATION_FAILED",
                verification_id,
                {
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )

        return request

    def _invoke_verifier(
        self,
        verifier: Any,
        request: VerificationState,
        payload: Optional[Dict[str, Any]],
    ) -> Any:
        """
        Adapt to several possible verifier interfaces without embedding
        verification intelligence inside UNITY.
        """
        request_payload = {
            "verification_id": request.verification_id,
            "task_id": request.task_id,
            "claim": deepcopy(request.claim),
            "payload": deepcopy(payload or {}),
            "metadata": deepcopy(request.metadata),
        }

        if hasattr(verifier, "verify"):
            return verifier.verify(request_payload)

        if hasattr(verifier, "verify_claim"):
            return verifier.verify_claim(
                claim=deepcopy(request.claim),
                context=deepcopy(payload or {}),
            )

        if callable(verifier):
            return verifier(request_payload)

        raise TypeError(
            "Registered verifier does not expose a supported "
            "verification interface."
        )

    # ------------------------------------------------------------------
    # Result ingestion
    # ------------------------------------------------------------------

    def ingest_result(
        self,
        verification_id: str,
        result: Any,
        verifier: Optional[str] = None,
    ) -> VerificationState:
        """
        Ingest a result produced by an external verification system.

        The gateway normalizes transport structure but does not reinterpret
        the substantive verification finding.
        """
        request = self.require_request(verification_id)

        if verifier is not None:
            request.set_verifier(verifier)

        normalized = self._normalize_result(result)

        if normalized.get("evidence") is not None:
            evidence = normalized["evidence"]

            if isinstance(evidence, list):
                for item in evidence:
                    request.add_evidence(item)
            else:
                request.add_evidence(evidence)

        if normalized.get("provenance") is not None:
            provenance = normalized["provenance"]

            if isinstance(provenance, list):
                for item in provenance:
                    request.add_provenance(item)
            else:
                request.add_provenance(provenance)

        if normalized.get("findings") is not None:
            findings = normalized["findings"]

            if isinstance(findings, list):
                for item in findings:
                    request.add_finding(item)
            else:
                request.add_finding(findings)

        if normalized.get("contradictions") is not None:
            contradictions = normalized["contradictions"]

            if isinstance(contradictions, list):
                for item in contradictions:
                    request.add_contradiction(item)
            else:
                request.add_contradiction(contradictions)

        status = normalized.get("status", "UNCERTAIN")

        request.complete(
            status=status,
            result=normalized.get("result", result),
            confidence=normalized.get("confidence", 0.0),
            uncertainty=normalized.get("uncertainty", 1.0),
        )

        self._publish(request)

        self._record_event(
            "UNITY_VERIFICATION_RESULT_RECEIVED",
            verification_id,
            {
                "status": request.status,
                "verifier": request.verifier,
                "confidence": request.confidence,
                "uncertainty": request.uncertainty,
            },
        )

        return request

    def _normalize_result(self, result: Any) -> Dict[str, Any]:
        """
        Normalize transport structure.

        This method does not determine whether the result is correct.
        """
        if isinstance(result, VerificationState):
            return {
                "status": result.status,
                "result": result.result,
                "confidence": result.confidence,
                "uncertainty": result.uncertainty,
                "evidence": result.evidence,
                "provenance": result.provenance,
                "findings": result.findings,
                "contradictions": result.contradictions,
            }

        if not isinstance(result, dict):
            return {
                "status": "UNCERTAIN",
                "result": result,
                "confidence": 0.0,
                "uncertainty": 1.0,
            }

        status = str(
            result.get("status", "UNCERTAIN")
        ).upper()

        allowed_statuses = {
            "VERIFIED",
            "REJECTED",
            "UNCERTAIN",
            "FAILED",
            "CANCELLED",
        }

        if status not in allowed_statuses:
            status = "UNCERTAIN"

        return {
            "status": status,
            "result": result.get(
                "result",
                result.get("finding", result),
            ),
            "confidence": result.get("confidence", 0.0),
            "uncertainty": result.get("uncertainty", 1.0),
            "evidence": result.get("evidence"),
            "provenance": result.get("provenance"),
            "findings": result.get("findings"),
            "contradictions": result.get("contradictions"),
        }

    # ------------------------------------------------------------------
    # Manual state updates
    # ------------------------------------------------------------------

    def add_evidence(
        self,
        verification_id: str,
        evidence: Any,
    ) -> VerificationState:
        request = self.require_request(verification_id)
        request.add_evidence(evidence)
        self._publish(request)
        return request

    def add_provenance(
        self,
        verification_id: str,
        provenance: Any,
    ) -> VerificationState:
        request = self.require_request(verification_id)
        request.add_provenance(provenance)
        self._publish(request)
        return request

    def add_contradiction(
        self,
        verification_id: str,
        contradiction: Any,
    ) -> VerificationState:
        request = self.require_request(verification_id)
        request.add_contradiction(contradiction)
        self._publish(request)
        return request

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def latest(self) -> Optional[VerificationState]:
        with self._lock:
            if not self._requests:
                return None

            return list(self._requests.values())[-1]

    def verified(self) -> List[VerificationState]:
        with self._lock:
            return [
                item
                for item in self._requests.values()
                if item.status == "VERIFIED"
            ]

    def uncertain(self) -> List[VerificationState]:
        with self._lock:
            return [
                item
                for item in self._requests.values()
                if item.status == "UNCERTAIN"
            ]

    def unresolved(self) -> List[VerificationState]:
        with self._lock:
            return [
                item
                for item in self._requests.values()
                if not item.is_terminal()
            ]

    def events(self) -> List[Dict[str, Any]]:
        with self._lock:
            return deepcopy(self._events)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        with self._lock:
            for verification_id, request in self._requests.items():
                result = request.validate()

                if not result["valid"]:
                    errors.extend(
                        [
                            f"{verification_id}: {error}"
                            for error in result["errors"]
                        ]
                    )

                warnings.extend(
                    [
                        f"{verification_id}: {warning}"
                        for warning in result["warnings"]
                    ]
                )

        if not self._verifiers:
            warnings.append(
                "No verification implementation is registered."
            )

        if "MCVL" not in self._verifiers:
            warnings.append(
                "MCVL is not registered as the active verification "
                "implementation."
            )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    def diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            status_counts: Dict[str, int] = {}

            for request in self._requests.values():
                status_counts[request.status] = (
