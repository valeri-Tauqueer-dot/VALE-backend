"""
VALE UNITY — Verification State

Version:
    0.1.0

Architecture Stage:
    UNITY_VERIFICATION_STATE_FOUNDATION

Purpose
-------
Stores the structural state of verification activity inside UNITY.

The actual verification intelligence belongs to MCVL.

This class therefore stores:

    - verification requests
    - verification status
    - claims being evaluated
    - evidence references
    - provenance
    - verification confidence
    - uncertainty
    - contradictions
    - verifier identity
    - timestamps
    - metadata

It does NOT decide whether a claim is true.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_VERIFICATION_STATE_FOUNDATION"


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _clamp(value: Any, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """Safely normalize numeric confidence values."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return minimum

    return max(minimum, min(maximum, number))


class VerificationState:
    """
    Structural verification state owned by UNITY.

    Verification lifecycle:

        CREATED
           ↓
        REQUESTED
           ↓
        IN_PROGRESS
           ↓
        VERIFIED / REJECTED / UNCERTAIN / FAILED

    The lifecycle describes the state of the verification process.
    It does not itself establish truth.
    """

    VALID_STATUSES = {
        "CREATED",
        "REQUESTED",
        "IN_PROGRESS",
        "VERIFIED",
        "REJECTED",
        "UNCERTAIN",
        "FAILED",
        "CANCELLED",
    }

    def __init__(
        self,
        verification_id: str,
        task_id: Optional[str] = None,
        claim: Any = None,
        requested_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.verification_id = str(verification_id)
        self.task_id = str(task_id) if task_id is not None else None

        self.claim = deepcopy(claim)

        self.requested_by = (
            str(requested_by) if requested_by is not None else None
        )

        self.status = "CREATED"

        self.verifier: Optional[str] = None

        self.evidence: List[Any] = []
        self.provenance: List[Any] = []

        self.confidence = 0.0
        self.uncertainty = 1.0

        self.findings: List[Any] = []
        self.contradictions: List[Any] = []

        self.result: Any = None

        self.metadata: Dict[str, Any] = dict(metadata or {})

        self.created_at = _utc_now()
        self.updated_at = self.created_at
        self.completed_at: Optional[str] = None

        self._lock = RLock()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _touch(self) -> None:
        self.updated_at = _utc_now()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def request(self) -> "VerificationState":
        """Mark verification as formally requested."""
        with self._lock:
            self.status = "REQUESTED"
            self._touch()

        return self

    def start(self, verifier: Optional[str] = None) -> "VerificationState":
        """Mark verification as in progress."""
        with self._lock:
            self.status = "IN_PROGRESS"

            if verifier is not None:
                self.verifier = str(verifier)

            self._touch()

        return self

    def complete(
        self,
        status: str,
        result: Any = None,
        confidence: Optional[float] = None,
        uncertainty: Optional[float] = None,
    ) -> "VerificationState":
        """
        Record a completed verification lifecycle state.

        Valid terminal statuses:

            VERIFIED
            REJECTED
            UNCERTAIN
            FAILED
            CANCELLED
        """
        normalized_status = str(status).upper()

        if normalized_status not in {
            "VERIFIED",
            "REJECTED",
            "UNCERTAIN",
            "FAILED",
            "CANCELLED",
        }:
            raise ValueError(
                "Invalid verification completion status: "
                f"{normalized_status}"
            )

        with self._lock:
            self.status = normalized_status
            self.result = deepcopy(result)

            if confidence is not None:
                self.confidence = _clamp(confidence)

            if uncertainty is not None:
                self.uncertainty = _clamp(uncertainty)

            self.completed_at = _utc_now()
            self._touch()

        return self

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def set_verifier(self, verifier: Optional[str]) -> "VerificationState":
        with self._lock:
            self.verifier = (
                str(verifier) if verifier is not None else None
            )
            self._touch()

        return self

    def add_evidence(self, evidence: Any) -> "VerificationState":
        with self._lock:
            self.evidence.append(deepcopy(evidence))
            self._touch()

        return self

    def add_provenance(self, provenance: Any) -> "VerificationState":
        with self._lock:
            self.provenance.append(deepcopy(provenance))
            self._touch()

        return self

    def add_finding(self, finding: Any) -> "VerificationState":
        with self._lock:
            self.findings.append(deepcopy(finding))
            self._touch()

        return self

    def add_contradiction(self, contradiction: Any) -> "VerificationState":
        with self._lock:
            self.contradictions.append(deepcopy(contradiction))
            self._touch()

        return self

    def set_result(self, result: Any) -> "VerificationState":
        with self._lock:
            self.result = deepcopy(result)
            self._touch()

        return self

    def set_confidence(self, confidence: Any) -> "VerificationState":
        with self._lock:
            self.confidence = _clamp(confidence)
            self._touch()

        return self

    def set_uncertainty(self, uncertainty: Any) -> "VerificationState":
        with self._lock:
            self.uncertainty = _clamp(uncertainty)
            self._touch()

        return self

    def set_metadata(self, key: str, value: Any) -> "VerificationState":
        with self._lock:
            self.metadata[str(key)] = deepcopy(value)
            self._touch()

        return self

    def get_metadata(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return deepcopy(self.metadata.get(key, default))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_terminal(self) -> bool:
        return self.status in {
            "VERIFIED",
            "REJECTED",
            "UNCERTAIN",
            "FAILED",
            "CANCELLED",
        }

    def is_verified(self) -> bool:
        return self.status == "VERIFIED"

    def is_uncertain(self) -> bool:
        return self.status == "UNCERTAIN"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        if not self.verification_id:
            errors.append("verification_id is required")

        if self.status not in self.VALID_STATUSES:
            errors.append(
                f"invalid verification status: {self.status}"
            )

        if not 0.0 <= self.confidence <= 1.0:
            errors.append("confidence must be between 0 and 1")

        if not 0.0 <= self.uncertainty <= 1.0:
            errors.append("uncertainty must be between 0 and 1")

        if self.status in {"VERIFIED", "REJECTED"}:
            if self.result is None:
                warnings.append(
                    "terminal verification state has no result"
                )

        if self.status == "UNCERTAIN":
            if self.uncertainty <= 0.0:
                warnings.append(
                    "UNCERTAIN state has zero uncertainty"
                )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "verification_id": self.verification_id,
                "task_id": self.task_id,
                "claim": deepcopy(self.claim),
                "requested_by": self.requested_by,
                "status": self.status,
                "verifier": self.verifier,
                "evidence": deepcopy(self.evidence),
                "provenance": deepcopy(self.provenance),
                "confidence": self.confidence,
                "uncertainty": self.uncertainty,
                "findings": deepcopy(self.findings),
                "contradictions": deepcopy(self.contradictions),
                "result": deepcopy(self.result),
                "metadata": deepcopy(self.metadata),
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "completed_at": self.completed_at,
                "validation": self.validate(),
            }

    def snapshot(self) -> Dict[str, Any]:
        """Alias for a serializable immutable-style snapshot."""
        return self.to_dict()
