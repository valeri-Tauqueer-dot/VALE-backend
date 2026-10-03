"""
VALE UNITY — Communication Protocol

Version:
    0.1.0

Architecture Stage:
    UNITY_COMMUNICATION_PROTOCOL_FOUNDATION

Purpose
-------
Defines the standardized communication contract used by UNITY components.

The protocol ensures that communication carries enough context for VALE
to maintain traceability across:

    - source
    - destination
    - task
    - correlation
    - message type
    - payload
    - provenance
    - metadata

The protocol is a structural contract.

It does NOT:

    - perform reasoning
    - select brains
    - determine objectives
    - verify claims
    - synthesize responses
    - optimize execution
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_COMMUNICATION_PROTOCOL_FOUNDATION"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_name(value: Any) -> str:
    return str(value).strip().upper()


@dataclass
class CommunicationEnvelope:
    """
    Standard VALE communication envelope.

    The envelope wraps a cognitive message while preserving its context.

    This object carries information.

    It does not decide what that information means.
    """

    source: str
    destination: str

    message_type: str = "COGNITIVE_MESSAGE"

    payload: Any = None

    task_id: Optional[str] = None
    correlation_id: Optional[str] = None

    message_id: Optional[str] = None

    provenance: List[Any] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: str = field(default_factory=_utc_now)

    status: str = "CREATED"

    delivered_at: Optional[str] = None

    error: Optional[str] = None

    def __post_init__(self) -> None:
        self.source = _normalize_name(self.source)
        self.destination = _normalize_name(self.destination)
        self.message_type = _normalize_name(self.message_type)

        if self.message_id is not None:
            self.message_id = str(self.message_id)

        if self.task_id is not None:
            self.task_id = str(self.task_id)

        if self.correlation_id is not None:
            self.correlation_id = str(
                self.correlation_id
            )

        self.metadata = dict(self.metadata or {})

        if not isinstance(self.provenance, list):
            self.provenance = [self.provenance]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def mark_sent(self) -> "CommunicationEnvelope":
        self.status = "SENT"
        return self

    def mark_delivered(self) -> "CommunicationEnvelope":
        self.status = "DELIVERED"
        self.delivered_at = _utc_now()
        return self

    def mark_failed(self, error: Any) -> "CommunicationEnvelope":
        self.status = "FAILED"
        self.error = str(error)
        return self

    def mark_cancelled(self) -> "CommunicationEnvelope":
        self.status = "CANCELLED"
        return self

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def add_provenance(self, provenance: Any) -> "CommunicationEnvelope":
        self.provenance.append(deepcopy(provenance))
        return self

    def set_metadata(
        self,
        key: str,
        value: Any,
    ) -> "CommunicationEnvelope":
        self.metadata[str(key)] = deepcopy(value)
        return self

    def get_metadata(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        return deepcopy(
            self.metadata.get(
                str(key),
                default,
            )
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        if not self.source:
            errors.append("source is required.")

        if not self.destination:
            errors.append("destination is required.")

        if not self.message_type:
            errors.append("message_type is required.")

        valid_statuses = {
            "CREATED",
            "SENT",
            "DELIVERED",
            "FAILED",
            "CANCELLED",
        }

        if self.status not in valid_statuses:
            errors.append(
                f"invalid communication status: {self.status}"
            )

        if self.status == "FAILED" and not self.error:
            warnings.append(
                "Message is marked FAILED without an error."
            )

        if self.status == "DELIVERED" and not self.delivered_at:
            warnings.append(
                "Message is DELIVERED without delivered_at."
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
            "source": self.source,
            "destination": self.destination,
            "message_type": self.message_type,
            "payload": deepcopy(self.payload),
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "message_id": self.message_id,
            "provenance": deepcopy(self.provenance),
            "metadata": deepcopy(self.metadata),
            "created_at": self.created_at,
            "status": self.status,
            "delivered_at": self.delivered_at,
            "error": self.error,
            "validation": self.validate(),
        }


class CommunicationProtocol:
    """
    Factory and validation service for communication envelopes.

    This class defines the communication contract without taking over
    routing, reasoning, verification, or synthesis.
    """

    VALID_MESSAGE_TYPES = {
        "COGNITIVE_MESSAGE",
        "COGNITIVE_REQUEST",
        "COGNITIVE_RESPONSE",
        "COGNITIVE_BROADCAST",
        "STATE_UPDATE",
        "CAPABILITY_REQUEST",
        "CAPABILITY_RESPONSE",
        "VERIFICATION_REQUEST",
        "VERIFICATION_RESULT",
        "CONTRADICTION_NOTICE",
        "SYNTHESIS_UPDATE",
        "SYSTEM_EVENT",
        "HEALTH_EVENT",
        "ERROR_EVENT",
    }

    def __init__(
        self,
        state: Any = None,
    ) -> None:
        self.state = state

        self._history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Envelope creation
    # ------------------------------------------------------------------

    def create(
        self,
        source: str,
        destination: str,
        payload: Any = None,
        message_type: str = "COGNITIVE_MESSAGE",
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        provenance: Optional[List[Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CommunicationEnvelope:
        normalized_type = _normalize_name(message_type)

        envelope = CommunicationEnvelope(
            source=source,
            destination=destination,
            message_type=normalized_type,
            payload=payload,
            task_id=task_id,
            correlation_id=correlation_id,
            message_id=message_id,
            provenance=provenance or [],
            metadata=metadata or {},
        )

        validation = envelope.validate()

        if not validation["valid"]:
            raise ValueError(
                "Invalid communication envelope: "
                + "; ".join(validation["errors"])
            )

        return envelope

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def send(
        self,
        envelope: CommunicationEnvelope,
    ) -> CommunicationEnvelope:
        """
        Mark an envelope as sent and record it.

        Actual transport remains the responsibility of
        MessageRouter/CognitiveFabric.
        """
        envelope.mark_sent()

        self._record(
            "COMMUNICATION_SENT",
            envelope,
        )

        return envelope

    def delivered(
        self,
        envelope: CommunicationEnvelope,
    ) -> CommunicationEnvelope:
        envelope.mark_delivered()

        self._record(
            "COMMUNICATION_DELIVERED",
            envelope,
        )

        return envelope

    def failed(
        self,
        envelope: CommunicationEnvelope,
        error: Any,
    ) -> CommunicationEnvelope:
        envelope.mark_failed(error)

        self._record(
            "COMMUNICATION_FAILED",
            envelope,
        )

        return envelope

    def cancel(
        self,
        envelope: CommunicationEnvelope,
    ) -> CommunicationEnvelope:
        envelope.mark_cancelled()

        self._record(
            "COMMUNICATION_CANCELLED",
            envelope,
        )

        return envelope

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(
        self,
        envelope: CommunicationEnvelope,
    ) -> Dict[str, Any]:
        if not isinstance(
            envelope,
            CommunicationEnvelope,
        ):
            return {
                "valid": False,
                "errors": [
                    "Expected CommunicationEnvelope."
                ],
                "warnings": [],
            }

        return envelope.validate()

    # ------------------------------------------------------------------
    # Type support
    # ------------------------------------------------------------------

    def supports_message_type(
        self,
        message_type: str,
    ) -> bool:
        return (
            _normalize_name(message_type)
            in self.VALID_MESSAGE_TYPES
        )

    def message_types(self) -> List[str]:
        return sorted(self.VALID_MESSAGE_TYPES)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _record(
        self,
        event_type: str,
        envelope: CommunicationEnvelope,
    ) -> None:
        record = {
            "event_type": event_type,
            "envelope": envelope.to_dict(),
            "timestamp": _utc_now(),
        }

        self._history.append(record)

        if self.state is not None:
            try:
                if hasattr(self.state, "event"):
                    self.state.event(
                        event_type=event_type,
                        source="UNITY_COMMUNICATION_PROTOCOL",
                        target=envelope.destination,
                        payload=record,
                    )
            except Exception:
                pass

    def history(self) -> List[Dict[str, Any]]:
        return deepcopy(self._history)

    def clear_history(self) -> None:
        self._history.clear()

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
            "supported_message_types": len(
                self.VALID_MESSAGE_TYPES
            ),
            "history_records": len(self._history),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": VERSION,
            "architecture_stage": ARCHITECTURE_STAGE,
            "supported_message_types": self.message_types(),
            "history": self.history(),
            "diagnostics": self.diagnostics(),
  }
