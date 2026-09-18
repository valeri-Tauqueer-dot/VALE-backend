"""
LEGEND Stage 14 — Trading Wisdom Library
========================================

Organizes, versions, retrieves, compares, validates, and retires reusable
market/trading wisdom produced by the Market Wisdom Engine.

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
    Market Wisdom Engine
        ↓
    Trading Wisdom Library

Important distinction:

    Market Wisdom Engine
        = creates and evaluates individual wisdom.

    Trading Wisdom Library
        = stores, organizes, versions, retrieves, compares, and manages
          the lifecycle of reusable wisdom.

This module is a knowledge-management layer.

It does NOT:
    - fetch market data
    - invent evidence
    - generate BUY/SELL signals
    - guarantee outcomes
    - turn historical patterns into certainty
    - automatically learn from every outcome
    - assume participant intent
    - override risk or safety systems
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


LIBRARY_STATES = {
    "DRAFT",
    "PROVISIONAL",
    "ACTIVE",
    "CONTESTED",
    "WEAKENED",
    "RETIRED",
    "INVALIDATED",
}


WISDOM_CATEGORIES = {
    "REGIME",
    "STRUCTURE",
    "TREND",
    "MOMENTUM",
    "VOLATILITY",
    "VOLUME",
    "PARTICIPANT",
    "LIQUIDITY",
    "HISTORICAL",
    "FAILURE_MODE",
    "DATA_QUALITY",
    "MARKET_BEHAVIOR",
    "RISK_CONTEXT",
    "TRANSITION",
    "OTHER",
}


@dataclass
class WisdomVersion:
    """
    Immutable-style snapshot of a wisdom item at a point in its lifecycle.
    """

    version: int
    wisdom_id: str
    title: str
    lesson: str
    conditions: List[str] = field(default_factory=list)

    confidence: float = 0.0
    uncertainty: float = 1.0

    state: str = "DRAFT"

    supporting_evidence_count: int = 0
    opposing_evidence_count: int = 0

    change_reason: str = ""
    created_at: str = field(default_factory=utc_now)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LibraryEntry:
    """
    A managed wisdom entry inside the Trading Wisdom Library.
    """

    wisdom_id: str
    title: str
    lesson: str

    category: str = "OTHER"
    state: str = "DRAFT"

    conditions: List[str] = field(default_factory=list)
    applicable_regimes: List[str] = field(default_factory=list)
    applicable_market_states: List[str] = field(default_factory=list)

    limitations: List[str] = field(default_factory=list)

    confidence: float = 0.0
    uncertainty: float = 1.0

    validation_count: int = 0
    supporting_observations: int = 0
    opposing_observations: int = 0

    outcome_count: int = 0
    supported_outcomes: int = 0
    unsupported_outcomes: int = 0

    version: int = 1

    tags: List[str] = field(default_factory=list)

    source_wisdom_id: Optional[str] = None

    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TradingWisdomLibrary:
    """
    LEGEND's reusable wisdom management system.

    The library treats wisdom as versioned knowledge rather than static truth.

    A wisdom item can therefore move through states such as:

        DRAFT
          ↓
        PROVISIONAL
          ↓
        ACTIVE
          ↓
        CONTESTED / WEAKENED
          ↓
        RETIRED / INVALIDATED

    Importantly, retirement does not erase historical knowledge.
    Previous versions remain available for audit and reasoning replay.
    """

    VERSION = "0.1.0"
    COMPONENT = "LEGEND_TRADING_WISDOM_LIBRARY"

    def __init__(
        self,
        max_entries: int = 2000,
        max_versions_per_entry: int = 100,
    ) -> None:

        self.max_entries = max(1, int(max_entries))
        self.max_versions_per_entry = max(
            1,
            int(max_versions_per_entry),
        )

        self.entries: Dict[str, LibraryEntry] = {}

        self.versions: Dict[
            str,
            List[WisdomVersion]
        ] = {}

        self.related_wisdom: Dict[
            str,
            List[str]
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
        except (TypeError, ValueError):
            return low

        return max(
            low,
            min(high, number),
        )

    @staticmethod
    def _normalize_category(
        category: str,
    ) -> str:

        value = str(
            category or "OTHER"
        ).strip().upper()

        if value not in WISDOM_CATEGORIES:
            return "OTHER"

        return value

    @staticmethod
    def _normalize_state(
        state: str,
    ) -> str:

        value = str(
            state or "DRAFT"
        ).strip().upper()

        if value not in LIBRARY_STATES:
            return "DRAFT"

        return value

    # ================================================================
    # Register wisdom
    # ================================================================

    def register_wisdom(
        self,
        wisdom_id: str,
        title: str,
        lesson: str,
        category: str = "OTHER",
        conditions: Optional[Iterable[str]] = None,
        applicable_regimes: Optional[Iterable[str]] = None,
        applicable_market_states: Optional[
            Iterable[str]
        ] = None,
        limitations: Optional[Iterable[str]] = None,
        confidence: float = 0.0,
        uncertainty: float = 1.0,
        state: str = "DRAFT",
        tags: Optional[Iterable[str]] = None,
        source_wisdom_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LibraryEntry:

        wisdom_id = str(
            wisdom_id
        ).strip()

        if not wisdom_id:
            raise ValueError(
                "wisdom_id cannot be empty."
            )

        if not str(title).strip():
            raise ValueError(
                "title cannot be empty."
            )

        if not str(lesson).strip():
            raise ValueError(
                "lesson cannot be empty."
            )

        if wisdom_id in self.entries:
            raise ValueError(
                f"Wisdom '{wisdom_id}' already exists."
            )

        entry = LibraryEntry(
            wisdom_id=wisdom_id,
            title=str(title).strip(),
            lesson=str(lesson).strip(),
            category=self._normalize_category(
                category
            ),
            state=self._normalize_state(
                state
            ),
            conditions=list(
                conditions or []
            ),
            applicable_regimes=list(
                applicable_regimes or []
            ),
            applicable_market_states=list(
                applicable_market_states or []
            ),
            limitations=list(
                limitations or []
            ),
            confidence=self._clamp(
                confidence
            ),
            uncertainty=self._clamp(
                uncertainty
            ),
            tags=list(
                tags or []
            ),
            source_wisdom_id=source_wisdom_id,
            metadata=dict(
                metadata or {}
            ),
        )

        if not entry.limitations:
            entry.limitations = [
                "Context dependent.",
                "Not a guarantee of future behavior.",
                "Historical evidence may contain counterexamples.",
                "Confidence must change when evidence changes.",
            ]

        self.entries[wisdom_id] = entry

        self.versions[wisdom_id] = []

        self._snapshot(
            wisdom_id=wisdom_id,
            change_reason="initial_registration",
        )

        self._enforce_limits()

        return entry

    # ================================================================
    # Import Market Wisdom Engine output
    # ================================================================

    def import_wisdom(
        self,
        wisdom: Dict[str, Any],
        category: str = "OTHER",
        tags: Optional[Iterable[str]] = None,
    ) -> LibraryEntry:

        if not isinstance(wisdom, dict):
            raise TypeError(
                "wisdom must be a dictionary."
            )

        wisdom_id = wisdom.get(
            "wisdom_id"
        )

        if not wisdom_id:
            raise ValueError(
                "Imported wisdom requires wisdom_id."
            )

        if wisdom_id in self.entries:
            return self.update_wisdom(
                wisdom_id=wisdom_id,
                title=wisdom.get(
                    "title",
                    self.entries[wisdom_id].title,
                ),
                lesson=wisdom.get(
                    "lesson",
                    self.entries[wisdom_id].lesson,
                ),
                confidence=wisdom.get(
                    "confidence",
                    self.entries[wisdom_id].confidence,
                ),
                uncertainty=wisdom.get(
                    "uncertainty",
                    self.entries[wisdom_id].uncertainty,
                ),
                change_reason="wisdom_engine_refresh",
            )

        return self.register_wisdom(
            wisdom_id=wisdom_id,
            title=wisdom.get(
                "title",
                "Unnamed wisdom",
            ),
            lesson=wisdom.get(
                "lesson",
                "",
            ),
            category=category,
            conditions=wisdom.get(
                "conditions",
                [],
            ),
            applicable_regimes=wisdom.get(
                "applicable_regimes",
                [],
            ),
            applicable_market_states=wisdom.get(
                "applicable_market_states",
                [],
            ),
            limitations=wisdom.get(
                "limitations",
                [],
            ),
            confidence=wisdom.get(
                "confidence",
                0.0,
            ),
            uncertainty=wisdom.get(
                "uncertainty",
                1.0,
            ),
            state=wisdom.get(
                "state",
                "PROVISIONAL",
            ),
            tags=tags,
            source_wisdom_id=wisdom_id,
            metadata={
                "imported_from": (
                    "market_wisdom_engine"
                ),
            },
        )

    # ================================================================
    # Versioning
    # ================================================================

    def _snapshot(
        self,
        wisdom_id: str,
        change_reason: str,
    ) -> WisdomVersion:

        entry = self.entries.get(
            wisdom_id
        )

        if entry is None:
            raise KeyError(
                f"Wisdom '{wisdom_id}' does not exist."
            )

        history = self.versions.setdefault(
            wisdom_id,
            [],
        )

        version_number = len(history) + 1

        snapshot = WisdomVersion(
            version=version_number,
            wisdom_id=entry.wisdom_id,
            title=entry.title,
            lesson=entry.lesson,
            conditions=list(
                entry.conditions
            ),
            confidence=entry.confidence,
            uncertainty=entry.uncertainty,
            state=entry.state,
            supporting_evidence_count=(
                entry.supporting_observations
            ),
            opposing_evidence_count=(
                entry.opposing_observations
            ),
            change_reason=change_reason,
        )

        history.append(snapshot)

        if len(history) > self.max_versions_per_entry:
            self.versions[wisdom_id] = (
                history[
                    -self.max_versions_per_entry:
                ]
            )

        return snapshot

    def get_versions(
        self,
        wisdom_id: str,
    ) -> List[Dict[str, Any]]:

        return [
            version.to_dict()
            for version in self.versions.get(
                wisdom_id,
                [],
            )
        ]

    # ================================================================
    # Update
    # ================================================================

    def update_wisdom(
        self,
        wisdom_id: str,
        title: Optional[str] = None,
        lesson: Optional[str] = None,
        conditions: Optional[
            Iterable[str]
        ] = None,
        category: Optional[str] = None,
        applicable_regimes: Optional[
            Iterable[str]
        ] = None,
        applicable_market_states: Optional[
            Iterable[str]
        ] = None,
        limitations: Optional[
            Iterable[str]
        ] = None,
        confidence: Optional[float] = None,
        uncertainty: Optional[float] = None,
        state: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
        change_reason: str = "manual_update",
    ) -> LibraryEntry:

        entry = self.entries.get(
            wisdom_id
        )

        if entry is None:
            raise KeyError(
                f"Wisdom '{wisdom_id}' does not exist."
            )

        if title is not None:
            entry.title = str(
                title
            ).strip()

        if lesson is not None:
            entry.lesson = str(
                lesson
            ).strip()

        if conditions is not None:
            entry.conditions = list(
                conditions
            )

        if category is not None:
            entry.category = (
                self._normalize_category(
                    category
                )
            )

        if applicable_regimes is not None:
            entry.applicable_regimes = list(
                applicable_regimes
            )

        if applicable_market_states is not None:
            entry.applicable_market_states = list(
                applicable_market_states
            )

        if limitations is not None:
            entry.limitations = list(
                limitations
            )

        if confidence is not None:
            entry.confidence = self._clamp(
                confidence
            )

        if uncertainty is not None:
            entry.uncertainty = self._clamp(
                uncertainty
            )

        if state is not None:
            entry.state = self._normalize_state(
                state
            )

        if tags is not None:
            entry.tags = list(
                tags
            )

        entry.version += 1
        entry.updated_at = utc_now()

        self._snapshot(
            wisdom_id=wisdom_id,
            change_reason=change_reason,
        )

        return entry

    # ================================================================
    # Validation
    # ================================================================

    def validate(
        self,
        wisdom_id: str,
        supported: bool,
        evidence_strength: float = 0.5,
        uncertainty: float = 0.5,
        reason: str = "",
    ) -> Optional[LibraryEntry]:

        entry = self.entries.get(
            wisdom_id
        )

        if entry is None:
            return None

        entry.validation_count += 1

        evidence_strength = self._clamp(
            evidence_strength
        )

        uncertainty = self._clamp(
            uncertainty
        )

        if supported:
            entry.supporting_observations += 1
        else:
            entry.opposing_observations += 1

        # Evidence affects confidence but cannot eliminate uncertainty.
        support_total = (
            entry.supporting_observations
            + entry.opposing_observations
        )

        if support_total > 0:

            balance = (
                entry.supporting_observations
                / support_total
            )

            evidence_factor = (
                min(
                    entry.validation_count,
                    20,
                )
                / 20.0
            )

            new_confidence = (
                balance * 0.55
                + evidence_strength * 0.30
                + evidence_factor * 0.15
            )

            new_confidence *= (
                1.0 - (0.5 * uncertainty)
            )

            entry.confidence = round(
                self._clamp(
                    new_confidence
                ),
                4,
            )

            entry.uncertainty = round(
                (
                    entry.uncertainty
                    + uncertainty
                ) / 2.0,
                4,
            )

        if (
            entry.opposing_observations
            > entry.supporting_observations
        ):
            entry.state = "CONTESTED"

        elif (
            entry.validation_count >= 3
            and entry.confidence >= 0.60
        ):
            entry.state = "ACTIVE"

        elif entry.validation_count > 0:
            entry.state = "PROVISIONAL"

        entry.updated_at = utc_now()

        self._snapshot(
            wisdom_id=wisdom_id,
            change_reason=(
                reason
                or (
                    "supported_validation"
                    if supported
                    else "counterexample_validation"
                )
            ),
        )

        return entry

    # ================================================================
    # Outcome recording
    # ================================================================

    def record_outcome(
        self,
        wisdom_id: str,
        supported: bool,
        outcome_description: str,
        uncertainty: float = 0.5,
    ) -> Optional[LibraryEntry]:

        entry = self.entries.get(
            wisdom_id
        )

        if entry is None:
            return None

        entry.outcome_count += 1

        if supported:
            entry.supported_outcomes += 1
        else:
            entry.unsupported_outcomes += 1

        # Outcome feedback is evidence, not automatic truth.
        self.validate(
            wisdom_id=wisdom_id,
            supported=supported,
            evidence_strength=0.5,
            uncertainty=uncertainty,
            reason=(
                "outcome_feedback:"
                + str(outcome_description)
            ),
        )

        return entry

    # ================================================================
    # Lifecycle management
    # ================================================================

    def activate(
        self,
        wisdom_id: str,
        reason: str = "activated",
    ) -> Optional[LibraryEntry]:

        entry = self.entries.get(
            wisdom_id
        )

        if entry is None:
            return None

        entry.state = "ACTIVE"
        entry.updated_at = utc_now()

        self._snapshot(
            wisdom_id,
            reason,
        )

        return entry

    def contest(
        self,
        wisdom_id: str,
        reason: str = "conflicting_evidence",
    ) -> Optional[LibraryEntry]:

        entry = self.entries.get(
            wisdom_id
        )

        if entry is None:
            return None

        entry.state = "CONTESTED"
        entry.updated_at = utc_now()

        self._snapshot(
            wisdom_id,
            reason,
        )

        return entry

    def weaken(
        self,
        wisdom_id: str,
        reason: str = "evidence_weakened",
    ) -> Optional[LibraryEntry]:

        entry = self.entries.get(
            wisdom_id
        )

        if entry is None:
            return None

        entry.state = "WEAKENED"
        entry.updated_at = utc_now()

        self._snapshot(
            wisdom_id,
            reason,
        )

        return entry

    def retire(
        self,
        wisdom_id: str,
        reason: str = "retired",
    ) -> Optional[LibraryEntry]:

        entry = self.entries.get(
            wisdom_id
        )

        if entry is None:
            return None

        entry.state = "RETIRED"
        entry.updated_at = utc_now()

        self._snapshot(
            wisdom_id,
            reason,
        )

        return entry

    def invalidate(
        self,
        wisdom_id: str,
        reason: str = "invalidated",
    ) -> Optional[LibraryEntry]:

        entry = self.entries.get(
            wisdom_id
        )

        if entry is None:
            return None

        entry.state = "INVALIDATED"
        entry.updated_at = utc_now()

        self._snapshot(
            wisdom_id,
            reason,
        )

        return entry

    # ================================================================
    # Relationships
    # ================================================================

    def link_wisdom(
        self,
        wisdom_id: str,
        related_wisdom_id: str,
    ) -> bool:

        if wisdom_id not in self.entries:
            return False

        if related_wisdom_id not in self.entries:
            return False

        if wisdom_id == related_wisdom_id:
            return False

        self.related_wisdom.setdefault(
            wisdom_id,
            [],
        )

        self.related_wisdom.setdefault(
            related_wisdom_id,
            [],
        )

        if related_wisdom_id not in (
            self.related_wisdom[wisdom_id]
        ):
            self.related_wisdom[
                wisdom_id
            ].append(
                related_wisdom_id
            )

        if wisdom_id not in (
            self.related_wisdom[
                related_wisdom_id
            ]
        ):
            self.related_wisdom[
                related_wisdom_id
            ].append(
                wisdom_id
            )

        return True

    def get_related(
        self,
        wisdom_id: str,
    ) -> List[Dict[str, Any]]:

        results = []

        for related_id in self.related_wisdom.get(
            wisdom_id,
            [],
        ):

            entry = self.entries.get(
                related_id
            )

            if entry is not None:
                results.append(
                    entry.to_dict()
                )

        return results

    # ================================================================
    # Retrieval
    # ================================================================

    def get(
        self,
        wisdom_id: str,
    ) -> Optional[Dict[str, Any]]:

        entry = self.entries.get(
            wisdom_id
        )

        if entry is None:
            return None

        result = entry.to_dict()

        result["versions"] = (
            self.get_versions(
                wisdom_id
            )
        )

        result["related_wisdom"] = [
            x["wisdom_id"]
            for x in self.get_related(
                wisdom_id
            )
        ]

        return result

    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        state: Optional[str] = None,
        regime: Optional[str] = None,
        market_state: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:

        results = []

        query_text = (
            str(query).lower().strip()
            if query
            else ""
        )

        category_text = (
            self._normalize_category(
                category
            )
            if category
            else None
        )

        state_text = (
            self._normalize_state(
                state
            )
            if state
            else None
        )

        requested_tags = {
            str(tag).lower().strip()
            for tag in (tags or [])
        }

        for entry in self.entries.values():

            if category_text is not None:
                if entry.category != category_text:
                    continue

            if state_text is not None:
                if entry.state != state_text:
                    continue

            if regime is not None:
                regime_text = str(
                    regime
                ).lower().strip()

                if not any(
                    regime_text
                    == str(x).lower().strip()
                    for x in entry.applicable_regimes
                ):
                    continue

            if market_state is not None:
                market_text = str(
                    market_state
                ).lower().strip()

                if not any(
                    market_text
                    == str(x).lower().strip()
                    for x in entry.applicable_market_states
                ):
                    continue

            if requested_tags:

                entry_tags = {
                    str(tag).lower().strip()
                    for tag in entry.tags
                }

                if not requested_tags.intersection(
                    entry_tags
                ):
                    continue

            if query_text:

                searchable = " ".join(
                    [
                        entry.title,
                        entry.lesson,
                        entry.category,
                        " ".join(
                            entry.conditions
                        ),
                        " ".join(
                            entry.tags
                        ),
                        " ".join(
                            entry.applicable_regimes
                        ),
                        " ".join(
                            entry.applicable_market_states
                        ),
                    ]
                ).lower()

                if query_text not in searchable:
                    continue

            results.append(
                entry.to_dict()
            )

        return results

    # ================================================================
    # Context matching
    # ================================================================

    def find_context_matches(
        self,
        context: Dict[str, Any],
        include_contested: bool = True,
    ) -> List[Dict[str, Any]]:

        if not isinstance(context, dict):
            return []

        regime = str(
            context.get(
                "regime",
                context.get(
                    "market_regime",
                    "",
                ),
            )
        ).lower().strip()

        market_state = str(
            context.get(
                "market_state",
                "",
            )
        ).lower().strip()

        results = []

        for entry in self.entries.values():

            if entry.state in {
                "RETIRED",
                "INVALIDATED",
            }:
                continue

            if (
                not include_contested
                and entry.state == "CONTESTED"
            ):
                continue

            score = 0.0
            matches = []

            if regime:

                for candidate in (
                    entry.applicable_regimes
                ):

                    if (
                        str(candidate).lower().strip()
                        == regime
                    ):
                        score += 0.40
                        matches.append(
                            "regime"
                        )
                        break

            if market_state:

                for candidate in (
                    entry.applicable_market_states
                ):

                    if (
                        str(candidate).lower().strip()
                        == market_state
                    ):
                        score += 0.30
                        matches.append(
                            "market_state"
                        )
                        break

            # Conditions receive a smaller matching weight because
            # conditions may be textual rather than normalized fields.
            context_text = " ".join(
                str(value).lower()
                for value in context.values()
                if isinstance(
                    value,
                    (str, int, float),
                )
            )

            condition_matches = 0

            for condition in entry.conditions:

                if str(
                    condition
                ).lower() in context_text:

                    condition_matches += 1

            if condition_matches:

                score += min(
                    0.30,
                    condition_matches * 0.10,
                )

                matches.append(
                    "conditions"
                )

            if score > 0:

                result = entry.to_dict()

                result["context_match_score"] = round(
                    min(score, 1.0),
                    4,
                )

                result["matched_dimensions"] = (
                    matches
                )

                results.append(
                    result
                )

        results.sort(
            key=lambda x: (
                x["context_match_score"],
                x["confidence"],
                -x["uncertainty"],
            ),
            reverse=True,
        )

        return results

    # ================================================================
    # Comparison
    # ================================================================

    def compare(
        self,
        wisdom_id_a: str,
        wisdom_id_b: str,
    ) -> Dict[str, Any]:

        a = self.entries.get(
            wisdom_id_a
        )

        b = self.entries.get(
            wisdom_id_b
        )

        if a is None or b is None:
            return {
                "success": False,
                "error": "One or both wisdom items do not exist.",
            }

        common_regimes = list(
            set(
                a.applicable_regimes
            ).intersection(
                b.applicable_regimes
            )
        )

        common_market_states = list(
            set(
                a.applicable_market_states
            ).intersection(
                b.applicable_market_states
            )
        )

        common_conditions = list(
            set(
                a.conditions
            ).intersection(
                b.conditions
            )
        )

        confidence_difference = (
            a.confidence
            - b.confidence
        )

        uncertainty_difference = (
            a.uncertainty
            - b.uncertainty
        )

        return {
            "success": True,
            "wisdom_a": a.to_dict(),
            "wisdom_b": b.to_dict(),
            "common_regimes": common_regimes,
            "common_market_states": (
                common_market_states
            ),
            "common_conditions": common_conditions,
            "confidence_difference": round(
                confidence_difference,
                4,
            ),
            "uncertainty_difference": round(
                uncertainty_difference,
                4,
            ),
            "interpretation": (
                "Comparison describes differences in "
                "stored evidence and applicability. "
                "It does not declare one wisdom universally "
                "correct."
            ),
        }

    # ================================================================
    # Context integration
    # ================================================================

    def integrate_context(
        self,
        context: Dict[str, Any],
        context_key: str = "trading_wisdom_library",
    ) -> Dict[str, Any]:

        if not isinstance(context, dict):
            raise TypeError(
                "context must be a dictionary."
            )

        matches = self.find_context_matches(
            context
        )

        result = {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "integrated_at": utc_now(),
            "library_size": len(
                self.entries
            ),
            "context_matches": matches,
            "active_wisdom": [
                entry.to_dict()
                for entry in self.entries.values()
                if entry.state == "ACTIVE"
            ],
            "contested_wisdom": [
                entry.to_dict()
                for entry in self.entries.values()
                if entry.state == "CONTESTED"
            ],
            "principles": [
                "stored_wisdom_is_contextual",
                "historical_patterns_are_not_guarantees",
                "counterexamples_remain_visible",
                "retired_wisdom_remains_auditable",
                "version_history_is_preserved",
                "outcomes_do_not_automatically_create_truth",
                "library_does_not_generate_buy_sell_signals",
            ],
        }

        context[context_key] = result

        self.last_context = result

        return result

    # ================================================================
    # Maintenance
    # ================================================================

    def _enforce_limits(self) -> None:

        if len(self.entries) <= self.max_entries:
            return

        removable = [
            entry
            for entry in self.entries.values()
            if entry.state in {
                "RETIRED",
                "INVALIDATED",
            }
        ]

        removable.sort(
            key=lambda x: x.updated_at
        )

        remove_count = (
            len(self.entries)
            - self.max_entries
        )

        for entry in removable[:remove_count]:

            self.entries.pop(
                entry.wisdom_id,
                None,
            )

            self.versions.pop(
                entry.wisdom_id,
                None,
            )

            self.related_wisdom.pop(
                entry.wisdom_id,
                None,
            )

    def remove(
        self,
        wisdom_id: str,
        preserve_history: bool = True,
    ) -> bool:

        if wisdom_id not in self.entries:
            return False

        self.entries.pop(
            wisdom_id,
            None,
        )

        if not preserve_history:
            self.versions.pop(
                wisdom_id,
                None,
            )

        self.related_wisdom.pop(
            wisdom_id,
            None,
        )

        for related in self.related_wisdom.values():

            while wisdom_id in related:
                related.remove(
                    wisdom_id
                )

        return True

    # ================================================================
    # Assessment / status
    # ================================================================

    def assess(self) -> Dict[str, Any]:

        entries = list(
            self.entries.values()
        )

        confidence_values = [
            x.confidence
            for x in entries
        ]

        uncertainty_values = [
            x.uncertainty
            for x in entries
        ]

        return {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "assessed_at": utc_now(),
            "entry_count": len(entries),
            "active_count": sum(
                1
                for x in entries
                if x.state == "ACTIVE"
            ),
            "provisional_count": sum(
                1
                for x in entries
                if x.state == "PROVISIONAL"
            ),
            "contested_count": sum(
                1
                for x in entries
                if x.state == "CONTESTED"
            ),
            "weakened_count": sum(
                1
                for x in entries
                if x.state == "WEAKENED"
            ),
            "retired_count": sum(
                1
                for x in entries
                if x.state == "RETIRED"
            ),
            "invalidated_count": sum(
                1
                for x in entries
                if x.state == "INVALIDATED"
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
            "version_count": sum(
                len(x)
                for x in self.versions.values()
            ),
        }

    def status(self) -> Dict[str, Any]:

        return {
            "component": self.COMPONENT,
            "version": self.VERSION,
            "status": "READY",
            "entry_count": len(
                self.entries
            ),
            "version_count": sum(
                len(x)
                for x in self.versions.values()
            ),
            "relationship_count": sum(
                len(x)
                for x in self.related_wisdom.values()
            ) // 2,
            "last_context_available": bool(
                self.last_context
            ),
            "checked_at": utc_now(),
        }


__all__ = [
    "WisdomVersion",
    "LibraryEntry",
    "TradingWisdomLibrary",
    "LIBRARY_STATES",
    "WISDOM_CATEGORIES",
  ]
