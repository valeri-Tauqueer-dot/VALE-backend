from future import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

class MediaType(str, Enum):
IMAGE = "image"
AUDIO = "audio"
DOCUMENT = "document"
TEXT = "text"
UNKNOWN = "unknown"

class ProcessingStatus(str, Enum):
SUCCESS = "success"
PARTIAL = "partial"
FAILED = "failed"

class MediaError(Exception):
"""Base exception for media processing errors."""

@dataclass
class MediaResult:
"""
Standard result returned by every VALE media processor.

All processors return this same structure so the rest of VALE does
not need separate logic for image, audio and document processing.
"""

media_type: MediaType
filename: str
content_type: str

status: ProcessingStatus = ProcessingStatus.SUCCESS

# Human-readable understanding of the media.
description: str = ""

# OCR, transcript or extracted document text.
extracted_text: str = ""

# Structured information extracted from the media.
structured_data: Dict[str, Any] = field(default_factory=dict)

# Warnings that do not completely stop processing.
warnings: List[str] = field(default_factory=list)

# Errors encountered during processing.
errors: List[str] = field(default_factory=list)

# Metadata such as image size, audio duration, page count, etc.
metadata: Dict[str, Any] = field(default_factory=dict)

# Time of processing.
processed_at: str = field(
    default_factory=lambda: datetime.now(timezone.utc).isoformat()
)

def add_warning(self, message: str) -> None:
    if message and message not in self.warnings:
        self.warnings.append(message)

    if self.status == ProcessingStatus.SUCCESS:
        self.status = ProcessingStatus.PARTIAL

def add_error(self, message: str) -> None:
    if message and message not in self.errors:
        self.errors.append(message)

    self.status = ProcessingStatus.FAILED

def build_brain_context(
    self,
    max_text_chars: int = 50000,
) -> str:
    """
    Build a clean context string for VALE and downstream brains.

    The full raw media is NOT passed to text-based brains.
    Instead they receive the actual extracted understanding.
    """

    parts: List[str] = []

    parts.append("=== VALE MEDIA CONTEXT ===")
    parts.append(f"Media type: {self.media_type.value}")
    parts.append(f"Filename: {self.filename}")

    if self.description:
        parts.append("")
        parts.append("MEDIA UNDERSTANDING:")
        parts.append(self.description)

    if self.extracted_text:
        text = self.extracted_text.strip()

        if len(text) > max_text_chars:
            text = (
                text[:max_text_chars]
                + "\n\n[Media text truncated for context size.]"
            )

        parts.append("")
        parts.append("EXTRACTED CONTENT:")
        parts.append(text)

    if self.structured_data:
        parts.append("")
        parts.append("STRUCTURED INFORMATION:")

        for key, value in self.structured_data.items():
            if value is None:
                continue

            parts.append(f"{key}: {value}")

    if self.metadata:
        parts.append("")
        parts.append("MEDIA METADATA:")

        for key, value in self.metadata.items():
            if value is None:
                continue

            parts.append(f"{key}: {value}")

    if self.warnings:
        parts.append("")
        parts.append("PROCESSING WARNINGS:")

        for warning in self.warnings:
            parts.append(f"- {warning}")

    parts.append("")
    parts.append("=== END VALE MEDIA CONTEXT ===")

    return "\n".join(parts)

def to_dict(
    self,
    include_full_text: bool = True,
) -> Dict[str, Any]:
    """
    Convert to a JSON-serializable dictionary.
    """

    data = asdict(self)

    data["media_type"] = self.media_type.value
    data["status"] = self.status.value

    if not include_full_text:
        data.pop("extracted_text", None)

    return data
