"""
VALE UNITY — Conflict State

ConflictState represents one tracked contradiction inside UNITY.

A conflict is treated as structured cognitive state rather than as an error
that must immediately be eliminated.

The state preserves:

    - conflicting sources
    - claims
    - evidence
    - assumptions
    - confidence
    - severity
    - status
    - verification state
    - resolution history

The component does not determine which side is correct.

Version: 0.1.0
Architecture Stage: UNITY_CONFLICT_STATE_FOUNDATION
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_CONFLICT_STATE_FOUNDATION"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(
    value: Any,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = minimum

    return max(minimum, min(maximum, value))


@dataclass
class ConflictState:
    """
    Structured state for a single contradiction.

    Status lifecycle:

        OPEN
          ↓
        INVESTIGATING
          ↓
        RESOLVED / UNRESOLVED / DISMISSED
    """

    conflict_id: str

    conflict_type: str = "GENERAL"

    status: str = "OPEN"

    severity: float = 0.5

    sources: List[str] = field(default_factory=list)

    claims: List[Dict[str, Any]] = field(
        default_factory=list
    )

    evidence: List[Dict[str, Any]] = field(
        default_factory=list
    )

    assumptions: List[str] = field(
        default_factory=list
    )

    verification: Dict[str, Any] = field(
        default_factory=dict
    )

    resolution: Optional[Dict[str, Any]] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    created_at: str = field(
        default_factory=_utc_now
    )

    updated_at: str = field(
        default_factory=_utc_now
    )

    resolved_at: Optional[str] = None

    def __post_init__(self) -> None:
        self.conflict_id = str(
            self.conflict_id
        ).strip()

        self.conflict_type = str(
            self.conflict_type
        ).strip().upper()

        self.status = str(
            self.status
        ).strip().upper()

        self.severity = _clamp(
            self.severity
        )

        self.sources = sorted(
            {
                str(source).strip().upper()
                for source in self.sources
                if str(source).strip()
            }
        )

        self.claims = list(
            self.claims or []
        )

        self.evidence = list(
            self.evidence or []
        )

        self.assumptions = [
            str(item).strip()
            for item in self.assumptions
            if str(item).strip()
        ]

        self.verification = dict(
            self.verification or {}
        )

        self.metadata = dict(
            self.metadata or {}
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def touch(self) -> None:
        self.updated_at = _utc_now()

    def begin_investigation(
        self,
        reason: str = "",
    ) -> None:
        self.status = "INVESTIGATING"

        if reason:
            self.metadata["investigation_reason"] = str(
                reason
            )

        self.touch()

    def resolve(
        self,
        resolution: Dict[str, Any],
    ) -> None:
        self.status = "RESOLVED"
        self.resolution = dict(
            resolution or {}
        )
        self.resolved_at = _utc_now()
        self.touch()

    def mark_unresolved(
        self,
        reason: str = "",
    ) -> None:
        self.status = "UNRESOLVED"

        if reason:
            self.metadata["unresolved_reason"] = str(
                reason
            )

        self.resolved_at = None
        self.touch()

    def dismiss(
        self,
        reason: str = "",
    ) -> None:
        self.status = "DISMISSED"

        if reason:
            self.metadata["dismissal_reason"] = str(
                reason
            )

        self.touch()

    # ------------------------------------------------------------------
    # Content management
    # ------------------------------------------------------------------

    def add_source(
        self,
        source: str,
    ) -> None:
        normalized = str(
            source
        ).strip().upper()

        if normalized and normalized not in self.sources:
            self.sources.append(normalized)
            self.sources.sort()
            self.touch()

    def add_claim(
        self,
        claim: Dict[str, Any],
    ) -> None:
        if not isinstance(claim, dict):
            raise TypeError(
                "Claim must be a dictionary."
            )

        self.claims.append(
            dict(claim)
        )

        self.touch()

    def add_evidence(
        self,
        evidence: Dict[str, Any],
    ) -> None:
        if not isinstance(evidence, dict):
            raise TypeError(
                "Evidence must be a dictionary."
            )

        self.evidence.append(
            dict(evidence)
        )

        self.touch()

    def add_assumption(
        self,
        assumption: str,
    ) -> None:
        value = str(
            assumption
        ).strip()

        if value:
            self.assumptions.append(
                value
            )
            self.touch()

    def set_verification(
        self,
        verification: Dict[str, Any],
    ) -> None:
        self.verification = dict(
            verification or {}
        )

        self.touch()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        if not self.conflict_id:
            errors.append(
                "Conflict ID cannot be empty."
            )

        if not self.conflict_type:
            errors.append(
                "Conflict type cannot be empty."
            )

        if not isinstance(
            self.sources,
            list,
        ):
            errors.append(
                "Sources must be a list."
            )

        if not isinstance(
            self.claims,
            list,
        ):
            errors.append(
                "Claims must be a list."
            )

        if not isinstance(
            self.evidence,
            list,
        ):
            errors.append(
                "Evidence must be a list."
            )

        if self.status == "RESOLVED" and not self.resolution:
            warnings.append(
                "Conflict is marked resolved without a resolution record."
            )

        if (
            self.status == "OPEN"
            and self.severity >= 0.8
        ):
            warnings.append(
                "High-severity conflict remains open."
            )

        if not self.sources:
            warnings.append(
                "Conflict has no identified sources."
            )

        if not self.claims:
            warnings.append(
                "Conflict has no claims."
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
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type,
            "status": self.status,
            "severity": self.severity,
            "sources": list(self.sources),
            "claims": list(self.claims),
            "evidence": list(self.evidence),
            "assumptions": list(self.assumptions),
            "verification": dict(
                self.verification
            ),
            "resolution": (
                dict(self.resolution)
                if self.resolution is not None
                else None
            ),
            "metadata": dict(
                self.metadata
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
  }
