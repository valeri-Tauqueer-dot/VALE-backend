from future import annotations

import logging
from typing import Optional

from .models import (
MediaResult,
MediaType,
)
from .validators import (
validate_upload,
MediaValidationError,
)
from .image_processor import (
ImageProcessor,
)
from .audio_processor import (
AudioProcessor,
)
from .document_processor import (
DocumentProcessor,
)

logger = logging.getLogger(name)

class MediaOrchestrator:
"""
Central VALE media routing system.

This class receives the uploaded file and routes it to the
appropriate specialist processor.
"""

def __init__(self) -> None:

    self.image_processor = (
        ImageProcessor()
    )

    self.audio_processor = (
        AudioProcessor()
    )

    self.document_processor = (
        DocumentProcessor()
    )

async def process(
    self,
    data: bytes,
    filename: Optional[str],
    content_type: Optional[str],
    user_message: str = "",
) -> MediaResult:
    """
    Validate and process uploaded media.
    """

    (
        safe_filename,
        normalized_content_type,
        media_type,
    ) = validate_upload(
        data=data,
        filename=filename,
        content_type=content_type,
    )

    logger.info(
        "VALE processing media: type=%s filename=%s bytes=%s",
        media_type.value,
        safe_filename,
        len(data),
    )

    if media_type == MediaType.IMAGE:

        return await self.image_processor.process(
            data=data,
            filename=safe_filename,
            content_type=normalized_content_type,
            user_message=user_message,
        )

    if media_type == MediaType.AUDIO:

        return await self.audio_processor.process(
            data=data,
            filename=safe_filename,
            content_type=normalized_content_type,
            user_message=user_message,
        )

    if media_type == MediaType.DOCUMENT:

        return await self.document_processor.process(
            data=data,
            filename=safe_filename,
            content_type=normalized_content_type,
            user_message=user_message,
        )

    raise MediaValidationError(
        "VALE could not determine how to process this media."
    )

def supported_media(self) -> dict:
    """
    Information useful for health checks and API responses.
    """

    return {
        "images": [
            "image/jpeg",
            "image/png",
            "image/webp",
        ],
        "audio": [
            "audio/webm",
            "audio/wav",
            "audio/mpeg",
            "audio/mp3",
            "audio/mp4",
            "audio/ogg",
        ],
        "documents": [
            "application/pdf",
            "text/plain",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ],
  }
