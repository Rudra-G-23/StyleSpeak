# Model Configuration

The reliability baseline uses deterministic regex and vocabulary parsing for color, garment type, price, gender, and ordinal references. It does not need a language model.

Cached local assets discovered during audit are `all-MiniLM-L6-v2` and `faster-whisper-tiny.en`. The backend contains a lazy CPU int8 faster-whisper adapter. It loads only when `/api/voice/transcribe` receives audio and returns a clear 422 response if unavailable.

Semantic MiniLM retrieval is intentionally not enabled in this release. The module seam is retained, but the validated local demo uses FTS5 and token relevance to keep startup memory small. Precompute MiniLM vectors offline before enabling a vector adapter for the full catalog.
