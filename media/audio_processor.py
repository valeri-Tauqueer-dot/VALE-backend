from future import annotations

import asyncio
import os
import tempfile
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .models import (
MediaResult,
MediaType,
)

logger = logging.getLogger(name)

class AudioProcessor:
"""
VALE audio intelligence processor.

Responsibilities:
- Save incoming audio safely to a temporary file
- Transcribe speech
- Detect language when supported
- Return standardized VALE context

The actual speech engine is isolated so it can later be changed
without changing main.py or the rest of the brain architecture.
"""

def __init__(self) -> None:

    self.enable_transcription = (
        os.getenv(
            "VALE_ENABLE_AUDIO_TRANSCRIPTION",
            "false",
        )
        .lower()
        .strip()
        in {"1", "true", "yes", "on"}
    )

    self.engine = (
        os.getenv(
            "VALE_AUDIO_ENGINE",
            "none",
        )
        .lower()
        .strip()
    )

    self.max_transcript_chars = int(
        os.getenv(
            "VALE_MAX_TRANSCRIPT_CHARS",
            "100000",
        )
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
        media_type=MediaType.AUDIO,
        filename=filename,
        content_type=content_type,
    )

    suffix = Path(filename).suffix

    if not suffix:
        suffix = self._suffix_from_content_type(
            content_type
        )

    temporary_path: Optional[str] = None

    try:

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temporary_file:

            temporary_file.write(data)

            temporary_path = temporary_file.name

        result.metadata["size_bytes"] = len(
            data
        )

        if not self.enable_transcription:

            result.description = (
                "Audio file successfully received. "
                "Speech transcription is currently disabled."
            )

            result.add_warning(
                "Audio transcription engine is not enabled."
            )

            result.structured_data[
                "user_question"
            ] = user_message or None

            return result

        transcription = self._transcribe(
            temporary_path
        )

        transcript = (
            transcription.get("text", "")
            .strip()
        )

        if len(transcript) > self.max_transcript_chars:

            transcript = (
                transcript[
                    :self.max_transcript_chars
                ]
                + "\n[Transcript truncated]"
            )

        result.extracted_text = transcript

        result.description = (
            "Speech was transcribed from the uploaded audio."
            if transcript
            else
            "No speech transcript was produced."
        )

        result.structured_data.update(
            {
                "transcript": transcript,
                "language": transcription.get(
                    "language"
                ),
                "engine": self.engine,
                "user_question": (
                    user_message or None
                ),
            }
        )

        if not transcript:

            result.add_warning(
                "No recognizable speech was found in the audio."
            )

        return result

    except Exception as exc:

        logger.exception(
            "Audio processing failed."
        )

        result.add_error(
            f"Audio processing failed: {exc}"
        )

        return result

    finally:

        if temporary_path:

            try:
                os.remove(
                    temporary_path
                )

            except OSError:
                pass

def _suffix_from_content_type(
    self,
    content_type: str,
) -> str:

    mapping = {
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/ogg": ".ogg",
    }

    return mapping.get(
        content_type,
        ".audio",
    )

def _transcribe(
    self,
    audio_path: str,
) -> Dict[str, Any]:
    """
    Dispatch transcription to the configured speech engine.
    """

    if self.engine == "faster-whisper":

        return self._transcribe_faster_whisper(
            audio_path
        )

    raise RuntimeError(
        "No supported VALE audio engine is configured. "
        "Set VALE_AUDIO_ENGINE to a configured engine."
    )

def _transcribe_faster_whisper(
    self,
    audio_path: str,
) -> Dict[str, Any]:
    """
    Local speech recognition using faster-whisper.

    Requires:
        pip install faster-whisper

    The selected model can be controlled with:
        VALE_WHISPER_MODEL=small

    Smaller models need less RAM but are generally less accurate.
    """

    try:
        from faster_whisper import WhisperModel

    except ImportError as exc:

        raise RuntimeError(
            "faster-whisper is not installed."
        ) from exc

    model_name = os.getenv(
        "VALE_WHISPER_MODEL",
        "small",
    )

    device = os.getenv(
        "VALE_WHISPER_DEVICE",
        "cpu",
    )

    compute_type = os.getenv(
        "VALE_WHISPER_COMPUTE_TYPE",
        "int8",
    )

    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )

    segments, info = model.transcribe(
        audio_path,
        vad_filter=True,
    )

    text_parts = []

    for segment in segments:

        if segment.text:
            text_parts.append(
                segment.text.strip()
            )

    transcript = " ".join(
        text_parts
    ).strip()

    return {
        "text": transcript,
        "language": getattr(
            info,
            "language",
            None,
        ),
      }
