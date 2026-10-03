"""
VALE UNITY — Integration Diagnostics

Observes the structural health of UNITY's integration layer.

This module checks:

    - brain registrations
    - brain availability
    - brain activation
    - capability registrations
    - provider relationships
    - registry consistency

It does not decide which brain should be used.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_INTEGRATION_DIAGNOSTICS_FOUNDATION"


class IntegrationDiagnostics:
    """
    Structural health observer for UNITY integration components.

    Expected dependencies are intentionally duck-typed so this diagnostic
    layer remains compatible with the existing UNITY foundation modules.
    """

    VERSION = VERSION
    ARCHITECTURE_STAGE = ARCHITECTURE_STAGE

    def __init__(
        self,
        brain_registry: Optional[Any] = None,
        capability_registry: Optional[Any] = None,
        activation_manager: Optional[Any] = None,
        state: Optional[Any] = None,
    ) -> None:
        self.brain_registry = brain_registry
        self.capability_registry = capability_registry
        self.activation_manager = activation_manager
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
        if errors > 0:
            return "CRITICAL"

        if warnings > 0:
            return "WARNING"

        return "HEALTHY"

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_brain_registry(self) -> Dict[str, Any]:
        """
        Check brain registry integrity.
        """

        result: Dict[str, Any] = {
            "component": "brain_registry",
            "status": "HEALTHY",
            "errors": [],
            "warnings": [],
            "details": {},
        }

        if self.brain_registry is None:
            result["status"] = "WARNING"
            result["warnings"].append(
                "Brain registry is not connected."
            )
            return result

        try:
            validation = self._safe_call(
                self.brain_registry,
                "validate",
                {},
            )

            diagnostics = self._safe_call(
                self.brain_registry,
                "diagnostics",
                {},
            )

            names = self._safe_call(
                self.brain_registry,
                "names",
                [],
            )

            result["details"]["registered_brains"] = list(names or [])
            result["details"]["validation"] = validation
            result["details"]["diagnostics"] = diagnostics

            if isinstance(validation, dict):
                errors = validation.get("errors", [])

                if errors:
                    result["errors"].extend(errors)

            if isinstance(diagnostics, dict):
                diagnostic_errors = diagnostics.get("errors", [])

                if diagnostic_errors:
                    result["errors"].extend(diagnostic_errors)

            if result["errors"]:
                result["status"] = "CRITICAL"

        except Exception as exc:
            result["status"] = "CRITICAL"
            result["errors"].append(
                f"Brain registry diagnostic failed: {exc}"
            )

        return result

    def check_capability_registry(self) -> Dict[str, Any]:
        """
        Check capability registry integrity.
        """

        result: Dict[str, Any] = {
            "component": "capability_registry",
            "status": "HEALTHY",
            "errors": [],
            "warnings": [],
            "details": {},
        }

        if self.capability_registry is None:
            result["status"] = "WARNING"
            result["warnings"].append(
                "Capability registry is not connected."
            )
            return result

        try:
            validation = self._safe_call(
                self.capability_registry,
                "validate",
                {},
            )

            diagnostics = self._safe_call(
                self.capability_registry,
                "diagnostics",
                {},
            )

            names = self._safe_call(
                self.capability_registry,
                "names",
                [],
            )

            result["details"]["registered_capabilities"] = list(
                names or []
            )

            result["details"]["validation"] = validation
            result["details"]["diagnostics"] = diagnostics

            if isinstance(validation, dict):
                errors = validation.get("errors", [])

                if errors:
                    result["errors"].extend(errors)

            if isinstance(diagnostics, dict):
                diagnostic_errors = diagnostics.get("errors", [])

                if diagnostic_errors:
                    result["errors"].extend(diagnostic_errors)

            if result["errors"]:
                result["status"] = "CRITICAL"

        except Exception as exc:
            result["status"] = "CRITICAL"
            result["errors"].append(
                f"Capability registry diagnostic failed: {exc}"
            )

        return result

    def check_activation(self) -> Dict[str, Any]:
        """
        Check brain activation state.
        """

        result: Dict[str, Any] = {
            "component": "brain_activation",
            "status": "HEALTHY",
            "errors": [],
            "warnings": [],
            "details": {},
        }

        if self.activation_manager is None:
            result["status"] = "WARNING"
            result["warnings"].append(
                "Brain activation manager is not connected."
            )
            return result

        try:
            active = self._safe_call(
                self.activation_manager,
                "active_names",
                [],
            )

            available = self._safe_call(
                self.activation_manager,
                "available_names",
                [],
            )

            inactive = self._safe_call(
                self.activation_manager,
                "inactive_names",
                [],
            )

            result["details"]["active"] = list(active or [])
            result["details"]["available"] = list(available or [])
            result["details"]["inactive"] = list(inactive or [])

            validation = self._safe_call(
                self.activation_manager,
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
                f"Activation diagnostic failed: {exc}"
            )

        return result

    def check_state(self) -> Dict[str, Any]:
        """
        Check whether the UNITY integration state is available and valid.
        """

        result: Dict[str, Any] = {
            "component": "integration_state",
            "status": "HEALTHY",
            "errors": [],
            "warnings": [],
            "details": {},
        }

        if self.state is None:
            result["status"] = "WARNING"
            result["warnings"].append(
                "UNITY integration state is not connected."
            )
            return result

        try:
            validation = self._safe_call(
                self.state,
                "validate",
                {},
            )

            status = self._safe_call(
                self.state,
                "status",
                {},
            )

            result["details"]["status"] = status
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
                f"Integration state diagnostic failed: {exc}"
            )

        return result

    # ------------------------------------------------------------------
    # Full report
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """
        Run all integration diagnostics.
        """

        checks = [
            self.check_brain_registry(),
            self.check_capability_registry(),
            self.check_activation(),
            self.check_state(),
        ]

        errors = []
        warnings = []

        for check in checks:
            errors.extend(check.get("errors", []))
            warnings.extend(check.get("warnings", []))

        report = {
            "component": "UNITY_INTEGRATION",
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
        """
        Return the most recent diagnostic report.
        """

        return self._last_report

    def validate(self) -> Dict[str, Any]:
        """
        Lightweight validation of the diagnostic component itself.
        """

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
        """
        Return diagnostic metadata.
        """

        return {
            "component": self.__class__.__name__,
            "version": self.VERSION,
            "architecture_stage": self.ARCHITECTURE_STAGE,
            "has_brain_registry": self.brain_registry is not None,
            "has_capability_registry": (
                self.capability_registry is not None
            ),
            "has_activation_manager": (
                self.activation_manager is not None
            ),
            "has_state": self.state is not None,
            "has_last_report": self._last_report is not None,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.diagnostics()
