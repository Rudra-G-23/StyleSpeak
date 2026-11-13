"""Configuration and secrets loading for StyleSpeak.

The Hugging Face token is read exclusively from the ``HF_TOKEN`` environment
variable (populated from a local ``.env`` file for development). The token is
never hardcoded and never committed - ``.env`` is git-ignored and only
``.env.example`` is tracked.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load .env from the project root regardless of the current working directory.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

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
