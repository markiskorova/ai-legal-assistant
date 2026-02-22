# AI Legal Assistant - ARCHITECTURE.md (v6)

This document is the canonical architecture for the AI Legal Assistant project.

It describes:
- the current implemented scope (MVP + Phase 2),
- the module boundaries in Django apps,
- the core data contracts for runs, chunks, and findings,
- and the planned Phase 3+ extensions.

> Status note: MVP and Phase 2 are complete.
> `POST /v1/review/run` is async (enqueue + `run_id`) with persisted run status, chunk artifacts, idempotency, and run instrumentation.

Related docs:
- `README.md`
- `docs/MVP_Checklist.md`
- `docs/PHASE_2_Checklist.md`
- `docs/POST_MVP_PLAN.md`
- `docs/AI_Legal_Assistant_Article_2025_10_29.md`

---

## 1. High-Level Design

### 1.1 Goal

Provide a modular architecture for document-level legal analysis that combines:
- deterministic, explainable checks,
- schema-constrained LLM analysis,
- auditable persistence and retrieval,
- and a clear path to search/indexing and multi-document reasoning.

### 1.2 Core principles

- Explainable outputs: each finding links to evidence and source (`rule` or `llm`).
- Auditable runs: each run stores lifecycle, metadata, and persisted outputs.
- Modular boundaries: Django apps grouped by bounded context under `apps/`.
- Incremental complexity: ingestion and review first, then search and corpus-level features.

### 1.3 Non-goals (current)

- Autonomous legal agents.
- End-to-end legal advice.
- Full enterprise SaaS hardening (RBAC, billing, compliance workflows).

---

## 2. Scope: Current Baseline vs Planned Phases

### 2.1 Current baseline (MVP + Phase 2)

Document-level analysis with async processing:
- `apps/documents`: upload + ingestion (`.txt`, `.pdf`, `.csv`, `.xlsx`).
- `apps/review`: enqueue path, worker pipeline, status, chunk artifacts, findings persistence/retrieval.
- `apps/accounts`: optional auth boundary.

Current flow:

```text
Upload document
  -> normalized text + ingestion metadata
  -> POST /v1/review/run (enqueue, return run_id)
  -> worker: preprocess chunks -> rules -> llm -> persist
  -> GET /v1/review-runs/{id} and GET /v1/documents/{id}/findings
```

### 2.2 Completed milestones

- MVP Step 7:
  - persisted `review_runs` + `findings`,
  - findings retrieval endpoint by document (optionally by run).
- Phase 2:
  - async execution (Celery + Redis),
  - idempotency key behavior and retry-safe persistence,
  - persisted `review_chunks` with stable `chunk_id`,
  - spreadsheet ingestion into canonical metadata and chunk windows,
  - run-level instrumentation (`token_usage`, `stage_timings`, cache metrics),
  - concurrency and request rate controls.

### 2.3 Planned scope (Phase 3+)

- `apps/search`: Elasticsearch indexing and search APIs.
- `apps/cases`: multi-document family/grouping workflows.
- `apps/strategy`: recommendation and next-action generation.
- `apps/explain`: richer trace/provenance inspection surfaces.
- `apps/metrics`: dashboards, corpus eval, and drift tooling.

---

## 3. Repository Structure

Source of truth convention: Django apps live under `/apps`; `/backend` is project wiring.

```text
ai-legal-assistant/
|-- apps/
|   |-- accounts/
|   |-- documents/
|   `-- review/
|-- backend/
|-- frontend/
|-- docs/
|-- docker/
|-- docker-compose.yml
`-- manage.py
```

---

## 4. Component Model

### 4.1 Runtime components (implemented)

- API layer (DRF):
  - upload endpoint,
  - async run enqueue endpoint,
  - run status endpoint,
  - findings retrieval endpoint.
- Document ingestion:
  - PDF/text extraction,
  - spreadsheet parsing and canonical metadata.
- Preprocessing/chunking:
  - deterministic chunk generation with stable `chunk_id`,
  - per-run persisted chunk artifacts (`review_chunks`).
- Rule engine:
  - deterministic checks over extracted chunks.
- LLM analysis:
  - schema-validated JSON findings with provenance fields.
- Async orchestration:
  - Celery task execution,
  - lifecycle tracking,
  - retries and partial-failure policy.
- Runtime controls:
  - idempotency key semantics,
  - concurrency and request rate limits,
  - optional cache for successful pipeline outputs.

### 4.2 Planned components (Phase 3+)

- Semantic layer (pgvector).
- Search index (Elasticsearch) as derived store from Postgres.
- Production deployment patterns (Kubernetes/Terraform hardening).

---

## 5. Core Workflows

### 5.1 Ingest a document

1. Upload document (`.txt`, `.pdf`, `.csv`, `.xlsx`).
2. Parse and normalize into `Document.text`.
3. Persist `source_type` and `ingestion_metadata`.

Outputs:
- `document_id`
- normalized `text`
- metadata (`source_type`, `ingestion_metadata`, `created_at`)

### 5.2 Run a review (`POST /v1/review/run`)

1. Validate request and resolve idempotency behavior.
2. Apply concurrency/rate guards.
3. Create queued run record.
4. Enqueue worker task.
5. Return run metadata immediately.

Current behavior:
- `POST /v1/review/run` does not return findings payload.
- Findings are retrieved after worker completion.

### 5.3 Worker processing

1. Transition run to `running`.
2. Preprocess document into chunks.
3. Run deterministic rules.
4. Run LLM stage (if LLM stage fails, retain rule findings and mark `partial`).
5. Persist chunks and findings for the run.
6. Finalize run status and instrumentation.

