from future import annotations

import asyncio
import io
import os
import logging
from typing import Dict, List

from .models import (
MediaResult,
MediaType,
)
from .validators import (
DEFAULT_LIMITS,
MediaValidationError,
)

logger = logging.getLogger(name)

class DocumentProcessor:
"""
VALE document intelligence processor.

Supports:
- PDF
- TXT
- DOCX
"""

def __init__(self) -> None:

    self.max_pages = DEFAULT_LIMITS.max_pdf_pages

    self.max_text_chars = (
        DEFAULT_LIMITS.max_extracted_text_chars
    )

async def process(
    self,
    data: bytes,
    filename: str,
    content_type: str,
    user_message: str = "",
) -> MediaResult:

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

    result = MediaResult(
        media_type=MediaType.DOCUMENT,
        filename=filename,
        content_type=content_type,
    )

    try:

        if content_type == "application/pdf":

            text, metadata = (
                self._process_pdf(data)
            )

        elif content_type == "text/plain":

            text, metadata = (
                self._process_text(data)
            )

        elif (
            content_type
            == "application/"
            "vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):

            text, metadata = (
                self._process_docx(data)
            )

        else:

            raise MediaValidationError(
                f"Unsupported document type: "
                f"{content_type}"
            )

        text = self._limit_text(
            text,
            result,
        )

        result.extracted_text = text

        result.metadata.update(
            metadata
        )

        result.structured_data.update(
            {
                "characters_extracted": len(
                    text
                ),
                "user_question": (
                    user_message or None
                ),
            }
        )

        result.description = (
            "Document content was extracted successfully."
        )

        if not text.strip():

            result.add_warning(
                "No readable text was extracted from "
                "the document."
            )

        return result

    except Exception as exc:

        logger.exception(
            "Document processing failed."
        )

        result.add_error(
            f"Document processing failed: {exc}"
        )

        return result

def _process_pdf(
    self,
    data: bytes,
) -> tuple[str, Dict]:

    try:
        import pypdf

    except ImportError as exc:

        raise RuntimeError(
            "pypdf is not installed."
        ) from exc

    reader = pypdf.PdfReader(
        io.BytesIO(data)
    )

    if reader.is_encrypted:

        raise MediaValidationError(
            "Password-protected PDFs are not currently supported."
        )

    page_count = len(
        reader.pages
    )

    if page_count > self.max_pages:

        raise MediaValidationError(
            f"PDF has {page_count} pages. "
            f"Maximum allowed is {self.max_pages}."
        )

    pages: List[str] = []

    for index, page in enumerate(
        reader.pages,
        start=1,
    ):

        try:

            page_text = (
                page.extract_text()
                or ""
            )

            if page_text:

                pages.append(
                    f"\n\n--- PAGE {index} ---\n"
                    f"{page_text}"
                )

        except Exception as exc:

            logger.warning(
                "Could not extract PDF page %s: %s",
                index,
                exc,
            )

    metadata = {
        "page_count": page_count,
        "document_format": "pdf",
    }

    return (
        "".join(pages).strip(),
        metadata,
    )

def _process_text(
    self,
    data: bytes,
) -> tuple[str, Dict]:

    try:

        text = data.decode(
            "utf-8"
        )

    except UnicodeDecodeError:

        text = data.decode(
            "utf-8",
            errors="replace",
        )

    return (
        text,
        {
            "document_format": "text",
        },
    )

def _process_docx(
    self,
    data: bytes,
) -> tuple[str, Dict]:

    try:
        from docx import Document

    except ImportError as exc:

        raise RuntimeError(
            "python-docx is not installed."
        ) from exc

    document = Document(
        io.BytesIO(data)
    )

    parts: List[str] = []

    for paragraph in document.paragraphs:

        text = paragraph.text.strip()

        if text:

            parts.append(text)

    # Extract table text as well.
    for table in document.tables:

        parts.append(
            "\n--- TABLE ---"
        )

        for row in table.rows:

            cells = [
                cell.text.strip()
                for cell in row.cells
            ]

            parts.append(
                " | ".join(cells)
            )

    return (
        "\n".join(parts),
        {
            "document_format": "docx",
            "paragraph_count": len(
                document.paragraphs
            ),
            "table_count": len(
                document.tables
            ),
        },
    )

def _limit_text(
    self,
    text: str,
    result: MediaResult,
) -> str:

    if len(text) <= self.max_text_chars:

        return text

    result.add_warning(
        "Document text exceeded the configured maximum "
        "and was truncated."
    )

    return (
        text[:self.max_text_chars]
        + "\n\n[Document text truncated.]"
            )
