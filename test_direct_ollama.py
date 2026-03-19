#!/usr/bin/env python3
"""Direct test of Ollama API from within the app container."""
import asyncio
import httpx
import json

async def test_ollama():
    url = "http://ollama:11434/api/generate"
    payload = {
        "model": "llama3.2:1b",
        "prompt": "Say hello in one word",
        "stream": False,
        "format": "json"
    }
    
    print(f"Testing Ollama at: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            print("Sending request...")
            resp = await client.post(url, json=payload)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"\nGenerated response: {data.get('response', 'NO RESPONSE')}")
                return True
            else:
                print(f"Error: {resp.status_code}")
                return False
                
    except Exception as e:
        print(f"Exception: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_ollama())
    print(f"\nTest {'PASSED' if result else 'FAILED'}")
