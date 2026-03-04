# Inference Revamp - Quick Start Guide

## Current Configuration (March 4, 2026)

### Model
- **Name**: `mistral24b-16k`
- **Base**: Mistral Small 24B (23.6B parameters)
- **Context Window**: 16,384 tokens (constrained for performance)
- **Max Generation**: 16,384 tokens
- **Temperature**: 0.2 (deterministic)

### Performance
- **VRAM Usage**: ~16.2 GB / 24 GB (RTX 4090)
- **Throughput**: 25-30 tokens/sec (estimated)
- **Timeout**: 30s connect, 600s read

## Getting Started

### 1. Set Environment Variables
```bash
source scripts/set_model_env.sh
```

This sets:
- `OLLAMA_MODEL=mistral24b-16k`
- `LLM_PROVIDER=ollama`

### 2. Verify Setup
```bash
ollama list
```

Should show:
- `mistral24b-16k:latest` (production model)
- `mistral-small:24b` (base model)

### 3. Test Integration
```bash
python3 -c "
from pageindex.utils import Ollama_API
response = Ollama_API(model='mistral24b-16k', prompt='Hello!')
print(f'Response: {response}')
"
```

### 4. Run PageIndex
```bash
python3 run_pageindex.py --pdf your_document.pdf
```

## Configuration Files

- **Production Model**: `/workspace/PageIndexOllama/Modelfile-mistral24b-16k`
- **Config**: `/workspace/PageIndexOllama/pageindex/config.yaml`
- **Storage**: `/workspace/.ollama` (symlinked from `/root/.ollama`)

## Monitoring

### Check GPU Usage
```bash
nvidia-smi
```

### Check Model Info
```bash
ollama show mistral24b-16k
```

### Check Ollama Server
```bash
curl http://localhost:11434/api/tags
```

## Troubleshooting

### If Ollama is not running
```bash
# Check process
ps aux | grep ollama

# Restart if needed
pkill ollama
nohup ollama serve > /tmp/ollama.log 2>&1 &
```

### If model not found
```bash
# Pull base model
ollama pull mistral-small:24b

# Rebuild production model
cd /workspace/PageIndexOllama
ollama create mistral24b-16k -f Modelfile-mistral24b-16k
```

### If timeouts occur
1. Check GPU is not overloaded: `nvidia-smi`
2. Verify model is loaded: `ollama list`
3. Check server logs: `tail /tmp/ollama.log`
4. Reduce context window in Modelfile (try 12k instead of 16k)

## Performance Tuning

### Reduce Context Window
Edit `Modelfile-mistral24b-16k`:
```
PARAMETER num_ctx 12288  # Reduce from 16384
```

Rebuild:
```bash
ollama create mistral24b-16k -f Modelfile-mistral24b-16k
```

### Increase Generation Limit
```
PARAMETER num_predict 1024  # Increase from 512
```

### Adjust Temperature
```
PARAMETER temperature 0.1   # More deterministic (from 0.2)
PARAMETER temperature 0.4   # More creative (from 0.2)
```

## What Changed

### From qwen2.5:14b to mistral24b-16k
- ✅ Better reasoning quality
- ✅ More stable (constrained context prevents timeouts)
- ✅ Controlled generation (512 token limit)
- ⚠️ Slightly slower per-token (expected for larger model)
- ⚠️ Slightly higher VRAM (+1.2 GB)

### Timeout Improvements
- Connect timeout: 10s → 30s
- Read timeout: 600s (unchanged, already generous)
- Model loading time included in first request

## Next Steps

1. **Run E2E Test Suite**: Validate with real PDFs
2. **Monitor Performance**: Track latency and timeout rates
3. **Optimize if Needed**: Reduce context window if performance issues persist
4. **Implement Chunking**: Don't feed full PDFs (see architectural recommendations)

## References

- Full revamp summary: `INFERENCE_REVAMP_SUMMARY.md`
- Model capabilities: `pageindex/model_capabilities.py`
- Prompt templates: `pageindex/prompts/*.txt`
