"""
VALE UNITY — Fabric Diagnostics

Observes the health of UNITY communication infrastructure.

Checks include:

    - Cognitive Fabric
    - Message Router
    - Event Dispatcher
    - Communication Protocol

This layer observes communication infrastructure.

It does not:
    - choose destinations
    - decide what a message means
    - perform cognitive reasoning
    - perform verification
    - synthesize responses
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_FABRIC_DIAGNOSTICS_FOUNDATION"


class FabricDiagnostics:
    """
    Structural health observer for UNITY communication infrastructure.
    """

    VERSION = VERSION
    ARCHITECTURE_STAGE = ARCHITECTURE_STAGE

    def __init__(
        self,
        cognitive_fabric: Optional[Any] = None,
        message_router: Optional[Any] = None,
        event_dispatcher: Optional[Any] = None,
        communication_protocol: Optional[Any] = None,
        state: Optional[Any] = None,
    ) -> None:
        self.cognitive_fabric = cognitive_fabric
        self.message_router = message_router
        self.event_dispatcher = event_dispatcher
        self.communication_protocol = communication_protocol
        self.state = state

        self._last_report: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _safe_call(
        obj: Any,
        method_name: str,
        default: Any = None,
    ) -> Any:
        if obj is None:
            return default

        method = getattr(obj, method_name, None)

        if not callable(method):
            return default

        try:
            return method()
        except Exception:
            return default

    @staticmethod
    def _severity(errors: int, warnings: int) -> str:
        if errors:
            return "CRITICAL"

        if warnings:
            return "WARNING"

        return "HEALTHY"

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def _check_component(
        self,
        component_name: str,
        component: Any,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "component": component_name,
            "status": "HEALTHY",
            "errors": [],
            "warnings": [],
            "details": {},
        }

        if component is None:
            result["status"] = "WARNING"
            result["warnings"].append(
                f"{component_name} is not connected."
            )
            return result

        try:
            validation = self._safe_call(
                component,
                "validate",
                {},
            )

            diagnostics = self._safe_call(
                component,
                "diagnostics",
                {},
            )

            result["details"]["validation"] = validation
            result["details"]["diagnostics"] = diagnostics

            if isinstance(validation, dict):
                errors = validation.get("errors", [])

                if errors:
                    result["errors"].extend(errors)

            if isinstance(diagnostics, dict):
                errors = diagnostics.get("errors", [])

                if errors:
                    result["errors"].extend(errors)

                warnings = diagnostics.get("warnings", [])

                if warnings:
                    result["warnings"].extend(warnings)

            if result["errors"]:
                result["status"] = "CRITICAL"

            elif result["warnings"]:
                result["status"] = "WARNING"

        except Exception as exc:
            result["status"] = "CRITICAL"
            result["errors"].append(
                f"{component_name} diagnostic failed: {exc}"
            )

        return result

    def check_cognitive_fabric(self) -> Dict[str, Any]:
        return self._check_component(
            "cognitive_fabric",
            self.cognitive_fabric,
        )

    def check_message_router(self) -> Dict[str, Any]:
        return self._check_component(
            "message_router",
            self.message_router,
        )

    def check_event_dispatcher(self) -> Dict[str, Any]:
        return self._check_component(
            "event_dispatcher",
            self.event_dispatcher,
        )

    def check_communication_protocol(self) -> Dict[str, Any]:
        return self._check_component(
            "communication_protocol",
            self.communication_protocol,
        )

    def check_state(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "component": "fabric_state",
            "status": "HEALTHY",
            "errors": [],
            "warnings": [],
            "details": {},
        }

        if self.state is None:
            result["status"] = "WARNING"
            result["warnings"].append(
                "UNITY state is not connected."
            )
            return result

        try:
            validation = self._safe_call(
                self.state,
                "validate",
                {},
            )

            result["details"]["validation"] = validation

            if isinstance(validation, dict):
                errors = validation.get("errors", [])

                if errors:
                    result["errors"].extend(errors)

            if result["errors"]:
                result["status"] = "CRITICAL"

        except Exception as exc:
            result["status"] = "CRITICAL"
            result["errors"].append(
                f"Fabric state diagnostic failed: {exc}"
            )

        return result

    # ------------------------------------------------------------------
    # Full report
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        checks = [
            self.check_cognitive_fabric(),
            self.check_message_router(),
            self.check_event_dispatcher(),
            self.check_communication_protocol(),
            self.check_state(),
        ]

        errors = []
        warnings = []

        for check in checks:
            errors.extend(check.get("errors", []))
            warnings.extend(check.get("warnings", []))

        report = {
            "component": "UNITY_FABRIC",
            "version": self.VERSION,
            "architecture_stage": self.ARCHITECTURE_STAGE,
            "status": self._severity(
                len(errors),
                len(warnings),
            ),
            "timestamp": self._now(),
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "checks": len(checks),
                "errors": len(errors),
                "warnings": len(warnings),
            },
        }

        self._last_report = report

        return report

    def last_report(self) -> Optional[Dict[str, Any]]:
        return self._last_report

    def validate(self) -> Dict[str, Any]:
        errors = []

        if not self.VERSION:
            errors.append("Diagnostic version is missing.")

        if not self.ARCHITECTURE_STAGE:
            errors.append("Architecture stage is missing.")

        return {
            "valid": not errors,
            "errors": errors,
            "timestamp": self._now(),
        }

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "component": self.__class__.__name__,
            "version": self.VERSION,
            "architecture_stage": self.ARCHITECTURE_STAGE,
            "has_cognitive_fabric": (
                self.cognitive_fabric is not None
            ),
            "has_message_router": (
                self.message_router is not None
            ),
            "has_event_dispatcher": (
                self.event_dispatcher is not None
            ),
            "has_communication_protocol": (
                self.communication_protocol is not None
            ),
            "has_state": self.state is not None,
            "has_last_report": self._last_report is not None,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.diagnostics()
