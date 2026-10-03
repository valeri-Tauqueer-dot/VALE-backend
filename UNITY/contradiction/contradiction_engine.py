"""
VALE UNITY — Contradiction Engine

The Contradiction Engine manages the lifecycle of disagreements between
cognitive contributions.

Core principle:

    CONTRADICTION ≠ FAILURE

A contradiction is information.

The engine therefore:

    1. detects structural conflicts
    2. records them
    3. preserves the conflicting claims
    4. tracks investigation
    5. accepts external verification results
    6. records resolution when justified
    7. preserves unresolved uncertainty

It does NOT independently determine which brain is correct.

MCVL and other appropriate intelligence systems remain responsible for
verification and evidence evaluation.

Version: 0.1.0
Architecture Stage: UNITY_CONTRADICTION_ENGINE_FOUNDATION
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .conflict_state import ConflictState


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_CONTRADICTION_ENGINE_FOUNDATION"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_name(value: Any) -> str:
    return str(value).strip().upper()


def _normalize_text(value: Any) -> str:
    return str(value).strip()


class ContradictionEngine:
    """
    Manages structured contradiction state for UNITY.
    """

    def __init__(
        self,
        state: Optional[Any] = None,
    ) -> None:
        self.state = state

        self._lock = RLock()

        self._conflicts: Dict[
            str,
            ConflictState,
        ] = {}

        self._counter = 0

    # ------------------------------------------------------------------
    # Conflict creation
    # ------------------------------------------------------------------

    def create_conflict(
        self,
        conflict_type: str = "GENERAL",
        sources: Optional[Iterable[str]] = None,
        claims: Optional[Iterable[Dict[str, Any]]] = None,
        evidence: Optional[Iterable[Dict[str, Any]]] = None,
        assumptions: Optional[Iterable[str]] = None,
        severity: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        conflict_id: Optional[str] = None,
    ) -> ConflictState:
        with self._lock:
            if conflict_id is None:
                self._counter += 1

                conflict_id = (
                    f"UNITY-CONFLICT-{self._counter}"
                )

            normalized_id = _normalize_text(
                conflict_id
            )

            if not normalized_id:
                raise ValueError(
                    "Conflict ID cannot be empty."
                )

            if normalized_id in self._conflicts:
                raise ValueError(
                    f"Conflict '{normalized_id}' already exists."
                )

            conflict = ConflictState(
                conflict_id=normalized_id,
                conflict_type=conflict_type,
                severity=severity,
                sources=list(
                    sources or []
                ),
                claims=list(
                    claims or []
                ),
                evidence=list(
                    evidence or []
                ),
                assumptions=list(
                    assumptions or []
                ),
                metadata=dict(
                    metadata or {}
                ),
            )

            validation = conflict.validate()

            if not validation["valid"]:
                raise ValueError(
                    f"Invalid conflict: "
                    f"{validation['errors']}"
                )

            self._conflicts[
                normalized_id
            ] = conflict

            self._publish(conflict)

            return conflict

    # ------------------------------------------------------------------
    # Structural detection
    # ------------------------------------------------------------------

    def detect_conflicts(
        self,
        contributions: Sequence[Any],
        conflict_type: str = "CONTRIBUTION_DISAGREEMENT",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[ConflictState]:
        """
        Detect explicit disagreement markers in contributions.

        This method is intentionally conservative.

        It does NOT infer that two different answers are contradictory merely
        because they differ. A contradiction must be explicitly represented
        through supported fields such as:

            conflict_with
            contradicts
            disagreement
            contradiction

        This avoids manufacturing conflicts from ordinary diversity of views.
        """

        detected: List[ConflictState] = []

        normalized = [
            self._normalize_contribution(
                contribution
            )
            for contribution in contributions
        ]

        for index, contribution in enumerate(
            normalized
        ):
            markers = self._conflict_markers(
                contribution
            )

            if not markers:
                continue

            sources = [
                contribution.get(
                    "brain",
                    "UNKNOWN",
                )
            ]

            for marker in markers:
                target = marker.get(
                    "target"
                )

                if target:
                    sources.append(
                        _normalize_name(
                            target
                        )
                    )

                claim = {
                    "source": contribution.get(
                        "brain",
                        "UNKNOWN",
                    ),
                    "content": contribution.get(
                        "content"
                    ),
                    "marker": marker,
                }

                conflict = self.create_conflict(
                    conflict_type=conflict_type,
                    sources=sources,
                    claims=[
                        claim
                    ],
                    severity=float(
                        contribution.get(
                            "conflict_severity",
                            0.5,
                        )
                    ),
                    metadata={
                        **dict(
                            metadata or {}
                        ),
                        "detected_from_index": index,
                    },
                )

                detected.append(
                    conflict
                )

        return detected

    def _normalize_contribution(
        self,
        contribution: Any,
    ) -> Dict[str, Any]:
        if hasattr(
            contribution,
            "to_dict",
        ):
            return dict(
                contribution.to_dict()
            )

        if isinstance(
            contribution,
            dict,
        ):
            return dict(
                contribution
            )

        return {
            "brain": "UNKNOWN",
            "content": contribution,
        }

    def _conflict_markers(
        self,
        contribution: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        markers: List[Dict[str, Any]] = []

        raw_metadata = contribution.get(
            "metadata",
            {},
        )

        metadata = (
            raw_metadata
            if isinstance(
                raw_metadata,
                dict,
            )
            else {}
        )

        possible_fields = [
            "conflict_with",
            "contradicts",
            "disagreement",
            "contradiction",
        ]

        for field_name in possible_fields:
            value = contribution.get(
                field_name
            )

            if value is None:
                value = metadata.get(
                    field_name
                )

            if value is None:
                continue

            if isinstance(
                value,
                list,
            ):
                values = value
            else:
                values = [
                    value
                ]

            for item in values:
                if isinstance(
                    item,
                    dict,
                ):
                    marker = dict(
                        item
                    )
                else:
                    marker = {
                        "target": item
                    }

                marker[
                    "field"
                ] = field_name

                markers.append(
                    marker
                )

        return markers

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(
        self,
        conflict_id: str,
    ) -> Optional[ConflictState]:
        with self._lock:
            return self._conflicts.get(
                _normalize_text(
                    conflict_id
                )
            )

    def require(
        self,
        conflict_id: str,
    ) -> ConflictState:
        conflict = self.get(
            conflict_id
        )

        if conflict is None:
            raise KeyError(
                f"Conflict '{conflict_id}' does not exist."
            )

        return conflict

    def has(
        self,
        conflict_id: str,
    ) -> bool:
        with self._lock:
            return (
                _normalize_text(
                    conflict_id
                )
                in self._conflicts
            )

    def all(self) -> List[ConflictState]:
        with self._lock:
            return list(
                self._conflicts.values()
            )

    def ids(self) -> List[str]:
        with self._lock:
            return sorted(
                self._conflicts.keys()
            )

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def by_status(
        self,
        status: str,
    ) -> List[ConflictState]:
        normalized = str(
            status
        ).strip().upper()

        with self._lock:
            return [
                conflict
                for conflict in self._conflicts.values()
                if conflict.status == normalized
            ]

    def open_conflicts(self) -> List[ConflictState]:
        return self.by_status(
            "OPEN"
        )

    def investigating_conflicts(
        self,
    ) -> List[ConflictState]:
        return self.by_status(
            "INVESTIGATING"
        )

    def unresolved_conflicts(
        self,
    ) -> List[ConflictState]:
        return self.by_status(
            "UNRESOLVED"
        )

    def resolved_conflicts(
        self,
    ) -> List[ConflictState]:
        return self.by_status(
            "RESOLVED"
        )

    def involving(
        self,
        source: str,
    ) -> List[ConflictState]:
        normalized = _normalize_name(
            source
        )

        with self._lock:
            return [
                conflict
                for conflict in self._conflicts.values()
                if normalized in conflict.sources
            ]

    # ------------------------------------------------------------------
    # Investigation
    # ------------------------------------------------------------------

    def begin_investigation(
        self,
        conflict_id: str,
        reason: str = "",
    ) -> ConflictState:
        with self._lock:
            conflict = self.require(
                conflict_id
            )

            conflict.begin_investigation(
                reason=reason
            )

            self._publish(
                conflict
            )

            return conflict

    # ------------------------------------------------------------------
    # Evidence / verification
    # ------------------------------------------------------------------

    def add_evidence(
        self,
        conflict_id: str,
        evidence: Dict[str, Any],
    ) -> ConflictState:
        with self._lock:
            conflict = self.require(
                conflict_id
            )

            conflict.add_evidence(
                evidence
            )

            self._publish(
                conflict
            )

            return conflict

    def set_verification(
        self,
        conflict_id: str,
        verification: Dict[str, Any],
    ) -> ConflictState:
        with self._lock:
            conflict = self.require(
                conflict_id
            )

            conflict.set_verification(
                verification
            )

            self._publish(
                conflict
            )

            return conflict

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(
        self,
        conflict_id: str,
        resolution: Dict[str, Any],
    ) -> ConflictState:
        """
        Record an externally justified resolution.

        The engine does not evaluate whether the supplied resolution is true.
        It records the resolution and its provenance.
        """

        if not isinstance(
            resolution,
            dict,
        ):
            raise TypeError(
                "Resolution must be a dictionary."
            )

        with self._lock:
            conflict = self.require(
                conflict_id
            )

            conflict.resolve(
                resolution
            )

            self._publish(
                conflict
            )

            return conflict

    def mark_unresolved(
        self,
        conflict_id: str,
        reason: str = "",
    ) -> ConflictState:
        with self._lock:
            conflict = self.require(
                conflict_id
            )

            conflict.mark_unresolved(
                reason=reason
            )

            self._publish(
                conflict
            )

            return conflict

    def dismiss(
        self,
        conflict_id: str,
        reason: str = "",
    ) -> ConflictState:
        with self._lock:
            conflict = self.require(
                conflict_id
            )

            conflict.dismiss(
                reason=reason
            )

            self._publish(
                conflict
            )

            return conflict

    # ------------------------------------------------------------------
    # State publication
    # ------------------------------------------------------------------

    def _publish(
        self,
        conflict: ConflictState,
    ) -> None:
        if self.state is None:
            return

        payload = conflict.to_dict()

        try:
            if hasattr(
                self.state,
                "add_contradiction",
            ):
                self.state.add_contradiction(
                    payload
                )

            if hasattr(
                self.state,
                "set",
            ):
                self.state.set(
                    "unity.contradictions."
                    + conflict.conflict_id,
                    payload,
                )

            if hasattr(
                self.state,
                "event",
            ):
                self.state.event(
                    event_type=(
                        "UNITY_CONTRADICTION_UPDATED"
                    ),
                    source="UNITY",
                    target=None,
                    payload={
                        "conflict_id": (
                            conflict.conflict_id
                        ),
                        "status": (
                            conflict.status
                        ),
                    },
                )

        except Exception:
            # Local contradiction state remains authoritative for this
            # component if external publication fails.
            return

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def validate(
        self,
    ) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        with self._lock:
            for conflict_id, conflict in (
                self._conflicts.items()
            ):
                result = conflict.validate()

                if not result["valid"]:
                    errors.extend(
                        f"{conflict_id}: {error}"
                        for error in result[
                            "errors"
                        ]
                    )

                warnings.extend(
                    f"{conflict_id}: {warning}"
                    for warning in result[
                        "warnings"
                    ]
                )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    def diagnostics(
        self,
    ) -> Dict[str, Any]:
        with self._lock:
            return {
                "version": VERSION,
                "architecture_stage": (
                    ARCHITECTURE_STAGE
                ),
                "conflict_count": len(
                    self._conflicts
                ),
                "open_count": len(
                    self.open_conflicts()
                ),
                "investigating_count": len(
                    self.investigating_conflicts()
                ),
                "unresolved_count": len(
                    self.unresolved_conflicts()
                ),
                "resolved_count": len(
                    self.resolved_conflicts()
                ),
                "validation": self.validate(),
            }

    def to_dict(
        self,
    ) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {
                conflict_id: conflict.to_dict()
                for conflict_id, conflict in (
                    self._conflicts.items()
                )
      }
