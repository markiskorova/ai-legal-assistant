# AI Legal Assistant — MVP Checklist

## Purpose of the MVP

The **AI Legal Assistant MVP** demonstrates how large language models can *augment* legal reasoning in a transparent, auditable way.

The MVP focuses on **document-level legal analysis**, not full case management. Its goal is to show:

- How legal documents can be ingested and parsed
- How clauses can be extracted and classified
- How deterministic legal rules and LLMs can work together
- How every AI-generated output can be traced back to evidence and model metadata

This MVP is intentionally narrow, explainable, and portfolio-ready.

---

## Core MVP Functionality

By the end of the MVP, the system can:

- Accept legal documents (PDF or text)
- Extract clauses from documents
- Analyze clauses using:
  - Deterministic rule checks
  - LLM-based reasoning
- Return structured findings with:
  - Risk level
  - Summary
  - Evidence
  - Source (rule vs LLM)
  - Model provenance (model, confidence, prompt revision)
- Expose results through clean, versioned APIs

---

## MVP Build Checklist

### Step 1 — Scaffold Django Project + Core Apps

- [x] Create Django project
- [x] Add core apps (`accounts`, `documents`, `review`)
- [x] Configure Django REST Framework
- [x] Project runs locally

---

### Step 2 — Document Input & Storage

- [x] Create `Document` model
- [x] Implement document upload / ingestion
- [x] Support PDF and raw text
- [x] Store text in database

---

### Step 3 — Clause Extraction

- [x] Implement clause extraction logic
- [x] Heading-based extraction
- [x] Paragraph fallback
- [x] Structured clause output

---

### Step 4 — Deterministic Rule Engine

- [x] Implement rule engine
- [x] Termination notice checks
- [x] Indemnity clauses
- [x] Confidentiality duration
- [x] Governing law mismatches

---

### Step 5 — LLM Integration

- [x] Integrate OpenAI client
- [x] Versioned prompts
- [x] JSON schema validation
- [x] Evidence spans required
- [x] Provenance metadata
- [x] `.env` configuration

---

### Step 6 — `/v1/review/run` Endpoint

- [x] Unified review pipeline
- [x] Clause → rules → LLM orchestration
- [x] `POST /v1/review/run`
- [x] Structured JSON response
- [x] Refactored services

---

### Step 7 — `/v1/documents/{id}/findings` Endpoint

- [x] Choose persistence strategy (ReviewRun groups findings per analysis run)
- [x] Persist findings during `/v1/review/run`
- [x] Implement findings retrieval endpoint
- [x] Return clause-level findings
- [x] Include provenance metadata

---

### Step 8 — Minimal Frontend (Optional)

- [ ] Upload UI
- [ ] Run analysis
- [ ] Display findings
- [ ] Evidence toggle

---

## MVP Completion Criteria

- [x] Documents ingested
- [x] Clauses extracted
- [x] Rules + LLM findings generated
- [x] Explainable outputs
- [x] Findings retrievable via API
- [ ] Optional demo UI

---

## Out of Scope (Post-MVP)

- Case aggregation
- Strategy suggestions
- Observability
- RBAC
- Production infra

---

*Last updated: November 14, 2025*
