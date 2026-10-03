"""
VALE UNITY — Communication Package

The communication layer provides the structured communication boundary
between UNITY and the wider VALE cognitive architecture.

Architecture:

    Brain / System
          │
          ▼
    Communication Protocol
          │
          ▼
    Message Router / Event Dispatcher
          │
          ▼
    Cognitive Fabric
          │
          ▼
    Destination Brain / System

Communication is different from:

- HEROIC objective intelligence
- ALPHA execution optimization
- routing of cognitive tasks
- contradiction resolution
- MCVL verification
- final UNITY synthesis

The communication layer is responsible for:

    - message structure
    - message routing
    - event dispatch
    - delivery coordination
    - communication lifecycle
    - traceability

The Cognitive Fabric remains the lower-level communication transport.

The communication layer does not decide what VALE should accomplish.
"""

from .message_router import MessageRouter
from .event_dispatcher import EventDispatcher
from .communication_protocol import CommunicationProtocol

__all__ = [
    "MessageRouter",
    "EventDispatcher",
    "CommunicationProtocol",
]
