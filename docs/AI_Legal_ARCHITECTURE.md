# ⚖️ AI Legal Assistant — ARCHITECTURE.md (v5)

This document is the **canonical architecture** for the **AI Legal Assistant** project.

It describes:
- the **current MVP scope** (document-level analysis),
- the **internal module boundaries** (Django bounded-context apps),
- the **data contracts** for findings + provenance,
- and the **planned phase extensions** (pgvector expansion, Elasticsearch search/indexing, Celery orchestration, Kubernetes deployment, etc.).

> **Status note (important):** The MVP currently returns **structured findings** from `POST /v1/review/run`.  
> **Findings persistence + retrieval** (Postgres system-of-record + pgvector) is tracked as **Step 7** in `docs/MVP_Checklist.md` and is **not yet completed**.

**Related docs**
- `README.md` (project overview)
- `docs/MVP_Checklist.md` (MVP build scope)
- `docs/POST_MVP_PLAN.md` (Post-MVP plan)
- `docs/AI_Legal_Assistant_Article_2025_10_29.md` (design rationale)

---

## 1. High-Level Design

### 1.1 Goal

Provide a modular architecture for **document-level legal analysis** that combines:

- **Deterministic, explainable rules** (baseline contract checks)
- **LLM-based analysis** (structured outputs with provenance + evidence)
- A clear path to **persistence, semantic retrieval, and search** without rewriting the core

### 1.2 Core principles

- **Explainable outputs:** Every finding includes evidence and a source (`rule` vs `llm`).
- **Auditable runs:** Each run records model/prompt metadata; findings are designed to be persisted (Step 7).
- **Modular apps:** Django apps are organized as bounded contexts under `apps/`.
- **Incremental sophistication:** Rules first → structured LLM analysis → persistence (Postgres) → semantic layer (pgvector) → search/indexing (Elasticsearch) → multi-document reasoning (cases/strategy).

### 1.3 Non-goals (MVP)

- End-to-end “legal advice”
- Fully automated negotiation / autonomous agents
- Full case management UI
- Large-scale multi-tenant SaaS hardening (RBAC, billing, enterprise audit logs)

---

## 2. Scope: Current MVP vs Planned Phases

### 2.1 MVP (current focus)

**Document-level only**

- `apps/documents`: ingestion and storage (PDF/text → extracted text)
- `apps/review`: clause extraction, rule engine, LLM analysis, response DTOs
- `apps/accounts`: optional auth boundary (SimpleJWT; can be minimal for demo)

**MVP flow (current):**

```
Document (text)
  → Clause Extraction
  → Rule Engine + LLM Analysis
  → Findings (structured JSON response)
```

### 2.2 MVP Step 7 (tracked work)

**Step 7 — Findings persistence + retrieval (Postgres + pgvector)**

- Persist findings as the **system-of-record** (Postgres)
- Store embeddings (pgvector) to support semantic similarity
- Add retrieval endpoint: `GET /v1/documents/{id}/findings`

### 2.3 Phase extensions (documented here; not MVP)

Planned bounded contexts (may be implemented as new apps or services):

- `apps/jobs`: async orchestration (Celery/Redis), idempotency, retries
- `apps/search`: Elasticsearch indexing + search endpoints (filters/facets/highlights)
- `apps/cases`: multi-document aggregation and issue grouping
- `apps/strategy`: recommendation and next-action generation
- `apps/explain`: deeper provenance, traceability, and inspection views
- `apps/metrics`: cost/latency metrics + evaluation harness

---

## 3. Repository Structure

**Source-of-truth convention:** Django apps live under `/apps`. The `/backend` package contains project wiring only.

```
ai-legal-assistant/
├── apps/
│   ├── accounts/        # Auth (JWT / SimpleJWT)
│   ├── documents/       # Document ingestion + storage
│   └── review/          # Clause extraction + rules + LLM analysis (+ DTOs)
├── backend/             # Django project wiring (settings/urls/asgi/wsgi)
├── docs/                # Architecture, MVP checklist, rationale, roadmap
├── infra/               # (phase) Terraform / Kubernetes manifests, etc.
└── scripts/             # (optional) fixtures, benchmarks, index rebuild, etc.
```

---

## 4. Component Model

### 4.1 Runtime components (MVP)

- **API layer (DRF)**
  - endpoints for upload + review run (and later retrieval)
  - request validation and auth boundary (optional for demo)

- **Document ingestion**
  - parse upload (PDF/text)
  - normalize extracted text and metadata

- **Clause extraction**
  - deterministic segmentation into clause candidates
  - outputs clause DTOs (heading/body, offsets)

- **Rule engine**
  - deterministic checks per clause (pattern/heuristics)
  - produces structured findings (`source = rule`)

