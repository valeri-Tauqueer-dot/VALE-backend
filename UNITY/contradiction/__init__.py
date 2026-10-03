"""
VALE UNITY — Contradiction Package

The contradiction layer identifies, records, tracks, and manages conflicts
between cognitive contributions.

Its purpose is not to force agreement.

A contradiction may represent:

    - different conclusions
    - conflicting evidence
    - different assumptions
    - different interpretations
    - different time horizons
    - stale versus current information
    - incomplete information
    - genuine unresolved uncertainty

The contradiction subsystem preserves these differences so that MCVL,
UNITY, and other appropriate systems can investigate them.

It does NOT:
    - arbitrarily select a winner
    - replace MCVL
    - perform final response synthesis
    - perform objective intelligence
    - perform execution orchestration
"""

from .contradiction_engine import ContradictionEngine
from .conflict_state import ConflictState

__all__ = [
    "ContradictionEngine",
    "ConflictState",
]
