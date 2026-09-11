# AI Interview Copilot — Technical Architecture & Troubleshooting Guide

This document records the technical architecture, design decisions, prompt engineering standards, ChromaDB deep-dive, and debugging post-mortems for future reference.

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
               │                         │
               ▼                         ▼
   [Web Speech TTS Engine]      [Web Speech STT Engine]
   (AI Speaks with Waveform)    (Candidate Dictates Voice)
```

1. **Document Ingestion & Section Chunking (`ai_apps/src/chunker.py`):** Splits candidate resumes and job descriptions into structured chunks (e.g. *Work Experience*, *Projects*, *Skills*, *Responsibilities*, *Requirements*).
2. **Dual-Engine Vector Embeddings (`ai_apps/src/embedding_client.py`):**
   - Cloud API (Default): Google Gemini Embeddings (`models/gemini-embedding-001`).
   - Local Mode (`LOCAL_EMBED=True`): Ollama endpoint (`nomic-embed-text` at `http://localhost:11434`) with an in-memory deterministic fallback.
3. **Vector Database (`ai_apps/src/vector_store.py`):** Persistent ChromaDB collection per interview session with cosine similarity search.
4. **RAG Context Grounding (`ai_apps/src/rag_service.py`):** Injects actual resume projects and JD requirements into LLM prompts.
5. **Structured Assessment Engine (`ai_apps/src/analyzer.py`, `ai_apps/src/evaluator.py`):** Generates gap-focused questions and scores typed/spoken responses against staff-level rubrics.
6. **Voice Synthesis & Recognition (`static/app.js`):** Web Speech API for bi-directional spoken interactions.

---

## 2. ChromaDB Deep-Dive: What It Is & How It Works

### 1. What is ChromaDB?
- ChromaDB is an open-source, embedded (in-process) **Vector Database**.
- Just like SQLite is an embedded relational database (no need to run a separate SQL server), ChromaDB runs directly inside your Python application process.
- Installed via:
  ```bash
  pip install chromadb numpy
  ```

### 2. Why ChromaDB instead of standard SQL?
- Traditional SQL databases search text by **exact keyword matching** (`WHERE text LIKE '%Kafka%'`).
- If a candidate writes *"Asynchronous message streaming with RabbitMQ"* and the JD requires *"Event-Driven Distributed Architecture"*, SQL returns **zero matches**.
- ChromaDB stores text as **high-dimensional numerical vectors (embeddings)** that capture semantic meaning.
- It performs Approximate Nearest Neighbor (ANN) search via **Cosine Similarity** to retrieve passages with matching *meaning*, regardless of specific phrasing.

### 3. How ChromaDB Works in Code (`ai_apps/src/vector_store.py`):

1. **Initialize Persistent Client:**
   ```python
   client = chromadb.PersistentClient(path="data/chroma")
   ```
2. **Create Session Collection:**
   ```python
   collection = client.create_collection(name=f"session_{session_id}")
   ```
3. **Index Chunks & Embeddings:**
   ```python
   collection.add(
       ids=["chunk_1", "chunk_2"],
       documents=["[Experience] Built Redis caching...", "[Projects] Kafka pipeline..."],
       embeddings=[[0.012, -0.045, ...], ...],
       metadatas=[{"source": "resume", "section": "Experience"}, ...]
   )
   ```
4. **Query (Semantic Retrieval):**
   ```python
   results = collection.query(
       query_embeddings=[query_vector],
       n_results=3,
       where={"source": "resume"}
   )
   ```

---

## 3. V3 Voice Interviewer Architecture (TTS + STT + 10-Stage Loop)

### 1. Real-Time Conversational Voice Features:
- **Web Speech Synthesis (TTS):** The AI interviewer speaks questions aloud with natural pacing, spoken transitions (`spoken_intro`), and a live audio waveform visualizer.
- **Web Speech Recognition (STT):** Candidates can dictate their responses verbally in real-time.
- **Auto-Speak Control:** Toggleable auto-play on question load.

### 2. 10-Stage Real-Life Interview Progression:
1. **Stage 1: Warm-up & Professional Background Introduction (Question 1)** — Welcomes the candidate, sets expectations, and asks for a career summary and recent architectural highlight.
2. **Stage 2: Resume Project Deep-Dive & Claim Verification (Questions 2 - 4)** — Inquires into specific tools and frameworks claimed on the candidate's resume (e.g. FastAPI concurrency, Redis cache invalidation).
3. **Stage 3: Skill Gap Deep-Dive & Core JD Competencies (Questions 5 - 7)** — Tests missing or weak competencies identified from the Job Description (e.g. Kafka partition rebalancing, Kubernetes auto-scaling).
4. **Stage 4: High-Scale System Design & Architectural Trade-offs (Questions 8 - 9)** — Scenarios handling high throughput (100k QPS, data partitioning, consistency vs availability).
5. **Stage 5: Behavioral, Outages & Engineering Culture Wrap-up (Question 10)** — Production outage post-mortems, handling technical disagreements, and candidate wrap-up.

---

## 4. Troubleshooting & Error Post-Mortems

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
   - `models/gemini-embedding-001` (Active Production - 3072 dims)
   - `models/gemini-embedding-2`
   - `models/gemini-embedding-2-preview`
2. **Updated Configuration:** Updated default `GEMINI_EMBEDDING_MODEL` in `config/settings.py` and environment templates to `models/gemini-embedding-001`.
3. **Multi-Model Auto Fallback:** Updated `EmbeddingClient._get_cloud_embedding` to iterate through candidate models (`["models/gemini-embedding-001", "models/gemini-embedding-2", "models/gemini-embedding-2-preview"]`) automatically before falling back to local vectors.

---

## 5. Answer Design: Concise & Verbal-Ready Benchmark Answers

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

## 6. Configuration Reference

| Setting | Default | Description |
| :--- | :--- | :--- |
| `USE_OPEN_SOURCE` | `False` | `False` = Google Gemini Cloud API; `True` = Local Ollama LLM |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Cloud LLM model for analysis, questions, and evaluation |
| `LOCAL_EMBED` | `False` | `False` = Cloud Gemini embeddings; `True` = Local Ollama embeddings |
| `GEMINI_EMBEDDING_MODEL` | `models/gemini-embedding-001` | Cloud embedding model endpoint |
| `LOCAL_EMBEDDING_BASE_URL` | `http://localhost:11434` | Endpoint for local Ollama embedding service |
| `LOCAL_EMBEDDING_MODEL` | `nomic-embed-text` | Model name for local Ollama embeddings |
| `CHROMA_PERSIST_DIR` | `data/chroma` | Directory for persistent vector database storage |
