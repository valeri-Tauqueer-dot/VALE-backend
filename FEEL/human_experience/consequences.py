"""
VALE FEELING Brain
Human Consequence Analyzer

File:
    FEEL/human_experience/consequences.py

Purpose:
    Models possible human consequences of a situation.

The analyzer distinguishes:
    - observed consequences
    - explicitly stated consequences
    - possible consequences
    - uncertain consequences

It does not predict a person's future with certainty and does not
assume that a possible consequence will actually occur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..core.contracts import (
    CognitiveContext,
    EngineResult,
)
from ..core.models import (
    HumanContext,
)


@dataclass
class HumanConsequence:
    """
    A possible human consequence associated with a situation.

    `certainty` is deliberately a confidence estimate about the
    reasoning, not a probability that the event will definitely happen.
    """

    description: str

    category: str = "general"

    source: str = "inference"

    certainty: float = 0.0

    affected_area: str = "unknown"

    time_horizon: str = "unknown"

    reversibility: str = "unknown"

    evidence: List[str] = field(
        default_factory=list
    )

    uncertainties: List[str] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.certainty = max(
            0.0,
            min(1.0, self.certainty),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "category": self.category,
            "source": self.source,
            "certainty": self.certainty,
            "affected_area": self.affected_area,
            "time_horizon": self.time_horizon,
            "reversibility": self.reversibility,
            "evidence": list(self.evidence),
            "uncertainties": list(self.uncertainties),
        }


class HumanConsequenceAnalyzer:
    """
    Analyzes possible human consequences of a situation.

    Responsibilities:
        - identify explicitly stated consequences
        - identify plausible consequence categories
        - distinguish immediate and longer-term implications
        - identify potentially affected areas
        - identify reversibility
        - expose uncertainty

    This engine does NOT:
        - determine what will happen
        - diagnose psychological consequences
        - claim emotional outcomes as facts
        - make decisions on behalf of UNITY
        - replace safety systems
    """

    NAME = "human_consequence_analyzer"

    CATEGORY_KEYWORDS = {
        "financial": (
            "money",
            "cost",
            "price",
            "financial",
            "income",
            "salary",
            "loss",
            "debt",
            "profit",
        ),
        "time": (
            "time",
            "deadline",
            "delay",
            "late",
            "schedule",
            "hours",
            "days",
        ),
        "work": (
            "job",
            "work",
            "project",
            "career",
            "business",
            "employee",
            "client",
        ),
        "relationship": (
            "friend",
            "family",
            "partner",
            "relationship",
            "team",
            "colleague",
            "communication",
        ),
        "learning": (
            "learn",
            "study",
            "education",
            "understand",
            "knowledge",
            "skill",
        ),
        "safety": (
            "danger",
            "risk",
            "unsafe",
            "safety",
            "harm",
            "accident",
            "emergency",
        ),
        "privacy": (
            "privacy",
            "private",
            "personal data",
            "password",
            "account",
            "information",
        ),
        "decision": (
            "choose",
            "choice",
            "decision",
            "decide",
            "option",
            "tradeoff",
        ),
    }

    def analyze(
        self,
        context: CognitiveContext,
    ) -> EngineResult:
        """
        Analyze possible consequences from the supplied context.
        """

        result = EngineResult(
            engine=self.NAME,
            success=True,
        )

        text = (context.user_input or "").strip()

        if not text:
            result.summary = (
                "No situation was supplied for consequence analysis."
            )
            result.add_uncertainty(
                "Human consequences cannot be meaningfully "
                "modeled without a situation."
            )
            return result

        consequences = self.identify_consequences(
            context
        )

        if not consequences:
            result.summary = (
                "No specific human consequence could be "
                "identified from the available information."
            )

            result.add_uncertainty(
                "The available context is insufficient to "
                "identify meaningful consequences."
            )

            result.outputs["consequences"] = []

            return result

        for consequence in consequences:
            result.add_inference(
                consequence.description
            )

            for uncertainty in consequence.uncertainties:
                result.add_uncertainty(
                    uncertainty
                )

        result.outputs["consequences"] = [
            consequence.to_dict()
            for consequence in consequences
        ]

        result.confidence = self._overall_confidence(
            consequences
        )

        result.summary = self._build_summary(
            consequences
        )

        result.metadata["epistemic_boundary"] = (
            "Consequences are possible outcomes or contextual "
            "implications, not guaranteed predictions."
        )

        return result

    def identify_consequences(
        self,
        context: CognitiveContext,
    ) -> List[HumanConsequence]:
        """
        Generate conservative consequence candidates.
        """

        text = (context.user_input or "").strip()

        consequences: List[HumanConsequence] = []

        categories = self._detect_categories(text)

        # --------------------------------------------------------------
        # Explicit user-stated consequences
        # --------------------------------------------------------------

        explicit = self._extract_explicit_consequence_language(
            text
        )

        for statement in explicit:
            consequences.append(
                HumanConsequence(
                    description=statement,
                    category="explicit",
                    source="user_statement",
                    certainty=0.90,
                    affected_area="user_stated",
                    time_horizon="unknown",
                    reversibility="unknown",
                    evidence=[
                        "Explicitly stated in the supplied input."
                    ],
                )
            )

        # --------------------------------------------------------------
        # Category-specific implications
        # --------------------------------------------------------------

        for category in categories:
            candidate = self._category_consequence(
                category
            )

            if candidate is not None:
                consequences.append(candidate)

        # --------------------------------------------------------------
        # General problem-solving consequence
        # --------------------------------------------------------------

        if self._contains_problem_signal(text):
            consequences.append(
                HumanConsequence(
                    description=(
                        "If the underlying problem remains unresolved, "
                        "it may continue to consume time, attention, "
                        "resources, or effort."
                    ),
                    category="problem_resolution",
                    source="contextual_inference",
                    certainty=0.45,
                    affected_area="resources",
                    time_horizon="near_term",
                    reversibility="potentially_reversible",
                    uncertainties=[
                        "The actual effect depends on the nature "
                        "and duration of the problem."
                    ],
                )
            )

        return self._deduplicate(
            consequences
        )

    def from_human_context(
        self,
        human_context: HumanContext,
    ) -> List[HumanConsequence]:
        """
        Generate consequence candidates from an existing
        HumanContext model.

        This method allows later integration with the
        Human Experience Engine.
        """

        consequences: List[HumanConsequence] = []

        # The exact fields available in HumanContext may evolve.
        # We therefore use safe attribute access to preserve
        # compatibility as the model expands.

        concerns = getattr(
            human_context,
            "concerns",
            [],
        )

        priorities = getattr(
            human_context,
            "priorities",
            [],
        )

        constraints = getattr(
            human_context,
            "constraints",
            [],
        )

        for concern in concerns or []:
            consequences.append(
                HumanConsequence(
                    description=(
                        f"The concern '{concern}' may influence "
                        "the person's experience or decisions."
                    ),
                    category="concern",
                    source="human_context",
                    certainty=0.40,
                    affected_area="human_experience",
                    uncertainties=[
                        "The importance of this concern "
                        "has not necessarily been established."
                    ],
                )
            )

        for priority in priorities or []:
            consequences.append(
                HumanConsequence(
                    description=(
                        f"The priority '{priority}' may shape "
                        "which outcomes matter most."
                    ),
                    category="priority",
                    source="human_context",
                    certainty=0.45,
                    affected_area="decision_context",
                    uncertainties=[
                        "Priority does not necessarily imply "
                        "a specific future behavior."
                    ],
                )
            )

        for constraint in constraints or []:
            consequences.append(
                HumanConsequence(
                    description=(
                        f"The constraint '{constraint}' may limit "
                        "available options or actions."
                    ),
                    category="constraint",
                    source="human_context",
                    certainty=0.55,
                    affected_area="available_options",
                    uncertainties=[
                        "The actual effect depends on whether "
                        "the constraint remains active."
                    ],
                )
            )

        return self._deduplicate(
            consequences
        )

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def _detect_categories(
        self,
        text: str,
    ) -> List[str]:
        normalized = text.lower()

        categories: List[str] = []

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(
                keyword in normalized
                for keyword in keywords
            ):
                categories.append(category)

        return categories

    def _contains_problem_signal(
        self,
        text: str,
    ) -> bool:
        normalized = text.lower()

        signals = (
            "problem",
            "issue",
            "error",
            "failed",
            "failure",
            "broken",
            "can't",
            "cannot",
            "unable",
            "not working",
            "stuck",
        )

        return any(
            signal in normalized
            for signal in signals
        )

    def _extract_explicit_consequence_language(
        self,
        text: str,
    ) -> List[str]:
        """
        Detect very simple explicit consequence patterns.

        We only extract what is actually stated; we do not infer the
        hidden meaning of the statement.
        """

        normalized = text.lower()

        markers = (
            "because",
            "so that",
            "which means",
            "as a result",
            "therefore",
            "this means",
        )

        statements: List[str] = []

        for marker in markers:
            index = normalized.find(marker)

            if index == -1:
                continue

            original_index = index + len(marker)

            consequence = text[
                original_index:
            ].strip(" :,-.")

            if consequence:
                statements.append(
                    f"Possible stated consequence: {consequence}"
                )

        return statements

    # ------------------------------------------------------------------
    # Category reasoning
    # ------------------------------------------------------------------

    def _category_consequence(
        self,
        category: str,
    ) -> HumanConsequence | None:
        if category == "financial":
            return HumanConsequence(
                description=(
                    "The situation may have financial implications "
                    "or resource costs."
                ),
                category=category,
                source="contextual_inference",
                certainty=0.40,
                affected_area="financial_resources",
                time_horizon="unknown",
                reversibility="unknown",
                uncertainties=[
                    "No specific financial magnitude "
                    "has been established."
                ],
            )

        if category == "time":
            return HumanConsequence(
                description=(
                    "The situation may affect available time, "
                    "deadlines, or scheduling."
                ),
                category=category,
                source="contextual_inference",
                certainty=0.50,
                affected_area="time",
                time_horizon="near_term",
                reversibility="partially_reversible",
                uncertainties=[
                    "The actual time impact depends on "
                    "the specific circumstances."
                ],
            )

        if category == "work":
            return HumanConsequence(
                description=(
                    "The situation may affect work tasks, "
                    "responsibilities, or project progress."
                ),
                category=category,
                source="contextual_inference",
                certainty=0.40,
                affected_area="work",
                time_horizon="unknown",
                reversibility="unknown",
                uncertainties=[
                    "The actual professional impact is unknown "
                    "without additional context."
                ],
            )

        if category == "relationship":
            return HumanConsequence(
                description=(
                    "The situation may influence communication "
                    "or relationships between people."
                ),
                category=category,
                source="contextual_inference",
                certainty=0.35,
                affected_area="relationships",
                time_horizon="unknown",
                reversibility="unknown",
                uncertainties=[
                    "Relationship effects depend heavily on "
                    "the people and circumstances involved."
                ],
            )

        if category == "learning":
            return HumanConsequence(
                description=(
                    "The situation may affect understanding, "
                    "learning, or skill development."
                ),
                category=category,
                source="contextual_inference",
                certainty=0.45,
                affected_area="learning",
                time_horizon="near_term",
                reversibility="reversible",
                uncertainties=[
                    "The actual learning outcome depends on "
                    "the quality and use of the information."
                ],
            )

        if category == "safety":
            return HumanConsequence(
                description=(
                    "The situation may have safety implications "
                    "that require explicit assessment."
                ),
                category=category,
                source="contextual_inference",
                certainty=0.55,
                affected_area="safety",
                time_horizon="unknown",
                reversibility="unknown",
                uncertainties=[
                    "The specific hazard and severity "
                    "are not established by this engine."
                ],
            )

        if category == "privacy":
            return HumanConsequence(
                description=(
                    "The situation may affect privacy or "
                    "exposure of personal information."
                ),
                category=category,
                source="contextual_inference",
                certainty=0.50,
                affected_area="privacy",
                time_horizon="unknown",
                reversibility="potentially_irreversible",
                uncertainties=[
                    "The actual privacy exposure depends on "
                    "what information is involved."
                ],
            )

        if category == "decision":
            return HumanConsequence(
                description=(
                    "The situation may involve trade-offs whose "
                    "consequences should be considered before choosing."
                ),
                category=category,
                source="contextual_inference",
                certainty=0.45,
                affected_area="decision_making",
                time_horizon="unknown",
                reversibility="unknown",
                uncertainties=[
                    "The available alternatives and their "
                    "trade-offs are not yet fully known."
                ],
            )

        return None

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _deduplicate(
        self,
        consequences: List[HumanConsequence],
    ) -> List[HumanConsequence]:
        seen = set()
        unique: List[HumanConsequence] = []

        for consequence in consequences:
            key = consequence.description.strip().lower()

            if not key or key in seen:
                continue

            seen.add(key)
            unique.append(consequence)

        return unique

    def _overall_confidence(
        self,
        consequences: List[HumanConsequence],
    ) -> float:
        if not consequences:
            return 0.0

        total = sum(
            consequence.certainty
            for consequence in consequences
        )

        return max(
            0.0,
            min(
                1.0,
                total / len(consequences),
            ),
        )

    def _build_summary(
        self,
        consequences: List[HumanConsequence],
    ) -> str:
        categories = sorted(
            {
                consequence.category
                for consequence in consequences
            }
        )

        return (
            "Identified "
            f"{len(consequences)} possible human consequence "
            "considerations across "
            f"{len(categories)} contextual area(s). "
            "These are not guaranteed outcomes."
        )


__all__ = [
    "HumanConsequence",
    "HumanConsequenceAnalyzer",
]
