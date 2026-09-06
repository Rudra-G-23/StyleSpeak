"""Local speech-to-text with faster-whisper (tiny.en, int8, CPU).

The browser records the audio (``st.audio_input``) and hands us WAV bytes, so
there is no microphone / PortAudio / ALSA dependency inside WSL. The model is
loaded once and reused across Streamlit reruns.
"""

from __future__ import annotations

import io
from functools import lru_cache

from src.config import WHISPER_COMPUTE_TYPE, WHISPER_MODEL


class TranscriptionError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise TranscriptionError("faster-whisper is not installed.") from exc
    # Downloads tiny.en (~75 MB) into the HF cache on first call, then offline.
    return WhisperModel(WHISPER_MODEL, device="cpu", compute_type=WHISPER_COMPUTE_TYPE)


def transcribe(audio_bytes: bytes) -> str:
    """Return the recognised English text for a WAV recording."""
    if not audio_bytes:
        raise TranscriptionError("Empty recording - nothing to transcribe.")
    try:
        segments, _info = _model().transcribe(
            io.BytesIO(audio_bytes),
            language="en",
            vad_filter=True,
            beam_size=1,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
    except TranscriptionError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface any decode/model failure cleanly
        raise TranscriptionError(f"Could not transcribe the recording: {exc}") from exc
    if not text:
        raise TranscriptionError("Didn't catch any speech - try again a bit louder.")
    return text


def warm_up() -> None:
    """Trigger the one-time model load (and download) ahead of first use."""
    _model()
