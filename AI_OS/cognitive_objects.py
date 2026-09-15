"""
VALE Generation AI OS
Cognitive Objects — Structured Semantic Objects v0.1.0

Builds concrete, typed cognitive objects on top of cognitive_types.py.

This layer gives the AI OS structured representations for:
- tasks, goals, constraints
- observations and data
- claims, evidence, assumptions
- hypotheses and beliefs
- capabilities and resources
- models
- decisions, actions, outcomes
- lessons and evolution proposals

This module does not perform reasoning or orchestration. It provides
validated state containers and explicit semantic boundaries for the
higher-level AI OS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

try:
    from .cognitive_types import (
        AuthorityLevel,
        CognitiveObject,
        CognitiveObjectType,
        CognitiveReference,
        EpistemicAnnotation,
        EpistemicStatus,
        EvidenceRelation,
        LifecycleStatus,
        RiskLevel,
        TemporalKind,
        TemporalMarker,
        make_object,
        utc_now,
    )
except ImportError:
    from cognitive_types import (
        AuthorityLevel,
        CognitiveObject,
        CognitiveObjectType,
        CognitiveReference,
        EpistemicAnnotation,
        EpistemicStatus,
        EvidenceRelation,
        LifecycleStatus,
        RiskLevel,
        TemporalKind,
        TemporalMarker,
        make_object,
        utc_now,
    )


COGNITIVE_OBJECTS_VERSION = "0.1.0"


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validate_probability(value: Optional[float], field_name: str) -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0")


def _validate_non_negative(value: float, field_name: str) -> None:
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative")


@dataclass
class TaskObject(CognitiveObject):
    """Represents an AI OS task and its explicit objective boundary."""

    objective: str = ""
    parent_task_id: Optional[str] = None
    goal_ids: List[str] = field(default_factory=list)
    constraint_ids: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.INFORMATIONAL

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.TASK:
            raise ValueError("TaskObject must have object_type TASK")
        self.objective = _require_text(self.objective, "objective")


@dataclass
class GoalObject(CognitiveObject):
    """Explicit desired state or outcome of a task."""

    description: str = ""
    priority: int = 0
    measurable_conditions: List[str] = field(default_factory=list)
    source: str = "explicit"

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.GOAL:
            raise ValueError("GoalObject must have object_type GOAL")
        self.description = _require_text(self.description, "description")


@dataclass
class ConstraintObject(CognitiveObject):
    """A boundary that cognition or execution must respect."""

    description: str = ""
    hard: bool = True
    source: str = "system"

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.CONSTRAINT:
            raise ValueError("ConstraintObject must have object_type CONSTRAINT")
        self.description = _require_text(self.description, "description")


@dataclass
class ObservationObject(CognitiveObject):
    """
    A representation of something observed/measured.

    observation_time and source are explicit because observations are
    not interchangeable with interpretations or world-model beliefs.
    """

    value: Any = None
    observation_time: datetime = field(default_factory=utc_now)
    source: Optional[str] = None
    reliability: Optional[float] = None
    measurement_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.OBSERVATION:
            raise ValueError("ObservationObject must have object_type OBSERVATION")
        _validate_probability(self.reliability, "reliability")


@dataclass
class DataObject(CognitiveObject):
    """Normalized data derived from one or more observations."""

    value: Any = None
    source_ids: List[str] = field(default_factory=list)
    observed_at: Optional[datetime] = None
    ingested_at: datetime = field(default_factory=utc_now)
    freshness_seconds: Optional[float] = None
    quality_score: Optional[float] = None

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.DATA:
            raise ValueError("DataObject must have object_type DATA")
        _validate_probability(self.quality_score, "quality_score")
        if self.freshness_seconds is not None:
            _validate_non_negative(self.freshness_seconds, "freshness_seconds")


@dataclass
class ClaimObject(CognitiveObject):
    """A proposition whose epistemic status can be evaluated."""

    statement: str = ""
    epistemic: EpistemicAnnotation = field(
        default_factory=lambda: EpistemicAnnotation(EpistemicStatus.NOT_VERIFIED)
    )
    source_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.CLAIM:
            raise ValueError("ClaimObject must have object_type CLAIM")
        self.statement = _require_text(self.statement, "statement")


@dataclass
class EvidenceObject(CognitiveObject):
    """Evidence explicitly associated with a claim or hypothesis."""

    content: Any = None
    source_id: Optional[str] = None
    observed_at: Optional[datetime] = None
    reliability: Optional[float] = None
    independence_group: Optional[str] = None
    provenance_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.EVIDENCE:
            raise ValueError("EvidenceObject must have object_type EVIDENCE")
        _validate_probability(self.reliability, "reliability")


@dataclass
class AssumptionObject(CognitiveObject):
    """A proposition temporarily accepted for reasoning."""

    statement: str = ""
    epistemic: EpistemicAnnotation = field(
        default_factory=lambda: EpistemicAnnotation(EpistemicStatus.UNCERTAIN)
    )
    invalidation_conditions: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.ASSUMPTION:
            raise ValueError("AssumptionObject must have object_type ASSUMPTION")
        self.statement = _require_text(self.statement, "statement")


@dataclass
class HypothesisObject(CognitiveObject):
    """A candidate explanation maintained inside a hypothesis space."""

    statement: str = ""
    prior_probability: Optional[float] = None
    posterior_probability: Optional[float] = None
    evidence_ids: List[str] = field(default_factory=list)
    competing_hypothesis_ids: List[str] = field(default_factory=list)
    status: EpistemicStatus = EpistemicStatus.UNCERTAIN

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.HYPOTHESIS:
            raise ValueError("HypothesisObject must have object_type HYPOTHESIS")
        self.statement = _require_text(self.statement, "statement")
        _validate_probability(self.prior_probability, "prior_probability")
        _validate_probability(self.posterior_probability, "posterior_probability")


@dataclass
class BeliefObject(CognitiveObject):
    """Current maintained position about a proposition."""

    statement: str = ""
    epistemic: EpistemicAnnotation = field(
        default_factory=lambda: EpistemicAnnotation(EpistemicStatus.UNCERTAIN)
    )
    supporting_evidence_ids: List[str] = field(default_factory=list)
    contradicting_evidence_ids: List[str] = field(default_factory=list)
    predecessor_belief_id: Optional[str] = None
    invalidated_by_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.BELIEF:
            raise ValueError("BeliefObject must have object_type BELIEF")
        self.statement = _require_text(self.statement, "statement")


@dataclass
class CapabilityObject(CognitiveObject):
    """A capability available to the AI OS."""

    name: str = ""
    provider_id: Optional[str] = None
    description: str = ""
    authority_required: AuthorityLevel = AuthorityLevel.USE
    latency_budget_ms: Optional[float] = None
    reliability: Optional[float] = None
    risk_level: RiskLevel = RiskLevel.INFORMATIONAL
    dependency_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.CAPABILITY:
            raise ValueError("CapabilityObject must have object_type CAPABILITY")
        self.name = _require_text(self.name, "name")
        self.description = _require_text(self.description, "description")
        if self.latency_budget_ms is not None:
            _validate_non_negative(self.latency_budget_ms, "latency_budget_ms")
        _validate_probability(self.reliability, "reliability")


@dataclass
class ResourceObject(CognitiveObject):
    """A finite cognitive resource."""

    name: str = ""
    capacity: Optional[float] = None
    unit: str = ""
    available: Optional[float] = None
    reserved: float = 0.0

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.RESOURCE:
            raise ValueError("ResourceObject must have object_type RESOURCE")
        self.name = _require_text(self.name, "name")
        self.unit = _require_text(self.unit, "unit")
        if self.capacity is not None:
            _validate_non_negative(self.capacity, "capacity")
        if self.available is not None:
            _validate_non_negative(self.available, "available")
        _validate_non_negative(self.reserved, "reserved")


@dataclass
class ModelObject(CognitiveObject):
    """A registered reasoning/prediction/world model."""

    name: str = ""
    model_kind: str = ""
    version: str = ""
    provider_id: Optional[str] = None
    applicability: List[str] = field(default_factory=list)
    limitation_ids: List[str] = field(default_factory=list)
    validation_status: str = "NOT_VALIDATED"

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.MODEL:
            raise ValueError("ModelObject must have object_type MODEL")
        self.name = _require_text(self.name, "name")
        self.model_kind = _require_text(self.model_kind, "model_kind")
        self.version = _require_text(self.version, "version")


@dataclass
class DecisionObject(CognitiveObject):
    """A proposed or finalized decision with explicit reasoning links."""

    statement: str = ""
    option_ids: List[str] = field(default_factory=list)
    selected_option_id: Optional[str] = None
    evidence_ids: List[str] = field(default_factory=list)
    assumption_ids: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.INFORMATIONAL
    reversibility: Optional[float] = None
    authorization_required: AuthorityLevel = AuthorityLevel.AUTHORIZE
    readiness_status: str = "NOT_READY"

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.DECISION:
            raise ValueError("DecisionObject must have object_type DECISION")
        self.statement = _require_text(self.statement, "statement")
        _validate_probability(self.reversibility, "reversibility")


@dataclass
class ActionObject(CognitiveObject):
    """An intended or executed action, separated from its outcome."""

    description: str = ""
    decision_id: Optional[str] = None
    authorization_id: Optional[str] = None
    precondition_ids: List[str] = field(default_factory=list)
    expected_outcome_ids: List[str] = field(default_factory=list)
    reversible: bool = False
    idempotency_key: Optional[str] = None
    execution_status: str = "NOT_EXECUTED"

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.ACTION:
            raise ValueError("ActionObject must have object_type ACTION")
        self.description = _require_text(self.description, "description")


@dataclass
class OutcomeObject(CognitiveObject):
    """An observed result of an action or event."""

    description: str = ""
    action_id: Optional[str] = None
    observed_at: datetime = field(default_factory=utc_now)
    expected: bool = False
    deviation: Optional[str] = None
    evidence_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.OUTCOME:
            raise ValueError("OutcomeObject must have object_type OUTCOME")
        self.description = _require_text(self.description, "description")


@dataclass
class LessonObject(CognitiveObject):
    """A candidate or validated lesson derived from experience."""

    statement: str = ""
    source_event_ids: List[str] = field(default_factory=list)
    validation_status: str = "UNVALIDATED"
    applicability: List[str] = field(default_factory=list)
    confidence: Optional[float] = None

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.LESSON:
            raise ValueError("LessonObject must have object_type LESSON")
        self.statement = _require_text(self.statement, "statement")
        _validate_probability(self.confidence, "confidence")


@dataclass
class EvolutionProposalObject(CognitiveObject):
    """A proposed change to cognition, capability, or architecture."""

    description: str = ""
    target_id: Optional[str] = None
    rationale: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    test_requirements: List[str] = field(default_factory=list)
    blast_radius: List[str] = field(default_factory=list)
    approval_status: str = "PROPOSED"

    def __post_init__(self) -> None:
        if self.object_type != CognitiveObjectType.EVOLUTION_PROPOSAL:
            raise ValueError(
                "EvolutionProposalObject must have object_type EVOLUTION_PROPOSAL"
            )
        self.description = _require_text(self.description, "description")
        self.rationale = _require_text(self.rationale, "rationale")


@dataclass(frozen=True)
class CognitiveObjectFactory:
    """
    Factory for creating correctly typed objects.

    Keeping construction centralized gives later schema migration,
    validation, provenance, and compatibility layers one clear boundary.
    """

    version: str = COGNITIVE_OBJECTS_VERSION

    def task(self, objective: str, **kwargs: Any) -> TaskObject:
        return TaskObject(
            **_base(CognitiveObjectType.TASK),
            objective=objective,
            **kwargs,
        )

    def goal(self, description: str, **kwargs: Any) -> GoalObject:
        return GoalObject(
            **_base(CognitiveObjectType.GOAL),
            description=description,
            **kwargs,
        )

    def constraint(self, description: str, **kwargs: Any) -> ConstraintObject:
        return ConstraintObject(
            **_base(CognitiveObjectType.CONSTRAINT),
            description=description,
            **kwargs,
        )

    def observation(self, value: Any, **kwargs: Any) -> ObservationObject:
        return ObservationObject(
            **_base(CognitiveObjectType.OBSERVATION),
            value=value,
            **kwargs,
        )

    def data(self, value: Any, **kwargs: Any) -> DataObject:
        return DataObject(
            **_base(CognitiveObjectType.DATA),
            value=value,
            **kwargs,
        )

    def claim(self, statement: str, **kwargs: Any) -> ClaimObject:
        return ClaimObject(
            **_base(CognitiveObjectType.CLAIM),
            statement=statement,
            **kwargs,
        )

    def evidence(self, content: Any, **kwargs: Any) -> EvidenceObject:
        return EvidenceObject(
            **_base(CognitiveObjectType.EVIDENCE),
            content=content,
            **kwargs,
        )

    def assumption(self, statement: str, **kwargs: Any) -> AssumptionObject:
        return AssumptionObject(
            **_base(CognitiveObjectType.ASSUMPTION),
            statement=statement,
            **kwargs,
        )

    def hypothesis(self, statement: str, **kwargs: Any) -> HypothesisObject:
        return HypothesisObject(
            **_base(CognitiveObjectType.HYPOTHESIS),
            statement=statement,
            **kwargs,
        )

    def belief(self, statement: str, **kwargs: Any) -> BeliefObject:
        return BeliefObject(
            **_base(CognitiveObjectType.BELIEF),
            statement=statement,
            **kwargs,
        )

    def capability(self, name: str, description: str, **kwargs: Any) -> CapabilityObject:
        return CapabilityObject(
            **_base(CognitiveObjectType.CAPABILITY),
            name=name,
            description=description,
            **kwargs,
        )

    def resource(self, name: str, unit: str, **kwargs: Any) -> ResourceObject:
        return ResourceObject(
            **_base(CognitiveObjectType.RESOURCE),
            name=name,
            unit=unit,
            **kwargs,
        )

    def model(self, name: str, model_kind: str, version: str, **kwargs: Any) -> ModelObject:
        return ModelObject(
            **_base(CognitiveObjectType.MODEL),
            name=name,
            model_kind=model_kind,
            version=version,
            **kwargs,
        )

    def decision(self, statement: str, **kwargs: Any) -> DecisionObject:
        return DecisionObject(
            **_base(CognitiveObjectType.DECISION),
            statement=statement,
            **kwargs,
        )

    def action(self, description: str, **kwargs: Any) -> ActionObject:
        return ActionObject(
            **_base(CognitiveObjectType.ACTION),
            description=description,
            **kwargs,
        )

    def outcome(self, description: str, **kwargs: Any) -> OutcomeObject:
        return OutcomeObject(
            **_base(CognitiveObjectType.OUTCOME),
            description=description,
            **kwargs,
        )

    def lesson(self, statement: str, **kwargs: Any) -> LessonObject:
        return LessonObject(
            **_base(CognitiveObjectType.LESSON),
            statement=statement,
            **kwargs,
        )

    def evolution_proposal(
        self,
        description: str,
        rationale: str,
        **kwargs: Any,
    ) -> EvolutionProposalObject:
        return EvolutionProposalObject(
            **_base(CognitiveObjectType.EVOLUTION_PROPOSAL),
            description=description,
            rationale=rationale,
            **kwargs,
        )


def _base(object_type: CognitiveObjectType) -> Dict[str, Any]:
    """Generate common fields for a concrete cognitive object."""
    return {
        "object_id": f"{object_type.value.lower()}_{__import__('uuid').uuid4().hex}",
        "object_type": object_type,
        "schema_version": COGNITIVE_OBJECTS_VERSION,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "lifecycle": LifecycleStatus.ACTIVE,
    }


__all__ = [
    "COGNITIVE_OBJECTS_VERSION",
    "TaskObject",
    "GoalObject",
    "ConstraintObject",
    "ObservationObject",
    "DataObject",
    "ClaimObject",
    "EvidenceObject",
    "AssumptionObject",
    "HypothesisObject",
    "BeliefObject",
    "CapabilityObject",
    "ResourceObject",
    "ModelObject",
    "DecisionObject",
    "ActionObject",
    "OutcomeObject",
    "LessonObject",
    "EvolutionProposalObject",
    "CognitiveObjectFactory",
]