- **LLM analysis**
  - prompt templates with explicit output schema
  - JSON-schema validation (reject/repair invalid outputs)
  - produces structured findings (`source = llm`) with provenance

### 4.2 Planned components (phase)

- **Findings persistence**
  - Postgres tables for documents, clauses (optional), findings, runs
  - upsert strategy (replace per document per run)

- **Semantic layer (pgvector)**
  - embeddings stored with findings (and/or clauses)
  - similarity search for “find similar findings/clauses”

- **Search index (Elasticsearch)**
  - derived index (rebuildable from Postgres)
  - full-text search + facets + highlights
  - result pointers back to Postgres record IDs

- **Async orchestration (Celery/Redis)**
  - job state model (queued/running/succeeded/failed)
  - idempotency keys
  - retry policy + dead-letter / failure introspection

- **Deployment (Kubernetes)**
  - API + worker deployments
  - managed Postgres recommended
  - optional Elasticsearch stack in-cluster or managed

---

## 5. Core Workflows

### 5.1 Ingest a document

1. Upload document (PDF/text)
2. Parse/normalize to extracted text
3. Store document record (and optionally raw upload reference)

**Outputs**
- `document_id`
- normalized `text`
- metadata (title, source, created_at)

### 5.2 Run a review (`POST /v1/review/run`)

1. Load document text
2. Clause extraction produces ordered clauses (with offsets)
3. Rule engine runs on clauses
4. LLM analysis runs on clauses and/or rule outputs
5. Aggregate findings into a single structured response

**Current behavior:** returns findings in the response payload.  
**Step 7 behavior:** also persists findings + run metadata.

### 5.3 Persist + retrieve findings (Step 7)

**Persist**
- `review_run` creates a `run` record and writes findings
- choose an upsert strategy:
  - “replace findings for document” (simple) **or**
  - “append per run” (auditable history)

**Retrieve**
- `GET /v1/documents/{id}/findings` returns:
  - findings ordered/grouped consistently
  - provenance fields included (source/model/prompt_rev/confidence)
  - evidence spans (offsets + excerpt text)

### 5.4 Build semantic similarity (pgvector)

- Store `embedding` on each finding (and/or clause)
- Provide query endpoint (phase) for:
  - “find similar findings”
  - “find similar clauses”

Guideline: Postgres remains the system of record; vectors are stored with the record.

### 5.5 Build cross-document search (Elasticsearch)

- Create an **index builder** job:
  - read documents/findings from Postgres
  - write derived docs to Elasticsearch
- Search endpoints return:
  - ES matches + highlights
  - record IDs for Postgres hydration
- Rebuild strategy:
  - full rebuild (simple) or incremental reindex by `updated_at`

Guideline: Elasticsearch is **derived**; loss is recoverable from Postgres.

---

## 6. Data Model (Canonical)

Below is a minimal canonical model. Implementation can evolve, but **auditability invariants** should not.

### 6.1 `documents`

- `id` (uuid)
- `title` (string, nullable)
- `text` (text)
- `source` (string, nullable)
- `created_at`

### 6.2 `review_runs` (Step 7+)

- `id` (uuid)
- `document_id` (fk)
- `requested_by` (fk, nullable)
- `started_at`, `completed_at`
- `status` (`succeeded|failed|partial`)
- `model` (string, nullable)
- `prompt_rev` (string, nullable)
- `token_usage` (json, nullable)
- `cost_usd` (numeric, nullable)

### 6.3 `findings` (canonical unit)

- `id` (uuid)
- `document_id` (fk)
- `run_id` (fk, nullable; required if storing per-run)
- `clause_id` (nullable; if clause table exists)
- `finding_type` (string)
- `severity` (`low|medium|high` or numeric score)
- `summary` (text)
- `recommendation` (text, nullable)
- `source` (`rule|llm`)
- `evidence` (json) — list of spans and excerpts
- `provenance` (json) — model, confidence, prompt_rev, etc.
- `created_at`

### 6.4 `clauses` (optional table)

You can persist clause segmentation to support reproducibility and indexing.

- `id` (uuid)
- `document_id` (fk)
- `ordinal` (int)
- `heading` (text, nullable)
- `body` (text)
- `start_offset`, `end_offset` (int)

### 6.5 Embeddings (pgvector, Step 7+)

Add to `findings` (initially):

- `embedding` (vector) — embedding for finding text (or clause text)
- `embedding_model` (string, nullable)
- `embedded_at`

---

## 7. Data Contracts (DTOs)

### 7.1 Document DTO

```json
{
  "id": "uuid",
  "title": "string",
  "text": "string",
  "created_at": "iso8601"
}
```

