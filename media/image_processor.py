from future import annotations

import asyncio
import io
import logging
import os
from typing import Any, Dict, Optional

from .models import (
MediaResult,
MediaType,
ProcessingStatus,
)
from .validators import validate_image_bytes

logger = logging.getLogger(name)

class ImageProcessor:
"""
VALE image intelligence processor.

Current capabilities:
- Safe image validation
- Metadata extraction
- OCR using Tesseract when installed
- Pluggable vision-language model support

The vision model is intentionally isolated in this class so the
rest of the VALE architecture does not depend on one AI provider.
"""

def __init__(self) -> None:
    self.enable_ocr = (
        os.getenv("VALE_ENABLE_OCR", "true")
        .lower()
        .strip()
        in {"1", "true", "yes", "on"}
    )

    self.enable_vision = (
        os.getenv("VALE_ENABLE_VISION", "false")
        .lower()
        .strip()
        in {"1", "true", "yes", "on"}
    )

    self.max_ocr_chars = int(
        os.getenv(
            "VALE_MAX_OCR_CHARS",
            "50000",
        )
    )

async def process(
    self,
    data: bytes,
    filename: str,
    content_type: str,
    user_message: str = "",
) -> MediaResult:
    """
    Process an uploaded image.
    """

    return await asyncio.to_thread(
        self._process_sync,
        data,
        filename,
        content_type,
        user_message,
    )

def _process_sync(
    self,
    data: bytes,
    filename: str,
    content_type: str,
    user_message: str,
) -> MediaResult:

    validate_image_bytes(data)

    result = MediaResult(
        media_type=MediaType.IMAGE,
        filename=filename,
        content_type=content_type,
    )

    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as image:

            result.metadata.update(
                {
                    "width": image.width,
                    "height": image.height,
                    "format": image.format,
                    "mode": image.mode,
                }
            )

    except Exception as exc:
        result.add_error(
            f"Image metadata processing failed: {exc}"
        )

        return result

    # OCR
    if self.enable_ocr:

        try:
            extracted_text = self._extract_ocr(
                data,
            )

            if extracted_text:
                result.extracted_text = extracted_text

                result.structured_data[
                    "ocr_detected"
                ] = True

            else:
                result.structured_data[
                    "ocr_detected"
                ] = False

        except Exception as exc:
            logger.warning(
                "OCR processing failed: %s",
                exc,
            )

            result.add_warning(
                "OCR text extraction was unavailable "
                "or failed."
            )

    # Optional vision-language understanding.
    if self.enable_vision:

        try:
            vision_data = self._analyze_with_vision_model(
                data=data,
                user_message=user_message,
            )

            if vision_data:

                description = vision_data.get(
                    "description",
                    "",
                )

                if description:
                    result.description = description

                structured = vision_data.get(
                    "structured_data",
                    {},
                )

                if structured:
                    result.structured_data.update(
                        structured
                    )

        except Exception as exc:
            logger.exception(
                "Vision analysis failed."
            )

            result.add_warning(
                f"Vision analysis failed: {exc}"
            )

    # Create useful fallback description.
    if not result.description:

        width = result.metadata.get(
            "width",
            "unknown",
        )

        height = result.metadata.get(
            "height",
            "unknown",
        )

        description_parts = [
            "Image successfully processed.",
            f"Resolution: {width} × {height}.",
        ]

        if result.extracted_text:
            description_parts.append(
                "Visible text was detected and extracted."
            )

        if not self.enable_vision:
            description_parts.append(
                "Full visual scene understanding is not yet "
                "enabled because VALE_ENABLE_VISION is disabled."
            )

        result.description = " ".join(
            description_parts
        )

    result.structured_data[
        "user_question"
    ] = user_message or None

    return result

def _extract_ocr(
    self,
    data: bytes,
) -> str:
    """
    Extract text using pytesseract.

    Requires the Tesseract executable to be installed on the
    operating system.
    """

    try:
        from PIL import Image, ImageOps
        import pytesseract

    except ImportError as exc:
        raise RuntimeError(
            "OCR dependencies are not installed."
        ) from exc

    with Image.open(
        io.BytesIO(data)
    ) as image:

        image = image.convert("RGB")

        # Simple normalization improves screenshot OCR.
        image = ImageOps.exif_transpose(
            image
        )

        text = pytesseract.image_to_string(
            image
        )

    text = text.strip()

    if len(text) > self.max_ocr_chars:

        text = (
            text[:self.max_ocr_chars]
            + "\n[OCR output truncated]"
        )

    return text

def _analyze_with_vision_model(
    self,
    data: bytes,
    user_message: str,
) -> Optional[Dict[str, Any]]:
    """
    Advanced vision model integration point.

    IMPORTANT:
    This method deliberately does not pretend that Python can
    understand an image by itself.

    Connect a real vision-language model here. For example:
    - a locally hosted open-source vision model
    - a self-hosted inference server
    - another vision backend controlled by your infrastructure

    The rest of VALE will not need to change because every engine
    must return:

    {
        "description": "...",
        "structured_data": {...}
    }
    """

    # Placeholder for the configured VALE vision backend.
    #
    # Do NOT fake an image description here.
    #
    # A real implementation should send `data` to the selected
    # vision-language model and return genuine model output.

    raise RuntimeError(
        "No VALE vision engine is configured. "
        "Set up a real vision-language model integration before "
        "enabling VALE_ENABLE_VISION."
                  )
