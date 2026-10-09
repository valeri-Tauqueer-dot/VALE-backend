from __future__ import annotations

from typing import Any, Dict, Optional

from .context_state import HeroicContextState


class HeroicContextAssembler:
    """
    Assembles information into a single HEROIC context state.

    Existing context is updated only with explicitly supplied
    information. Missing information is not invented.
    """

    def assemble(
        self,
        user_request: str = "",
        user_context: Optional[Dict[str, Any]] = None,
        system_context: Optional[Dict[str, Any]] = None,
        environmental_context: Optional[Dict[str, Any]] = None,
        existing_context: Optional[
            HeroicContextState
        ] = None,
    ) -> HeroicContextState:
        context = (
            existing_context
            if existing_context is not None
            else HeroicContextState()
        )

        if user_request.strip():
            context.set_user_request(user_request)

        if user_context:
            context.update_user_context(user_context)

        if system_context:
            context.update_system_context(system_context)

        if environmental_context:
            context.update_environmental_context(
                environmental_context
            )

        return context

    def add_fact(
        self,
        context: HeroicContextState,
        fact: str,
    ) -> HeroicContextState:
        context.add_fact(fact)
        return context

    def add_assumption(
        self,
        context: HeroicContextState,
        assumption: str,
    ) -> HeroicContextState:
        context.add_assumption(assumption)
        return context

    def add_uncertainty(
        self,
        context: HeroicContextState,
        uncertainty: str,
    ) -> HeroicContextState:
        context.add_uncertainty(uncertainty)
        return context

    def add_missing_information(
        self,
        context: HeroicContextState,
        item: str,
    ) -> HeroicContextState:
        context.add_missing_information(item)
        return context

    def is_sufficient(
        self,
        context: HeroicContextState,
    ) -> bool:
        return context.is_sufficient()

    def to_dict(
        self,
        context: HeroicContextState,
    ) -> Dict[str, Any]:
        return context.to_dict()
