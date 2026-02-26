## 1. AI Legal Assistant
[https://github.com/markiskorova/ai-legal-assistant](https://github.com/markiskorova/ai-legal-assistant)

- **Tech Stack (implemented):** Python (Django 5 + DRF), PostgreSQL 16 (Docker Compose) / SQLite (local dev), Celery + Redis, OpenAI API (strict JSON-schema validated outputs + embeddings), pgvector bootstrap for Postgres findings vectors, React 18 + TypeScript (Vite), Docker Compose  
- **Tech Stack (planned / Phase 3+):** Elasticsearch search/indexing, Terraform/AWS hardening, Kubernetes deployment patterns, Prometheus/Grafana
- **Methods / Keywords:** Context & prompt engineering; structured outputs with JSON Schema validation; hybrid rules+LLM analysis; evidence spans + provenance/traceability; async orchestration; idempotency; concurrency/rate controls; run instrumentation; embedding persistence + vector-ready storage

- **Purpose:** Modular, transparent, and extensible platform demonstrating how LLMs *augment* (not replace) document-level legal analysis with explainable, auditable outputs.

- **Key Features (implemented):**
  - Multi-format document ingestion (`.txt`, `.pdf`, `.csv`, `.xlsx`) with normalized text + ingestion metadata
  - Hybrid review pipeline combining deterministic rule checks and schema-constrained LLM analysis
  - Always-async review execution (`POST /v1/review/run` returns `run_id`) with persisted run lifecycle states (`queued`, `running`, `succeeded`, `failed`, `partial`)
  - Idempotency-key support, concurrency caps, and request rate limits for review execution
  - Persisted review artifacts (`review_runs`, `findings`, `review_chunks`) with stable `chunk_id` provenance
  - Structured findings with severity, evidence/evidence spans, source attribution (`rule` vs `llm`), and provenance fields (model, confidence, prompt revision)
  - Partial-result policy: deterministic findings persist even when LLM stage fails/timeouts (`partial` run state)
  - Run-level instrumentation (`token_usage`, `stage_timings`, cache hit/miss fields) for pipeline visibility and debugging
  - Findings retrieval supports pagination/sorting controls (`page`, `page_size`, `ordering`) and run scoping (`run_id`)
  - Findings include optional recommendations and persisted embeddings
  - pgvector bootstrap migration for Postgres (`vector` extension + vector column/index) plus embedding backfill command support
  - Minimal React + TypeScript UI for upload, review run initiation, status checking, and findings review
  - Versioned API endpoints for upload, async run enqueueing, run status, and findings retrieval

- **Architecture / Evolution Path (planned):**
  - `apps/search` for Elasticsearch-backed indexing and search APIs
  - Expanded semantic retrieval use-cases on top of existing pgvector foundation (for example similarity APIs and cross-entity vector search)
  - `apps/cases`, `apps/strategy`, and `apps/explain` for multi-document reasoning, recommendations, and richer provenance inspection
  - Expanded observability/evaluation tooling (e.g., dashboards, tracing, regression/eval harness)

- **Value:** Proof-of-work for explainable legal-tech workflows that demonstrates how to engineer transparency, reliability, and auditability into AI-assisted review using persisted runs, provenance-linked findings, async pipeline controls, and production-minded workflow semantics.

### Resume bullets (implemented-only)
- Multi-format document ingestion (`.txt`, `.pdf`, `.csv`, `.xlsx`) with normalized text + ingestion metadata