### 5.4 Retrieve status and findings

- `GET /v1/review-runs/{id}` returns run lifecycle state and metadata.
- `GET /v1/documents/{id}/findings` returns persisted findings for latest or specified run.

---

## 6. Data Model (Canonical)

### 6.1 `documents`

- `id` (uuid)
- `title` (string)
- `text` (text)
- `source_type` (`text|pdf|spreadsheet`)
- `ingestion_metadata` (json)
- `created_at`

### 6.2 `review_runs`

- `id` (uuid)
- `document_id` (fk)
- `idempotency_key` (nullable)
- `request_fingerprint` (nullable, indexed)
- `status` (`queued|running|succeeded|failed|partial`)
- `current_stage` (`preprocess|extract|rules|llm|persist`, nullable)
- `llm_model` (nullable)
- `prompt_rev` (nullable)
- `error` (nullable)
- `cache_key` (nullable)
- `cache_hits` (int)
- `cache_misses` (int)
- `token_usage` (json)
- `stage_timings` (json)
- `started_at` (nullable)
- `completed_at` (nullable)
- `created_at`

Constraint:
- unique `(document_id, idempotency_key)` when `idempotency_key` is not null.

### 6.3 `findings`

- `id` (uuid)
- `document_id` (fk)
- `run_id` (fk, nullable for backward compatibility)
- `clause_id` (string, nullable)
- `chunk_id` (string, nullable)
- `clause_heading` (nullable)
- `clause_body` (nullable)
- `summary` (text)
- `explanation` (nullable)
- `severity` (`low|medium|high`)
- `evidence` (text)
- `evidence_span` (json, nullable)
- `source` (`rule|llm|unknown`)
- `rule_code` (nullable)
- `model` (nullable)
- `confidence` (nullable)
- `prompt_rev` (nullable)
- `created_at`

### 6.4 `review_chunks`

- `id` (uuid)
- `run_id` (fk)
- `document_id` (fk)
- `chunk_id` (string)
- `schema_version` (string)
- `ordinal` (int)
- `heading` (nullable)
- `body` (text)
- `start_offset` (nullable)
- `end_offset` (nullable)
- `metadata` (json)
- `created_at`

Constraints/indexes:
- unique `(run_id, chunk_id)`
- index `(run_id, ordinal)`
- index `(document_id, chunk_id)`

### 6.5 Embeddings (planned)

Future extension:
- vector fields and embedding metadata on findings/chunks.

---

## 7. Data Contracts (DTOs)

### 7.1 Run enqueue response (shape)

```json
{
  "document": {"id": "uuid", "title": "string"},
  "clauses": [],
  "findings": [],
  "run": {
    "id": "uuid",
    "document_id": "uuid",
    "status": "queued|running|succeeded|failed|partial"
  },
  "idempotency_reused": false
}
```

### 7.2 Finding DTO (shape)

```json
{
  "id": "uuid",
  "run_id": "uuid",
  "clause_id": "string",
  "chunk_id": "string",
  "summary": "string",
  "explanation": "string",
  "severity": "low|medium|high",
  "evidence": "string",
  "evidence_span": {"start": 12, "end": 42},
  "source": "rule|llm|unknown",
  "rule_code": "string",
  "model": "string",
  "prompt_rev": "string",
  "confidence": 0.72
}
```

Invariant:
- findings must include explainable evidence and source provenance.

---

## 8. API Surface

### 8.1 Implemented endpoints

- `GET /`
- `POST /v1/documents/upload`
- `POST /v1/review/run`
- `GET /v1/review-runs/{id}`
- `GET /v1/documents/{id}/findings`

### 8.2 Planned endpoints (Phase 3+)

- `GET /v1/search/*`
- `POST /v1/contracts/*`
- `GET /v1/strategy/*`
- `GET /v1/explain/*`

---

## 9. Security and Guardrails

- JWT boundary can be enabled via `apps/accounts` (SimpleJWT).
- Treat uploaded documents as sensitive data.
- Keep schema-constrained LLM output validation in place.
- Preserve provenance fields for auditability.

---

## 10. Deployment and Infrastructure

### 10.1 Local

- SQLite for quick local work.
- Postgres + Redis recommended for full async workflow.
- Docker Compose provides API, worker, db, redis, and frontend services.

### 10.2 CI/CD and production direction

- CI: lint/test/build checks.
- Phase 3+: image pipelines, deployment automation, infra provisioning.

---

## 11. Observability and Evaluation

### 11.1 Current baseline

- structured logs to stdout,
- explicit run error/status surfaces,
- run-level `stage_timings` and `token_usage`,
- cache hit/miss tracking per run.

### 11.2 Planned extensions

- Prometheus and Grafana dashboards,
- OpenTelemetry tracing,
- regression/eval harness over labeled corpora.

---

## 12. Roadmap Extensions

### Phase 3

- Search/indexing (Elasticsearch) and quality loop (eval/debug tooling).

### Phase 4

- Contract families and composite "as-of" document views.

### Phase 5

- Deviation analysis across corpus baselines.

### Phase 6

- Kubernetes/Terraform ops maturity and runbooks.

---

## Appendix A - Glossary

- Finding: structured, evidence-linked output.
- Provenance: metadata describing how a finding was produced.
- Derived store: secondary system rebuildable from Postgres.
- System of record: canonical persisted state in Postgres.

---

*Last updated: February 22, 2026*
