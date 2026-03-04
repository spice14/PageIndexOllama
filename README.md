# 🌲 PageIndexOllama: Local-First Tree RAG for Long Documents

**PageIndex-Ollama** is an independent fork of PageIndex focused on **fully local document indexing and reasoning** with **Ollama**.

You point it to a PDF (or Markdown), it builds a **hierarchical tree index**, and then uses LLM reasoning over that tree to retrieve relevant sections.

Run it on your own machine with **no API keys** and no required external inference service.

Detailed technical delta report: [ENHANCEMENTS_REPORT.md](ENHANCEMENTS_REPORT.md)

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

### Enhancement Highlights in This Fork

- **Runtime decoupling:** provider-routed wrappers replace OpenAI-tied call assumptions.
- **Response contract stability:** finish-reason and response-shape normalization reduce provider-specific branching downstream.
- **Prompt governance:** registry + loader architecture replaces large inline prompts and improves reproducibility.
- **Performance:** bounded async parallelism accelerates TOC/summarization stages for local inference.
- **Robustness:** adaptive chunking and hierarchical fallbacks reduce failure rates on difficult PDFs.
- **Validation:** expanded e2e/integration/performance coverage validates local-first behavior end-to-end.

### Upstream vs Fork (Practical Delta)

| Area | Upstream | Fork | Decoupling Value |
|---|---|---|---|
| Provider API wrappers | OpenAI-branded wrappers | Provider-routed `Ollama_API*` wrappers | High |
| Finish reason semantics | Provider-specific assumptions | Normalized response handler | High |
| Credentials/env handling | More distributed | Centralized provider-aware module | Medium-High |
| Prompt management | Inline prompt strings | Registry + loader + prompt files | High (operational) |
| TOC/summary processing | More sequential | Async bounded concurrency | Medium-High |
| Fallback behavior | Simpler/no hardening in some paths | Hierarchical/adaptive fallback paths | Medium |
| CLI defaults | OpenAI model default | Local model default path | High (UX/ops) |
| Test coverage | Minimal Python tests | Expanded e2e/integration/perf checks | High (risk reduction) |
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
- `pageindex/credentials.py` centralizes provider-specific credential/environment resolution.
- `pageindex/models.py` defines typed schemas for structured outputs and parsing stability.
- `pageindex/chunking_config.py` provides adaptive chunking strategy used for large-document handling.
- Prompt templates are loaded through `pageindex/prompt_loader.py` and `pageindex/prompts/`.

### Provider-Decoupling Design

This fork keeps provider-specific behavior at the runtime boundary:

1. Resolve provider/model from environment and config.
2. Dispatch to provider-specific call path.
3. Normalize output/finish reason into a stable internal shape.
4. Continue tree/search/answer logic with provider-agnostic contracts.

This keeps indexing and retrieval flows isolated from vendor-specific response differences.

This design allows the same indexing/search pipeline to operate across providers with minimal call-site change.

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
- `test_parallel_processing.py`

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
- provider-decoupled response handling (including continuation behavior)
- concurrency paths used for local throughput improvements

This fork’s validation flow is intended to run locally with Ollama configured as active provider.

---

## ⚙️ Performance and Reliability Enhancements

- **Parallel TOC/summarization paths:** async + semaphore-limited execution improves wall-clock performance.
- **Prompt externalization:** prompts are versionable artifacts rather than embedded strings.
- **Structured-output hardening:** JSON extraction/sanitization paths reduce breakage on imperfect model output.
- **Continuation control:** truncated generations are recovered through continuation prompts.
- **No-TOC resiliency:** fallback flows preserve output generation when canonical TOC extraction is weak.

### Why These Enhancements Matter Locally

Local-first systems face two practical constraints: variable model quality and slower inference throughput.
These enhancements directly target those constraints by improving deterministic behavior under imperfect outputs
and reducing total latency through bounded parallelism.

---

## 📌 Current Standardization Gaps

The core architecture is stable, but a few consistency items remain:

- Canonical default model should be unified across CLI, config, docs, and tests.
- Tree-search output key naming should be standardized (`node_ids` vs `relevant_node_ids`).
- Some legacy naming/constants should be aligned with current model/provider behavior.

These are consistency and maintenance concerns, not blockers for local-first operation.

For full technical analysis, see [ENHANCEMENTS_REPORT.md](ENHANCEMENTS_REPORT.md).

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
│   ├── credentials.py
│   ├── models.py
│   ├── chunking_config.py
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

- Upstream: [VectifyAI/PageIndex](https://github.com/VectifyAI/PageIndex)
- This fork is maintained separately and focuses on local Ollama-based operation.
- No official affiliation or endorsement is implied unless explicitly authorized by upstream maintainers.
- For upstream cloud-hosted offerings, refer to upstream documentation.

This fork’s change direction can be summarized as:

**provider decoupling + local-first operationalization + reliability/performance hardening**.

---

## 📄 License

See [LICENSE](LICENSE).

