import httpx
import json
import logging
from config import settings

logger = logging.getLogger(__name__)

async def call_ollama(messages: list, temperature: float = 1.0) -> str:
    """Call Ollama API to generate LLM response using the /api/generate endpoint."""
    
    # Ensure we have the base URL without any endpoints
    base_url = settings.OLLAMA_URL.rstrip('/').replace('/api/chat', '').replace('/api/generate', '')
    
    # Convert messages to a single prompt for Ollama's generate endpoint
    prompt = ""
    for msg in messages:
        if msg["role"] == "system":
            prompt += f"System: {msg['content']}\n\n"
        elif msg["role"] == "user":
            prompt += f"User: {msg['content']}\n\n"
        elif msg["role"] == "assistant":
            prompt += f"Assistant: {msg['content']}\n\n"
    
    prompt += "Assistant: "
    
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature}
        # Note: "format": "json" removed - small models struggle with strict JSON mode
    }
    
    try:
        url = f"{base_url}/api/generate"
        logger.info(f"Calling Ollama at: {url}")
        logger.info(f"Using model: {settings.OLLAMA_MODEL}")
        
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            response_text = data.get("response", "")
            logger.info(f"Ollama response received: {len(response_text)} characters")
            
            return response_text
            
    except httpx.RequestError as e:
        error_msg = f"Request error calling Ollama generate: {type(e).__name__} - {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg) from e
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error calling Ollama generate: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        raise Exception(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error calling Ollama generate: {type(e).__name__} - {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg) from e