#!/usr/bin/env python3
"""
Script to test Ollama model functionality from Docker environment.
This script tests both API endpoints and model availability.
"""

import asyncio
import httpx
import json
import sys
import os
from typing import Dict, Any

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
TIMEOUT = 30

def print_status(message: str, status: str = "INFO"):
    """Print formatted status message."""
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m", 
        "ERROR": "\033[91m",
        "WARNING": "\033[93m"
    }
    reset = "\033[0m"
    print(f"{colors.get(status, '')}{status}: {message}{reset}")

async def test_ollama_health() -> bool:
    """Test if Ollama service is running."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                print_status("Ollama service is running", "SUCCESS")
                return True
            else:
                print_status(f"Ollama health check failed: {response.status_code}", "ERROR")
                return False
    except Exception as e:
        print_status(f"Failed to connect to Ollama: {e}", "ERROR")
        return False

async def list_models() -> Dict[str, Any]:
    """List available models in Ollama."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print_status(f"Found {len(models)} models:", "INFO")
                for model in models:
                    print(f"  - {model.get('name', 'Unknown')} ({model.get('size', 'Unknown size')})")
                return data
            else:
                print_status(f"Failed to list models: {response.status_code}", "ERROR")
                return {}
    except Exception as e:
        print_status(f"Error listing models: {e}", "ERROR")
        return {}

async def test_chat_endpoint() -> bool:
    """Test the /api/chat endpoint."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello in JSON format with a 'message' field."}
        ],
        "stream": False,
        "format": "json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            if response.status_code == 200:
                data = response.json()
                print_status("Chat endpoint working", "SUCCESS")
                print(f"Response: {data.get('message', {}).get('content', 'No content')}")
                return True
            elif response.status_code == 404:
                print_status("Chat endpoint not available (404)", "WARNING")
                return False
            else:
                print_status(f"Chat endpoint failed: {response.status_code} - {response.text}", "ERROR")
                return False
    except Exception as e:
        print_status(f"Chat endpoint error: {e}", "ERROR")
        return False

async def test_generate_endpoint() -> bool:
    """Test the /api/chat endpoint."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": "System: You are a helpful assistant.\n\nUser: Say hello in JSON format with a 'message' field.\n\nAssistant: ",
        "stream": False,
        "format": "json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            if response.status_code == 200:
                data = response.json()
                print_status("Generate endpoint working", "SUCCESS")
                print(f"Response: {data.get('response', 'No response')}")
                return True
            else:
                print_status(f"Generate endpoint failed: {response.status_code} - {response.text}", "ERROR")
                return False
    except Exception as e:
        print_status(f"Generate endpoint error: {e}", "ERROR")
        return False

async def test_model_specific() -> bool:
    """Test if the specific model is available and working."""
    models_data = await list_models()
    models = models_data.get("models", [])
    
    # Check if our model is in the list
    model_found = False
    for model in models:
        if model.get("name") == OLLAMA_MODEL:
            model_found = True
            break
    
    if not model_found:
        print_status(f"Model '{OLLAMA_MODEL}' not found in available models", "ERROR")
        print_status("Available models:", "INFO")
        for model in models:
            print(f"  - {model.get('name', 'Unknown')}")
        return False
    else:
        print_status(f"Model '{OLLAMA_MODEL}' is available", "SUCCESS")
        return True

async def main():
    """Run all tests."""
    print_status("Starting Ollama tests...", "INFO")
    print_status(f"Testing Ollama at: {OLLAMA_URL}", "INFO")
    print_status(f"Testing model: {OLLAMA_MODEL}", "INFO")
    print("-" * 50)
    
    # Test 1: Health check
    print_status("1. Testing Ollama service health...", "INFO")
    health_ok = await test_ollama_health()
    if not health_ok:
        print_status("Ollama service is not accessible. Exiting.", "ERROR")
        sys.exit(1)
    
    # Test 2: List models
    print_status("2. Listing available models...", "INFO")
    await list_models()
    
    # Test 3: Check specific model
    print_status("3. Checking if target model is available...", "INFO")
    model_ok = await test_model_specific()
    if not model_ok:
        print_status("Target model is not available. You may need to pull it.", "WARNING")
        print_status(f"Run: docker-compose exec ollama ollama pull {OLLAMA_MODEL}", "INFO")
    
    # Test 4: Test chat endpoint
    print_status("4. Testing chat endpoint...", "INFO")
    chat_ok = await test_chat_endpoint()
    
    # Test 5: Test generate endpoint
    print_status("5. Testing generate endpoint...", "INFO")
    generate_ok = await test_generate_endpoint()
    
    # Summary
    print("-" * 50)
    print_status("Test Summary:", "INFO")
    print(f"  Health Check: {'✓' if health_ok else '✗'}")
    print(f"  Model Available: {'✓' if model_ok else '✗'}")
    print(f"  Chat Endpoint: {'✓' if chat_ok else '✗'}")
    print(f"  Generate Endpoint: {'✓' if generate_ok else '✗'}")
    
    if health_ok and model_ok and (chat_ok or generate_ok):
        print_status("Ollama is working correctly!", "SUCCESS")
        return 0
    else:
        print_status("Some tests failed. Check the issues above.", "ERROR")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)