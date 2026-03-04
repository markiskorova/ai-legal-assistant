# Project Overview

AI Legal Assistant is an application for document-level legal review that combines deterministic checks with LLM-assisted analysis while preserving traceability. It is designed as a practical demonstration of how AI can augment legal workflows with structured, explainable outputs instead of opaque, one-shot answers.

This overview describes the current product behavior and implemented functionality. For the technical design, data contracts, and planned architectural evolution, see the Software Architecture Document in [architecture.md](./architecture.md).

## Purpose

The project exists to show how legal-tech workflows can use AI in a controlled way:

- documents are normalized into a consistent internal representation before review,
- rule-based checks provide predictable, explainable findings,
- LLM output is schema-constrained and attached to provenance metadata,
- and each review run is persisted so results can be audited after processing.

The emphasis is on transparency, repeatability, and operational safeguards rather than autonomous legal decision-making.

## What The Application Does

At a high level, the system lets a user upload a legal document, queue an asynchronous review, and inspect the findings after the run completes. The backend stores the document, breaks it into stable review chunks, runs deterministic rules and LLM analysis over those chunks, persists the resulting findings, and exposes APIs to retrieve both run status and findings.

The included React UI acts as a lightweight review console for this workflow: it supports document upload, review initiation, findings refresh, and evidence inspection.

## Current Functionality

### Document Ingestion

The application accepts several document formats:

- plain text files (`.txt`)
- PDF files (`.pdf`)
- CSV files (`.csv`)
- Excel files (`.xlsx`)

Uploaded documents are converted into stored text so the review pipeline can operate over a normalized input. The system also records source type and ingestion metadata, including spreadsheet parsing metadata where applicable.

### Async Review Execution

Review runs are started through `POST /v1/review/run`. The endpoint always returns immediately with a `run_id` instead of blocking until analysis finishes.

Behind that endpoint, the system:

1. validates the request and resolves idempotency behavior,
2. applies concurrency and per-requester rate limits,
3. creates a queued review run record,
4. enqueues Celery work for processing,
5. returns the queued run metadata to the client.

This gives the application stable, production-oriented workflow semantics even when analysis is slow or partially fails.

### Review Pipeline

Each review run processes a document through a staged pipeline:

1. preprocessing and chunk generation,
2. deterministic rule checks,
3. schema-constrained LLM analysis,
4. persistence of chunks, findings, and run metadata.

The pipeline stores stable `chunk_id` values so findings can be traced back to specific chunks. It also records stage timings, token usage, cache hit/miss metrics, and stage-level lifecycle state for operational visibility.

If the LLM stage fails or times out, rule-based findings are still persisted and the run is marked `partial` instead of losing all useful output.

### Findings And Provenance

Persisted findings are structured records rather than free-form text. Each finding can include:

- summary and explanation text,
- severity (`low`, `medium`, `high`),
- evidence text and evidence spans,
- recommendation text,
- source attribution (`rule`, `llm`, or `unknown`),
- provenance such as `rule_code`, model name, confidence, and prompt revision,
- references back to clause and chunk identifiers.

This allows downstream consumers to inspect what was found, where it came from, and how confident the system was in the result.

### Findings Retrieval

The system exposes retrieval endpoints for completed or in-progress work:

- `GET /v1/review-runs/{id}` returns run status and document metadata
- `GET /v1/documents/{id}/findings` returns persisted findings for the most recent run by default

Findings retrieval also supports:

- scoping to a specific run with `run_id`
- pagination via `page` and `page_size`
- sorting via `ordering`

This makes the persisted review output queryable after the original request has completed.

### Embeddings And Vector Readiness

The current implementation can persist embeddings for findings. Embeddings are stored on the finding record and can also be synchronized into Postgres pgvector structures when the application is running against PostgreSQL with the pgvector bootstrap migration applied.

The repository also includes a backfill command for generating embeddings for existing findings:

`python manage.py backfill_finding_embeddings --batch-size 100`

This gives the project a foundation for semantic retrieval and vector-based extensions without changing the primary review workflow.

### Frontend Review Console

The React frontend provides a minimal interface for the current workflow. A user can:

- upload a document with a title,
- start a review run,
- refresh findings for the current document or run,
- inspect run metadata such as status, model, and prompt revision,
- review finding counts by severity,
- expand and collapse evidence details for each finding.

The UI is intentionally small, but it covers the core end-to-end path from ingestion through findings inspection.

### Local And Containerized Operation

The project supports:

- local backend execution with Django,
- local async workers with Celery,
- local frontend execution with Vite,
- Docker Compose orchestration with PostgreSQL, Redis, the Django API, a Celery worker, and the frontend.

This makes it usable both as a development project and as a demonstrable full-stack workflow.

## Implemented API Surface

The current API surface is:

- `GET /`
- `POST /v1/documents/upload`
- `POST /v1/review/run`
- `GET /v1/review-runs/{id}`
- `GET /v1/documents/{id}/findings`

An accounts route namespace exists at `v1/accounts/`, but it is currently a placeholder boundary rather than a surfaced user flow.

## Scope Boundaries

The project is focused on explainable document review, not autonomous legal advice. It does not currently implement full enterprise product concerns such as complete authentication workflows, role-based access control, billing, or production observability stacks.

Those architectural boundaries and the planned expansion path are described in the Software Architecture Document: [architecture.md](./architecture.md).
