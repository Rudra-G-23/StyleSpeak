"""Thin synchronous client for the local Ollama server.

Two calls only: ``chat_json`` (structured intent parsing) and ``embed_texts``
(MiniLM vectors for semantic search). Everything is local HTTP to
``OLLAMA_HOST``; there is no API key and no fallback to any cloud service.
"""

from __future__ import annotations

import json

import httpx

from src.config import (
    OLLAMA_EMBED_MODEL,
    OLLAMA_HOST,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
)


class OllamaError(RuntimeError):
    """Raised when the local model server is unreachable or misbehaves."""


def _post(path: str, payload: dict) -> dict:
    url = f"{OLLAMA_HOST.rstrip('/')}{path}"
    try:
        response = httpx.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError as exc:
        raise OllamaError(
            f"Cannot reach Ollama at {OLLAMA_HOST}. Start it with `ollama serve` "
            "(or `systemctl start ollama`)."
        ) from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()
        if exc.response.status_code == 404 and "model" in detail.lower():
            raise OllamaError(
                f"Model not found. Pull it once with `ollama pull {OLLAMA_MODEL}`."
            ) from exc
        raise OllamaError(f"Ollama HTTP {exc.response.status_code}: {detail}") from exc
    except httpx.HTTPError as exc:
        raise OllamaError(f"Ollama request failed: {exc}") from exc


def chat_json(
    system: str,
    user: str,
    *,
    model: str | None = None,
    num_predict: int = 300,
    num_ctx: int = 2048,
) -> dict:
    """Run one chat turn constrained to JSON output and parse the result.

    ``format="json"`` makes Ollama grammar-constrain the decode, so the payload
    is always syntactically valid JSON; callers still validate the *shape*.
    """
    data = _post(
        "/api/chat",
        {
            "model": model or OLLAMA_MODEL,
            "format": "json",
            "stream": False,
            "keep_alive": OLLAMA_KEEP_ALIVE,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {
                "temperature": 0,
                "top_p": 0.9,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
            },
        },
    )
    content = (data.get("message") or {}).get("content", "").strip()
    if not content:
        raise OllamaError("Ollama returned an empty response.")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise OllamaError(f"Model did not return JSON: {content[:200]!r}") from exc


def embed_texts(texts: list[str], *, model: str | None = None) -> list[list[float]]:
    """Return one embedding vector per input string."""
    if not texts:
        return []
    data = _post(
        "/api/embed",
        {"model": model or OLLAMA_EMBED_MODEL, "input": texts, "keep_alive": OLLAMA_KEEP_ALIVE},
    )
    vectors = data.get("embeddings")
    if not vectors or len(vectors) != len(texts):
        raise OllamaError("Ollama returned no embeddings.")
    return vectors


def health() -> tuple[bool, str]:
    """``(ok, message)`` - used by the UI to show a clear offline banner."""
    try:
        response = httpx.get(f"{OLLAMA_HOST.rstrip('/')}/api/tags", timeout=5)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return False, f"Ollama not reachable at {OLLAMA_HOST} ({exc.__class__.__name__})."
    names = {m.get("name", "") for m in response.json().get("models", [])}
    missing = [
        name
        for name in (OLLAMA_MODEL, OLLAMA_EMBED_MODEL)
        if name not in names and f"{name}:latest" not in names
    ]
    if missing:
        return False, "Missing Ollama model(s): " + ", ".join(
            f"`ollama pull {name}`" for name in missing
        )
    return True, "Ollama ready."
