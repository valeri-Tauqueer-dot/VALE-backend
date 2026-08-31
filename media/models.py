from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List


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

    All processors return the same structure so the rest of VALE
    does not need separate logic for image, audio, and document
    processing.
    """

    media_type: MediaType
    filename: str
    content_type: str

    status: ProcessingStatus = ProcessingStatus.SUCCESS

    description: str = ""
    extracted_text: str = ""

    structured_data: Dict[str, Any] = field(default_factory=dict)

    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    processed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def add_warning(self, message: str) -> None:
        """Add a processing warning."""

        if message and message not in self.warnings:
            self.warnings.append(message)

        if self.status == ProcessingStatus.SUCCESS:
            self.status = ProcessingStatus.PARTIAL

    def add_error(self, message: str) -> None:
        """Add a processing error."""

        if message and message not in self.errors:
            self.errors.append(message)

        self.status = ProcessingStatus.FAILED

    def build_brain_context(
        self,
        max_text_chars: int = 50000,
    ) -> str:
        """
        Build a clean context string for VALE and downstream brains.
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
                if value is not None:
                    parts.append(f"{key}: {value}")

        if self.metadata:
            parts.append("")
            parts.append("MEDIA METADATA:")

            for key, value in self.metadata.items():
                if value is not None:
                    parts.append(f"{key}: {value}")

        if self.warnings:
            parts.append("")
            parts.append("PROCESSING WARNINGS:")

            for warning in self.warnings:
                parts.append(f"- {warning}")

        if self.errors:
            parts.append("")
            parts.append("PROCESSING ERRORS:")

            for error in self.errors:
                parts.append(f"- {error}")

        parts.append("")
        parts.append("=== END VALE MEDIA CONTEXT ===")

        return "\n".join(parts)

    def to_dict(
        self,
        include_full_text: bool = True,
    ) -> Dict[str, Any]:
        """Convert the result to a JSON-serializable dictionary."""

        data = asdict(self)

        data["media_type"] = self.media_type.value
        data["status"] = self.status.value

        if not include_full_text:
            data.pop("extracted_text", None)

        return data