### 7.2 Clause DTO

```json
{
  "id": "string",
  "ordinal": 0,
  "heading": "string",
  "text": "string",
  "start": 0,
  "end": 0
}
```

### 7.3 Finding DTO (canonical)

```json
{
  "id": "uuid",
  "finding_type": "string",
  "severity": "low|medium|high",
  "source": "rule|llm",
  "summary": "string",
  "recommendation": "string",
  "evidence": [
    {
      "start": 123,
      "end": 456,
      "text": "excerpt..."
    }
  ],
  "provenance": {
    "model": "gpt-4o",
    "prompt_rev": "rev_2026_01_09",
    "confidence": 0.72
  }
}
```

**Invariant:** Findings must be explainable via evidence spans and must indicate whether they came from a rule or an LLM.

---

## 8. API Surface

### 8.1 MVP endpoints

- `POST /v1/documents/upload`
- `POST /v1/review/run`

### 8.2 Step 7 endpoint (planned)

- `GET /v1/documents/{id}/findings`

### 8.3 Phase endpoints (planned)

- Search:
  - `GET /v1/search?query=...&severity=...&type=...`
- Jobs:
  - `POST /v1/review/jobs` (create async run)
  - `GET /v1/jobs/{id}` (status)
- Cases/Strategy/Explain:
  - `/v1/cases/*`
  - `/v1/strategy/*`
  - `/v1/explain/*`

---

## 9. Security, Privacy, and Guardrails

### 9.1 Auth boundary

- Use JWT (SimpleJWT) for authenticated endpoints when needed.
- MVP can allow a “demo mode” boundary where auth is optional, but keep auth pluggable.

### 9.2 Data handling

- Treat uploaded documents as sensitive.
- Ensure:
  - request logging avoids raw document text
  - redaction hooks can be added (phase) before sending text to the LLM
  - retention policy can be implemented (phase)

### 9.3 LLM safety and determinism

- Enforce strict JSON output via schema validation.
- Prefer:
  - deterministic rule checks for crisp constraints
  - LLM outputs for interpretation, summarization, and redline suggestions
- Record provenance so outputs can be audited and reproduced.

---

## 10. Deployment & Infrastructure

### 10.1 Local development

- SQLite can be used for quick local dev.
- Postgres is the intended system-of-record and should be used for Step 7 onward.
- Docker is recommended for consistent environments.

### 10.2 CI/CD

- GitHub Actions for lint/test/build checks.
- Phase: add image builds and deployment workflows.

### 10.3 Kubernetes (phase)

A typical K8s layout:

- Deployment: `api`
- (Optional) Deployment: `worker` (Celery)
- Service: `api`
- Ingress: `api-ingress`
- External: managed Postgres (recommended)
- Optional: `elasticsearch` (+ Kibana) either in-cluster or managed

### 10.4 Terraform/AWS (phase)

- Terraform provisions:
  - networking, compute, secrets, managed DB (recommended)
  - optional managed search (or self-hosted ES) depending on constraints

---

## 11. Observability & Evaluation

### 11.1 MVP baseline

- structured logs to stdout
- request IDs / correlation IDs where available
- basic error handling with clear failure surfaces

### 11.2 Phase extensions

- Prometheus metrics:
  - request latency, error rate
  - token usage and cost per run
  - throughput and queue depth (jobs)
- Grafana dashboards
- OpenTelemetry tracing (optional)
- Evaluation harness:
  - deterministic rules: unit tests + fixture contracts
  - LLM analysis: golden sets + drift detection

---

## 12. Roadmap Extensions

These extensions are designed to be implemented as **additive layers** on top of the MVP.

### Phase A — Orchestration + indexing

- Async review runs (Celery + Redis) with persistent job state
- Elasticsearch indexing from Postgres (derived store)
- Search endpoints with filtering/faceting and highlight snippets

### Phase B — Contract families + composite versions

- Link base agreements + amendments into “families”
- Produce “composite” versions (timeline snapshots)
- Diff summaries with evidence + provenance

### Phase C — Deviation analysis (“buried risk”)

- Normalize clause fields (e.g., termination notice, liability cap, governing law)
- Compare against baseline clause profiles per contract type
- Flag buried or non-standard risks with explainable evidence

---

## Appendix A — Glossary

- **Finding:** A structured, evidence-linked output (risk, issue, suggestion).
- **Provenance:** Metadata about how a finding was generated (model, prompt, confidence, source).
- **Derived store:** A secondary system (Elasticsearch) that can be rebuilt from the system-of-record.
- **System-of-record:** Postgres tables that represent canonical truth for documents/findings.

---

*Last updated: January 9, 2026*
