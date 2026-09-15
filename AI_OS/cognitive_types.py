"""
VALE Generation AI OS
Cognitive Metamodel — Typed Cognitive Primitives v0.1.0

This module defines the foundational type vocabulary used by the AI OS.

Design goal:
    Prevent semantic/category errors before higher-level cognition is built.

Examples of distinctions enforced by the model:
    observation != interpretation != evidence != hypothesis != belief
    capability != permission/authority
    prediction != outcome
    recommendation != authorization != execution
    fact != assumption

This file contains definitions only. It does not perform reasoning,
Internet research, specialist-brain coordination, trading, or execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Tuple
from uuid import uuid4


COGNITIVE_TYPES_VERSION = "0.1.0"


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    """Create a globally unique typed-object identifier."""
    return f"{prefix}_{uuid4().hex}"


class CognitiveObjectType(str, Enum):
    SYSTEM = "SYSTEM"
    BRAIN = "BRAIN"
    SUBSYSTEM = "SUBSYSTEM"
    CAPABILITY = "CAPABILITY"
    RESOURCE = "RESOURCE"
    TASK = "TASK"
    GOAL = "GOAL"
    CONSTRAINT = "CONSTRAINT"
    OBSERVATION = "OBSERVATION"
    DATA = "DATA"
    EVIDENCE = "EVIDENCE"
    CLAIM = "CLAIM"
    ASSUMPTION = "ASSUMPTION"
    HYPOTHESIS = "HYPOTHESIS"
    BELIEF = "BELIEF"
    MODEL = "MODEL"
    DECISION = "DECISION"
    ACTION = "ACTION"
    OUTCOME = "OUTCOME"
    LESSON = "LESSON"
    EVOLUTION_PROPOSAL = "EVOLUTION_PROPOSAL"


class EpistemicStatus(str, Enum):
    """
    What the system currently knows about a proposition.

    These are deliberately not numeric confidence values. Confidence
    belongs to a later epistemic layer; status expresses the semantic
    category of the proposition.
    """

    KNOW = "KNOW"
    INFERRED = "INFERRED"
    LIKELY = "LIKELY"
    UNCERTAIN = "UNCERTAIN"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_VERIFIED = "NOT_VERIFIED"


class EvidenceRelation(str, Enum):
    SUPPORTS = "SUPPORTS"
    WEAKLY_SUPPORTS = "WEAKLY_SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    CONDITIONALLY_SUPPORTS = "CONDITIONALLY_SUPPORTS"
    INDIRECTLY_SUPPORTS = "INDIRECTLY_SUPPORTS"
    DEPENDS_ON = "DEPENDS_ON"
    DERIVED_FROM = "DERIVED_FROM"
    DUPLICATES = "DUPLICATES"
    INDEPENDENT_OF = "INDEPENDENT_OF"


class TemporalKind(str, Enum):
    """
    Different clocks must not be silently collapsed into one timestamp.
    """

    EVENT_TIME = "EVENT_TIME"
    OBSERVATION_TIME = "OBSERVATION_TIME"
    INGESTION_TIME = "INGESTION_TIME"
    PROCESSING_TIME = "PROCESSING_TIME"
    DECISION_TIME = "DECISION_TIME"
    EXECUTION_TIME = "EXECUTION_TIME"
    OUTCOME_TIME = "OUTCOME_TIME"
    MEMORY_TIME = "MEMORY_TIME"
    VALID_FROM = "VALID_FROM"
    VALID_UNTIL = "VALID_UNTIL"


class AuthorityLevel(str, Enum):
    """
    Authority is separate from capability.

    A component may possess a capability without being authorized to
    exercise that capability in a particular context.
    """

    NONE = "NONE"
    OBSERVE = "OBSERVE"
    REQUEST = "REQUEST"
    USE = "USE"
    COORDINATE = "COORDINATE"
    AUTHORIZE = "AUTHORIZE"
    EXECUTE = "EXECUTE"
    MODIFY = "MODIFY"
    DEPLOY = "DEPLOY"


class RiskLevel(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    ADVISORY = "ADVISORY"
    CONSEQUENTIAL = "CONSEQUENTIAL"
    HIGH_IMPACT = "HIGH_IMPACT"
    EXTERNALLY_ACTING = "EXTERNALLY_ACTING"
    IRREVERSIBLE = "IRREVERSIBLE"
    CRITICAL = "CRITICAL"


class LifecycleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DEGRADED = "DEGRADED"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class CognitiveTypeDescriptor:
    """
    Runtime descriptor for a cognitive type.

    semantic_role:
        Human-readable semantic purpose.

    allowed_epistemic_statuses:
        Prevents inappropriate epistemic states for an object.
    """

    object_type: CognitiveObjectType
    semantic_role: str
    allowed_epistemic_statuses: Tuple[EpistemicStatus, ...] = field(
        default_factory=tuple
    )


@dataclass
class CognitiveObject:
    """
    Root typed object for the cognitive metamodel.

    This is metadata/identity structure, not a reasoning engine.
    """

    object_id: str
    object_type: CognitiveObjectType
    schema_version: str = COGNITIVE_TYPES_VERSION
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    lifecycle: LifecycleStatus = LifecycleStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """Update modification time explicitly."""
        self.updated_at = utc_now()


@dataclass(frozen=True)
class CognitiveReference:
    """
    Typed reference between cognitive objects.

    This becomes the basic building block for future dependency,
    provenance, causal, memory, and belief graphs.
    """

    source_id: str
    target_id: str
    relation: str
    created_at: datetime = field(default_factory=utc_now)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EpistemicAnnotation:
    """
    Semantic annotation attached to a claim-like cognitive object.

    Confidence is optional here because epistemic status and numerical
    confidence are intentionally separate concepts.
    """

    status: EpistemicStatus
    confidence: Optional[float] = None
    reason: Optional[str] = None
    invalidation_condition: Optional[str] = None

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class TemporalMarker:
    """
    Explicit temporal metadata.

    Keeping temporal semantics typed prevents event time from being
    confused with ingestion, processing, decision, or outcome time.
    """

    kind: TemporalKind
    timestamp: datetime
    source: Optional[str] = None


@dataclass(frozen=True)
class AuthorityDescriptor:
    """
    Explicit authority boundary.

    permissions describe what is permitted; capability is represented
    separately by CognitiveObjectType.CAPABILITY.
    """

    subject_id: str
    level: AuthorityLevel
    scope: str
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None

    def is_expired(self, at: Optional[datetime] = None) -> bool:
        if self.expires_at is None:
            return False
        current = at or utc_now()
        return current >= self.expires_at


@dataclass(frozen=True)
class CognitiveTypeSystem:
    """
    Static registry of foundational semantic types.

    Higher layers can extend this registry without redefining the core
    vocabulary.
    """

    version: str = COGNITIVE_TYPES_VERSION

    def descriptor(self, object_type: CognitiveObjectType) -> CognitiveTypeDescriptor:
        descriptors = {
            CognitiveObjectType.OBSERVATION: CognitiveTypeDescriptor(
                object_type,
                "A recorded observation of something perceived or measured.",
                (
                    EpistemicStatus.KNOW,
                    EpistemicStatus.UNCERTAIN,
                    EpistemicStatus.UNKNOWN,
                    EpistemicStatus.UNAVAILABLE,
                ),
            ),
            CognitiveObjectType.EVIDENCE: CognitiveTypeDescriptor(
                object_type,
                "Information used to support, weaken, or contradict a claim.",
                (
                    EpistemicStatus.KNOW,
                    EpistemicStatus.UNCERTAIN,
                    EpistemicStatus.NOT_VERIFIED,
                ),
            ),
            CognitiveObjectType.ASSUMPTION: CognitiveTypeDescriptor(
                object_type,
                "A proposition provisionally accepted for reasoning.",
                (
                    EpistemicStatus.INFERRED,
                    EpistemicStatus.LIKELY,
                    EpistemicStatus.UNCERTAIN,
                    EpistemicStatus.UNKNOWN,
                ),
            ),
            CognitiveObjectType.HYPOTHESIS: CognitiveTypeDescriptor(
                object_type,
                "A candidate explanation or proposition under evaluation.",
                (
                    EpistemicStatus.INFERRED,
                    EpistemicStatus.LIKELY,
                    EpistemicStatus.UNCERTAIN,
                    EpistemicStatus.CONTRADICTED,
                    EpistemicStatus.UNKNOWN,
                ),
            ),
            CognitiveObjectType.BELIEF: CognitiveTypeDescriptor(
                object_type,
                "The system's current maintained position about a proposition.",
                (
                    EpistemicStatus.KNOW,
                    EpistemicStatus.INFERRED,
                    EpistemicStatus.LIKELY,
                    EpistemicStatus.UNCERTAIN,
                    EpistemicStatus.CONTRADICTED,
                    EpistemicStatus.UNKNOWN,
                    EpistemicStatus.NOT_VERIFIED,
                ),
            ),
            CognitiveObjectType.OUTCOME: CognitiveTypeDescriptor(
                object_type,
                "An observed result of an action or event.",
                (
                    EpistemicStatus.KNOW,
                    EpistemicStatus.UNCERTAIN,
                    EpistemicStatus.UNKNOWN,
                    EpistemicStatus.NOT_VERIFIED,
                ),
            ),
        }

        return descriptors.get(
            object_type,
            CognitiveTypeDescriptor(
                object_type=object_type,
                semantic_role="Foundational cognitive object.",
            ),
        )


def make_object(
    object_type: CognitiveObjectType,
    *,
    metadata: Optional[Mapping[str, Any]] = None,
    prefix: Optional[str] = None,
) -> CognitiveObject:
    """Create a correctly typed foundational cognitive object."""
    object_prefix = prefix or object_type.value.lower()

    return CognitiveObject(
        object_id=new_id(object_prefix),
        object_type=object_type,
        metadata=dict(metadata or {}),
    )


def validate_epistemic_annotation(
    object_type: CognitiveObjectType,
    annotation: EpistemicAnnotation,
) -> None:
    """
    Validate that an epistemic status is semantically allowed for the
    supplied cognitive object type.
    """
    descriptor = CognitiveTypeSystem().descriptor(object_type)

    if (
        descriptor.allowed_epistemic_statuses
        and annotation.status not in descriptor.allowed_epistemic_statuses
    ):
        raise ValueError(
            f"Epistemic status {annotation.status.value} is not valid for "
            f"{object_type.value}"
        )


__all__ = [
    "COGNITIVE_TYPES_VERSION",
    "utc_now",
    "new_id",
    "CognitiveObjectType",
    "EpistemicStatus",
    "EvidenceRelation",
    "TemporalKind",
    "AuthorityLevel",
    "RiskLevel",
    "LifecycleStatus",
    "CognitiveTypeDescriptor",
    "CognitiveObject",
    "CognitiveReference",
    "EpistemicAnnotation",
    "TemporalMarker",
    "AuthorityDescriptor",
    "CognitiveTypeSystem",
    "make_object",
    "validate_epistemic_annotation",
]
