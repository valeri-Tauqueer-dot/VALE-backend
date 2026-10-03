"""
VALE UNITY — Verification Package

The verification layer provides the structural boundary between UNITY and
the VALE verification system, primarily MCVL.

Important architectural boundary:

    UNITY
       ↓
    Verification Gateway
       ↓
      MCVL
       ↓
    Verification Result
       ↓
    UNITY State

UNITY does NOT replace MCVL verification intelligence.

This package is responsible for:

    - verification requests
    - verification state
    - verification result registration
    - provenance preservation
    - confidence/uncertainty transport
    - verification lifecycle management

It does NOT:

    - independently determine truth
    - invent evidence
    - replace MCVL
    - silently resolve contradictions
    - manufacture confidence
"""

from .verification_state import VerificationState
from .verification_gateway import VerificationGateway

__all__ = [
    "VerificationState",
    "VerificationGateway",
]
