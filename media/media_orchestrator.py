from __future__ import annotations

import logging
from typing import Optional

from .audio_processor import AudioProcessor
from .document_processor import DocumentProcessor
from .image_processor import ImageProcessor
from .models import MediaError, MediaResult, MediaType
from .validators import MediaValidationError, validate_upload

logger = logging.getLogger(__name__)


class MediaOrchestrator:
    """Single entry point that validates and routes all VALE media."""

    def __init__(self) -> None:
        self.image_processor = ImageProcessor()
        self.audio_processor = AudioProcessor()
        self.document_processor = DocumentProcessor()

    async def process(
        self,
        data: bytes,
        filename: Optional[str],
        content_type: Optional[str],
        user_message: str = "",
    ) -> MediaResult:
        safe_filename, normalized_type, media_type = validate_upload(
            data=data,
            filename=filename,
            content_type=content_type,
        )

        logger.info(
            "VALE media: type=%s filename=%s bytes=%s",
            media_type.value,
            safe_filename,
            len(data),
        )

        if media_type == MediaType.IMAGE:
            return await self.image_processor.process(
                data, safe_filename, normalized_type, user_message
            )
        if media_type == MediaType.AUDIO:
            return await self.audio_processor.process(
                data, safe_filename, normalized_type, user_message
            )
        if media_type == MediaType.DOCUMENT:
            return await self.document_processor.process(
                data, safe_filename, normalized_type, user_message
            )

        raise MediaValidationError(
            "VALE could not determine how to process this media."
        )

    def supported_media(self) -> dict:
        return {
            "images": [
                "image/jpeg", "image/png", "image/webp"
            ],
            "audio": [
                "audio/webm", "audio/wav", "audio/x-wav",
                "audio/mpeg", "audio/mp3", "audio/mp4",
                "audio/ogg", "audio/aac",
            ],
            "documents": [
                "application/pdf",
                "text/plain",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ],
        }
