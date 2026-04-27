from __future__ import annotations

import os
from collections.abc import Generator

import ollama

# Phi-3 default; can be overridden via OLLAMA_MODEL in .env
MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def _client():
    """
    Prefer an explicit client so BASE_URL is respected even if OLLAMA_HOST
    isn't set in the environment.
    """
    client_cls = getattr(ollama, "Client", None)
    if client_cls is None:
        return None
    return client_cls(host=BASE_URL)


def chat_completion(system_prompt: str, messages: list[dict]) -> str:
    """Synchronous chat call via Ollama."""
    client = _client()
    fn = client.chat if client is not None else ollama.chat
    response = fn(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt}] + messages,
    )
    return response["message"]["content"]


def stream_completion(system_prompt: str, messages: list[dict]) -> Generator[str, None, None]:
    """Generator for token streaming (content chunks)."""
    client = _client()
    fn = client.chat if client is not None else ollama.chat
    stream = fn(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        stream=True,
    )
    for chunk in stream:
        msg = chunk.get("message") or {}
        content = msg.get("content")
        if content:
            yield content


def ping() -> bool:
    """Return True if Ollama is reachable."""
    try:
        client = _client()
        fn = client.list if client is not None else getattr(ollama, "list", None)
        if fn is None:
            return False
        fn()
        return True
    except Exception:
        return False

