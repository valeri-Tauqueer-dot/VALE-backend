from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .models import MediaResult, MediaType

logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    Deployment-safe audio processor.

    Upload/validation never requires a speech model. Transcription is optional
    and activated only when VALE_ENABLE_AUDIO_TRANSCRIPTION=true and a supported
    engine is installed.
    """

    def __init__(self) -> None:
        self.enable_transcription = os.getenv(
            "VALE_ENABLE_AUDIO_TRANSCRIPTION", "false"
        ).lower() in {"1", "true", "yes", "on"}
        self.engine = os.getenv("VALE_AUDIO_ENGINE", "none").lower().strip()
        self.max_transcript_chars = max(
            1, int(os.getenv("VALE_MAX_TRANSCRIPT_CHARS", "100000"))
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
        result = MediaResult(
            media_type=MediaType.AUDIO,
            filename=filename,
            content_type=content_type,
        )
        result.metadata["size_bytes"] = len(data)
        result.metadata["extension"] = Path(filename).suffix.lower() or "unknown"

        # Do not write audio to permanent storage. Temporary storage is cleaned
        # immediately after optional processing.
        temporary_path: Optional[str] = None
        try:
            suffix = Path(filename).suffix or self._suffix_from_content_type(
                content_type
            )
            with tempfile.NamedTemporaryFile(
                suffix=suffix, prefix="vale_audio_", delete=False
            ) as tmp:
                tmp.write(data)
                temporary_path = tmp.name

            if not self.enable_transcription:
                result.description = (
                    "Audio file successfully received and validated. "
                    "Speech transcription is disabled for this deployment."
                )
                result.add_warning(
                    "Set VALE_ENABLE_AUDIO_TRANSCRIPTION=true and configure "
                    "a speech engine to enable transcription."
                )
            else:
                transcription = self._transcribe(temporary_path)
                transcript = str(transcription.get("text", "") or "").strip()
                if len(transcript) > self.max_transcript_chars:
                    transcript = (
                        transcript[: self.max_transcript_chars]
                        + "\n[Transcript truncated]"
                    )
                result.extracted_text = transcript
                result.structured_data.update(
                    {
                        "transcript": transcript,
                        "language": transcription.get("language"),
                        "engine": self.engine,
                    }
                )
                result.description = (
                    "Speech was transcribed successfully."
                    if transcript
                    else "Audio was processed but no recognizable speech was found."
                )
                if not transcript:
                    result.add_warning("No recognizable speech was found.")

            result.structured_data["user_question"] = user_message or None
            return result

        except Exception as exc:
            logger.exception("Audio processing failed")
            result.add_error(f"Audio processing failed: {exc}")
            return result
        finally:
            if temporary_path:
                try:
                    os.remove(temporary_path)
                except OSError:
                    pass

    @staticmethod
    def _suffix_from_content_type(content_type: str) -> str:
        return {
            "audio/webm": ".webm",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/mp4": ".m4a",
            "audio/ogg": ".ogg",
            "audio/aac": ".aac",
        }.get(content_type, ".audio")

    def _transcribe(self, audio_path: str) -> Dict[str, Any]:
        if self.engine == "faster-whisper":
            return self._transcribe_faster_whisper(audio_path)
        raise RuntimeError(
            "No supported audio engine is configured. "
            "Use VALE_AUDIO_ENGINE=faster-whisper and install faster-whisper."
        )

    def _transcribe_faster_whisper(self, audio_path: str) -> Dict[str, Any]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed. Audio upload still works "
                "with transcription disabled."
            ) from exc

        model_name = os.getenv("VALE_WHISPER_MODEL", "small")
        device = os.getenv("VALE_WHISPER_DEVICE", "cpu")
        compute_type = os.getenv("VALE_WHISPER_COMPUTE_TYPE", "int8")

        model = WhisperModel(
            model_name, device=device, compute_type=compute_type
        )
        segments, info = model.transcribe(audio_path, vad_filter=True)
        text = " ".join(
            segment.text.strip() for segment in segments if segment.text
        ).strip()
        return {
            "text": text,
            "language": getattr(info, "language", None),
        }
