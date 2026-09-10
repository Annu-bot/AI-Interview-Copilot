# AI Interview Copilot — Technical Architecture & Troubleshooting Guide

This document records the technical architecture, design decisions, prompt engineering standards, and debugging post-mortems for future reference.

---

## 1. System Architecture Overview

The system is a FastAPI-powered technical interview preparation copilot structured around two core workflows:

```text
[Candidate Resume + Job Description]
               │
               ▼
   [Section-Aware Chunker]
               │
               ├──► [Embedding Client] (Gemini Cloud API or Local Ollama)
               │            │
               │            ▼
               └──► [ChromaDB Vector Store]
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
   [Skill Gap Analyzer]         [Answer Evaluator]
  (Grounded RAG Questions)    (Rubric Scoring & Model Answers)
```

1. **Document Ingestion & Section Chunking (`ai_apps/src/chunker.py`):** Splits candidate resumes and job descriptions into structured chunks (e.g. *Work Experience*, *Projects*, *Skills*, *Responsibilities*, *Requirements*).
2. **Dual-Engine Vector Embeddings (`ai_apps/src/embedding_client.py`):**
   - Cloud API (Default): Google Gemini Embeddings (`models/gemini-embedding-001`).
   - Local Mode (`LOCAL_EMBED=True`): Ollama endpoint (`nomic-embed-text` at `http://localhost:11434`) with an in-memory deterministic fallback.
3. **Vector Database (`ai_apps/src/vector_store.py`):** Persistent ChromaDB collection per interview session with cosine similarity search.
4. **RAG Context Grounding (`ai_apps/src/rag_service.py`):** Injects actual resume projects and JD requirements into LLM prompts.
5. **Structured Assessment Engine (`ai_apps/src/analyzer.py`, `ai_apps/src/evaluator.py`):** Generates gap-focused questions and scores typed/spoken responses against staff-level rubrics.

---

## 2. Troubleshooting & Error Post-Mortems

### Error #001: Gemini Embedding 404 (`models/text-embedding-004 not found for v1beta`)

#### Log Snippet:
```text
Cloud Gemini embedding failed (404 models/text-embedding-004 is not found for API version v1beta, or is not supported for embedContent. Call ModelService.ListModels to see the list of available models and their supported methods.), falling back to deterministic local embedding
```

#### Root Cause:
- When using the Google Gemini Python SDK (`google.generativeai`), calling `genai.embed_content()` against the `v1beta` API endpoint with model name `models/text-embedding-004` resulted in a 404 error because the model endpoint is registered under `models/gemini-embedding-001` or `models/gemini-embedding-2` in the active API environment.
- Although the system gracefully fell back to the local deterministic vector generator without breaking the user flow, the cloud embedding call logged repeated warnings.

#### Resolution:
1. **Identified Supported Models:** Queried `genai.list_models()` to inspect the exact endpoints supporting `embedContent`:
   - `models/gemini-embedding-001` (Active Production)
   - `models/gemini-embedding-2`
   - `models/gemini-embedding-2-preview`
2. **Updated Configuration:** Updated default `GEMINI_EMBEDDING_MODEL` in `config/settings.py` and environment templates to `models/gemini-embedding-001`.
3. **Multi-Model Auto Fallback:** Updated `EmbeddingClient._get_cloud_embedding` to iterate through candidate models (`["models/gemini-embedding-001", "models/gemini-embedding-2", "models/gemini-embedding-2-preview"]`) automatically before falling back to local vectors.

---

## 3. Answer Design: Concise & Verbal-Ready Benchmark Answers

### Problem:
Early versions produced long (400-500 word) textbook answers. While technically thorough, long monologues are:
- Unrealistic for real technical interviews (where candidates have 45-60 seconds to answer before the interviewer asks a follow-up).
- Difficult for users to memorize and recall under interview pressure.

### Solution:
Updated `SYSTEM_PROMPT_EVALUATION` and `ai_apps/src/evaluator.py` to enforce a strict **3-Part Verbal Framework (under 120 words)**:

1. **Direct Definition / Core Concept (1-2 sentences):** Immediately answer the core question with precision.
2. **Architectural Mechanics & Trade-offs (2-3 concise bullet points):** Explain how it works under the hood and key trade-offs (e.g. latency vs. memory, consistency vs. availability).
3. **Production Example / Metric (1 crisp sentence):** Reference a concrete production scenario, configuration flag, or metric.

#### Example Target Output:
> **Core Concept:** vLLM uses PagedAttention to eliminate memory fragmentation in GPU KV-caches by mapping logical tokens to non-contiguous physical memory blocks, similar to OS virtual memory.
>
> **Key Architecture & Trade-offs:**
> - **Zero Waste:** Standard HuggingFace pre-allocates for maximum context (wasting up to 60-80% VRAM); PagedAttention allocates dynamically on-demand in 16-token blocks.
> - **Continuous Batching:** Schedules tokens at the iteration level rather than request level, enabling 2-4x higher throughput under concurrent multi-user load.
>
> **Production Application:** Configured via `--gpu-memory-utilization 0.90` and `--max-model-len 8192` to maximize concurrency while preventing VRAM OOMs.

---

## 4. Configuration Reference

| Setting | Default | Description |
| :--- | :--- | :--- |
| `USE_OPEN_SOURCE` | `False` | `False` = Google Gemini Cloud API; `True` = Local Ollama LLM |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Cloud LLM model for analysis, questions, and evaluation |
| `LOCAL_EMBED` | `False` | `False` = Cloud Gemini embeddings; `True` = Local Ollama embeddings |
| `GEMINI_EMBEDDING_MODEL` | `models/gemini-embedding-001` | Cloud embedding model endpoint |
| `LOCAL_EMBEDDING_BASE_URL` | `http://localhost:11434` | Endpoint for local Ollama embedding service |
| `LOCAL_EMBEDDING_MODEL` | `nomic-embed-text` | Model name for local Ollama embeddings |
| `CHROMA_PERSIST_DIR` | `data/chroma` | Directory for persistent vector database storage |
