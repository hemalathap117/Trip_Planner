import httpx
import json
import logging
from config import settings

logger = logging.getLogger(__name__)

async def call_ollama(messages: list, temperature: float = 1.0) -> str:
    """Call Ollama API to generate LLM response."""
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
        "format": "json"  # enforce JSON mode
    }
    
    try:
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
            resp = await client.post(settings.OLLAMA_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
    except httpx.RequestError as e:
        logger.error(f"Request error calling Ollama: {e}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling Ollama: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling Ollama: {e}")
        raise