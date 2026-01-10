# AI Legal Assistant — Post‑MVP Implementation Plan (After MVP Step 7)

This document translates the **README** + **Architecture v5** roadmap into an implementable, phased plan with:
- Phase goals and “Definition of Done”
- PR-sized task slices (small, reviewable increments)
- A rough timeline estimate under two capacity assumptions

---

## Assumptions

- **MVP completion** means Step 7 is done: **findings are persisted + retrievable**, and each finding is linked to a **review run** (audit trail).
- **Postgres is the system of record.** Elasticsearch is a derived index.
- “LLM outputs” remain **schema-validated JSON** with required provenance fields (model, prompt revision, confidence proxy) and evidence spans.
- This plan stays consistent with current repo direction: **document-level MVP first**, then expansions.

---

## Current baseline (what exists before post‑MVP)

- Document ingestion (PDF/text → normalized text)
- Clause extraction (deterministic)
- Rule engine (deterministic checks)
- LLM analysis (schema-validated outputs; evidence spans; provenance fields)
- `POST /v1/review/run` returns structured results

---

## Phase overview

| Phase | Name | Primary outcome | Dependencies |
|---:|---|---|---|
| 0 | Finish MVP Step 7 | Persisted findings + retrieval + run audit trail | Existing MVP steps |
| 1 | Async orchestration | `review/run` becomes queued; job status + retries | Phase 0 |
| 2 | Elasticsearch search layer | Fast cross-document search + filters/facets | Phase 0–1 (recommended) |
| 3 | Contract families + composites | Base + amendments graph; effective “as-of” composites | Phase 0–2 |
| 4 | Deviation analysis (“buried risk”) | Compare normalized clauses vs baseline profiles | Phase 3 (preferred) |
| 5 | Production-ish ops | K8s + Terraform + observability + eval harness | Any prior phase |

---

## Phase 0 — Finish MVP Step 7 (Persistence + Retrieval + Audit Trail)

### Objective
Make “auditability” real: runs and findings are persisted, queryable, and reproducible.

### Definition of Done
- `review_runs` persisted with lifecycle fields: `status`, `started_at`, `finished_at`, `model`, `prompt_rev`
- `findings` persisted and linked to `run_id`
- `GET /v1/documents/{id}/findings` and/or `GET /v1/review-runs/{id}` returns persisted data
- pgvector enabled and embeddings stored for at least one entity (start with `findings`)
- Minimal tests for: schema validation, persistence, retrieval

### PR-sized task slices
- **PR-0.1: DB schema (audit trail)**
  - Add `review_runs` table + model
  - Add `run_id` FK on findings (or linking table)
  - Add migration + admin visibility (optional)
- **PR-0.2: Persist runs**
  - Create run record at start of `POST /v1/review/run`
  - Update status + timestamps on completion/failure
  - Store error message (optional)
- **PR-0.3: Persist findings**
  - Upsert/replace findings for a run
  - Ensure evidence spans + provenance fields persisted
  - Add optional `recommendation` field (nullable)
- **PR-0.4: Retrieval endpoints**
  - `GET /v1/documents/{id}/findings`
  - `GET /v1/review-runs/{id}` (recommended)
  - Add pagination/sorting (lightweight)
- **PR-0.5: pgvector bootstrap**
  - Enable pgvector extension
  - Add vector column + embedding function for findings
  - Store embedding on create (or background migration)
- **PR-0.6: Tests**
  - Serializer/schema tests for findings
  - Integration test: run → persist → retrieve

---

## Phase 1 — Async orchestration (Celery + Redis)

### Objective
Support long-running reviews without blocking requests; add retries/idempotency and clear run status.

### Definition of Done
- `POST /v1/review/run` can enqueue a job and return `run_id`
- Workers execute the pipeline and persist results
- Idempotency key supported (prevents duplicate runs for same request)
- Retry policy and failure modes are explicit (including partial results policy)

### PR-sized task slices
- **PR-1.1: Celery + Redis skeleton**
  - Add Celery config + Redis dependency (compose)
  - Add worker container target
