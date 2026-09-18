"""
LEGEND Stage 15 — Strategy Intelligence
========================================

Transforms LEGEND's market intelligence into structured strategy
descriptions and strategy-condition assessments.

Architecture position:

    Market Data
        ↓
    Market State
        ↓
    Market DNA
        ↓
    Market Regime
        ↓
    Regime Memory
        ↓
    Historical Intelligence
        ↓
    Hypothesis Generator
        ↓
    Missing Information
        ↓
    Market Understanding
        ↓
    Market Influence Map
        ↓
    Participant Behavior
        ↓
    Market Wisdom
        ↓
    Trading Wisdom Library
        ↓
    Strategy Intelligence

Core principle:

    A strategy is a conditional decision framework, not a guaranteed
    prediction of market behavior.

Strategy Intelligence therefore evaluates:

    - what market conditions a strategy is designed for
    - what evidence supports those conditions
    - what evidence contradicts them
    - what information is missing
    - historical relevance
    - regime compatibility
    - volatility compatibility
    - structural compatibility
    - known failure conditions
    - uncertainty
    - strategy lifecycle

This module does NOT:

    - execute trades
    - place orders
    - generate BUY/SELL commands
    - guarantee profitability
    - fabricate backtest results
    - invent historical performance
    - assume future market direction
    - replace Risk Intelligence
    - replace Backtesting
    - replace Strategy Stress Testing
    - override MCVL
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


STRATEGY_STATES = {
    "DRAFT",
    "PROVISIONAL",
    "CONDITIONALLY_SUPPORTED",
    "SUPPORTED",
    "CONTESTED",
    "WEAKENED",
    "RETIRED",
    "INVALIDATED",
    "INSUFFICIENT_INFORMATION",
}


STRATEGY_TYPES = {
    "TREND_FOLLOWING",
    "MEAN_REVERSION",
    "BREAKOUT",
    "MOMENTUM",
    "RANGE",
    "VOLATILITY",
    "EVENT_DRIVEN",
    "MULTI_REGIME",
    "MARKET_NEUTRAL",
    "OTHER",
}


@dataclass
class StrategyEvidence:
    """
    Evidence associated with a strategy assessment.

    Evidence may support or contradict the strategy's applicability.
    """

    evidence_id: str
    evidence_type: str
    statement: str

    supports: bool = True

    strength: float = 0.0
    uncertainty: float = 1.0

    source: Optional[str] = None
    observed_at: Optional[str] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyCondition:
    """
    One condition under which a strategy may be applicable.
    """

    condition_id: str
    description: str

    category: str = "GENERAL"

    required: bool = False

    observed: bool = False
    contradicted: bool = False
    unknown: bool = True

    confidence: float = 0.0
    uncertainty: float = 1.0

    evidence_ids: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyAssessment:
    """
    Current intelligence assessment of one strategy.

    This is an analytical state, not an execution instruction.
    """

    strategy_id: str
    name: str

    strategy_type: str = "OTHER"

    description: str = ""

    state: str = "DRAFT"

    conditions_total: int = 0
    conditions_observed: int = 0
    conditions_contradicted: int = 0
    conditions_unknown: int = 0

    supporting_evidence_count: int = 0
    opposing_evidence_count: int = 0

    historical_support: int = 0
    historical_counterexamples: int = 0

    backtest_count: int = 0
    stress_test_count: int = 0

    confidence: float = 0.0
    uncertainty: float = 1.0

    failure_conditions: List[str] = field(
        default_factory=list
    )

    applicable_regimes: List[str] = field(
        default_factory=list
    )

    incompatible_regimes: List[str] = field(
        default_factory=list
    )

    applicable_market_states: List[str] = field(
        default_factory=list
    )

    limitations: List[str] = field(
        default_factory=list
    )

    created_at: str = field(
        default_factory=utc_now
    )

    updated_at: str = field(
        default_factory=utc_now
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyDefinition:
    """
    Structured strategy definition.

    The definition explains what the strategy expects from the market.
    It does not assert that those expectations will occur.
    """

    strategy_id: str
    name: str

    strategy_type: str = "OTHER"

    description: str = ""

    conditions: List[StrategyCondition] = field(
        default_factory=list
    )

    failure_conditions: List[str] = field(
        default_factory=list
    )

    applicable_regimes: List[str] = field(
        default_factory=list
    )

    incompatible_regimes: List[str] = field(
        default_factory=list
    )

    applicable_market_states: List[str] = field(
        default_factory=list
    )

    required_information: List[str] = field(
        default_factory=list
    )

    limitations: List[str] = field(
        default_factory=list
    )

    tags: List[str] = field(
        default_factory=list
    )

    created_at: str = field(
        default_factory=utc_now
    )

    updated_at: str = field(
        default_factory=utc_now
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)

        result["conditions"] = [
            condition.to_dict()
            for condition in self.conditions
        ]

        return result


class StrategyIntelligence:
    """
    LEGEND's Strategy Intelligence Engine.

    Responsibilities:

        1. Store explicit strategy definitions.
        2. Represent required market conditions.
        3. Compare current market context with those conditions.
        4. Collect supporting/opposing evidence.
        5. Track historical support and counterexamples.
        6. Preserve failure conditions.
        7. Track uncertainty.
        8. Identify conditionally compatible strategies.
        9. Provide structured intelligence to later systems.

    It deliberately does not decide whether a human should trade.
    """

    VERSION = "0.1.0"
    COMPONENT = "LEGEND_STRATEGY_INTELLIGENCE"

    def __init__(
        self,
        max_strategies: int = 500,
        max_evidence_per_strategy: int = 300,
    ) -> None:

        self.max_strategies = max(
            1,
            int(max_strategies),
        )

        self.max_evidence_per_strategy = max(
            1,
            int(max_evidence_per_strategy),
        )

        self.strategies: Dict[
            str,
            StrategyDefinition,
        ] = {}

        self.assessments: Dict[
            str,
            StrategyAssessment,
        ] = {}

        self.evidence: Dict[
            str,
            List[StrategyEvidence],
        ] = {}

        self.last_context: Dict[str, Any] = {}

    # ================================================================
    # Helpers
    # ================================================================

    @staticmethod
    def _clamp(
        value: Any,
        low: float = 0.0,
        high: float = 1.0,
    ) -> float:

        try:
            number = float(value)
        except (
            TypeError,
            ValueError,
        ):
            return low

        return max(
            low,
            min(high, number),
        )

    @staticmethod
    def _normalize_type(
        value: str,
    ) -> str:

        normalized = str(
            value or "OTHER"
        ).strip().upper()

        if normalized not in STRATEGY_TYPES:
            return "OTHER"

        return normalized

    @staticmethod
    def _normalize_state(
        value: str,
    ) -> str:

        normalized = str(
            value or "DRAFT"
        ).strip().upper()

        if normalized not in STRATEGY_STATES:
            return "DRAFT"

        return normalized

    @staticmethod
    def _dict(
        context: Dict[str, Any],
        *keys: str,
    ) -> Dict[str, Any]:

        for key in keys:

            value = context.get(
                key
            )

            if isinstance(
                value,
                dict,
            ):
                return value

        return {}

    @staticmethod
    def _list(
        context: Dict[str, Any],
        *keys: str,
    ) -> List[Any]:

        for key in keys:

            value = context.get(
                key
            )

            if isinstance(
                value,
                list,
            ):
                return value

        return []

    # ================================================================
    # Strategy registration
    # ================================================================

    def register_strategy(
        self,
        strategy_id: str,
        name: str,
        strategy_type: str = "OTHER",
        description: str = "",
        conditions: Optional[
            Iterable[StrategyCondition]
        ] = None,
        failure_conditions: Optional[
            Iterable[str]
        ] = None,
        applicable_regimes: Optional[
            Iterable[str]
        ] = None,
        incompatible_regimes: Optional[
            Iterable[str]
        ] = None,
        applicable_market_states: Optional[
            Iterable[str]
        ] = None,
        required_information: Optional[
            Iterable[str]
        ] = None,
        limitations: Optional[
            Iterable[str]
        ] = None,
        tags: Optional[
            Iterable[str]
        ] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> StrategyDefinition:

        strategy_id = str(
            strategy_id
        ).strip()

        if not strategy_id:
            raise ValueError(
                "strategy_id cannot be empty."
            )

        if not str(name).strip():
            raise ValueError(
                "Strategy name cannot be empty."
            )

        if strategy_id in self.strategies:
            raise ValueError(
                f"Strategy '{strategy_id}' already exists."
            )

        definition = StrategyDefinition(
            strategy_id=strategy_id,
            name=str(name).strip(),
            strategy_type=self._normalize_type(
                strategy_type
            ),
            description=str(
                description
            ).strip(),
            conditions=list(
                conditions or []
            ),
            failure_conditions=list(
                failure_conditions or []
            ),
            applicable_regimes=list(
                applicable_regimes or []
            ),
            incompatible_regimes=list(
                incompatible_regimes or []
            ),
            applicable_market_states=list(
                applicable_market_states or []
            ),
            required_information=list(
                required_information or []
            ),
            limitations=list(
                limitations or []
            ),
            tags=list(
                tags or []
            ),
            metadata=dict(
                metadata or {}
            ),
        )

        if not definition.limitations:

            definition.limitations = [
                "Strategy applicability is conditional.",
                "Historical behavior does not guarantee future behavior.",
                "Backtesting does not eliminate live-market uncertainty.",
                "Execution and risk controls are outside this component.",
            ]

        self.strategies[strategy_id] = definition

        self.assessments[strategy_id] = (
            StrategyAssessment(
                strategy_id=strategy_id,
                name=definition.name,
                strategy_type=(
                    definition.strategy_type
                ),
                description=definition.description,
                applicable_regimes=list(
                    definition.applicable_regimes
                ),
                incompatible_regimes=list(
                    definition.incompatible_regimes
                ),
                applicable_market_states=list(
                    definition.applicable_market_states
                ),
                failure_conditions=list(
                    definition.failure_conditions
                ),
                limitations=list(
                    definition.limitations
                ),
            )
        )

        self.evidence[strategy_id] = []

        self._enforce_limits()

        return definition

    # ================================================================
    # Condition creation
    # ================================================================

    def add_condition(
        self,
        strategy_id: str,
        description: str,
        category: str = "GENERAL",
        required: bool = False,
        condition_id: Optional[str] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> StrategyCondition:

        strategy = self.strategies.get(
            strategy_id
        )

        if strategy is None:
            raise KeyError(
                f"Strategy '{strategy_id}' does not exist."
            )

        if not str(description).strip():
            raise ValueError(
                "Condition description cannot be empty."
            )

        condition_id = condition_id or (
            f"{strategy_id}:condition:"
            f"{len(strategy.conditions) + 1}"
        )

        condition = StrategyCondition(
            condition_id=condition_id,
            description=str(
                description
            ).strip(),
            category=str(
                category or "GENERAL"
            ).upper(),
            required=bool(
                required
            ),
            metadata=dict(
                metadata or {}
            ),
        )

        strategy.conditions.append(
            condition
        )

        strategy.updated_at = utc_now()

        self._recalculate(
            strategy_id
        )

        return condition

    # ================================================================
    # Evidence
    # ================================================================

    def add_evidence(
        self,
        strategy_id: str,
        evidence_type: str,
        statement: str,
        supports: bool = True,
        strength: float = 0.5,
        uncertainty: float = 0.5,
        source: Optional[str] = None,
        observed_at: Optional[str] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> StrategyEvidence:

        if strategy_id not in self.strategies:
            raise KeyError(
                f"Strategy '{strategy_id}' does not exist."
            )

        if not str(statement).strip():
            raise ValueError(
                "Evidence statement cannot be empty."
            )

        evidence_id = (
            f"{strategy_id}:evidence:"
            f"{len(self.evidence.get(strategy_id, [])) + 1}"
        )

        item = StrategyEvidence(
            evidence_id=evidence_id,
            evidence_type=str(
                evidence_type or "OTHER"
            ).upper(),
            statement=str(
                statement
            ).strip(),
            supports=bool(
                supports
            ),
            strength=self._clamp(
                strength
            ),
            uncertainty=self._clamp(
                uncertainty
            ),
            source=source,
            observed_at=(
                observed_at or utc_now()
            ),
            metadata=dict(
                metadata or {}
            ),
        )

        self.evidence.setdefault(
            strategy_id,
            [],
        ).append(
            item
        )

        if len(
            self.evidence[strategy_id]
        ) > self.max_evidence_per_strategy:

            self.evidence[strategy_id] = (
                self.evidence[strategy_id]
                [
                    -self.max_evidence_per_strategy:
                ]
            )

        self._recalculate(
            strategy_id
        )

        return item

    # ================================================================
    # Context assessment
    # ================================================================

    def assess_context(
        self,
        strategy_id: str,
        context: Dict[str, Any],
    ) -> Optional[StrategyAssessment]:

        strategy = self.strategies.get(
            strategy_id
        )

        assessment = self.assessments.get(
            strategy_id
        )

        if (
            strategy is None
            or assessment is None
        ):
            return None

        if not isinstance(
            context,
            dict,
        ):
            raise TypeError(
                "context must be a dictionary."
            )

        state = self._dict(
            context,
            "market_state",
        )

        dna = self._dict(
            context,
            "market_dna",
        )

        regime = self._dict(
            context,
            "market_regime",
        )

        understanding = self._dict(
            context,
            "market_understanding",
        )

        history = self._dict(
            context,
            "historical_intelligence",
        )

        wisdom = self._dict(
            context,
            "market_wisdom",
            "trading_wisdom_library",
        )

        current_regime = str(
            regime.get(
                "regime",
                regime.get(
                    "regime_label",
                    "",
                ),
            )
        ).strip()

        current_direction = str(
            state.get(
                "direction",
                state.get(
                    "trend_direction",
                    "",
                ),
            )
        ).strip()

        current_volatility = str(
            state.get(
                "volatility",
                dna.get(
                    "volatility_behavior",
                    "",
                ),
            )
        ).strip()

        context_text = " ".join(
            str(value).lower()
            for value in context.values()
            if isinstance(
                value,
                (
                    str,
                    int,
                    float,
                ),
            )
        )

        observed = 0
        contradicted = 0
        unknown = 0

        for condition in strategy.conditions:

            condition_text = (
                condition.description
                .lower()
            )

            condition.observed = False
            condition.contradicted = False
            condition.unknown = True

              # --------------------------------------------------------
            # Direct regime matching
            # --------------------------------------------------------

            if (
                condition.category.upper()
                == "REGIME"
            ):

                if current_regime:

                    if any(
                        current_regime.lower()
                        in str(
                            allowed
                        ).lower()
                        for allowed
                        in strategy.applicable_regimes
                    ):

                        condition.observed = True
                        condition.unknown = False

                    elif any(
                        current_regime.lower()
                        in str(
                            blocked
                        ).lower()
                        for blocked
                        in strategy.incompatible_regimes
                    ):

                        condition.contradicted = True
                        condition.unknown = False

            # --------------------------------------------------------
            # Direction
            # --------------------------------------------------------

            elif (
                condition.category.upper()
                in {
                    "DIRECTION",
                    "TREND",
                }
            ):

                if current_direction:

                    if (
                        current_direction.lower()
                        in condition_text
                    ):

                        condition.observed = True
                        condition.unknown = False

            # --------------------------------------------------------
            # Volatility
            # --------------------------------------------------------

            elif (
                condition.category.upper()
                == "VOLATILITY"
            ):

                if current_volatility:

                    if (
                        current_volatility.lower()
                        in condition_text
                    ):

                        condition.observed = True
                        condition.unknown = False

            # --------------------------------------------------------
            # Generic textual evidence
            # --------------------------------------------------------

            if condition.unknown:

                if condition_text in context_text:

                    condition.observed = True
                    condition.unknown = False

            if condition.observed:

                observed += 1

                condition.confidence = 0.60
                condition.uncertainty = 0.40

            elif condition.contradicted:

                contradicted += 1

                condition.confidence = 0.20
                condition.uncertainty = 0.80

            else:

                unknown += 1

                condition.confidence = 0.0
                condition.uncertainty = 1.0

        assessment.conditions_total = (
            len(strategy.conditions)
        )

        assessment.conditions_observed = observed
        assessment.conditions_contradicted = (
            contradicted
        )
        assessment.conditions_unknown = unknown

        # ------------------------------------------------------------
        # Add context evidence
        # ------------------------------------------------------------

        if current_regime:

            regime_supported = (
                current_regime.lower()
                in {
                    str(x).lower()
                    for x in strategy.applicable_regimes
                }
            )

            regime_contradicted = (
                current_regime.lower()
                in {
                    str(x).lower()
                    for x in strategy.incompatible_regimes
                }
            )

            if regime_supported:

                self.add_evidence(
                    strategy_id,
                    "MARKET_REGIME",
                    (
                        f"Current observed regime is "
                        f"'{current_regime}', which is listed "
                        f"as an applicable regime."
                    ),
                    supports=True,
                    strength=self._clamp(
                        regime.get(
                            "confidence",
                            0.5,
                        )
                    ),
                    uncertainty=self._clamp(
                        regime.get(
                            "uncertainty",
                            0.5,
                        )
                    ),
                    source="market_regime",
                )

            elif regime_contradicted:

                self.add_evidence(
                    strategy_id,
                    "MARKET_REGIME",
                    (
                        f"Current observed regime is "
                        f"'{current_regime}', which is listed "
                        f"as incompatible with this strategy."
                    ),
                    supports=False,
                    strength=0.7,
                    uncertainty=self._clamp(
                        regime.get(
                            "uncertainty",
                            0.5,
                        )
                    ),
                    source="market_regime",
                )

        if current_direction:

            self.add_evidence(
                strategy_id,
                "MARKET_STATE",
                (
                    f"Current observed directional context: "
                    f"{current_direction}."
                ),
                supports=True,
                strength=self._clamp(
                    state.get(
                        "confidence",
                        0.5,
                    )
                ),
                uncertainty=self._clamp(
                    state.get(
                        "uncertainty",
                        0.5,
                    )
                ),
                source="market_state",
            )

        if current_volatility:

            self.add_evidence(
                strategy_id,
                "VOLATILITY",
                (
                    f"Current observed volatility context: "
                    f"{current_volatility}."
                ),
                supports=True,
                strength=self._clamp(
                    state.get(
                        "confidence",
                        0.5,
                    )
                ),
                uncertainty=self._clamp(
                    state.get(
                        "uncertainty",
                        0.5,
                    )
                ),
                source="market_state",
            )

        # ------------------------------------------------------------
        # Historical context
        # ------------------------------------------------------------

        if history:

            comparable_count = history.get(
                "comparable_condition_count",
                history.get(
                    "comparison_count",
                    0,
                ),
            )

            if comparable_count:

                self.add_evidence(
                    strategy_id,
                    "HISTORICAL",
                    (
                        f"Historical intelligence supplied "
                        f"{comparable_count} comparable observations."
                    ),
                    supports=True,
                    strength=0.5,
                    uncertainty=0.6,
                    source="historical_intelligence",
                )

        # ------------------------------------------------------------
        # Wisdom context
        # ------------------------------------------------------------

        if wisdom:

            wisdom_items = wisdom.get(
                "wisdom",
                wisdom.get(
                    "active_wisdom",
                    [],
                ),
            )

            if isinstance(
                wisdom_items,
                list,
            ):

                for item in wisdom_items[:20]:

                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    statement = item.get(
                        "lesson"
                    )

                    if not statement:
                        continue

                    self.add_evidence(
                        strategy_id,
                        "MARKET_WISDOM",
                        str(statement),
                        supports=(
                            item.get(
                                "state"
                            )
                            not in {
                                "CONTESTED",
                                "INVALIDATED",
                            }
                        ),
                        strength=self._clamp(
                            item.get(
                                "confidence",
                                0.5,
                            )
                        ),
                        uncertainty=self._clamp(
                            item.get(
                                "uncertainty",
                                0.5,
                            )
                        ),
                        source=(
                            "market_wisdom"
                        ),
                    )

        self._recalculate(
            strategy_id
        )

        self.last_context = {
            "strategy_id": strategy_id,
            "assessed_at": utc_now(),
            "context_keys": list(
                context.keys()
            ),
        }

        return self.assessments[
            strategy_id
        ]

    # ================================================================
    # Recalculation
    # ================================================================

    def _recalculate(
        self,
        strategy_id: str,
    ) -> None:

        strategy = self.strategies.get(
            strategy_id
        )

        assessment = self.assessments.get(
            strategy_id
        )

        if (
            strategy is None
            or assessment is None
        ):
            return

        evidence = self.evidence.get(
            strategy_id,
            [],
        )

        supporting = [
            x
            for x in evidence
            if x.supports
        ]

        opposing = [
            x
            for x in evidence
            if not x.supports
        ]

        assessment.supporting_evidence_count = (
            len(supporting)
        )

        assessment.opposing_evidence_count = (
            len(opposing)
        )

        assessment.conditions_total = (
            len(strategy.conditions)
        )

        assessment.conditions_observed = sum(
            1
            for x in strategy.conditions
            if x.observed
        )

        assessment.conditions_contradicted = sum(
            1
            for x in strategy.conditions
            if x.contradicted
        )

        assessment.conditions_unknown = sum(
            1
            for x in strategy.conditions
            if x.unknown
        )

        if not evidence:

            assessment.confidence = 0.0
            assessment.uncertainty = 1.0
            assessment.state = (
                "INSUFFICIENT_INFORMATION"
            )

            assessment.updated_at = utc_now()

            return

        support_strength = sum(
            x.strength
            for x in supporting
        )

        opposition_strength = sum(
            x.strength
            for x in opposing
        )

        total_strength = (
            support_strength
            + opposition_strength
        )

        if total_strength > 0:

            evidence_balance = (
                support_strength
                / total_strength
            )

        else:

            evidence_balance = 0.0

        condition_total = max(
            len(strategy.conditions),
            1,
        )

        condition_coverage = (
            assessment.conditions_observed
            / condition_total
        )

        condition_penalty = (
            assessment.conditions_contradicted
            / condition_total
        )

        average_evidence_uncertainty = (
            sum(
                x.uncertainty
                for x in evidence
            )
            / len(evidence)
        )

        evidence_quantity_factor = min(
            len(evidence),
            20,
        ) / 20.0

        confidence = (
            evidence_balance * 0.40
            + condition_coverage * 0.30
            + evidence_quantity_factor * 0.15
            + (
                (1.0 - condition_penalty)
                * 0.15
            )
        )

        confidence *= (
            1.0
            - (
                0.50
                * average_evidence_uncertainty
            )
        )

        assessment.confidence = round(
            self._clamp(
                confidence
            ),
            4,
        )

        assessment.uncertainty = round(
            self._clamp(
                average_evidence_uncertainty
                + (
                    assessment.conditions_unknown
                    / condition_total
                ) * 0.30
            ),
            4,
        )

        # ------------------------------------------------------------
        # State classification
        # ------------------------------------------------------------

        if (
            assessment.conditions_contradicted
            > 0
            and (
                assessment.conditions_contradicted
                >= assessment.conditions_observed
            )
        ):

            assessment.state = "CONTESTED"

        elif (
            assessment.conditions_unknown
            == assessment.conditions_total
        ):

            assessment.state = (
                "INSUFFICIENT_INFORMATION"
            )

        elif assessment.confidence < 0.30:

            assessment.state = "PROVISIONAL"

        elif (
            assessment.confidence >= 0.65
            and assessment.conditions_unknown == 0
        ):

            assessment.state = (
                "CONDITIONALLY_SUPPORTED"
            )

        else:

            assessment.state = "PROVISIONAL"

        assessment.updated_at = utc_now()

    # ================================================================
    # Historical validation
    # ================================================================

    def record_historical_result(
        self,
        strategy_id: str,
        supported: bool,
        description: str,
        strength: float = 0.5,
        uncertainty: float = 0.5,
    ) -> Optional[StrategyAssessment]:

        assessment = self.assessments.get(
            strategy_id
        )

        if assessment is None:
            return None

        if supported:

            assessment.historical_support += 1

        else:

            assessment.historical_counterexamples += 1

        self.add_evidence(
            strategy_id=strategy_id,
            evidence_type="HISTORICAL",
            statement=str(
                description
            ),
            supports=supported,
            strength=strength,
            uncertainty=uncertainty,
            source="historical_validation",
        )

        return assessment

    # ================================================================
    # Backtest registration
    # ================================================================

    def record_backtest(
        self,
        strategy_id: str,
        description: str,
        supports_strategy: bool,
        evidence_strength: float = 0.5,
        uncertainty: float = 0.5,
    ) -> Optional[StrategyAssessment]:

        assessment = self.assessments.get(
            strategy_id
        )

        if assessment is None:
            return None

        assessment.backtest_count += 1

        self.add_evidence(
            strategy_id=strategy_id,
            evidence_type="BACKTEST",
            statement=str(
                description
            ),
            supports=supports_strategy,
            strength=evidence_strength,
            uncertainty=uncertainty,
            source="backtesting_engine",
        )

        return assessment

    # ================================================================
    # Stress-test registration
    # ================================================================

    def record_stress_test(
        self,
        strategy_id: str,
        description: str,
        supports_strategy: bool,
        evidence_strength: float = 0.5,
        uncertainty: float = 0.5,
    ) -> Optional[StrategyAssessment]:

        assessment = self.assessments.get(
            strategy_id
        )

        if assessment is None:
            return None

        assessment.stress_test_count += 1

        self.add_evidence(
            strategy_id=strategy_id,
            evidence_type="STRESS_TEST",
            statement=str(
                description
            ),
            supports=supports_strategy,
            strength=evidence_strength,
            uncertainty=uncertainty,
            source="strategy_stress_tester",
        )

        return assessment

    # ================================================================
    # Strategy lifecycle
    # ================================================================

    def set_state(
        self,
        strategy_id: str,
        state: str,
    ) -> Optional[StrategyAssessment]:

        assessment = self.assessments.get(
            strategy_id
        )

        if assessment is None:
            return None

        assessment.state = (
            self._normalize_state(
                state
            )
        )

        assessment.updated_at = utc_now()

        return assessment

    # ================================================================
    # Strategy retrieval
    # ================================================================

    def get_strategy(
        self,
        strategy_id: str,
    ) -> Optional[Dict[str, Any]]:

        strategy = self.strategies.get(
            strategy_id
        )

        assessment = self.assessments.get(
            strategy_id
        )

        if (
            strategy is None
            or assessment is None
        ):
            return None

        return {
            "definition": strategy.to_dict(),
            "assessment": assessment.to_dict(),
            "evidence": [
                x.to_dict()
                for x in self.evidence.get(
                    strategy_id,
                    [],
                )
            ],
        }

    def list_strategies(
        self,
        state: Optional[str] = None,
        strategy_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        results = []

        normalized_state = (
            self._normalize_state(
                state
            )
            if state
            else None
        )

        normalized_type = (
            self._normalize_type(
                strategy_type
            )
            if strategy_type
            else None
        )

        for strategy_id, definition in (
            self.strategies.items()
        ):

            assessment = self.assessments[
                strategy_id
            ]

            if (
                normalized_state is not None
                and assessment.state
                != normalized_state
            ):
                continue

            if (
                normalized_type is not None
                and definition.strategy_type
                != normalized_type
            ):
                continue

            results.append(
                {
                    "definition": (
                        definition.to_dict()
                    ),
                    "assessment": (
                        assessment.to_dict()
                    ),
                }
            )

        return results

    # ================================================================
    # Find context-compatible strategies
    # ================================================================

    def find_compatible_strategies(
        self,
        context: Dict[str, Any],
        include_provisional: bool = True,
    ) -> List[Dict[str, Any]]:

        if not isinstance(
            context,
            dict,
        ):
            raise TypeError(
                "context must be a dictionary."
            )

        results = []

        for strategy_id in self.strategies:

            assessment = self.assess_context(
                strategy_id,
                context,
            )

            if assessment is None:
                continue

            if assessment.state in {
                "RETIRED",
                "INVALIDATED",
            }:
                continue

            if (
                not include_provisional
                and assessment.state
                in {
                    "PROVISIONAL",
                    "INSUFFICIENT_INFORMATION",
                }
            ):
                continue

            # Compatibility is a descriptive score of the current
            # condition match. It is NOT a probability of success.
            total_conditions = max(
                assessment.conditions_total,
                1,
            )

            observed_ratio = (
                assessment.conditions_observed
                / total_conditions
            )

            contradiction_ratio = (
                assessment.conditions_contradicted
                / total_conditions
            )

            compatibility = (
                observed_ratio
                - contradiction_ratio
            )

            compatibility = self._clamp(
                (
                    compatibility
                    + 1.0
                ) / 2.0
            )

            result = assessment.to_dict()

            result[
                "current_condition_compatibility"
            ] = round(
                compatibility,
                4,
            )

            result[
                "compatibility_interpretation"
            ] = (
                "Describes observed condition alignment "
                "only. It is not a forecast or probability "
                "of strategy success."
            )

            results.append(
                result
            )

        results.sort(
            key=lambda x: (
                x[
                    "current_condition_compatibility"
                ],
                x["confidence"],
                -x["uncertainty"],
            ),
            reverse=True,
        )

        return results

    # ================================================================
    # Failure conditions
    # ================================================================

    def add_failure_condition(
        self,
        strategy_id: str,
        description: str,
    ) -> bool:

        strategy = self.strategies.get(
            strategy_id
        )

        assessment = self.assessments.get(
            strategy_id
        )

        if (
            strategy is None
            or assessment is None
        ):
            return False

        description = str(
            description
        ).strip()

        if not description:
            return False

        if description not in (
            strategy.failure_conditions
        ):
            strategy.failure_conditions.append(
                description
            )

        if description not in (
            assessment.failure_conditions
        ):
            assessment.failure_conditions.append(
                description
            )

        strategy.updated_at = utc_now()
        assessment.updated_at = utc_now()

        return True

    # ================================================================
    # Context integration
    # ================================================================

    def analyze_into_context(
        self,
        context: Dict[str, Any],
        context_key: str = "strategy_intelligence",
    ) -> Dict[str, Any]:

        if not isinstance(
            context,
            dict,
        ):
            raise TypeError(
                "context must be a dictionary."
            )

        compatible = (
            self.find_compatible_strategies(
                context
            )
        )

        result = {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "analyzed_at": utc_now(),
            "strategy_count": len(
                self.strategies
            ),
            "compatible_strategies": compatible,
            "active_strategies": [
                self.assessments[
                    strategy_id
                ].to_dict()
                for strategy_id in self.strategies
                if self.assessments[
                    strategy_id
                ].state
                in {
                    "ACTIVE",
                    "SUPPORTED",
                    "CONDITIONALLY_SUPPORTED",
                }
            ],
            "contested_strategies": [
                self.assessments[
                    strategy_id
                ].to_dict()
                for strategy_id in self.strategies
                if self.assessments[
                    strategy_id
                ].state
                == "CONTESTED"
            ],
            "principles": [
                "strategy_is_conditional",
                "condition_alignment_is_not_prediction",
                "historical_support_is_not_guarantee",
                "backtest_results_are_evidence_not_certainty",
                "stress_testing_is_separate",
                "risk_intelligence_is_separate",
                "execution_is_separate",
                "missing_information_must_remain_visible",
                "contradictory_evidence_must_remain_visible",
                "no_buy_sell_generation",
            ],
        }

        context[
            context_key
        ] = result

        self.last_context = result

        return result

    # ================================================================
    # Maintenance
    # ================================================================

    def remove_strategy(
        self,
        strategy_id: str,
    ) -> bool:

        if strategy_id not in self.strategies:
            return False

        self.strategies.pop(
            strategy_id,
            None,
        )

        self.assessments.pop(
            strategy_id,
            None,
        )

        self.evidence.pop(
            strategy_id,
            None,
        )

        return True

    def clear(self) -> None:

        self.strategies.clear()
        self.assessments.clear()
        self.evidence.clear()
        self.last_context = {}

    def _enforce_limits(self) -> None:

        if (
            len(self.strategies)
            <= self.max_strategies
        ):
            return

        removable = [
            assessment
            for assessment
            in self.assessments.values()
            if assessment.state
            in {
                "RETIRED",
                "INVALIDATED",
            }
        ]

        removable.sort(
            key=lambda x: x.updated_at
        )

        remove_count = (
            len(self.strategies)
            - self.max_strategies
        )

        for assessment in removable[
            :remove_count
        ]:

            self.remove_strategy(
                assessment.strategy_id
            )

    # ================================================================
    # Assessment
    # ================================================================

    def assess(self) -> Dict[str, Any]:

        for strategy_id in self.strategies:

            self._recalculate(
                strategy_id
            )

        assessments = list(
            self.assessments.values()
        )

        confidence_values = [
            x.confidence
            for x in assessments
        ]

        uncertainty_values = [
            x.uncertainty
            for x in assessments
        ]

        return {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "assessed_at": utc_now(),
            "strategy_count": len(
                assessments
            ),
            "supported_count": sum(
                1
                for x in assessments
                if x.state
                in {
                    "SUPPORTED",
                    "CONDITIONALLY_SUPPORTED",
                }
            ),
            "provisional_count": sum(
                1
                for x in assessments
                if x.state
                == "PROVISIONAL"
            ),
            "contested_count": sum(
                1
                for x in assessments
                if x.state
                == "CONTESTED"
            ),
            "insufficient_information_count": sum(
                1
                for x in assessments
                if x.state
                == "INSUFFICIENT_INFORMATION"
            ),
            "retired_count": sum(
                1
                for x in assessments
                if x.state
                == "RETIRED"
            ),
            "invalidated_count": sum(
                1
                for x in assessments
                if x.state
                == "INVALIDATED"
            ),
            "average_confidence": round(
                (
                    sum(confidence_values)
                    / len(confidence_values)
                    if confidence_values
                    else 0.0
                ),
                4,
            ),
            "average_uncertainty": round(
                (
                    sum(uncertainty_values)
                    / len(uncertainty_values)
                    if uncertainty_values
                    else 1.0
                ),
                4,
            ),
            "principles": [
                "strategy_intelligence_is_not_trade_execution",
                "strategy_compatibility_is_not_success_probability",
                "evidence_quality_controls_confidence",
                "counterexamples_are_preserved",
                "failure_conditions_are_first_class",
                "historical_data_does_not_guarantee_future_results",
            ],
        }

    def status(self) -> Dict[str, Any]:

        return {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "status": "READY",
            "strategy_count": len(
                self.strategies
            ),
            "evidence_count": sum(
                len(items)
                for items in self.evidence.values()
            ),
            "condition_count": sum(
                len(
                    strategy.conditions
                )
                for strategy
                in self.strategies.values()
            ),
            "last_context_available": bool(
                self.last_context
            ),
            "checked_at": utc_now(),
        }


__all__ = [
    "StrategyEvidence",
    "StrategyCondition",
    "StrategyAssessment",
    "StrategyDefinition",
    "StrategyIntelligence",
    "STRATEGY_STATES",
    "STRATEGY_TYPES",
      ]
