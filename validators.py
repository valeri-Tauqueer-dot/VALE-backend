from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from typing import Dict, Optional, Set

from .models import MediaError, MediaType


class MediaValidationError(MediaError):
    """Raised when an uploaded file is invalid or unsupported."""


@dataclass(frozen=True)
class MediaLimits:
    max_image_bytes: int
    max_audio_bytes: int
    max_document_bytes: int
    max_pdf_pages: int
    max_extracted_text_chars: int


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


DEFAULT_LIMITS = MediaLimits(
    max_image_bytes=_env_int("VALE_MAX_IMAGE_BYTES", 10 * 1024 * 1024),
    max_audio_bytes=_env_int("VALE_MAX_AUDIO_BYTES", 30 * 1024 * 1024),
    max_document_bytes=_env_int("VALE_MAX_DOCUMENT_BYTES", 30 * 1024 * 1024),
    max_pdf_pages=_env_int("VALE_MAX_PDF_PAGES", 200),
    max_extracted_text_chars=_env_int(
        "VALE_MAX_EXTRACTED_TEXT_CHARS", 1_000_000
    ),
)

IMAGE_TYPES: Set[str] = {"image/jpeg", "image/png", "image/webp"}
AUDIO_TYPES: Set[str] = {
    "audio/webm", "audio/wav", "audio/x-wav", "audio/mpeg",
    "audio/mp3", "audio/mp4", "audio/ogg", "audio/aac",
}
DOCUMENT_TYPES: Set[str] = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

EXTENSION_TO_CONTENT_TYPE: Dict[str, str] = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp",
    ".webm": "audio/webm", ".wav": "audio/wav", ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg", ".m4a": "audio/mp4", ".aac": "audio/aac",
    ".pdf": "application/pdf", ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def sanitize_filename(filename: Optional[str]) -> str:
    name = os.path.basename(filename or "").replace("\x00", "")
    name = re.sub(r"[^a-zA-Z0-9._()\- ]", "_", name).strip()
    return (name or "unnamed_file")[:255]


def normalize_content_type(
    content_type: Optional[str], filename: str
) -> str:
    if content_type:
        value = content_type.split(";", 1)[0].strip().lower()
        if value and value != "application/octet-stream":
            return value
    extension = os.path.splitext(filename.lower())[1]
    return EXTENSION_TO_CONTENT_TYPE.get(extension, "application/octet-stream")


def detect_media_type(content_type: str) -> MediaType:
    if content_type in IMAGE_TYPES or content_type.startswith("image/"):
        return MediaType.IMAGE
    if content_type in AUDIO_TYPES or content_type.startswith("audio/"):
        return MediaType.AUDIO
    if content_type in DOCUMENT_TYPES:
        return MediaType.DOCUMENT
    return MediaType.UNKNOWN


def get_max_size(media_type: MediaType, limits: MediaLimits = DEFAULT_LIMITS) -> int:
    if media_type == MediaType.IMAGE:
        return limits.max_image_bytes
    if media_type == MediaType.AUDIO:
        return limits.max_audio_bytes
    if media_type == MediaType.DOCUMENT:
        return limits.max_document_bytes
    return 0


def validate_upload(
    data: bytes,
    filename: Optional[str],
    content_type: Optional[str],
    limits: MediaLimits = DEFAULT_LIMITS,
):
    safe_filename = sanitize_filename(filename)
    normalized_type = normalize_content_type(content_type, safe_filename)
    media_type = detect_media_type(normalized_type)

    if media_type == MediaType.UNKNOWN:
        raise MediaValidationError(
            "Unsupported media type. Supported types: JPG, PNG, WEBP, "
            "WEBM, WAV, MP3, OGG, M4A, PDF, TXT and DOCX."
        )

    if not data:
        raise MediaValidationError("The uploaded file is empty.")

    max_size = get_max_size(media_type, limits)
    if len(data) > max_size:
        raise MediaValidationError(
            f"File is too large. Maximum size for {media_type.value} "
            f"is {max_size // (1024 * 1024)} MB."
        )

    return safe_filename, normalized_type, media_type


def validate_image_bytes(data: bytes) -> None:
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        raise MediaValidationError(
            "The uploaded image is corrupted or invalid."
        ) from exc
