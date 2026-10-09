from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class HeroicContextState:
    """
    Stores the context HEROIC needs to understand and
    coordinate a mission.

    This state records supplied information. It does not
    treat missing information as established fact.
    """

    context_id: str = "heroic_context"
    user_request: str = ""

    user_context: Dict[str, Any] = field(
        default_factory=dict
    )
    system_context: Dict[str, Any] = field(
        default_factory=dict
    )
    environmental_context: Dict[str, Any] = field(
        default_factory=dict
    )

    facts: List[str] = field(
        default_factory=list
    )
    assumptions: List[str] = field(
        default_factory=list
    )
    uncertainties: List[str] = field(
        default_factory=list
    )
    missing_information: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def set_user_request(
        self,
        request: str,
    ) -> None:
        self.user_request = request.strip()

    def add_fact(
        self,
        fact: str,
    ) -> None:
        if fact and fact not in self.facts:
            self.facts.append(fact)

    def add_assumption(
        self,
        assumption: str,
    ) -> None:
        if (
            assumption
            and assumption not in self.assumptions
        ):
            self.assumptions.append(assumption)

    def add_uncertainty(
        self,
        uncertainty: str,
    ) -> None:
        if (
            uncertainty
            and uncertainty not in self.uncertainties
        ):
            self.uncertainties.append(uncertainty)

    def add_missing_information(
        self,
        item: str,
    ) -> None:
        if (
            item
            and item not in self.missing_information
        ):
            self.missing_information.append(item)

    def resolve_missing_information(
        self,
        item: str,
    ) -> bool:
        if item not in self.missing_information:
            return False

        self.missing_information.remove(item)
        return True

    def update_user_context(
        self,
        values: Dict[str, Any],
    ) -> None:
        self.user_context.update(values)

    def update_system_context(
        self,
        values: Dict[str, Any],
    ) -> None:
        self.system_context.update(values)

    def update_environmental_context(
        self,
        values: Dict[str, Any],
    ) -> None:
        self.environmental_context.update(values)

    def is_sufficient(self) -> bool:
        return (
            bool(self.user_request)
            and not self.missing_information
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "user_request": self.user_request,
            "user_context": dict(self.user_context),
            "system_context": dict(self.system_context),
            "environmental_context": dict(
                self.environmental_context
            ),
            "facts": list(self.facts),
            "assumptions": list(self.assumptions),
            "uncertainties": list(self.uncertainties),
            "missing_information": list(
                self.missing_information
            ),
            "metadata": dict(self.metadata),
        }
