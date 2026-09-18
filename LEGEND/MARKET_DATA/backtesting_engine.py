"""
VALE LEGEND — Stage 16
Backtesting Engine

Purpose
-------
Evaluate explicitly supplied historical market observations against an
explicitly supplied strategy definition.

This engine is an evidence-generation component, NOT a trading executor
and NOT a live BUY/SELL signal generator.

Design principles
-----------------
- Never fabricate market data or results.
- Never fetch external data.
- Never assume profitability.
- Backtest results are evidence, not proof.
- Preserve the exact methodology and configuration used.
- Make costs, slippage, position sizing, and assumptions explicit.
- Detect insufficient data and potentially dangerous methodology.
- Avoid look-ahead bias by evaluating signals using information available
  at the evaluation timestamp.
- Preserve individual trade/episode records so aggregate metrics remain
  auditable.
- Track performance by market regime where regime information is supplied.
- Surface limitations and overfitting risks.
- A strategy that performs well historically is not automatically valid
  for future markets.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from statistics import mean, median, pstdev
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence
from uuid import uuid4


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        result = float(value)
        return result if isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _mean(values: Sequence[float]) -> Optional[float]:
    return mean(values) if values else None


def _median(values: Sequence[float]) -> Optional[float]:
    return median(values) if values else None


def _stdev(values: Sequence[float]) -> Optional[float]:
    if len(values) < 2:
        return None
    return pstdev(values)


def _percentile(values: Sequence[float], percentile: float) -> Optional[float]:
    if not values:
        return None

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    p = _clamp(percentile)
    position = (len(ordered) - 1) * p
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)

    if lower == upper:
        return ordered[lower]

    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BacktestStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    FAILED = "FAILED"


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class EpisodeStatus(str, Enum):
    OPENED = "OPENED"
    CLOSED = "CLOSED"
    INVALID = "INVALID"


class EvidenceQuality(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class BiasFlag(str, Enum):
    LOOKAHEAD_RISK = "LOOKAHEAD_RISK"
    DATA_LEAKAGE_RISK = "DATA_LEAKAGE_RISK"
    SURVIVORSHIP_BIAS_RISK = "SURVIVORSHIP_BIAS_RISK"
    SELECTION_BIAS_RISK = "SELECTION_BIAS_RISK"
    OVERFITTING_RISK = "OVERFITTING_RISK"
    COST_ASSUMPTION_RISK = "COST_ASSUMPTION_RISK"
    SAMPLE_SIZE_RISK = "SAMPLE_SIZE_RISK"
    REGIME_COVERAGE_RISK = "REGIME_COVERAGE_RISK"


# ---------------------------------------------------------------------------
# Historical observation
# ---------------------------------------------------------------------------

@dataclass
class HistoricalObservation:
    """
    Normalized observation consumed by the backtest.

    `features` contains strategy-specific information calculated from data
    that was available at this observation timestamp.

    `regime` is optional and should originate from LEGEND's regime engine
    or another evidence-backed source.
    """

    timestamp: str
    price: float

    instrument: Optional[str] = None
    open_price: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None

    regime: Optional[str] = None
    market_state: Dict[str, Any] = field(default_factory=dict)
    market_dna: Dict[str, Any] = field(default_factory=dict)

    features: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    source_type: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Backtest configuration
# ---------------------------------------------------------------------------

@dataclass
class BacktestConfig:
    """
    Explicit methodology and assumptions for a backtest.

    Costs and slippage default to zero only because the engine cannot
    invent them. A zero-cost result is therefore explicitly labeled as
    an assumption rather than treated as realistic execution.
    """

    initial_capital: float = 100000.0

    commission_rate: float = 0.0
    slippage_rate: float = 0.0

    position_fraction: float = 1.0

    allow_long: bool = True
    allow_short: bool = True

    max_holding_periods: Optional[int] = None

    minimum_observations: int = 30
    minimum_closed_episodes: int = 10

    require_cost_assumptions: bool = False

    execution_delay_periods: int = 1

    prevent_lookahead: bool = True

    record_equity_curve: bool = True
    record_observations: bool = True

    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Strategy signal
# ---------------------------------------------------------------------------

@dataclass
class StrategySignal:
    """
    A strategy decision at one historical timestamp.

    This is NOT a live trading recommendation.

    `reasoning` should contain the strategy's observable rationale.
    """

    action: str
    direction: Optional[str] = None

    strength: Optional[float] = None

    reasoning: List[str] = field(default_factory=list)

    evidence: List[Dict[str, Any]] = field(default_factory=list)

    timestamp: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


StrategyFunction = Callable[
    [HistoricalObservation, Sequence[HistoricalObservation]],
    Optional[StrategySignal],
]


# ---------------------------------------------------------------------------
# Episode / trade record
# ---------------------------------------------------------------------------

@dataclass
class BacktestEpisode:
    episode_id: str

    direction: str

    entry_timestamp: str
    entry_price: float

    quantity: float

    exit_timestamp: Optional[str] = None
    exit_price: Optional[float] = None

    gross_pnl: Optional[float] = None
    total_cost: float = 0.0
    net_pnl: Optional[float] = None

    return_pct: Optional[float] = None

    holding_periods: int = 0

    entry_regime: Optional[str] = None
    exit_regime: Optional[str] = None

    status: str = EpisodeStatus.OPENED.value

    entry_reasoning: List[str] = field(default_factory=list)
    entry_evidence: List[Dict[str, Any]] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class BacktestMetrics:
    observation_count: int = 0
    closed_episode_count: int = 0
    winning_episode_count: int = 0
    losing_episode_count: int = 0
    flat_episode_count: int = 0

    initial_capital: float = 0.0
    final_equity: Optional[float] = None

    gross_profit: float = 0.0
    gross_loss: float = 0.0

    net_pnl: Optional[float] = None
    total_costs: float = 0.0

    total_return_pct: Optional[float] = None

    win_rate: Optional[float] = None
    loss_rate: Optional[float] = None

    average_trade_return_pct: Optional[float] = None
    median_trade_return_pct: Optional[float] = None

    average_win: Optional[float] = None
    average_loss: Optional[float] = None

    profit_factor: Optional[float] = None

    maximum_drawdown_pct: Optional[float] = None
    maximum_drawdown_amount: Optional[float] = None

    best_trade: Optional[float] = None
    worst_trade: Optional[float] = None

    return_stddev: Optional[float] = None

    return_p25: Optional[float] = None
    return_p50: Optional[float] = None
    return_p75: Optional[float] = None

    longest_winning_streak: int = 0
    longest_losing_streak: int = 0

    average_holding_periods: Optional[float] = None
    median_holding_periods: Optional[float] = None

    exposure_fraction: Optional[float] = None


# ---------------------------------------------------------------------------
# Regime metrics
# ---------------------------------------------------------------------------

@dataclass
class RegimePerformance:
    regime: str

    observations: int = 0
    closed_episodes: int = 0

    wins: int = 0
    losses: int = 0

    net_pnl: float = 0.0

    average_return_pct: Optional[float] = None
    win_rate: Optional[float] = None

    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Backtest result
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    backtest_id: str

    strategy_id: str
    strategy_name: str

    status: str

    started_at: str
    completed_at: Optional[str] = None

    data_start: Optional[str] = None
    data_end: Optional[str] = None

    metrics: BacktestMetrics = field(
        default_factory=BacktestMetrics
    )

    regime_performance: Dict[str, RegimePerformance] = field(
        default_factory=dict
    )

    episodes: List[BacktestEpisode] = field(default_factory=list)

    equity_curve: List[Dict[str, Any]] = field(default_factory=list)

    bias_flags: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    methodology: Dict[str, Any] = field(default_factory=dict)

    evidence_quality: str = EvidenceQuality.INSUFFICIENT.value

    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Backtesting Engine
# ---------------------------------------------------------------------------

class BacktestingEngine:
    """
    Evidence-generation engine for historical strategy testing.

    The engine does not:
        - download data,
        - invent prices,
        - create historical results,
        - execute live trades,
        - produce live BUY/SELL recommendations.

    The caller supplies:
        1. historical observations,
        2. a strategy function,
        3. explicit configuration.

    The engine then records what actually happened under the supplied
    assumptions.
    """

    VERSION = "0.1.0"
    ARCHITECTURE_STAGE = "LEGEND_STAGE_16_BACKTESTING"

    SHARED_CONTEXT_KEY = "legend_context"

    def __init__(
        self,
        max_backtests: int = 100,
        max_episodes_per_backtest: int = 10000,
    ) -> None:
        self.max_backtests = max(1, int(max_backtests))
        self.max_episodes_per_backtest = max(
            100,
            int(max_episodes_per_backtest),
        )

        self.results: Dict[str, BacktestResult] = {}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_config(
        self,
        config: BacktestConfig,
    ) -> List[str]:
        errors: List[str] = []

        if config.initial_capital <= 0:
            errors.append(
                "initial_capital must be greater than zero."
            )

        if not 0 <= config.commission_rate:
            errors.append(
                "commission_rate cannot be negative."
            )

        if not 0 <= config.slippage_rate:
            errors.append(
                "slippage_rate cannot be negative."
            )

        if not 0 < config.position_fraction <= 1:
            errors.append(
                "position_fraction must be greater than zero and "
                "less than or equal to one."
            )

        if config.execution_delay_periods < 0:
            errors.append(
                "execution_delay_periods cannot be negative."
            )

        if config.minimum_observations < 1:
            errors.append(
                "minimum_observations must be at least one."
            )

        if config.minimum_closed_episodes < 0:
            errors.append(
                "minimum_closed_episodes cannot be negative."
            )

        if (
            config.max_holding_periods is not None
            and config.max_holding_periods < 1
        ):
            errors.append(
                "max_holding_periods must be positive when supplied."
            )

        if not config.allow_long and not config.allow_short:
            errors.append(
                "At least one trading direction must be enabled."
            )

        return errors

    def validate_observations(
        self,
        observations: Sequence[HistoricalObservation],
    ) -> List[str]:
        errors: List[str] = []

        if not observations:
            errors.append("No historical observations were supplied.")
            return errors

        previous_timestamp: Optional[str] = None

        for index, observation in enumerate(observations):
            if not observation.timestamp:
                errors.append(
                    f"Observation {index} has no timestamp."
                )

            price = _safe_float(observation.price)

            if price is None or price <= 0:
                errors.append(
                    f"Observation {index} has an invalid price."
                )

            if (
                previous_timestamp is not None
                and observation.timestamp < previous_timestamp
            ):
                errors.append(
                    "Historical observations are not sorted "
                    "chronologically."
                )

            previous_timestamp = observation.timestamp

        return errors

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def normalize_observations(
        self,
        observations: Iterable[
            HistoricalObservation
        ],
    ) -> List[HistoricalObservation]:
        """
        Normalize supplied observations without inventing missing values.
        """

        normalized = list(observations)

        normalized.sort(
            key=lambda item: item.timestamp
        )

        return normalized

    # ------------------------------------------------------------------
    # Signal validation
    # ------------------------------------------------------------------

    def validate_signal(
        self,
        signal: Optional[StrategySignal],
        config: BacktestConfig,
    ) -> Optional[StrategySignal]:
        if signal is None:
            return None

        action = str(signal.action or "").strip().upper()

        if action in {
            "",
            "NONE",
            "HOLD",
            "WAIT",
            "EXIT",
        }:
            signal.action = action or "NONE"
            return signal

        direction = str(
            signal.direction or ""
        ).strip().upper()

        if direction == Direction.LONG.value:
            if not config.allow_long:
                return None

        elif direction == Direction.SHORT.value:
            if not config.allow_short:
                return None

        else:
            return None

        signal.action = action
        signal.direction = direction

        return signal

    # ------------------------------------------------------------------
    # Execution price
    # ------------------------------------------------------------------

    def apply_slippage(
        self,
        price: float,
        direction: str,
        is_entry: bool,
        config: BacktestConfig,
    ) -> float:
        """
        Apply explicitly configured slippage.

        Long:
            entry is slightly worse,
            exit is slightly worse.

        Short:
            entry and exit are handled symmetrically through direction.
        """

        slippage = max(
            0.0,
            float(config.slippage_rate),
        )

        if slippage == 0:
            return price

        if direction == Direction.LONG.value:
            if is_entry:
                return price * (1.0 + slippage)

            return price * (1.0 - slippage)

        if direction == Direction.SHORT.value:
            if is_entry:
                return price * (1.0 - slippage)

            return price * (1.0 + slippage)

        return price

    # ------------------------------------------------------------------
    # Cost calculation
    # ------------------------------------------------------------------

    def calculate_cost(
        self,
        price: float,
        quantity: float,
        config: BacktestConfig,
    ) -> float:
        notional = abs(price * quantity)

        return notional * max(
            0.0,
            float(config.commission_rate),
        )

    # ------------------------------------------------------------------
    # Episode opening
    # ------------------------------------------------------------------

    def open_episode(
        self,
        signal: StrategySignal,
        observation: HistoricalObservation,
        capital: float,
        config: BacktestConfig,
    ) -> Optional[BacktestEpisode]:
        if signal.direction not in {
            Direction.LONG.value,
            Direction.SHORT.value,
        }:
            return None

        raw_price = _safe_float(observation.price)

        if raw_price is None or raw_price <= 0:
            return None

        entry_price = self.apply_slippage(
            raw_price,
            signal.direction,
            True,
            config,
        )

        capital_allocated = (
            capital * config.position_fraction
        )

        if capital_allocated <= 0:
            return None

        quantity = capital_allocated / entry_price

        if quantity <= 0:
            return None

        entry_cost = self.calculate_cost(
            entry_price,
            quantity,
            config,
        )

        return BacktestEpisode(
            episode_id=f"episode_{uuid4().hex[:12]}",
            direction=signal.direction,
            entry_timestamp=observation.timestamp,
            entry_price=entry_price,
            quantity=quantity,
            total_cost=entry_cost,
            entry_regime=observation.regime,
            entry_reasoning=list(signal.reasoning),
            entry_evidence=list(signal.evidence),
            metadata={
                "strategy_signal_action": signal.action,
                "signal_strength": signal.strength,
                "execution_delay_periods": (
                    config.execution_delay_periods
                ),
            },
        )

    # ------------------------------------------------------------------
    # Episode closing
    # ------------------------------------------------------------------

    def close_episode(
        self,
        episode: BacktestEpisode,
        observation: HistoricalObservation,
        config: BacktestConfig,
    ) -> BacktestEpisode:
        raw_price = _safe_float(observation.price)

        if raw_price is None or raw_price <= 0:
            episode.status = EpisodeStatus.INVALID.value
            return episode

        exit_price = self.apply_slippage(
            raw_price,
            episode.direction,
            False,
            config,
        )

        quantity = episode.quantity

        if episode.direction == Direction.LONG.value:
            gross_pnl = (
                exit_price - episode.entry_price
            ) * quantity

        else:
            gross_pnl = (
                episode.entry_price - exit_price
            ) * quantity

        exit_cost = self.calculate_cost(
            exit_price,
            quantity,
            config,
        )

        total_cost = (
            episode.total_cost + exit_cost
        )

        net_pnl = gross_pnl - total_cost

        entry_value = (
            episode.entry_price * quantity
        )

        return_pct = (
            net_pnl / entry_value
        ) * 100 if entry_value else None

        episode.exit_timestamp = observation.timestamp
        episode.exit_price = exit_price
        episode.gross_pnl = gross_pnl
        episode.total_cost = total_cost
        episode.net_pnl = net_pnl
        episode.return_pct = return_pct

        episode.exit_regime = observation.regime

        episode.status = EpisodeStatus.CLOSED.value

        return episode

    # ------------------------------------------------------------------
    # Main backtest
    # ------------------------------------------------------------------

    def run(
        self,
        strategy_id: str,
        strategy_name: str,
        observations: Iterable[
            HistoricalObservation
        ],
        strategy: StrategyFunction,
        config: Optional[BacktestConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BacktestResult:
        config = config or BacktestConfig()

        backtest_id = (
            f"backtest_{uuid4().hex[:12]}"
        )

        started_at = utc_now()

        result = BacktestResult(
            backtest_id=backtest_id,
            strategy_id=str(strategy_id),
            strategy_name=str(strategy_name),
            status=BacktestStatus.CREATED.value,
            started_at=started_at,
            methodology=self.methodology(config),
            metadata=metadata or {},
        )

        self._store_result(result)

        config_errors = self.validate_config(config)

        if config_errors:
            result.status = (
                BacktestStatus.INVALID_CONFIGURATION.value
            )
            result.warnings.extend(config_errors)
            result.completed_at = utc_now()
            return result

        normalized = self.normalize_observations(
            observations
        )

        observation_errors = self.validate_observations(
            normalized
        )

        if observation_errors:
            result.status = (
                BacktestStatus.INVALID_CONFIGURATION.value
            )
            result.warnings.extend(observation_errors)
            result.completed_at = utc_now()
            return result

        if len(normalized) < config.minimum_observations:
            result.status = (
                BacktestStatus.INSUFFICIENT_DATA.value
            )

            result.warnings.append(
                "Historical sample is smaller than the configured "
                "minimum observation requirement."
            )

            result.limitations.append(
                "No performance conclusion should be drawn from "
                "an insufficient historical sample."
            )

            result.data_start = normalized[0].timestamp
            result.data_end = normalized[-1].timestamp
            result.metrics.observation_count = len(normalized)
            result.metrics.initial_capital = (
                config.initial_capital
            )
            result.completed_at = utc_now()

            self._update_evidence_quality(result)
            return result

        result.status = BacktestStatus.RUNNING.value

        result.data_start = normalized[0].timestamp
        result.data_end = normalized[-1].timestamp

        result.metrics.observation_count = len(normalized)
        result.metrics.initial_capital = (
            config.initial_capital
        )

        self._add_methodology_warnings(
            result,
            config,
            normalized,
        )

        capital = float(config.initial_capital)

        active_episode: Optional[BacktestEpisode] = None

        equity_peak = capital

        periods_with_exposure = 0

        closed_episodes: List[
            BacktestEpisode
        ] = []

        for index, observation in enumerate(normalized):

            history = normalized[:index]

            try:
                signal = strategy(
                    observation,
                    history,
                )
            except Exception as exc:
                result.status = BacktestStatus.FAILED.value
                result.warnings.append(
                    f"Strategy execution failed at observation "
                    f"{index}: {exc}"
                )
                result.completed_at = utc_now()
                return result

            signal = self.validate_signal(
                signal,
                config,
            )

            # ----------------------------------------------------------
            # Existing position
            # ----------------------------------------------------------

            if active_episode is not None:

                active_episode.holding_periods += 1

                periods_with_exposure += 1

                should_close = False

                action = (
                    str(signal.action).upper()
                    if signal is not None
                    else "NONE"
                )

                if action in {
                    "EXIT",
                    "CLOSE",
                }:
                    should_close = True

                elif (
                    signal is not None
                    and signal.direction
                    and signal.direction
                    != active_episode.direction
                ):
                    should_close = True

                elif (
                    config.max_holding_periods is not None
                    and active_episode.holding_periods
                    >= config.max_holding_periods
                ):
                    should_close = True

                # A signal cannot retroactively alter the current
                # episode before the observation at which it occurs.
                if should_close:
                    active_episode = self.close_episode(
                        active_episode,
                        observation,
                        config,
                    )

                    if (
                        active_episode.status
                        == EpisodeStatus.CLOSED.value
                    ):
                        closed_episodes.append(
                            active_episode
                        )

                        capital += (
                            active_episode.net_pnl or 0.0
                        )

                        if len(closed_episodes) <= (
                            self.max_episodes_per_backtest
                        ):
                            result.episodes.append(
                                active_episode
                            )

                    active_episode = None

            # ----------------------------------------------------------
            # New position
            # ----------------------------------------------------------

            if active_episode is None and signal is not None:
                action = str(
                    signal.action or ""
                ).upper()

                if action in {
                    "ENTER",
                    "OPEN",
                    "LONG",
                    "SHORT",
                }:
                    active_episode = self.open_episode(
                        signal,
                        observation,
                        capital,
                        config,
                    )

            # ----------------------------------------------------------
            # Equity recording
            # ----------------------------------------------------------

            mark_to_market = capital

            if active_episode is not None:
                periods_with_exposure += 0

                current_price = (
                    _safe_float(observation.price)
                    or active_episode.entry_price
                )

                if (
                    active_episode.direction
                    == Direction.LONG.value
                ):
                    unrealized = (
                        current_price
                        - active_episode.entry_price
                    ) * active_episode.quantity

                else:
                    unrealized = (
                        active_episode.entry_price
                        - current_price
                    ) * active_episode.quantity

                mark_to_market += unrealized

            equity_peak = max(
                equity_peak,
                mark_to_market,
            )

            drawdown_amount = (
                equity_peak - mark_to_market
            )

            drawdown_pct = (
                drawdown_amount / equity_peak * 100
                if equity_peak
                else 0.0
            )

            if config.record_equity_curve:
                result.equity_curve.append(
                    {
                        "timestamp": observation.timestamp,
                        "equity": mark_to_market,
                        "peak_equity": equity_peak,
                        "drawdown_amount": drawdown_amount,
                        "drawdown_pct": drawdown_pct,
                        "exposed": active_episode is not None,
                    }
                )

        # ------------------------------------------------------------------
        # Close remaining position at final supplied observation.
        # ------------------------------------------------------------------

        if active_episode is not None:
            final_observation = normalized[-1]

            active_episode = self.close_episode(
                active_episode,
                final_observation,
                config,
            )

            if (
                active_episode.status
                == EpisodeStatus.CLOSED.value
            ):
                closed_episodes.append(
                    active_episode
                )

                capital += (
                    active_episode.net_pnl or 0.0
                )

                if len(closed_episodes) <= (
                    self.max_episodes_per_backtest
                ):
                    result.episodes.append(
                        active_episode
                    )

        # ------------------------------------------------------------------
        # Final metrics.
        # ------------------------------------------------------------------

        result.metrics.final_equity = capital

        self._calculate_metrics(
            result,
            closed_episodes,
            capital,
            periods_with_exposure,
            len(normalized),
        )

        self._calculate_regime_performance(
            result,
            normalized,
            closed_episodes,
        )

        self._evaluate_sample_quality(
            result,
            config,
        )

        result.completed_at = utc_now()

        if result.status == BacktestStatus.RUNNING.value:
            result.status = BacktestStatus.COMPLETED.value

        self._update_evidence_quality(result)

        return result

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _calculate_metrics(
        self,
        result: BacktestResult,
        episodes: Sequence[BacktestEpisode],
        final_equity: float,
        exposure_periods: int,
        observation_count: int,
    ) -> None:
        metrics = result.metrics

        metrics.closed_episode_count = len(episodes)

        pnl_values = [
            float(episode.net_pnl or 0.0)
            for episode in episodes
        ]

        return_values = [
            float(episode.return_pct)
            for episode in episodes
            if episode.return_pct is not None
        ]

        wins = [
            value
            for value in pnl_values
            if value > 0
        ]

        losses = [
            value
            for value in pnl_values
            if value < 0
        ]

        flats = [
            value
            for value in pnl_values
            if value == 0
        ]

        metrics.winning_episode_count = len(wins)
        metrics.losing_episode_count = len(losses)
        metrics.flat_episode_count = len(flats)

        metrics.final_equity = final_equity

        metrics.gross_profit = sum(
            max(value, 0.0)
            for value in (
                float(episode.gross_pnl or 0.0)
                for episode in episodes
            )
        )

        metrics.gross_loss = abs(
            sum(
                min(value, 0.0)
                for value in (
                    float(episode.gross_pnl or 0.0)
                    for episode in episodes
                )
            )
        )

        metrics.net_pnl = sum(pnl_values)

        metrics.total_costs = sum(
            float(episode.total_cost or 0.0)
            for episode in episodes
        )

        if metrics.initial_capital:
            metrics.total_return_pct = (
                metrics.net_pnl
                / metrics.initial_capital
            ) * 100

        if episodes:
            metrics.win_rate = (
                len(wins) / len(episodes)
            )

            metrics.loss_rate = (
                len(losses) / len(episodes)
            )

        metrics.average_trade_return_pct = (
            _mean(return_values)
        )

        metrics.median_trade_return_pct = (
            _median(return_values)
        )

        metrics.average_win = (
            _mean(wins)
        )

        metrics.average_loss = (
            _mean(losses)
        )

        if metrics.gross_loss > 0:
            metrics.profit_factor = (
                metrics.gross_profit
                / metrics.gross_loss
            )

        if pnl_values:
            metrics.best_trade = max(
                pnl_values
            )

            metrics.worst_trade = min(
                pnl_values
            )

        metrics.return_stddev = _stdev(
            return_values
        )

        metrics.return_p25 = _percentile(
            return_values,
            0.25,
        )

        metrics.return_p50 = _percentile(
            return_values,
            0.50,
        )

        metrics.return_p75 = _percentile(
            return_values,
            0.75,
        )

        holding_periods = [
            episode.holding_periods
            for episode in episodes
        ]

        metrics.average_holding_periods = (
            _mean(holding_periods)
        )

        metrics.median_holding_periods = (
            _median(holding_periods)
        )

        if observation_count > 0:
            metrics.exposure_fraction = (
                exposure_periods
                / observation_count
            )

        self._calculate_drawdown(
            metrics,
            result.equity_curve,
        )

        (
            metrics.longest_winning_streak,
            metrics.longest_losing_streak,
        ) = self._calculate_streaks(
            pnl_values
        )

    def _calculate_drawdown(
        self,
        metrics: BacktestMetrics,
        equity_curve: Sequence[Dict[str, Any]],
    ) -> None:
        if not equity_curve:
            return

        maximum_amount = 0.0
        maximum_pct = 0.0

        for point in equity_curve:
            drawdown_amount = _safe_float(
                point.get("drawdown_amount")
            ) or 0.0

            drawdown_pct = _safe_float(
                point.get("drawdown_pct")
            ) or 0.0

            maximum_amount = max(
                maximum_amount,
                drawdown_amount,
            )

            maximum_pct = max(
                maximum_pct,
                drawdown_pct,
            )

        metrics.maximum_drawdown_amount = (
            maximum_amount
        )

        metrics.maximum_drawdown_pct = (
            maximum_pct
        )

    def _calculate_streaks(
        self,
        pnl_values: Sequence[float],
    ) -> tuple[int, int]:
        best_win = 0
        best_loss = 0

        current_win = 0
        current_loss = 0

        for pnl in pnl_values:
            if pnl > 0:
                current_win += 1
                current_loss = 0

            elif pnl < 0:
                current_loss += 1
                current_win = 0

            else:
                current_win = 0
                current_loss = 0

            best_win = max(
                best_win,
                current_win,
            )

            best_loss = max(
                best_loss,
                current_loss,
            )

        return best_win, best_loss

    # ------------------------------------------------------------------
    # Regime analysis
    # ------------------------------------------------------------------

    def _calculate_regime_performance(
        self,
        result: BacktestResult,
        observations: Sequence[HistoricalObservation],
        episodes: Sequence[BacktestEpisode],
    ) -> None:
        regimes: Dict[str, RegimePerformance] = {}

        for observation in observations:
            regime = (
                observation.regime
                or "UNKNOWN"
            )

            if regime not in regimes:
                regimes[regime] = (
                    RegimePerformance(
                        regime=regime
                    )
                )

            regimes[regime].observations += 1

        for episode in episodes:
            regime = (
                episode.entry_regime
                or "UNKNOWN"
            )

            if regime not in regimes:
                regimes[regime] = (
                    RegimePerformance(
                        regime=regime
                    )
                )

            performance = regimes[regime]

            performance.closed_episodes += 1

            pnl = float(
                episode.net_pnl or 0.0
            )

            performance.net_pnl += pnl

            if pnl > 0:
                performance.wins += 1

            elif pnl < 0:
                performance.losses += 1

        for performance in regimes.values():
            returns = [
                episode.return_pct
                for episode in episodes
                if (
                    (episode.entry_regime or "UNKNOWN")
                    == performance.regime
                    and episode.return_pct is not None
                )
            ]

            performance.average_return_pct = (
                _mean(
                    [
                        float(value)
                        for value in returns
                    ]
                )
            )

            if performance.closed_episodes:
                performance.win_rate = (
                    performance.wins
                    / performance.closed_episodes
                )

        result.regime_performance = regimes

        known_regimes = {
            key
            for key in regimes
            if key != "UNKNOWN"
        }

        if len(known_regimes) <= 1:
            result.bias_flags.append(
                BiasFlag.REGIME_COVERAGE_RISK.value
            )

            result.limitations.append(
                "Historical regime diversity is limited or "
                "regime labels are unavailable."
            )

    # ------------------------------------------------------------------
    # Methodology / bias assessment
    # ------------------------------------------------------------------

    def methodology(
        self,
        config: BacktestConfig,
    ) -> Dict[str, Any]:
        return {
            "engine_version": self.VERSION,
            "architecture_stage": self.ARCHITECTURE_STAGE,
            "initial_capital": config.initial_capital,
            "commission_rate": config.commission_rate,
            "slippage_rate": config.slippage_rate,
            "position_fraction": config.position_fraction,
            "allow_long": config.allow_long,
            "allow_short": config.allow_short,
            "max_holding_periods": (
                config.max_holding_periods
            ),
            "minimum_observations": (
                config.minimum_observations
            ),
            "minimum_closed_episodes": (
                config.minimum_closed_episodes
            ),
            "execution_delay_periods": (
                config.execution_delay_periods
            ),
            "prevent_lookahead": (
                config.prevent_lookahead
            ),
            "cost_assumptions_explicit": True,
            "external_data_fetching": False,
            "live_execution": False,
            "generated_market_data": False,
            "generated_performance_results": False,
        }

    def _add_methodology_warnings(
        self,
        result: BacktestResult,
        config: BacktestConfig,
        observations: Sequence[HistoricalObservation],
    ) -> None:
        if (
            config.commission_rate == 0
            and config.slippage_rate == 0
        ):
            result.bias_flags.append(
                BiasFlag.COST_ASSUMPTION_RISK.value
            )

            result.warnings.append(
                "Commission and slippage are both zero. "
                "Results may materially differ from real execution."
            )

            result.limitations.append(
                "No execution costs were supplied."
            )

        if config.prevent_lookahead:
            result.metadata[
                "lookahead_protection"
            ] = (
                "Strategy receives only observations at or before "
                "the current evaluation index."
            )

        if config.execution_delay_periods == 0:
            result.warnings.append(
                "Execution delay is zero. The supplied strategy "
                "methodology must justify same-observation execution."
            )

        if len(observations) < 100:
            result.bias_flags.append(
                BiasFlag.SAMPLE_SIZE_RISK.value
            )

            result.warnings.append(
                "The historical observation count is relatively small "
                "for broad generalization."
            )

    def _evaluate_sample_quality(
        self,
        result: BacktestResult,
        config: BacktestConfig,
    ) -> None:
        count = result.metrics.closed_episode_count

        if count < config.minimum_closed_episodes:
            result.bias_flags.append(
                BiasFlag.SAMPLE_SIZE_RISK.value
            )

            result.warnings.append(
                "Closed-episode count is below the configured "
                "minimum required for stronger evidence."
            )

            result.limitations.append(
                "Trade-level sample size is insufficient for "
                "strong statistical inference."
            )

        if count > 0:
            result.metadata[
                "episode_sample_sufficient"
            ] = (
                count >= config.minimum_closed_episodes
            )
        else:
            result.metadata[
                "episode_sample_sufficient"
            ] = False

    # ------------------------------------------------------------------
    # Evidence quality
    # ------------------------------------------------------------------

    def _update_evidence_quality(
        self,
        result: BacktestResult,
    ) -> None:
        observations = (
            result.metrics.observation_count
        )

        episodes = (
            result.metrics.closed_episode_count
        )

        if observations == 0:
            result.evidence_quality = (
                EvidenceQuality.INSUFFICIENT.value
            )
            return

        if (
            observations < 30
            or episodes < 10
        ):
            result.evidence_quality = (
                EvidenceQuality.INSUFFICIENT.value
            )
            return

        if (
            observations < 100
            or episodes < 30
        ):
            result.evidence_quality = (
                EvidenceQuality.LOW.value
            )
            return

        if (
            len(result.bias_flags) >= 3
            or result.metrics.maximum_drawdown_pct is None
        ):
            result.evidence_quality = (
                EvidenceQuality.MODERATE.value
            )
            return

        result.evidence_quality = (
            EvidenceQuality.HIGH.value
        )

    # ------------------------------------------------------------------
    # Overfitting assessment
    # ------------------------------------------------------------------

    def assess_overfitting_risk(
        self,
        result: BacktestResult,
        strategy_complexity: Optional[int] = None,
        parameter_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Provides a methodological warning, not a statistical proof of
        overfitting.

        Complexity information must be supplied by the caller because
        the engine cannot infer the true research process.
        """

        warnings: List[str] = []

        episodes = (
            result.metrics.closed_episode_count
        )

        if strategy_complexity is not None:
            if strategy_complexity >= 10:
                warnings.append(
                    "Strategy complexity is high relative to a simple "
                    "historical test."
                )

        if parameter_count is not None:
            if parameter_count >= 10:
                warnings.append(
                    "Parameter count is high and may increase "
                    "selection/overfitting risk."
                )

        if episodes < 30:
            warnings.append(
                "The number of closed episodes is small relative "
                "to the possibility of parameter selection."
            )

        if len(result.regime_performance) <= 1:
            warnings.append(
                "The test contains limited regime diversity."
            )

        if (
            result.metrics.total_return_pct is not None
            and result.metrics.maximum_drawdown_pct is not None
            and result.metrics.maximum_drawdown_pct > 50
        ):
            warnings.append(
                "Large historical drawdown reduces the usefulness "
                "of a return-only interpretation."
            )

        risk = (
            "HIGH"
            if len(warnings) >= 3
            else "MODERATE"
            if warnings
            else "UNASSESSED"
        )

        if warnings:
            result.bias_flags.append(
                BiasFlag.OVERFITTING_RISK.value
            )

        assessment = {
            "risk_level": risk,
            "warnings": warnings,
            "strategy_complexity": strategy_complexity,
            "parameter_count": parameter_count,
            "closed_episode_count": episodes,
            "note": (
                "This is a methodological risk assessment, "
                "not proof that overfitting occurred."
            ),
        }

        result.metadata[
            "overfitting_assessment"
        ] = assessment

        self._update_evidence_quality(result)

        return assessment

    # ------------------------------------------------------------------
    # Train/test split helper
    # ------------------------------------------------------------------

    def chronological_split(
        self,
        observations: Sequence[HistoricalObservation],
        train_fraction: float = 0.7,
    ) -> Dict[str, List[HistoricalObservation]]:
        """
        Chronological split.

        No random shuffling is performed because temporal ordering is
        fundamental to historical market testing.
        """

        if not observations:
            return {
                "train": [],
                "test": [],
            }

        fraction = max(
            0.01,
            min(
                0.99,
                float(train_fraction),
            ),
        )

        ordered = self.normalize_observations(
            observations
        )

        split_index = int(
            len(ordered) * fraction
        )

        split_index = max(
            1,
            min(
                len(ordered) - 1,
                split_index,
            ),
        )

        return {
            "train": ordered[:split_index],
            "test": ordered[split_index:],
        }

    # ------------------------------------------------------------------
    # Walk-forward windows
    # ------------------------------------------------------------------

    def walk_forward_windows(
        self,
        observations: Sequence[HistoricalObservation],
        train_size: int,
        test_size: int,
        step: Optional[int] = None,
    ) -> List[Dict[str, List[HistoricalObservation]]]:
        """
        Create chronological walk-forward windows.

        This method only constructs windows. It does not automatically
        retrain or alter the strategy.
        """

        ordered = self.normalize_observations(
            observations
        )

        train_size = max(
            1,
            int(train_size),
        )

        test_size = max(
            1,
            int(test_size),
        )

        step = (
            test_size
            if step is None
            else max(1, int(step))
        )

        windows: List[
            Dict[str, List[HistoricalObservation]]
        ] = []

        start = 0

        while (
            start + train_size + test_size
            <= len(ordered)
        ):
            train_end = (
                start + train_size
            )

            test_end = (
                train_end + test_size
            )

            windows.append(
                {
                    "train": ordered[
                        start:train_end
                    ],
                    "test": ordered[
                        train_end:test_end
                    ],
                }
            )

            start += step

        return windows

    # ------------------------------------------------------------------
    # Compare results
    # ------------------------------------------------------------------

    def compare_results(
        self,
        backtest_ids: Sequence[str],
    ) -> Dict[str, Any]:
        comparisons: List[Dict[str, Any]] = []

        for backtest_id in backtest_ids:
            result = self.results.get(
                backtest_id
            )

            if result is None:
                continue

            comparisons.append(
                {
                    "backtest_id": result.backtest_id,
                    "strategy_id": result.strategy_id,
                    "strategy_name": result.strategy_name,
                    "status": result.status,
                    "evidence_quality": (
                        result.evidence_quality
                    ),
                    "net_pnl": (
                        result.metrics.net_pnl
                    ),
                    "return_pct": (
                        result.metrics.total_return_pct
                    ),
                    "win_rate": (
                        result.metrics.win_rate
                    ),
                    "maximum_drawdown_pct": (
                        result.metrics.maximum_drawdown_pct
                    ),
                    "closed_episode_count": (
                        result.metrics.closed_episode_count
                    ),
                    "profit_factor": (
                        result.metrics.profit_factor
                    ),
                    "bias_flags": list(
                        result.bias_flags
                    ),
                }
            )

        return {
            "count": len(comparisons),
            "results": comparisons,
            "note": (
                "This comparison reports measured backtest "
                "characteristics. It does not select a winning "
                "strategy or guarantee future performance."
            ),
        }

    # ------------------------------------------------------------------
    # Context integration
    # ------------------------------------------------------------------

    def integrate_into_context(
        self,
        result: BacktestResult,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Write auditable backtest evidence into LEGEND shared context.
        """

        context.setdefault(
            self.SHARED_CONTEXT_KEY,
            {},
        )

        legend_context = context[
            self.SHARED_CONTEXT_KEY
        ]

        legend_context.setdefault(
            "backtesting",
            {},
        )

        backtesting = legend_context[
            "backtesting"
        ]

        backtesting[
            result.backtest_id
        ] = {
            "strategy_id": result.strategy_id,
            "strategy_name": result.strategy_name,
            "status": result.status,
            "evidence_quality": (
                result.evidence_quality
            ),
            "data_start": result.data_start,
            "data_end": result.data_end,
            "metrics": asdict(
                result.metrics
            ),
            "regime_performance": {
                key: asdict(value)
                for key, value
                in result.regime_performance.items()
            },
            "bias_flags": list(
                result.bias_flags
            ),
            "warnings": list(
                result.warnings
            ),
            "limitations": list(
                result.limitations
            ),
            "methodology": dict(
                result.methodology
            ),
            "updated_at": utc_now(),
        }

        return context

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_result(
        self,
        backtest_id: str,
    ) -> Optional[BacktestResult]:
        return self.results.get(
            str(backtest_id)
        )

    def list_results(self) -> List[BacktestResult]:
        return list(
            self.results.values()
        )

    def _store_result(
        self,
        result: BacktestResult,
    ) -> None:
        self.results[
            result.backtest_id
        ] = result

        while len(self.results) > self.max_backtests:
            oldest_id = next(
                iter(self.results)
            )

            self.results.pop(
                oldest_id,
                None,
            )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "engine": (
                "LEGEND Backtesting Engine"
            ),
            "version": self.VERSION,
            "architecture_stage": (
                self.ARCHITECTURE_STAGE
            ),
            "stored_backtests": len(
                self.results
            ),
            "external_data_fetching": False,
            "live_execution": False,
            "generated_market_data": False,
            "generated_results": False,
            "lookahead_protection": True,
            "regime_analysis": True,
            "cost_tracking": True,
            "drawdown_tracking": True,
            "overfitting_assessment": True,
            "walk_forward_support": True,
            "updated_at": utc_now(),
        }


__all__ = [
    "BacktestStatus",
    "Direction",
    "EpisodeStatus",
    "EvidenceQuality",
    "BiasFlag",
    "HistoricalObservation",
    "BacktestConfig",
    "StrategySignal",
    "BacktestEpisode",
    "BacktestMetrics",
    "RegimePerformance",
    "BacktestResult",
    "BacktestingEngine",
          ]
