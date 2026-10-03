"""
VALE UNITY — Synthesis Package

The synthesis layer is responsible for combining validated cognitive state
into a coherent UNITY representation.

The synthesis layer is distinct from:

- HEROIC objective intelligence
- ALPHA execution orchestration
- specialized brain reasoning
- MCVL verification
- Memory and Knowledge
- Cognitive Fabric communication
- routing and coordination

Synthesis should consume already-produced and appropriately verified
information. It must not manufacture evidence or silently resolve
contradictions.

Current foundation components:

    SynthesisEngine
        ↓
    StateIntegrator
        ↓
    ResponseIntegrator

These components will be implemented incrementally.
"""

from .synthesis_engine import SynthesisEngine
from .state_integrator import StateIntegrator
from .response_integrator import ResponseIntegrator

__all__ = [
    "SynthesisEngine",
    "StateIntegrator",
    "ResponseIntegrator",
]
