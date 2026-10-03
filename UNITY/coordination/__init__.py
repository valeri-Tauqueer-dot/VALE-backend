"""
VALE UNITY — Coordination Package

The coordination layer maintains shared task and execution context across
multiple VALE brains and supporting systems.

Coordination is distinct from:
- HEROIC objective intelligence
- ALPHA execution optimization
- Cognitive Fabric communication
- Routing transport
- MCVL verification
- Final UNITY synthesis
"""

from .task_context import TaskContext
from .execution_context import ExecutionContext
from .coordination_engine import CoordinationEngine

__all__ = [
    "TaskContext",
    "ExecutionContext",
    "CoordinationEngine",
]