- **PR-1.2: Job model + idempotency**
  - Add `idempotency_key` column on runs (or a separate table)
  - Enforce uniqueness for `(document_id, idempotency_key)`
- **PR-1.3: Enqueue pathway**
  - `POST /v1/review/run` → create run record → enqueue task → return `run_id`
- **PR-1.4: Worker execution**
  - Worker loads doc → runs pipeline → persists findings → finalizes run status
  - Safe retries (do not duplicate findings)
- **PR-1.5: Status & progress**
  - `GET /v1/review-runs/{id}` returns status + timestamps
  - Optional: progress markers per stage (extract/rules/llm/persist)
- **PR-1.6: Cost controls**
  - Concurrency caps
  - Rate limiting per user/org (basic)
  - Token usage and cost fields recorded (optional but recommended)

---

## Phase 2 — Elasticsearch indexing + Search API

### Objective
Make the system usable across a corpus: fast search, filters, and facets.

### Definition of Done
- ES index mapping for documents + findings (and clauses if persisted)
- Indexer pipeline (DB → ES) with backfill + reindex strategy
- Search endpoints with filtering/faceting:
  - search findings by keyword + severity + type + date + doc metadata
- Clear “source-of-truth” rule: Postgres authoritative; ES derived

### PR-sized task slices
- **PR-2.1: ES dev setup**
  - Add ES to docker compose (dev only)
  - Add index settings + mapping in repo
- **PR-2.2: Index model + mapping**
  - Define canonical ES documents (document, finding)
  - Add versioned index naming strategy (`findings_v1`, etc.)
- **PR-2.3: Indexer task**
  - Implement indexer as Celery task (recommended)
  - Index on “run completed” events
- **PR-2.4: Backfill + reindex**
  - CLI command to backfill ES from Postgres
  - Reindex pipeline for mapping changes
- **PR-2.5: Search endpoints**
  - `GET /v1/search/findings?...`
  - Basic facets (severity, type, source, date)
  - Highlight snippets (optional)
- **PR-2.6: Test & validation**
  - Contract tests for search filters
  - Smoke tests in compose

---

## Phase 3 — Contract families + Composite versions

### Objective
Move from single-document analysis to multi-document structure:
- Base agreement + amendments linked into a family
- Generate “effective as-of” composites with auditable diffs

### Definition of Done
- Data model for contract family graph:
  - `contracts`, `contract_relations` (base/amends/supersedes), confidence, evidence
- Family resolution endpoint + composite generation endpoint
- Composite output includes: effective text segments + evidence pointers + change summary

### PR-sized task slices
- **PR-3.1: Family graph schema**
  - Tables/models for contracts and relations
  - Store linking evidence + confidence + method (rule/heuristic/llm)
- **PR-3.2: Heuristic linker (first pass)**
  - Match by title/date/parties/identifiers (lightweight)
  - Provide “unresolved” state
- **PR-3.3: LLM-assisted linker (optional)**
  - Second-pass suggestions for uncertain links
  - Persist justification + evidence spans
- **PR-3.4: Family resolution API**
  - `POST /v1/contracts/{id}/family/resolve`
  - `GET /v1/contracts/{id}/family`
- **PR-3.5: Composite generator**
  - Produce effective “as-of” representation
  - Generate diff summaries with citations
- **PR-3.6: Index composite artifacts (optional)**
  - Store composite outputs for retrieval/search

---

## Phase 4 — Deviation analysis (“buried risk”) across a corpus

### Objective
Detect non-obvious risk by comparing clause content and normalized fields against a baseline.

### Definition of Done
- Clause normalization schemas per clause type (fields you can compare)
- Baseline profile generation (per template/customer/industry sample)
- Deviation scoring output includes: what deviated, how far, why it matters, and evidence

### PR-sized task slices
- **PR-4.1: Normalization schema**
  - Define per-clause-type fields (e.g., governing law, cap, termination triggers)
  - Implement extraction into structured fields (rule first; LLM assist where needed)
