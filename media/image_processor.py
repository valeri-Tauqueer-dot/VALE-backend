from __future__ import annotations

import asyncio
import io
import logging
import os
from typing import Any, Dict, Optional

from .models import MediaResult, MediaType
from .validators import validate_image_bytes

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Lightweight image processor with optional OCR/vision hooks."""

    def __init__(self) -> None:
        self.enable_ocr = os.getenv("VALE_ENABLE_OCR", "true").lower() in {
            "1", "true", "yes", "on"
        }
        self.enable_vision = os.getenv("VALE_ENABLE_VISION", "false").lower() in {
            "1", "true", "yes", "on"
        }
        self.max_ocr_chars = max(
            1, int(os.getenv("VALE_MAX_OCR_CHARS", "50000"))
        )

    async def process(
        self, data: bytes, filename: str, content_type: str, user_message: str = ""
    ) -> MediaResult:
        return await asyncio.to_thread(
            self._process_sync, data, filename, content_type, user_message
        )

    def _process_sync(
        self, data: bytes, filename: str, content_type: str, user_message: str
    ) -> MediaResult:
        validate_image_bytes(data)
        result = MediaResult(
            media_type=MediaType.IMAGE,
            filename=filename,
            content_type=content_type,
        )

        try:
            from PIL import Image, ImageOps

            with Image.open(io.BytesIO(data)) as image:
                image = ImageOps.exif_transpose(image)
                result.metadata.update(
                    {
                        "width": image.width,
                        "height": image.height,
                        "format": image.format,
                        "mode": image.mode,
                    }
                )
        except Exception as exc:
            result.add_error(f"Image metadata processing failed: {exc}")
            return result

        if self.enable_ocr:
            try:
                text = self._extract_ocr(data)
                result.structured_data["ocr_detected"] = bool(text)
                if text:
                    result.extracted_text = text
            except Exception as exc:
                logger.warning("OCR unavailable: %s", exc)
                result.add_warning(
                    "OCR was unavailable. Install/configure Tesseract to enable it."
                )

        if self.enable_vision:
            try:
                vision = self._analyze_with_vision_model(data, user_message)
                if vision:
                    result.description = str(vision.get("description", "") or "")
                    structured = vision.get("structured_data")
                    if isinstance(structured, dict):
                        result.structured_data.update(structured)
            except Exception as exc:
                logger.warning("Vision analysis unavailable: %s", exc)
                result.add_warning(
                    "Advanced visual scene understanding is not configured."
                )

        if not result.description:
            result.description = (
                f"Image successfully received and validated. "
                f"Resolution: {result.metadata.get('width', '?')} × "
                f"{result.metadata.get('height', '?')}."
            )
            if result.extracted_text:
                result.description += " Visible text was extracted with OCR."

        result.structured_data["user_question"] = user_message or None
        return result

    def _extract_ocr(self, data: bytes) -> str:
        from PIL import Image, ImageOps
        import pytesseract

        with Image.open(io.BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            text = pytesseract.image_to_string(image).strip()
        return text[: self.max_ocr_chars]

    def _analyze_with_vision_model(
        self, data: bytes, user_message: str
    ) -> Optional[Dict[str, Any]]:
        raise RuntimeError("No VALE vision engine is configured.")
