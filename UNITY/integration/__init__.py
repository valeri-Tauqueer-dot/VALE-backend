"""
VALE UNITY — Integration Package

The integration layer maintains the structural relationship between UNITY
and the brains/supporting systems participating in VALE.

Integration is different from:
- HEROIC objective intelligence
- ALPHA execution optimization
- Cognitive Fabric communication
- Routing
- Verification
- Synthesis

This package provides the registry and activation foundations required for
UNITY to coordinate the wider VALE cognitive architecture.
"""

from .brain_registry import BrainRegistry
from .capability_registry import CapabilityRegistry
from .brain_activation import BrainActivationManager

__all__ = [
    "BrainRegistry",
    "CapabilityRegistry",
    "BrainActivationManager",
]
