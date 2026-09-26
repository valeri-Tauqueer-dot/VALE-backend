"""
VALE FEELINGS BRAIN
===================

Main entry point for the FEELINGS Brain.

FEELINGS is responsible for:
    - Human experience understanding
    - Emotional context
    - Empathy
    - Human perspective
    - Psychological context
    - Human impact
    - Communication context
    - Imagination and creativity as they are connected later

Important boundary:
    FEELINGS does not claim to directly know another person's
    internal mental or emotional state.

    FACT != INFERENCE != HYPOTHESIS != IMAGINATION
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from vale_connector import VALEConnector
from vale_brain_interface import VALEBrainInterface

from FEEL.Core.contracts import CognitiveContext


class FeelingsBrain(VALEBrainInterface):
    """
    Main FEELINGS Brain facade.

    This class connects the existing VALE Brain Network to the
    internal FEELING subsystems.

    The internal subsystems remain modular. FEELINGS Brain is the
    entry point and integration layer for them.
    """

    VERSION = "0.2.0"
    ARCHITECTURE_STAGE = "FEELING_INTEGRATION_FOUNDATION"

    def __init__(
        self,
        connector: Optional[VALEConnector] = None,
    ) -> None:
        super().__init__(
            brain_name="FEELINGS",
            connector=connector,
        )

        self.human_experience_engine = None
        self.emotional_context_engine = None
        self.empathy_engine = None

        self._initialize_engines()

    # ------------------------------------------------------------------
    # ENGINE INITIALIZATION
    # ------------------------------------------------------------------

    def _initialize_engines(self) -> None:
        """
        Initialize the FEELING engines.

        Imports are kept here rather than at module level so the main
        VALE backend can still import the FEELINGS Brain cleanly while
        individual FEELING subsystems are being developed.
        """

        try:
            from FEEL.human_experience.engine import (
                HumanExperienceEngine,
            )

            self.human_experience_engine = (
                HumanExperienceEngine()
            )

        except Exception:
            self.human_experience_engine = None

        try:
            from FEEL.emotional_context.engine import (
                EmotionalContextEngine,
            )

            self.emotional_context_engine = (
                EmotionalContextEngine()
            )

        except Exception:
            self.emotional_context_engine = None

        try:
            from FEEL.empathy.engine import (
                EmpathyEngine,
            )

            self.empathy_engine = EmpathyEngine()

        except Exception:
            self.empathy_engine = None

    # ------------------------------------------------------------------
    # IDENTITY
    # ------------------------------------------------------------------

    def identity(self) -> Dict[str, Any]:
        """
        Return FEELINGS Brain identity and subsystem status.
        """

        identity = super().identity()

        identity.update(
            {
                "version": self.VERSION,
                "architecture_stage": self.ARCHITECTURE_STAGE,
                "role": (
                    "Human, emotional, psychological, "
                    "creative and human-context intelligence"
                ),
                "engines": {
                    "human_experience": (
                        self.human_experience_engine
                        is not None
                    ),
                    "emotional_context": (
                        self.emotional_context_engine
                        is not None
                    ),
                    "empathy": (
                        self.empathy_engine
                        is not None
                    ),
                },
                "epistemic_boundary": {
                    "fact": True,
                    "inference": True,
                    "hypothesis": True,
                    "imagination": True,
                    "mind_reading": False,
                    "clinical_diagnosis": False,
                },
            }
        )

        return identity

    # ------------------------------------------------------------------
    # MAIN THINK METHOD
    # ------------------------------------------------------------------

    def think(
        self,
        state: Any,
    ) -> Dict[str, Any]:
        """
        Process one VALE Brain State through the currently connected
        FEELING engines.

        The result is returned through the existing VALE Brain
        interface as one structured FEELINGS contribution.
        """

        user_message = self._extract_user_message(
            state
        )

        cognitive_context = self._build_cognitive_context(
            state,
            user_message,
        )

        result: Dict[str, Any] = {
            "brain": self.brain_name,
            "version": self.VERSION,
            "architecture_stage": self.ARCHITECTURE_STAGE,
            "status": "READY",
            "input": {
                "user_message": user_message,
            },
            "human_experience": None,
            "emotional_context": None,
            "empathy": None,
            "uncertainties": [],
            "epistemic_boundary": {
                "fact": [],
                "inference": [],
                "hypothesis": [],
                "imagination": [],
            },
            "engine_status": {
                "human_experience": (
                    self.human_experience_engine
                    is not None
                ),
                "emotional_context": (
                    self.emotional_context_engine
                    is not None
                ),
                "empathy": (
                    self.empathy_engine
                    is not None
                ),
            },
        }

        # --------------------------------------------------------------
        # Human Experience
        # --------------------------------------------------------------

        if self.human_experience_engine is not None:

            try:
                assessment = (
                    self.human_experience_engine.analyze(
                        cognitive_context
                    )
                )

                result["human_experience"] = (
                    self._serialize_result(
                        assessment
                    )
                )

            except Exception as exc:
                result["human_experience"] = {
                    "status": "ERROR",
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                }

                result["uncertainties"].append(
                    "Human Experience Engine could not complete "
                    "this analysis."
                )

        else:

            result["human_experience"] = {
                "status": "UNAVAILABLE",
            }

        # --------------------------------------------------------------
        # Emotional Context
        # --------------------------------------------------------------

        if self.emotional_context_engine is not None:

            try:
                assessment = (
                    self.emotional_context_engine.analyze(
                        cognitive_context
                    )
                )

                result["emotional_context"] = (
                    self._serialize_result(
                        assessment
                    )
                )

            except Exception as exc:
                result["emotional_context"] = {
                    "status": "ERROR",
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                }

                result["uncertainties"].append(
                    "Emotional Context Engine could not complete "
                    "this analysis."
                )

        else:

            result["emotional_context"] = {
                "status": "UNAVAILABLE",
            }

        # --------------------------------------------------------------
        # Empathy
        # --------------------------------------------------------------

        if self.empathy_engine is not None:

            try:
                assessment = (
                    self.empathy_engine.analyze(
                        context=cognitive_context
                    )
                )

                result["empathy"] = (
                    self._serialize_result(
                        assessment
                    )
                )

            except Exception as exc:
                result["empathy"] = {
                    "status": "ERROR",
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                }

                result["uncertainties"].append(
                    "Empathy Engine could not complete "
                    "this analysis."
                )

        else:

            result["empathy"] = {
                "status": "UNAVAILABLE",
            }

        # --------------------------------------------------------------
        # Epistemic boundary
        # --------------------------------------------------------------

        result["epistemic_boundary"] = (
            self._collect_epistemic_information(
                result
            )
        )

        # --------------------------------------------------------------
        # Publish FEELINGS contribution into shared VALE state
        # --------------------------------------------------------------

        self._publish_result(
            state,
            result,
        )

        return result

    # ------------------------------------------------------------------
    # BUILD COGNITIVE CONTEXT
    # ------------------------------------------------------------------

    def _build_cognitive_context(
        self,
        state: Any,
        user_message: str,
    ) -> CognitiveContext:
        """
        Convert the existing VALEBrainState into the FEELING
        CognitiveContext contract.
        """

        task_id = str(
            getattr(
                state,
                "task_id",
                "unknown-task",
            )
        )

        conversation = getattr(
            state,
            "conversation",
            [],
        )

        conversation_context = []

        if isinstance(
            conversation,
            list,
        ):

            for item in conversation:

                if isinstance(
                    item,
                    dict,
                ):

                    content = item.get(
                        "content",
                        "",
                    )

                    if content:
                        conversation_context.append(
                            str(content)
                        )

                elif item:

                    conversation_context.append(
                        str(item)
                    )

        metadata = getattr(
            state,
            "metadata",
            {},
        )

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = {}

        return CognitiveContext(
            task_id=task_id,
            user_input=user_message,
            conversation_context=conversation_context,
            metadata=dict(metadata),
        )

    # ------------------------------------------------------------------
    # USER MESSAGE
    # ------------------------------------------------------------------

    def _extract_user_message(
        self,
        state: Any,
    ) -> str:
        """
        Extract the current user message from VALEBrainState.
        """

        if state is None:
            return ""

        value = getattr(
            state,
            "user_message",
            "",
        )

        if value is None:
            return ""

        return str(value).strip()

    # ------------------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------------------

    def _serialize_result(
        self,
        result: Any,
    ) -> Any:
        """
        Convert FEELING result objects into dictionaries when
        possible.
        """

        if result is None:
            return None

        if isinstance(
            result,
            dict,
        ):
            return result

        to_dict = getattr(
            result,
            "to_dict",
            None,
        )

        if callable(
            to_dict
        ):

            try:
                return to_dict()

            except Exception:
                pass

        return result

    # ------------------------------------------------------------------
    # EPISTEMIC INFORMATION
    # ------------------------------------------------------------------

    def _collect_epistemic_information(
        self,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Collect epistemic information already produced by the
        connected FEELING engines.

        No psychological conclusion is promoted to fact here.
        """

        information = {
            "fact": [],
            "inference": [],
            "hypothesis": [],
            "imagination": [],
        }

        for engine_name in (
            "human_experience",
            "emotional_context",
            "empathy",
        ):

            engine_result = result.get(
                engine_name
            )

            if not isinstance(
                engine_result,
                dict,
            ):
                continue

            claims = engine_result.get(
                "epistemic_claims",
                [],
            )

            if not isinstance(
                claims,
                list,
            ):
                continue

            for claim in claims:

                if isinstance(
                    claim,
                    dict,
                ):

                    epistemic_type = str(
                        claim.get(
                            "epistemic_type",
                            "",
                        )
                    ).lower()

                    content = claim.get(
                        "content",
                        "",
                    )

                    if (
                        epistemic_type
                        in information
                        and content
                    ):
                        information[
                            epistemic_type
                        ].append(
                            content
                        )

        return information

    # ------------------------------------------------------------------
    # PUBLISH RESULT
    # ------------------------------------------------------------------

    def _publish_result(
        self,
        state: Any,
        result: Dict[str, Any],
    ) -> None:
        """
        Store the FEELINGS contribution in the shared VALE state.

        This uses the existing VALEBrainInterface and VALEBrainState
        contracts.
        """

        if state is None:
            return

        self.set_shared(
            state,
            "feelings_assessment",
            result,
        )

        confidence = self._calculate_confidence(
            result
        )

        self.contribute(
            state=state,
            kind="feelings_assessment",
            content=result,
            confidence=confidence,
            importance=0.7,
            metadata={
                "version": self.VERSION,
                "architecture_stage": (
                    self.ARCHITECTURE_STAGE
                ),
            },
        )

        state.event(
            event_type="FEELINGS_ASSESSMENT",
            source=self.brain_name,
            payload={
                "status": result.get(
                    "status",
                    "UNKNOWN",
                ),
                "confidence": confidence,
            },
        )

    # ------------------------------------------------------------------
    # CONFIDENCE
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        result: Dict[str, Any],
    ) -> float:
        """
        Calculate a conservative confidence from actual engine
        outputs.

        If no engine provides a confidence value, confidence remains
        zero rather than inventing a value.
        """

        values = []

        for engine_name in (
            "human_experience",
            "emotional_context",
            "empathy",
        ):

            engine_result = result.get(
                engine_name
            )

            if not isinstance(
                engine_result,
                dict,
            ):
                continue

            value = engine_result.get(
                "confidence"
            )

            if isinstance(
                value,
                (int, float),
            ):

                values.append(
                    max(
                        0.0,
                        min(
                            1.0,
                            float(value),
                        ),
                    )
                )

        if not values:
            return 0.0

        return sum(values) / len(values)


__all__ = [
    "FeelingsBrain",
        ]
