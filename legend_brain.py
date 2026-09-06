"""
VALE LEGEND Brain
Stage 1: LEGEND Core Cognitive Foundation

LEGEND is VALE's market/trading intelligence brain.

This module intentionally does NOT:
- invent market data
- generate BUY/SELL signals
- pretend to have live market feeds
- fabricate confidence
- automatically learn from outcomes

Stage 1 establishes the internal cognitive contract on top of
VALEBrainInterface. Specialized market engines will be added later.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from vale_connector import VALEConnector
from vale_brain_interface import VALEBrainInterface


def utc_now() -> str:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def clamp_confidence(value: Optional[float]) -> Optional[float]:
    """
    Keep confidence within [0, 1].

    None remains None because absence of evidence is different
    from a low-confidence numerical estimate.
    """
    if value is None:
        return None

    return max(0.0, min(1.0, float(value)))


class LegendBrain(VALEBrainInterface):
    """
    LEGEND — VALE's market and trading intelligence brain.

    Stage 1 provides the cognitive foundation.
    """

    VERSION = "0.1.0"
    ARCHITECTURE_STAGE = "LEGEND_CORE_FOUNDATION"

    def __init__(self, connector: Optional[VALEConnector] = None):
        super().__init__(
            brain_name="LEGEND",
            connector=connector,
        )

        self.identity_profile = {
            "brain": "LEGEND",
            "role": "Market and Trading Intelligence",
            "version": self.VERSION,
            "architecture_stage": self.ARCHITECTURE_STAGE,
            "mission": (
                "Build evidence-based market understanding and trading intelligence "
                "without manufacturing certainty."
            ),
            "not_responsible_for": [
                "system-wide orchestration",
                "system-wide supervision",
                "final VALE synthesis",
                "ultimate capital protection authority",
            ],
        }

    # ------------------------------------------------------------------
    # IDENTITY
    # ------------------------------------------------------------------

    def identity(self) -> Dict[str, Any]:
        """Return LEGEND's machine-readable identity."""
        base = super().identity()

        base.update(
            {
                "legend_version": self.VERSION,
                "architecture_stage": self.ARCHITECTURE_STAGE,
                "role": self.identity_profile["role"],
                "mission": self.identity_profile["mission"],
                "principles": [
                    "evidence_first",
                    "no_invented_market_data",
                    "no_premature_conclusions",
                    "explicit_uncertainty",
                    "contradiction_awareness",
                    "missing_information_detection",
                    "self_criticism",
                ],
            }
        )

        return base

    # ------------------------------------------------------------------
    # CAPABILITIES
    # ------------------------------------------------------------------

    def capabilities(self) -> Dict[str, Any]:
        """
        LEGEND-specific capability registry.

        False means the architecture is planned but the specialized
        implementation has not yet been installed.
        """

        return {
            "legend_core": True,

            # Stage 1 cognitive foundation
            "task_context": True,
            "missing_information_detection": True,
            "hypothesis_management": True,
            "evidence_management": True,
            "uncertainty_tracking": True,
            "contradiction_tracking": True,
            "self_critique": True,
            "decision_quality_framework": True,

            # Planned specialized intelligence
            "market_data_intelligence": False,
            "market_state_engine": False,
            "market_dna": False,
            "market_regime_detection": False,
            "market_regime_memory": False,
            "historical_intelligence": False,
            "participant_behavior": False,
            "market_influence_map": False,
            "market_wisdom": False,
            "trading_wisdom_library": False,
            "strategy_intelligence": False,
            "backtesting": False,
            "strategy_stress_testing": False,
            "scenario_engine": False,
            "risk_intelligence": False,
            "outcome_learning": False,

            # Shared VALE systems
            "mcvl_verification": True,
            "shared_memory": True,
            "shared_knowledge": True,
            "evolution_interface": True,
        }

    # ------------------------------------------------------------------
    # COGNITIVE CONTEXT
    # ------------------------------------------------------------------

    def create_context(
        self,
        state: Any,
        task_type: str = "market_intelligence",
    ) -> Dict[str, Any]:
        """
        Create LEGEND's structured task-local cognitive context.

        This is deliberately kept in shared VALE state so future
        LEGEND modules and other brains can consume the same context.
        """

        existing = self.get_shared(state, "legend_context")

        if isinstance(existing, dict):
            return existing

        context = {
            "context_id": f"legend-{uuid4().hex[:12]}",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "task_type": task_type,
            "status": "INITIALIZING",

            "market": {
                "instrument": None,
                "asset_class": None,
                "exchange": None,
                "timeframe": None,
            },

            "data": {
                "available": [],
                "missing": [],
                "sources": [],
                "freshness": [],
            },

            "observations": [],
            "hypotheses": [],
            "evidence": [],
            "contradictions": [],
            "risks": [],
            "scenarios": [],

            "uncertainty": {
                "state": "UNASSESSED",
                "reasons": [],
            },

            "decision": {
                "status": "NOT_READY",
                "conclusion": None,
            },

            "timeline": [],
        }

        self.set_shared(state, "legend_context", context)

        state.event(
            "legend_context_created",
            "LEGEND",
            payload={
                "context_id": context["context_id"],
                "task_type": task_type,
            },
        )

        return context

    def _touch_context(self, state: Any, context: Dict[str, Any]) -> None:
        context["updated_at"] = utc_now()
        self.set_shared(state, "legend_context", context)

    def _timeline(
        self,
        context: Dict[str, Any],
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        context["timeline"].append(
            {
                "timestamp": utc_now(),
                "event": event_type,
                "details": details or {},
            }
        )

    # ------------------------------------------------------------------
    # MARKET REQUIREMENTS
    # ------------------------------------------------------------------

    def define_market_requirements(
        self,
        state: Any,
        requirements: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Register information required for meaningful market analysis.

        This does not claim that the information exists.
        """

        context = self.create_context(state)

        default_requirements = [
            "instrument",
            "market_data",
            "timeframe",
            "data_timestamp",
        ]

        required = requirements or default_requirements

        context["data"]["required"] = list(dict.fromkeys(required))

        self._timeline(
            context,
            "requirements_defined",
            {"required": context["data"]["required"]},
        )

        self._touch_context(state, context)

        return {
            "success": True,
            "required_information": context["data"]["required"],
        }

    # ------------------------------------------------------------------
    # MISSING INFORMATION
    # ------------------------------------------------------------------

    def detect_missing_information(
        self,
        state: Any,
        available_information: Optional[Dict[str, Any]] = None,
        required_information: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Determine which required inputs are missing.

        Critical missing information prevents LEGEND from claiming
        that a market conclusion is ready.
        """

        context = self.create_context(state)

        available = available_information or {}

        required = required_information or context["data"].get(
            "required",
            [
                "instrument",
                "market_data",
                "timeframe",
                "data_timestamp",
            ],
        )

        missing = []

        for key in required:
            value = available.get(key)

            if value is None:
                missing.append(key)

            elif isinstance(value, str) and not value.strip():
                missing.append(key)

        context["data"]["available"] = [
            key for key in required if key not in missing
        ]

        context["data"]["missing"] = missing

        if missing:
            context["decision"]["status"] = "NOT_READY"
            context["uncertainty"]["state"] = "MATERIAL_MISSING_INFORMATION"

            for item in missing:
                if item not in context["uncertainty"]["reasons"]:
                    context["uncertainty"]["reasons"].append(
                        f"Required information missing: {item}"
                    )

            self._timeline(
                context,
                "missing_information_detected",
                {"missing": missing},
            )

            result = {
                "ready": False,
                "missing": missing,
                "message": (
                    "LEGEND cannot complete a reliable market conclusion "
                    "because required information is missing."
                ),
            }

        else:
            context["uncertainty"]["state"] = "INPUTS_PRESENT"

            self._timeline(
                context,
                "required_information_present",
                {"required_count": len(required)},
            )

            result = {
                "ready": True,
                "missing": [],
                "message": "Required information is present for the current stage.",
            }

        self._touch_context(state, context)

        return result

    # ------------------------------------------------------------------
    # OBSERVATIONS
    # ------------------------------------------------------------------

    def add_observation(
        self,
        state: Any,
        observation: str,
        source: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add an observed fact without converting it into a conclusion."""

        if not observation or not observation.strip():
            return {
                "success": False,
                "error": "Observation cannot be empty.",
            }

        context = self.create_context(state)

        item = {
            "id": f"obs-{uuid4().hex[:12]}",
            "observation": observation.strip(),
            "source": source,
            "timestamp": timestamp or utc_now(),
            "type": "observation",
        }

        context["observations"].append(item)

        self._timeline(
            context,
            "observation_added",
            {"observation_id": item["id"]},
        )

        self._touch_context(state, context)

        return {
            "success": True,
            "observation": item,
        }

    # ------------------------------------------------------------------
    # HYPOTHESES
    # ------------------------------------------------------------------

    def create_hypothesis(
        self,
        state: Any,
        statement: str,
        basis: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a hypothesis.

        A hypothesis is explicitly NOT treated as a verified fact.
        """

        if not statement or not statement.strip():
            return {
                "success": False,
                "error": "Hypothesis statement cannot be empty.",
            }

        context = self.create_context(state)

        hypothesis = {
            "id": f"hyp-{uuid4().hex[:12]}",
            "statement": statement.strip(),
            "basis": basis or [],
            "status": "UNTESTED",
            "confidence": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }

        context["hypotheses"].append(hypothesis)

        self._timeline(
            context,
            "hypothesis_created",
            {"hypothesis_id": hypothesis["id"]},
        )

        self._touch_context(state, context)

        return {
            "success": True,
            "hypothesis": hypothesis,
        }

    # ------------------------------------------------------------------
    # EVIDENCE
    # ------------------------------------------------------------------

    def add_evidence(
        self,
        state: Any,
        claim: str,
        source: str,
        evidence: Any,
        supports: Optional[bool] = None,
        quality: Optional[float] = None,
        relevance: Optional[float] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add evidence with provenance.

        Quality and relevance remain optional until a proper evidence
        evaluation engine is implemented.
        """

        if not claim or not claim.strip():
            return {"success": False, "error": "Claim cannot be empty."}

        if not source or not source.strip():
            return {
                "success": False,
                "error": "Evidence source is required.",
            }

        context = self.create_context(state)

        item = {
            "id": f"evidence-{uuid4().hex[:12]}",
            "claim": claim.strip(),
            "source": source.strip(),
            "evidence": evidence,
            "supports": supports,
            "quality": clamp_confidence(quality),
            "relevance": clamp_confidence(relevance),
            "timestamp": timestamp or utc_now(),
        }

        context["evidence"].append(item)

        self._timeline(
            context,
            "evidence_added",
            {"evidence_id": item["id"]},
        )

        self._touch_context(state, context)

        return {
            "success": True,
            "evidence": item,
        }

    # ------------------------------------------------------------------
    # CONTRADICTIONS
    # ------------------------------------------------------------------

    def add_contradiction(
        self,
        state: Any,
        hypothesis_id: str,
        contradiction: str,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register evidence or reasoning that challenges a hypothesis."""

        context = self.create_context(state)

        item = {
            "id": f"contra-{uuid4().hex[:12]}",
            "hypothesis_id": hypothesis_id,
            "contradiction": contradiction.strip(),
            "source": source,
            "timestamp": utc_now(),
            "resolved": False,
        }

        context["contradictions"].append(item)

        for hypothesis in context["hypotheses"]:
            if hypothesis["id"] == hypothesis_id:
                hypothesis["status"] = "CHALLENGED"
                hypothesis["updated_at"] = utc_now()

        self._timeline(
            context,
            "contradiction_detected",
            {
                "contradiction_id": item["id"],
                "hypothesis_id": hypothesis_id,
            },
        )

        self._touch_context(state, context)

        return {
            "success": True,
            "contradiction": item,
        }

    # ------------------------------------------------------------------
    # CONFIDENCE / UNCERTAINTY
    # ------------------------------------------------------------------

    def assess_confidence(
        self,
        state: Any,
        hypothesis_id: str,
        confidence: Optional[float],
        reasons: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Record an explicitly supplied confidence assessment.

        LEGEND does not manufacture confidence here.
        A future Confidence Engine will calculate it from evidence.
        """

        context = self.create_context(state)

        value = clamp_confidence(confidence)

        for hypothesis in context["hypotheses"]:
            if hypothesis["id"] == hypothesis_id:
                hypothesis["confidence"] = value
                hypothesis["updated_at"] = utc_now()

                if value is None:
                    label = "UNASSESSED"
                elif value >= 0.75:
                    label = "HIGH"
                elif value >= 0.50:
                    label = "MEDIUM"
                else:
                    label = "LOW"

                context["uncertainty"]["state"] = label
                context["uncertainty"]["reasons"].extend(reasons or [])

                self._timeline(
                    context,
                    "confidence_assessed",
                    {
                        "hypothesis_id": hypothesis_id,
                        "confidence": value,
                        "label": label,
                    },
                )

                self._touch_context(state, context)

                return {
                    "success": True,
                    "hypothesis_id": hypothesis_id,
                    "confidence": value,
                    "label": label,
                }

        return {
            "success": False,
            "error": f"Hypothesis '{hypothesis_id}' not found.",
        }

    # ------------------------------------------------------------------
    # SELF CRITIC
    # ------------------------------------------------------------------

    def self_critique(self, state: Any) -> Dict[str, Any]:
        """
        Perform the Stage 1 structural self-critique.

        This is a framework, not a fake AI claim.
        Future LEGEND reasoning engines will provide deeper analysis.
        """

        context = self.create_context(state)

        weaknesses: List[str] = []

        if not context["observations"]:
            weaknesses.append("No explicit observations recorded.")

        if not context["hypotheses"]:
            weaknesses.append("No hypotheses recorded.")

        if not context["evidence"]:
            weaknesses.append("No evidence recorded.")

        if context["data"].get("missing"):
            weaknesses.append(
                "Required information remains missing."
            )

        if context["contradictions"]:
            unresolved = [
                c
                for c in context["contradictions"]
                if not c.get("resolved")
            ]

            if unresolved:
                weaknesses.append(
                    f"{len(unresolved)} contradiction(s) remain unresolved."
                )

        critique = {
            "timestamp": utc_now(),
            "questions": [
                "What could make the current interpretation wrong?",
                "What information was overlooked?",
                "Which assumption is weakest?",
                "Is the evidence sufficient?",
                "Are important contradictions unresolved?",
            ],
            "weaknesses": weaknesses,
            "ready_for_final_conclusion": len(weaknesses) == 0,
        }

        context["self_critique"] = critique

        if weaknesses:
            context["decision"]["status"] = "NOT_READY"
        else:
            context["decision"]["status"] = "READY_FOR_VERIFICATION"

        self._timeline(
            context,
            "self_critique_completed",
            {
                "weakness_count": len(weaknesses),
                "ready": critique["ready_for_final_conclusion"],
            },
        )

        self._touch_context(state, context)

        return critique

    # ------------------------------------------------------------------
    # DECISION QUALITY
    # ------------------------------------------------------------------

    def evaluate_decision_quality(self, state: Any) -> Dict[str, Any]:
        """
        Evaluate whether the current cognitive process is sufficiently
        prepared for verification.

        This is not a prediction-performance score.
        """

        context = self.create_context(state)

        checks = {
            "required_information_present": not bool(
                context["data"].get("missing")
            ),
            "observations_present": bool(context["observations"]),
            "hypotheses_present": bool(context["hypotheses"]),
            "evidence_present": bool(context["evidence"]),
            "contradictions_reviewed": not any(
                not item.get("resolved")
                for item in context["contradictions"]
            ),
            "self_critique_completed": "self_critique" in context,
        }

        passed = sum(1 for value in checks.values() if value)
        total = len(checks)

        result = {
            "checks": checks,
            "passed": passed,
            "total": total,
            "quality_status": (
                "READY_FOR_VERIFICATION"
                if passed == total
                else "NOT_READY"
            ),
            "note": (
                "Decision quality is not equivalent to financial outcome. "
                "A profitable outcome does not automatically mean the "
                "decision process was sound."
            ),
        }

        context["decision_quality"] = result

        self._timeline(
            context,
            "decision_quality_evaluated",
            {
                "passed": passed,
                "total": total,
                "status": result["quality_status"],
            },
        )

        self._touch_context(state, context)

        return result

    # ------------------------------------------------------------------
    # THINK
    # ------------------------------------------------------------------

    def think(self, state: Any) -> Dict[str, Any]:
        """
        LEGEND's Stage 1 entry point.

        It initializes the LEGEND cognitive context and evaluates
        readiness. It does NOT invent market intelligence.
        """

        context = self.create_context(state)

        self.define_market_requirements(state)

        readiness = self.detect_missing_information(
            state,
            available_information=self._extract_available_information(state),
        )

        critique = self.self_critique(state)
        quality = self.evaluate_decision_quality(state)

        context = self.get_shared(state, "legend_context", context)

        result = {
            "brain": "LEGEND",
            "status": "ACTIVE",
            "version": self.VERSION,
            "architecture_stage": self.ARCHITECTURE_STAGE,

            "mission": self.identity_profile["mission"],

            "market_analysis_ready": readiness["ready"],

            "missing_information": readiness["missing"],

            "hypothesis_count": len(context["hypotheses"]),
            "evidence_count": len(context["evidence"]),
            "contradiction_count": len(context["contradictions"]),

            "self_critique": critique,
            "decision_quality": quality,

            "conclusion": None,

            "principle": (
                "LEGEND will not manufacture a market conclusion when "
                "critical information is unavailable."
            ),
        }

        self.contribute(
            state,
            kind="legend_core_assessment",
            content=result,
            confidence=0.0,
            importance=0.9,
            metadata={
                "architecture_stage": self.ARCHITECTURE_STAGE,
            },
        )

        state.event(
            "legend_analysis_completed",
            "LEGEND",
            payload={
                "market_analysis_ready": readiness["ready"],
                "missing_count": len(readiness["missing"]),
            },
        )

        return result

    # ------------------------------------------------------------------
    # INPUT EXTRACTION
    # ------------------------------------------------------------------

    def _extract_available_information(
        self,
        state: Any,
    ) -> Dict[str, Any]:
        """
        Extract market information already present in shared state.

        We deliberately do not scrape or invent anything here.
        """

        available: Dict[str, Any] = {}

        possible_keys = [
            "instrument",
            "asset",
            "asset_class",
            "exchange",
            "timeframe",
            "market_data",
            "ohlcv",
            "price",
            "volume",
            "data_timestamp",
        ]

        for key in possible_keys:
            value = self.get_shared(state, key)

            if value is not None:
                available[key] = value

        # Allow upstream brains/API layers to provide a structured
        # market request.
        market_request = self.get_shared(
            state,
            "market_request",
            {},
        )

        if isinstance(market_request, dict):
            for key, value in market_request.items():
                if value is not None:
                    available[key] = value

        return available

    # ------------------------------------------------------------------
    # MESSAGE HANDLING
    # ------------------------------------------------------------------

    def receive_message(
        self,
        message: str,
        state: Any,
        source_brain: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Receive structured requests from other VALE brains.

        Stage 1 records the request rather than pretending that
        specialized market engines already exist.
        """

        context = self.create_context(state)

        request = {
            "timestamp": utc_now(),
            "from": source_brain,
            "message": message,
            "payload": payload or {},
        }

        requests = context.setdefault("incoming_requests", [])
        requests.append(request)

        self._timeline(
            context,
            "inter_brain_request_received",
            {
                "from": source_brain,
                "message": message,
            },
        )

        self._touch_context(state, context)

        return {
            "brain": "LEGEND",
            "received": True,
            "from": source_brain,
            "status": "REQUEST_RECORDED",
            "message": message,
            "available_stage": self.ARCHITECTURE_STAGE,
            "specialized_engine_required": True,
                       }
