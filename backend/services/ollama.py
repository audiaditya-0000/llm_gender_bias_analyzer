"""
Ollama REST API integration service.
Communicates with the local Ollama server at http://localhost:11434.
"""

import httpx
from typing import Any, Optional

OLLAMA_BASE_URL = "http://localhost:11434"


async def generate(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_tokens: int = 512,
    seed: Optional[int] = None,
) -> str:
    """
    Generate a response from an Ollama model using the /api/chat endpoint.
    Returns the assistant's message content as a string.
    """
    options: dict[str, Any] = {
        "temperature": temperature,
        "top_p": top_p,
        "num_predict": max_tokens,
    }
    if seed is not None:
        options["seed"] = seed

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": options,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")


async def list_models() -> list[dict[str, Any]]:
    """
    Fetch the list of locally available models from Ollama.
    Returns a list of model info dicts.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
        response.raise_for_status()
        data = response.json()
        return data.get("models", [])


async def check_health() -> bool:
    """Check if the Ollama server is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(OLLAMA_BASE_URL)
            return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False
