"""
VALE UNITY — Routing Package

Routing is a UNITY integration capability.

The routing layer connects:
    required capability
        ↓
    selected brain/system
        ↓
    execution destination

Routing does not replace:
- HEROIC objective intelligence
- ALPHA execution orchestration
- Cognitive Fabric communication
- MCVL verification
- UNITY final synthesis
"""

from .routing_engine import RoutingEngine
from .routing_policy import RoutingPolicy
from .route_plan import RoutePlan

__all__ = [
    "RoutingEngine",
    "RoutingPolicy",
    "RoutePlan",
]
