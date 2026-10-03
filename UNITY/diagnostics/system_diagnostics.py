"""
VALE UNITY — System Diagnostics

System-wide UNITY health aggregation.

This component combines:

    Integration Diagnostics
            +
    Fabric Diagnostics
            ↓
       System Health

It is intentionally an observer.

It does not repair the system or make cognitive decisions.

Supervisor will eventually be able to consume these health signals and
decide whether recovery, isolation, restart, or escalation is required.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


VERSION = "0.1.0"
ARCHITECTURE_STAGE = "UNITY_SYSTEM_DIAGNOSTICS_FOUNDATION"


class SystemDiagnostics:
    """
    Aggregates structural diagnostics from UNITY subsystems.
    """

    VERSION = VERSION
    ARCHITECTURE_STAGE = ARCHITECTURE_STAGE

    def __init__(
        self,
        integration_diagnostics: Optional[Any] = None,
        fabric_diagnostics: Optional[Any] = None,
        state: Optional[Any] = None,
    ) -> None:
        self.integration_diagnostics = integration_diagnostics
        self.fabric_diagnostics = fabric_diagnostics
        self.state = state

        self._last_report: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _safe_run(
        diagnostic: Any,
    ) -> Dict[str, Any]:
        if diagnostic is None:
            return {
                "status": "WARNING",
                "errors": [],
                "warnings": [
                    "Diagnostic component is not connected."
                ],
            }

        run = getattr(diagnostic, "run", None)

        if not callable(run):
            return {
                "status": "CRITICAL",
                "errors": [
                    "Diagnostic component does not provide run()."
                ],
                "warnings": [],
            }

        try:
            result = run()

            if isinstance(result, dict):
                return result

            return {
                "status": "CRITICAL",
                "errors": [
                    "Diagnostic component returned invalid data."
                ],
                "warnings": [],
            }

        except Exception as exc:
            return {
                "status": "CRITICAL",
                "errors": [
                    f"Diagnostic execution failed: {exc}"
                ],
                "warnings": [],
            }

    @staticmethod
    def _overall_status(
        errors: int,
        warnings: int,
        component_statuses: list[str],
    ) -> str:
        if errors:
            return "CRITICAL"

        if "CRITICAL" in component_statuses:
            return "CRITICAL"

        if warnings:
            return "WARNING"

        if "WARNING" in component_statuses:
            return "WARNING"

        return "HEALTHY"

    # ------------------------------------------------------------------
    # State check
    # ------------------------------------------------------------------

    def check_state(self) -> Dict[str, Any]:
        result = {
            "component": "unity_state",
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
            validate = getattr(
                self.state,
                "validate",
                None,
            )

            if callable(validate):
                validation = validate()
                result["details"]["validation"] = validation

                if isinstance(validation, dict):
                    result["errors"].extend(
                        validation.get("errors", [])
                    )

            status_method = getattr(
                self.state,
                "status",
                None,
            )

            if callable(status_method):
                result["details"]["status"] = status_method()

            if result["errors"]:
                result["status"] = "CRITICAL"

        except Exception as exc:
            result["status"] = "CRITICAL"
            result["errors"].append(
                f"UNITY state diagnostic failed: {exc}"
            )

        return result

    # ------------------------------------------------------------------
    # System report
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        integration_report = self._safe_run(
            self.integration_diagnostics
        )

        fabric_report = self._safe_run(
            self.fabric_diagnostics
        )

        state_report = self.check_state()

        component_reports = {
            "integration": integration_report,
            "fabric": fabric_report,
            "state": state_report,
        }

        errors = []
        warnings = []
        statuses = []

        for report in component_reports.values():
            errors.extend(
                report.get("errors", [])
            )

            warnings.extend(
                report.get("warnings", [])
            )

            statuses.append(
                report.get("status", "UNKNOWN")
            )

        status = self._overall_status(
            errors=len(errors),
            warnings=len(warnings),
            component_statuses=statuses,
        )

        report = {
            "component": "UNITY_SYSTEM",
            "version": self.VERSION,
            "architecture_stage": self.ARCHITECTURE_STAGE,
            "status": status,
            "timestamp": self._now(),
            "components": component_reports,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "components": len(component_reports),
                "errors": len(errors),
                "warnings": len(warnings),
                "component_statuses": statuses,
            },
        }

        self._last_report = report

        return report

    def health(self) -> str:
        """
        Run diagnostics and return only the overall health state.
        """

        return self.run().get(
            "status",
            "UNKNOWN",
        )

    def is_healthy(self) -> bool:
        return self.health() == "HEALTHY"

    def has_errors(self) -> bool:
        report = self.run()

        return bool(
            report.get("errors")
            or report.get("status") == "CRITICAL"
        )

    def last_report(self) -> Optional[Dict[str, Any]]:
        return self._last_report

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Diagnostics metadata
    # ------------------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "component": self.__class__.__name__,
            "version": self.VERSION,
            "architecture_stage": self.ARCHITECTURE_STAGE,
            "has_integration_diagnostics": (
                self.integration_diagnostics is not None
            ),
            "has_fabric_diagnostics": (
                self.fabric_diagnostics is not None
            ),
            "has_state": self.state is not None,
            "has_last_report": self._last_report is not None,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.diagnostics()
