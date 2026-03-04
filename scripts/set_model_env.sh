#!/bin/bash
# Set environment variables for PageIndex Ollama inference
# Source this file before running PageIndex: source scripts/set_model_env.sh

export OLLAMA_MODEL="mistral24b-16k"
export LLM_PROVIDER="ollama"

echo "✅ Environment configured for PageIndex Ollama"
echo "   OLLAMA_MODEL: $OLLAMA_MODEL"
echo "   LLM_PROVIDER: $LLM_PROVIDER"