- **PR-4.2: Baselines**
  - Compute baseline profiles (means/ranges or categorical distributions)
  - Store baseline metadata and scope
- **PR-4.3: Deviation scoring**
  - Implement scoring function per field type
  - Generate explainable deviation “cards”
- **PR-4.4: Analytics endpoints**
  - `GET /v1/analytics/deviations?...`
  - Filter by clause type, severity, customer/template
- **PR-4.5: ES + vector integration**
  - Index deviations
  - Add “similar deviations” via pgvector (optional)

---

## Phase 5 — Deployment & Operations maturity (Kubernetes + Terraform + Observability + Eval)

### Objective
Make the project deployable and maintainable as a realistic SaaS backend prototype.

### Definition of Done
- K8s deployment for API + worker; managed Postgres recommended; optional ES/Redis
- Terraform provisions core infra (networking, secrets, storage, compute)
- Prometheus metrics + Grafana dashboards
- Evaluation harness (synthetic corpus + regression checks) to prevent silent quality regressions

### PR-sized task slices
- **PR-5.1: Container hardening**
  - Multi-stage Dockerfiles (api/worker)
  - Runtime config via env + secrets pattern
- **PR-5.2: K8s manifests**
  - Deployments/services/ingress for API + worker
  - HPA/autoscaling knobs (basic)
- **PR-5.3: Terraform base**
  - VPC, security groups, secrets manager, load balancer
  - Choose container runtime target (EKS/ECS) and keep consistent
- **PR-5.4: Observability**
  - Metrics: run duration, queue depth, failures, token usage, cost
  - Dashboards + alert thresholds (lightweight)
- **PR-5.5: Evaluation harness**
  - Synthetic contract set + golden outputs
  - Regression runner in CI (diff structured outputs; allow tolerance)
- **PR-5.6: Documentation + runbooks**
  - “How to deploy” + “How to reindex” + “How to roll back prompts”

---

## Guestimated timeline (rough)

These are coarse estimates for a single developer. They assume clean scope boundaries and “prototype-quality” (not enterprise hardening). Actual time will vary with refactors, debugging, and documentation.

### Scenario A — Part-time build (≈ 10–15 hours/week)
- Phase 0: **2–4 weeks**
- Phase 1: **2–4 weeks**
- Phase 2: **3–6 weeks**
- Phase 3: **4–8 weeks**
- Phase 4: **4–8 weeks**
- Phase 5: **3–6 weeks**
- **Total:** ~ **18–36 weeks** depending on how much of each phase you implement

### Scenario B — Focused build (≈ 25–35 hours/week)
- Phase 0: **1–2 weeks**
- Phase 1: **1–2 weeks**
- Phase 2: **2–3 weeks**
- Phase 3: **3–5 weeks**
- Phase 4: **3–5 weeks**
- Phase 5: **2–4 weeks**
- **Total:** ~ **12–21 weeks**

### Notes on timeline risk
- The largest schedule risk is Phase 3–4 scope creep (families, composites, baselines).
- ES indexing is straightforward, but “great search UX” can expand quickly.
- Evaluation harness work pays off early; it prevents regressions as prompts evolve.

---

## Recommended execution order (practical)

If your goal is “most impressive proof-of-work fastest”:
1. **Phase 0** (make auditability real)
2. **Phase 1** (async jobs + run status + cost controls)
3. **Phase 2** (search; demo value increases sharply)
4. **Phase 5 (partial)** (basic metrics + dashboards early)
5. **Phase 3** (families + composites)
6. **Phase 4** (deviation analysis)

---

## Optional: deliverable-oriented milestones (for demos)

- **Milestone M1:** Persisted findings + run audit trail + retrieval
- **Milestone M2:** Async runs + job status + retries + token/cost reporting
- **Milestone M3:** Search UI-ready API (ES backed) with facets (severity/type/source)
- **Milestone M4:** Contract family graph + “as-of” composite + auditable change summaries
- **Milestone M5:** Deviation dashboard endpoints (top deviations by clause type)

---

*Last updated: January 9, 2026*
