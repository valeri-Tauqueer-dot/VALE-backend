"""
VALE UNITY — Response Integrator

The Response Integrator transforms an already integrated UNITY cognitive state
into a structured response representation.

It does not perform the final language-generation responsibility itself.

Its purpose is to establish the structure of the final VALE response:

    conclusion / answer
    supporting evidence
    uncertainty
    contradictions
    limitations
    provenance
    confidence
    metadata

The component deliberately avoids inventing conclusions when the integrated
state does not contain sufficient information.

MCVL remains responsible for verification. This component only carries the
verification state into the response representation.

Version: 0.1.0
Architecture Stage: UNITY_RESPONSE_INTEGRATION_FOUNDATION
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_RESPONSE_INTEGRATION_FOUNDATION"


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


class ResponseIntegrator:
    """
    Builds a structured UNITY response object from integrated cognitive state.
    """

    def __init__(self) -> None:
        self._lock = RLock()

        self._last_response: Optional[Dict[str, Any]] = None
        self._response_count = 0

    # ------------------------------------------------------------------
    # Evidence extraction
    # ------------------------------------------------------------------

    def extract_supporting_information(
        self,
        integrated_state: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        contributions = integrated_state.get(
            "contributions",
            [],
        )

        supporting: List[Dict[str, Any]] = []

        for contribution in contributions:
            supporting.append(
                {
                    "source": contribution.get(
                        "brain",
                        "UNKNOWN",
                    ),
                    "kind": contribution.get(
                        "kind",
                        "unknown",
                    ),
                    "content": contribution.get(
                        "content",
                    ),
                    "confidence": _clamp(
                        contribution.get(
                            "confidence",
                            0.0,
                        )
                    ),
                    "importance": _clamp(
                        contribution.get(
                            "importance",
                            0.5,
                        )
                    ),
                    "timestamp": contribution.get(
                        "timestamp",
                    ),
                    "metadata": dict(
                        contribution.get(
                            "metadata",
                            {},
                        )
                        or {}
                    ),
                }
            )

        return supporting

    # ------------------------------------------------------------------
    # Response construction
    # ------------------------------------------------------------------

    def integrate(
        self,
        integrated_state: Dict[str, Any],
        answer: Any = None,
        summary: Optional[str] = None,
        limitations: Optional[Iterable[str]] = None,
        uncertainty: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build the structured response representation.

        The answer parameter must come from an upstream cognitive process.
        This class does not invent a substantive answer.
        """

        if not isinstance(integrated_state, dict):
            raise TypeError(
                "integrated_state must be a dictionary."
            )

        with self._lock:
            contradictions = list(
                integrated_state.get(
                    "contradictions",
                    [],
                )
            )

            verification = dict(
                integrated_state.get(
                    "verification",
                    {},
                )
                or {}
            )

            supporting_information = (
                self.extract_supporting_information(
                    integrated_state
                )
            )

            response_metadata = dict(
                metadata or {}
            )

            response_metadata.setdefault(
                "source",
                "UNITY_SYNTHESIS",
            )

            response = {
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "created_at": _utc_now(),

                "status": "STRUCTURED",

                "answer": answer,
                "summary": summary,

                "supporting_information": (
                    supporting_information
                ),

                "verification": verification,

                "contradictions": contradictions,

                "uncertainty": [
                    str(item)
                    for item in (uncertainty or [])
                ],

                "limitations": [
                    str(item)
                    for item in (limitations or [])
                ],

                "provenance": {
                    "task_id": integrated_state.get(
                        "task_id"
                    ),
                    "active_brains": list(
                        integrated_state.get(
                            "active_brains",
                            [],
                        )
                    ),
                    "required_capabilities": list(
                        integrated_state.get(
                            "required_capabilities",
                            [],
                        )
                    ),
                    "contribution_count": len(
                        supporting_information
                    ),
                },

                "confidence": self._derive_structural_confidence(
                    integrated_state
                ),

                "metadata": response_metadata,
            }

            if contradictions:
                response["status"] = "CONTRADICTIONS_PRESENT"

            if not supporting_information:
                response["status"] = "INSUFFICIENT_COGNITIVE_INPUT"

            self._response_count += 1
            response["response_count"] = self._response_count

            self._last_response = response

            return response

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def integrate_existing_answer(
        self,
        integrated_state: Dict[str, Any],
        answer: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return self.integrate(
            integrated_state=integrated_state,
            answer=answer,
            **kwargs,
        )

    def last_response(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._last_response is None:
                return None

            return dict(self._last_response)

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _derive_structural_confidence(
        self,
        integrated_state: Dict[str, Any],
    ) -> float:
        """
        Produce a structural confidence indicator.

        This is NOT a truth score.

        It reflects the availability of cognitive inputs and verification
        state, while preserving uncertainty and contradictions.
        """

        contributions = integrated_state.get(
            "contributions",
            [],
        )

        if not contributions:
            return 0.0

        weighted_total = 0.0
        weight_total = 0.0

        for contribution in contributions:
            confidence = _clamp(
                contribution.get(
                    "confidence",
                    0.0,
                )
            )

            importance = _clamp(
                contribution.get(
                    "importance",
                    0.5,
                )
            )

            weight = max(
                0.01,
                importance,
            )

            weighted_total += confidence * weight
            weight_total += weight

        if weight_total <= 0:
            return 0.0

        confidence = weighted_total / weight_total

        contradictions = integrated_state.get(
            "contradictions",
            [],
        )

        if contradictions:
            confidence *= 0.75

        verification = integrated_state.get(
            "verification",
            {},
        )

        if isinstance(verification, dict):
            verification_confidence = verification.get(
                "confidence"
            )

            if verification_confidence is not None:
                confidence = (
                    confidence
                    * 0.5
                    + _clamp(verification_confidence)
                    * 0.5
                )

        return _clamp(confidence)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def validate(
        self,
        response: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        target = response or self._last_response

        errors: List[str] = []
        warnings: List[str] = []

        if target is None:
            warnings.append(
                "No response has been integrated yet."
            )

            return {
                "valid": True,
                "errors": errors,
                "warnings": warnings,
            }

        required_fields = [
            "answer",
            "supporting_information",
            "verification",
            "contradictions",
            "uncertainty",
            "limitations",
            "provenance",
        ]

        for field_name in required_fields:
            if field_name not in target:
                errors.append(
                    f"Response is missing '{field_name}'."
                )

        if target.get("contradictions"):
            warnings.append(
                "Response contains unresolved contradictions."
            )

        if target.get("answer") is None:
            warnings.append(
                "No substantive answer has been supplied."
            )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    def diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "version": VERSION,
                "architecture_stage": ARCHITECTURE_STAGE,
                "response_count": self._response_count,
                "has_last_response": (
                    self._last_response is not None
                ),
                "validation": self.validate(),
}
