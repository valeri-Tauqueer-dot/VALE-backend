"""
VALE FEELING Brain
Human Experience Package

This package contains the systems responsible for computationally
modeling human experience and human-centered context.

FEELING does not possess human experience itself.

It models:
    - what happened to a person
    - what the situation may mean to them
    - what may matter to them
    - possible consequences
    - contextual human needs
    - possible perspectives
    - uncertainty surrounding those interpretations

All internal interpretations remain distinguishable from observed facts.
"""

from .engine import HumanExperienceEngine
from .context import HumanExperienceContext
from .consequences import HumanConsequenceAnalyzer
from .needs import HumanNeedsAnalyzer


__all__ = [
    "HumanExperienceEngine",
    "HumanExperienceContext",
    "HumanConsequenceAnalyzer",
    "HumanNeedsAnalyzer",
]
