"""Configuration and secrets loading for StyleSpeak.

The Hugging Face token is read exclusively from the ``HF_TOKEN`` environment
variable (populated from a local ``.env`` file for development). The token is
never hardcoded and never committed - ``.env`` is git-ignored and only
``.env.example`` is tracked.

Everything the voice assistant needs (Ollama endpoint, model names, Whisper
size, demo-catalog paths) is centralised here and overridable via environment
variables, so nothing downstream hardcodes a model or an absolute path.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load .env from the project root regardless of the current working directory.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

# --------------------------------------------------------------------------- #
# Voice shopping assistant
# --------------------------------------------------------------------------- #
# Local Ollama server. No API key, no cloud - see README "Assistant setup".
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# Small instruct model used purely as a structured intent parser. Chosen over
# qwen3:1.7b because qwen2.5-instruct has no "thinking" mode to suppress and is
# a strong JSON follower at ~1 GB on disk / ~2 GB resident.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b-instruct-q4_K_M")
# 46 MB MiniLM-L6-v2 served by the same Ollama runtime (no extra torch stack).
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "all-minilm")
# Generous because the first call also loads ~1 GB of weights into RAM on a
# cold CPU machine; warm calls are ~5-15 s.
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "150"))
# Keep the model resident between turns so only the first request pays load cost.
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "15m")

# faster-whisper size. tiny.en is English-only, ~75 MB, int8 on CPU.
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny.en")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

DEMO_CATALOG_PATH = Path(
    os.getenv("DEMO_CATALOG_PATH", str(PROJECT_ROOT / "data" / "products" / "catalog_demo.json"))
)
DEMO_EMBEDDINGS_PATH = Path(
    os.getenv(
        "DEMO_EMBEDDINGS_PATH",
        str(PROJECT_ROOT / "data" / "products" / "catalog_demo_embeddings.npy"),
    )
)

_MISSING_TOKEN_MESSAGE = (
    "HF_TOKEN is not set.\n"
    "Copy .env.example to .env and add your Hugging Face token:\n"
    "    cp .env.example .env\n"
    "    # then edit .env and set HF_TOKEN=hf_xxx\n"
    "Create a token at https://huggingface.co/settings/tokens"
)


def get_hf_token() -> str:
    """Return the Hugging Face token or raise a clear error if it is missing."""
    token = os.getenv("HF_TOKEN")
    if not token or not token.strip():
        raise RuntimeError(_MISSING_TOKEN_MESSAGE)
    return token.strip()
