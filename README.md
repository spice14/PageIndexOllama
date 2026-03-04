# 🌲 PageIndex-Ollama: Local-First Tree RAG for Long Documents

**PageIndex-Ollama** is an independent fork of PageIndex focused on **fully local document indexing and reasoning** with **Ollama**.

You point it to a PDF (or Markdown), it builds a **hierarchical tree index**, and then uses LLM reasoning over that tree to retrieve relevant sections.

Run it on your own machine with **no API keys** and no required external inference service.

---

## ✨ Why This Fork Exists

The upstream project is broad. This fork is opinionated:

- local-first workflows
- Ollama as the default inference backend
- minimal cloud assumptions in setup and usage docs
- engineer-focused, reproducible CLI + test flow

This repo keeps the core PageIndex retrieval design while making local execution the default operating mode.

---

## 🔍 What’s Different From Upstream PageIndex

- OpenAI SDK is not part of the documented local workflow for this fork.
- Ollama is the default backend used in setup and examples.
- Provider abstraction is retained so model-call logic stays isolated from pipeline logic.
- Offline-capable after model download.
- No external API dependency required for normal local operation.

---

## 🧠 How It Works (Architecture)

PageIndex-Ollama keeps the same core pattern:

1. Build a structured tree from a document
2. Run LLM-guided search over that tree
3. Generate answers from selected node context

Key implementation points:

- `pageindex/page_index.py` contains the PDF pipeline (`page_index_main`) and tree construction flow.
- `pageindex/page_index_md.py` provides the Markdown path (`md_to_tree`).
- `pageindex/utils.py` contains model-call wrappers (`Ollama_API_with_finish_reason`, `Ollama_API`, `Ollama_API_async`) and env-driven provider/model resolution.
- `pageindex/response_handlers.py` normalizes response shape (including finish reason handling) to keep downstream logic stable.
- `pageindex/continuation.py` handles truncated outputs by generating continuation prompts and stitching responses.
- Prompt templates are loaded through `pageindex/prompt_loader.py` and `pageindex/prompts/`.

Runtime controls:

- `LLM_PROVIDER=ollama`
- `OLLAMA_URL=http://localhost:11434`
- `OLLAMA_MODEL=mistral24b-16k` (or any installed Ollama model)

---

## 🤖 Supported Models

Any Ollama-compatible model can be used, including:

- mistral
- llama
- qwen
- other locally available Ollama models

Default examples in this repo use `mistral24b-16k`.

Model quality and speed depend on:

- model family + parameter size
- quantization
- context length
- local CPU/GPU/VRAM

---

## 🚀 Quick Start (Local Only)

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Install Ollama

Use one of the repo scripts if helpful:

```bash
# Linux/macOS
bash scripts/setup_ollama.sh

# Windows PowerShell
powershell scripts/setup_ollama.ps1
```

### 3) Pull a model

```bash
ollama pull mistral24b-16k
```

If that tag is unavailable on your machine, use any installed Ollama model and set `OLLAMA_MODEL` accordingly.

### 4) Set environment variables

```bash
# Linux/macOS
export LLM_PROVIDER=ollama
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=mistral24b-16k

# Windows PowerShell
$env:LLM_PROVIDER="ollama"
$env:OLLAMA_URL="http://localhost:11434"
$env:OLLAMA_MODEL="mistral24b-16k"
```

### 5) Run the CLI

PDF:

```bash
python cli.py --pdf_path /path/to/document.pdf --model mistral24b-16k
```

Markdown:

```bash
python cli.py --md_path /path/to/document.md --model mistral24b-16k
```

Outputs are written to `results/*_structure.json`.

---

## 🧪 Testing

Main test surfaces:

- `run_comprehensive_e2e_tests.py`
- `tests/e2e/`
- `tests/`

Run:

```bash
python run_comprehensive_e2e_tests.py
python -m pytest tests
```

What these validate (end-to-end):

- tree generation
- tree availability/structure checks
- LLM-driven node selection over tree content
- answer generation from extracted node context

This fork’s validation flow is intended to run locally with Ollama configured as active provider.

---

## ⚠️ Known Limitations

- Local model choice matters a lot; small models can struggle on deep reasoning.
- ~3B class models are usually weaker than larger frontier-class systems on complex document QA.
- Very large PDFs can pressure RAM/VRAM depending on model/context settings.
- Inference throughput and latency are hardware-dependent.
- Some scripts in the repo assume specific local paths/shell conventions and may need environment-specific adjustment.

---

## 🗂️ Project Layout

```text
PageIndexOllama/
├── cli.py
├── run_comprehensive_e2e_tests.py
├── pageindex/
│   ├── page_index.py
│   ├── page_index_md.py
│   ├── utils.py
│   ├── response_handlers.py
│   ├── continuation.py
│   ├── prompt_loader.py
│   └── prompts/
├── scripts/
│   ├── setup_ollama.sh
│   └── setup_ollama.ps1
├── tests/
│   ├── e2e/
│   ├── pdfs/
│   └── results/
└── requirements.txt
```

---

## 🔗 Relationship to Official PageIndex

This repository is an **independent fork**.

- Upstream: https://github.com/VectifyAI/PageIndex
- This fork is maintained separately and focuses on local Ollama-based operation.
- No official affiliation or endorsement is implied unless explicitly authorized by upstream maintainers.
- For upstream cloud-hosted offerings, refer to upstream documentation.

---

## 📄 License

This repository preserves the existing project license.
See [LICENSE](LICENSE).
