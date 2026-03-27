#!/bin/bash

# Test Ollama functionality from Docker environment
# This script tests basic connectivity and model availability

set -e

OLLAMA_URL=${OLLAMA_URL:-"http://ollama:11434"}
OLLAMA_MODEL=${OLLAMA_MODEL:-"llama3.2:1b"}

echo "🔍 Testing Ollama at: $OLLAMA_URL"
echo "🤖 Testing model: $OLLAMA_MODEL"
echo "----------------------------------------"

# Test 1: Check if Ollama is running
echo "1. Testing Ollama service health..."
if docker-compose exec ollama ollama --version > /dev/null 2>&1; then
    echo "✅ Ollama service is running"
else
    echo "❌ Ollama service is not running"
    exit 1
fi

# Test 2: List available models
echo ""
echo "2. Listing available models..."
echo "Available models:"
docker-compose exec ollama ollama list

# Test 3: Check if target model exists
echo ""
echo "3. Checking if target model '$OLLAMA_MODEL' is available..."
if docker-compose exec ollama ollama list | grep -q "$OLLAMA_MODEL"; then
    echo "✅ Model '$OLLAMA_MODEL' is available"
else
    echo "❌ Model '$OLLAMA_MODEL' is not available"
    echo "💡 To pull the model, run:"
    echo "   docker-compose exec ollama ollama pull $OLLAMA_MODEL"
    exit 1
fi

# Test 4: Test model with simple prompt
echo ""
echo "4. Testing model with simple prompt..."
echo "   Attempting to run model (this may take a moment)..."
if timeout 60s docker-compose exec ollama ollama run "$OLLAMA_MODEL" "Hello" 2>&1; then
    echo "✅ Model responds to prompts"
else
    echo "❌ Model failed to respond"
    echo "🔍 Checking Ollama service status..."
    docker-compose exec ollama ps aux | head -5
    echo ""
    echo "🔍 Memory usage:"
    docker-compose exec ollama free -h
    echo ""
    echo "💡 This could be due to:"
    echo "   - Insufficient memory/CPU resources"
    echo "   - Model loading timeout"
    echo "   - Ollama service issues"
    echo ""
    echo "🔧 Try these solutions:"
    echo "   1. Increase Docker memory allocation"
    echo "   2. Use a smaller model: docker-compose exec ollama ollama pull llama3.2:1b"
    echo "   3. Restart Ollama: docker-compose restart ollama"
    exit 1
fi

echo ""
echo "🎉 All tests passed! Ollama is working correctly."
echo ""
echo "📋 Summary:"
echo "  - Service: Running"
echo "  - Model: Available ($OLLAMA_MODEL)"
echo "  - Response: Working"
echo ""
echo "🔧 To test API endpoints, run:"
echo "   docker-compose exec app python test_ollama.py"