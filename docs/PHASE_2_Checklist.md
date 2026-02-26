# AI Legal Assistant - Phase 2 Checklist

**Status:** Completed and re-verified against code/tests on February 26, 2026.

## Purpose of Phase 2

Phase 2 moves the review pipeline to an always-async execution model and hardens ingestion/provenance so longer-running analysis is reliable, traceable, and production-lean.

This phase focuses on:

- Non-blocking review execution (`POST /v1/review/run` enqueues work)
- Clear run lifecycle tracking (queued/running/succeeded/failed/partial)
- Idempotent run creation and safe retry behavior
- Stronger evidence provenance via persisted chunk artifacts
- Expanded ingestion support for spreadsheets (`.xlsx` / `.csv`)
- Run-level instrumentation for cost/latency/throughput visibility

---

## Core Phase 2 Functionality

By the end of Phase 2, the system can:

- Accept a review request and return a `run_id` immediately
- Execute review pipelines in background workers
- Prevent duplicate runs for the same idempotent request
- Persist run status and optional stage-level progress
- Persist stable chunk artifacts and link findings to `chunk_id`
- Ingest spreadsheets into the same review pipeline as document text
- Capture run instrumentation (token usage, stage timings, cache behavior)
- Apply explicit retry and failure handling policies

---

## Phase 2 Build Checklist

### Step 1 - Celery + Redis skeleton (PR-2.1)

- [x] Add Celery app configuration
- [x] Add Redis to Docker Compose
- [x] Add worker service/container target
- [x] Document local worker startup

---

### Step 2 - Job model + idempotency (PR-2.2)

- [x] Add `idempotency_key` to run model (or separate table)
- [x] Enforce uniqueness for `(document_id, idempotency_key)`
- [x] Add supporting DB indexes for run status/timestamps

---

### Step 3 - Enqueue pathway (PR-2.3)

- [x] Update `POST /v1/review/run` to create run + enqueue worker task
- [x] Return `run_id` immediately with async status semantics
- [x] Handle duplicate idempotent requests deterministically

---

### Step 4 - Worker execution + safe retries (PR-2.4)

- [x] Move review pipeline orchestration into worker execution
- [x] Persist lifecycle transitions (`queued` -> `running` -> terminal state)
- [x] Ensure retries do not duplicate findings
- [x] Capture failure reason and partial-result behavior

---

### Step 5 - Status and progress API (PR-2.5)

- [x] Extend `GET /v1/review-runs/{id}` for lifecycle status/timestamps
- [x] Add optional stage progress markers (preprocess/extract/rules/llm/persist)
- [x] Standardize status/error response contract

---

### Step 6 - Layout-aware preprocessing + chunk artifacts (PR-2.6)

- [x] Add preprocessing stage producing stable `chunk_id` values
- [x] Persist chunk artifacts with schema versioning
- [x] Ensure findings reference `chunk_id` (+ optional span metadata)

---

### Step 7 - Spreadsheet ingestion (PR-2.7)

- [x] Add `.xlsx` parser
- [x] Add `.csv` parser
- [x] Normalize rows to canonical representation (sheet/row/cell values)
- [x] Generate row-window chunks + spreadsheet evidence pointers

---

### Step 8 - Instrumentation + cache controls (PR-2.8)

- [x] Record token usage per run
- [x] Record stage timings
- [x] Record cache hit/miss fields
- [x] Add basic concurrency caps and rate limits
- [x] Define lightweight cache key strategy (`doc_hash + prompt_rev + schema_version`)

---

### Step 9 - Validation and release hardening

- [x] Integration test: enqueue -> run -> persist -> retrieve
- [x] Idempotency and retry-path test coverage
- [x] Failure-mode tests (worker crash, timeout, partial policy)
- [x] Update API docs and runbook notes

---

## Phase 2 Completion Criteria

- [x] `POST /v1/review/run` is always async and returns `run_id`
- [x] Worker-based execution persists runs and findings reliably
- [x] Idempotency key support prevents duplicate equivalent runs
- [x] Chunk artifacts are persisted and findings reference stable `chunk_id`
- [x] Spreadsheet ingestion feeds the standard downstream review pipeline
- [x] Run-level instrumentation is available for debugging/operations
- [x] Retry/failure behavior is explicit and tested

---

## Out of Scope (Phase 3+)

- Elasticsearch indexing and search endpoints
- Eval harness and internal debug tooling
- Contract family graph and composite generation
- Deviation analysis across corpus baselines
- Production Kubernetes/Terraform rollout and full observability stack

---

*Last updated: February 26, 2026*
