"""
VALE FEELINGS Brain
Empathy Subsystem

Purpose:
    Provide computational empathy capabilities for FEELING.

Empathy in VALE means:
    - modeling another person's possible perspective
    - considering their possible emotional/contextual state
    - anticipating how communication may affect them
    - reducing unnecessary confusion or friction
    - adapting communication appropriately

Empathy does NOT mean:
    - claiming to feel another person's emotions
    - claiming certainty about another person's internal state
    - mind-reading
    - psychological diagnosis
"""

from .engine import EmpathyEngine
from .perspective import EmpathyPerspectiveModel
from .impact import EmpathyImpactAnalyzer
from .needs import EmpathyNeedsAnalyzer

__all__ = [
    "EmpathyEngine",
    "EmpathyPerspectiveModel",
    "EmpathyImpactAnalyzer",
    "EmpathyNeedsAnalyzer",
]
