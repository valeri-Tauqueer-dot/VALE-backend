from future import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

from HEROIC.context.context_state import (
ContextScope,
ContextSource,
HeroicContextState,
)

class HeroicContextAssembler:
"""
Assembles structured context for HEROIC mission planning.

The assembler combines explicitly supplied information into a
single contextual state. It does not invent missing facts and
does not perform external retrieval by itself.
"""

def __init__(
    self,
    *,
    default_scope: ContextScope = ContextScope.MISSION,
) -> None:
    self.default_scope = default_scope

def create_context(
    self,
    context_id: str,
    *,
    user_request: str = "",
    scope: Optional[ContextScope] = None,
    mission_id: str = "",
    goal_id: str = "",
    objective_id: str = "",
    task_id: str = "",
) -> HeroicContextState:
    """
    Create an empty contextual state.
    """
    if not context_id:
        raise ValueError("Context ID cannot be empty.")

    return HeroicContextState(
        context_id=context_id,
        scope=scope or self.default_scope,
        mission_id=mission_id,
        goal_id=goal_id,
        objective_id=objective_id,
        task_id=task_id,
        user_request=user_request,
    )

def assemble(
    self,
    context: HeroicContextState,
    *,
    facts: Optional[Mapping[str, Any]] = None,
    signals: Optional[Mapping[str, Any]] = None,
    assumptions: Optional[Iterable[str]] = None,
    constraints: Optional[Iterable[str]] = None,
    capabilities: Optional[Iterable[str]] = None,
    brains: Optional[Iterable[str]] = None,
    missing_information: Optional[Iterable[str]] = None,
    contradictions: Optional[Iterable[str]] = None,
    default_source: ContextSource = ContextSource.UNKNOWN,
    fact_sources: Optional[Mapping[str, ContextSource]] = None,
    signal_sources: Optional[Mapping[str, ContextSource]] = None,
) -> HeroicContextState:
    """
    Add supplied contextual information to an existing state.

    Nothing is inferred when a value is absent.
    """
    if facts:
        for key, value in facts.items():
            source = default_source

            if fact_sources and key in fact_sources:
                source = fact_sources[key]

            context.add_fact(
                key,
                value,
                source,
            )

    if signals:
        for key, value in signals.items():
            source = default_source

            if signal_sources and key in signal_sources:
                source = signal_sources[key]

            context.add_signal(
                key,
                value,
                source,
            )

    if assumptions:
        for assumption in assumptions:
            context.add_assumption(assumption)

    if constraints:
        for constraint in constraints:
            context.add_constraint(constraint)

    if capabilities:
        for capability_id in capabilities:
            context.add_capability(capability_id)

    if brains:
        for brain_name in brains:
            context.add_brain(brain_name)

    if missing_information:
        for information in missing_information:
            context.add_missing_information(information)

    if contradictions:
        for contradiction in contradictions:
            context.add_contradiction(contradiction)

    return context

def merge(
    self,
    target: HeroicContextState,
    source: HeroicContextState,
) -> HeroicContextState:
    """
    Merge one contextual state into another.

    Existing target values are preserved unless the source contains
    a value for the same fact or signal key.
    """
    for key, value in source.facts.items():
        source_type = source.sources.get(
            key,
            ContextSource.UNKNOWN,
        )

        target.add_fact(
            key,
            value,
            source_type,
        )

    for key, value in source.signals.items():
        source_type = source.sources.get(
            key,
            ContextSource.UNKNOWN,
        )

        target.add_signal(
            key,
            value,
            source_type,
        )

    for assumption in source.assumptions:
        target.add_assumption(assumption)

    for constraint in source.constraints:
        target.add_constraint(constraint)

    for capability_id in source.relevant_capabilities:
        target.add_capability(capability_id)

    for brain_name in source.relevant_brains:
        target.add_brain(brain_name)

    for information in source.missing_information:
        target.add_missing_information(information)

    for contradiction in source.contradictions:
        target.add_contradiction(contradiction)

    target.confidence = min(
        target.confidence,
        source.confidence,
    )

    return target

def add_user_context(
    self,
    context: HeroicContextState,
    values: Mapping[str, Any],
) -> HeroicContextState:
    """Add explicitly user-provided contextual values."""
    return self.assemble(
        context,
        facts=values,
        default_source=ContextSource.USER,
    )

def add_memory_context(
    self,
    context: HeroicContextState,
    values: Mapping[str, Any],
) -> HeroicContextState:
    """Add context supplied by the memory system."""
    return self.assemble(
        context,
        facts=values,
        default_source=ContextSource.MEMORY,
    )

def add_knowledge_context(
    self,
    context: HeroicContextState,
    values: Mapping[str, Any],
) -> HeroicContextState:
    """Add context supplied by the knowledge system."""
    return self.assemble(
        context,
        facts=values,
        default_source=ContextSource.KNOWLEDGE,
    )

def add_cognitive_state(
    self,
    context: HeroicContextState,
    values: Mapping[str, Any],
) -> HeroicContextState:
    """Add context supplied by VALE cognitive state."""
    return self.assemble(
        context,
        facts=values,
        default_source=ContextSource.COGNITIVE_STATE,
    )

def mark_missing(
    self,
    context: HeroicContextState,
    information: Iterable[str],
) -> HeroicContextState:
    """Explicitly mark information as missing."""
    for item in information:
        context.add_missing_information(item)

    return context

def add_contradictions(
    self,
    context: HeroicContextState,
    contradictions: Iterable[str],
) -> HeroicContextState:
    """Explicitly register contextual contradictions."""
    for contradiction in contradictions:
        context.add_contradiction(contradiction)

    return context
