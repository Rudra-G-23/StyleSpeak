"""Optional lazy local transcription adapter."""

from __future__ import annotations

import io
from functools import lru_cache

from .config import get_settings


class TranscriptionUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscriptionUnavailable("Local speech recognition is not installed.") from exc
    return WhisperModel(get_settings().whisper_model, device="cpu", compute_type="int8")


def transcribe(audio: bytes) -> str:
    if not audio:
        raise ValueError("No audio was uploaded.")
    try:
        segments, _ = _model().transcribe(
            io.BytesIO(audio), language="en", beam_size=1, vad_filter=True
        )
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
    except TranscriptionUnavailable:
        raise
    except Exception as exc:
        raise TranscriptionUnavailable("The audio could not be transcribed locally.") from exc
    if not transcript:
        raise TranscriptionUnavailable("No speech was detected. Please try again.")
    return transcript
