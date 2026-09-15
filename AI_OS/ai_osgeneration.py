"""
VALE Generation AI OS
=====================

Generation AI OS is VALE's operating/cognitive infrastructure layer.

It is NOT a specialized brain.

Therefore this module intentionally does not define:

    AiOsGenerationBrain(VALEBrainInterface)

Instead it provides a lightweight infrastructure object that can
eventually own the complete VALE cognitive lifecycle.

Current lifecycle:

    Understand
        ↓
    Think
        ↓
    Verify
        ↓
    Decide
        ↓
    Execute
        ↓
    Observe
        ↓
    Learn
        ↓
    Evolve

The actual specialized intelligence remains inside the VALE brains.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


from vale_connector import VALEConnector


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


class GenerationAIOS:

    VERSION = "1.0"

    LIFECYCLE = (
        "UNDERSTAND",
        "THINK",
        "VERIFY",
        "DECIDE",
        "EXECUTE",
        "OBSERVE",
        "LEARN",
        "EVOLVE",
    )

    def __init__(
        self,
        connector: Optional[
            VALEConnector
        ] = None,
    ):

        self.name = "VALE GENERATION AI OS"

        self.version = (
            self.VERSION
        )

        self.connector = (
            connector
            if connector is not None
            else VALEConnector()
        )

        self.status = "ONLINE"

        self.current_phase = (
            "UNDERSTAND"
        )

        self.active_tasks = {}

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    def begin_task(
        self,
        user_message: str,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:

        task = {
            "message": (
                user_message or ""
            ).strip(),
            "metadata": (
                metadata or {}
            ),
            "phase": "UNDERSTAND",
            "started_at": utc_now(),
        }

        task_id = (
            f"os-{len(self.active_tasks) + 1}-"
            f"{int(datetime.now().timestamp() * 1000)}"
        )

        self.active_tasks[
            task_id
        ] = task

        self.current_phase = (
            "UNDERSTAND"
        )

        return {
            "success": True,
            "task_id": task_id,
            "phase": "UNDERSTAND",
            "lifecycle": list(
                self.LIFECYCLE
            ),
        }

    def set_phase(
        self,
        phase: str,
    ) -> Dict[str, Any]:

        normalized = (
            str(
                phase or ""
            )
            .strip()
            .upper()
        )

        if normalized not in self.LIFECYCLE:

            return {
                "success": False,
                "error": (
                    f"Unknown Generation AI OS "
                    f"phase: {normalized}"
                ),
            }

        self.current_phase = (
            normalized
        )

        return {
            "success": True,
            "phase": normalized,
        }

    def observe(
        self,
        event: str,
        data: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:

        return {
            "success": True,
            "event": event,
            "data": data or {},
            "timestamp": utc_now(),
        }

    # ------------------------------------------------------------------
    # Architecture information
    # ------------------------------------------------------------------

    def architecture(
        self,
    ) -> Dict[str, Any]:

        return {
            "name": self.name,
            "version": self.version,
            "status": self.status,
            "role": (
                "Underlying operating architecture "
                "for VALE cognition"
            ),
            "is_specialized_brain": False,
            "lifecycle": list(
                self.LIFECYCLE
            ),
            "connector_available": (
                self.connector is not None
            ),
        }

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

    def capabilities(
        self,
    ) -> Dict[str, bool]:

        return {
            "task_lifecycle": True,
            "cognitive_context": True,
            "shared_state_support": True,
            "routing_support": True,
            "communication_support": True,
            "memory_support": True,
            "knowledge_support": True,
            "reasoning_support": True,
            "verification_support": True,
            "safety_support": True,
            "observability_support": True,
            "learning_support": True,
            "evolution_support": True,
            "specialized_brain": False,
        }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status_report(
        self,
    ) -> Dict[str, Any]:

        return {
            "name": self.name,
            "version": self.version,
            "status": self.status,
            "current_phase": (
                self.current_phase
            ),
            "active_tasks": len(
                self.active_tasks
            ),
            "is_brain": False,
            "role": "OPERATING_ARCHITECTURE",
            "checked": utc_now(),
        }


# ----------------------------------------------------------------------
# Compatibility alias
# ----------------------------------------------------------------------
#
# Existing external imports that only expect the old class name will
# continue to import successfully, but it is now an OS object rather
# than a VALEBrainInterface brain.
#
# New code should use GenerationAIOS.
# ----------------------------------------------------------------------

AiOsGenerationBrain = GenerationAIOS