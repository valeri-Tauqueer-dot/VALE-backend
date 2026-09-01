"""
VALE AI Media Intelligence System.

This package converts uploaded images, audio and documents into a
standardized MediaResult object that can be passed to VALE Brain and
the rest of the VALE multi-brain architecture.
"""

from .models import (
MediaResult,
MediaType,
ProcessingStatus,
MediaError,
)
from .media_orchestrator import MediaOrchestrator

all = [
"MediaResult",
"MediaType",
"ProcessingStatus",
"MediaError",
"MediaOrchestrator",
]
