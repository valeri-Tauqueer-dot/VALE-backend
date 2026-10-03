"""
VALE UNITY — Diagnostics Package

The diagnostics layer observes the health and structural integrity of the
UNITY integration system.

Architecture:

                    UNITY
                      │
              ┌───────┴────────┐
              │   Diagnostics  │
              └───────┬────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
    Integration     Fabric      System
      Health        Health       Health
          └───────────┼───────────┘
                      ▼
                UNITY HEALTH

Diagnostics are observational.

They do NOT:
    - make cognitive decisions
    - select brains
    - perform objective intelligence
    - orchestrate execution
    - verify truth
    - resolve contradictions
    - synthesize responses
    - modify cognitive conclusions

They identify structural problems so UNITY and Supervisor can react
appropriately.
"""

from .integration_diagnostics import IntegrationDiagnostics
from .fabric_diagnostics import FabricDiagnostics
from .system_diagnostics import SystemDiagnostics

__all__ = [
    "IntegrationDiagnostics",
    "FabricDiagnostics",
    "SystemDiagnostics",
]
