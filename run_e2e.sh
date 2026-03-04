#!/bin/bash
# E2E Test Run Script - Complete 4-step PageIndex workflow

set -e

echo "=========================================="
echo "PageIndex E2E Test Suite"
echo "=========================================="
echo ""

# Set environment
export LLM_PROVIDER="ollama"
export OLLAMA_MODEL="mistral24b-16k"
export OLLAMA_URL="http://localhost:11434"

echo "✓  Environment configured:"
echo "   - LLM_PROVIDER: $LLM_PROVIDER"
echo "   - OLLAMA_MODEL: $OLLAMA_MODEL"
echo "   - OLLAMA_URL: $OLLAMA_URL"
echo ""

# Check Ollama is running
echo "Checking Ollama status..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ Ollama is not running at $OLLAMA_URL"
    echo "   Start Ollama with: ollama serve"
    exit 1
fi
echo "✓  Ollama server is running"
echo ""

# Check model exists
echo "Checking mistral24b-16k model..."
if curl -s http://localhost:11434/api/tags | grep -q "mistral24b-16k"; then
    echo "✓  mistral24b-16k model found"
else
    echo "❌ mistral24b-16k model not found"
    echo "   Create it with: ollama create mistral24b-16k -f Modelfile-mistral24b-16k"
    exit 1
fi
echo ""

# Run tests
echo "=========================================="
echo "Running E2E Tests"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

if [ -f "run_e2e_tests.py" ]; then
    python3 run_e2e_tests.py
else
    echo "❌ run_e2e_tests.py not found"
    exit 1
fi

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "Results saved to: tests/reports/e2e_test_results.json"
