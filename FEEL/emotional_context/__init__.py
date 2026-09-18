"""
VALE FEELING Brain
Emotional Context subsystem.

This package models emotional information as uncertain,
evidence-grounded contextual signals.

It does not claim literal access to a person's internal
emotional state.
"""

from .engine import EmotionalContextEngine
from .signals import EmotionalSignalDetector
from .appraisal import EmotionalAppraisalEngine
from .state import EmotionalStateModel

__all__ = [
    "EmotionalContextEngine",
    "EmotionalSignalDetector",
    "EmotionalAppraisalEngine",
    "EmotionalStateModel",
]
