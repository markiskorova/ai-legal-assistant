# ⚖️ AI Legal Assistant

**AI Legal Assistant** is a modular, transparent, and extensible web application that demonstrates how large language models can *augment* — not replace — legal reasoning.

It provides a structured, explainable interface for:
- Clause extraction and classification  
- Contract risk analysis and redline suggestions  
- Plain-language clause summaries  
- Evidence provenance and explainability  
- *(Planned post-MVP)* Multi-document case reasoning and strategy mapping  

---

## 📚 Docs

- **MVP checklist (GitHub-friendly):** [`docs/MVP_Checklist.md`](docs/MVP_Checklist.md)
- **Project article / design rationale:** [`docs/AI_Legal_Assistant_Article_2025_10_29.md`](docs/AI_Legal_Assistant_Article_2025_10_29.md)

---

## 🧭 Purpose

The goal of this project is to build an **AI-native legal reasoning platform** — a proof-of-concept that combines deterministic rule-based checks with LLM-driven insights.  
It is designed for research, portfolio demonstration, or as a foundation for legal-tech SaaS products (e.g., Eve Legal / LegalOn-style workflows).

**Key Principles**
- **Explainable:** Every finding links to evidence and rationale.  
- **Auditable:** Model version, prompt revision, and confidence are tracked.  
- **Modular:** Each domain (documents, review, cases, strategy, explain) is its own app.  
- **Extensible:** Built with Django’s modular app structure and clean APIs.

---

## ✅ MVP Scope

The MVP focuses on **document-level** analysis:

**Upload / ingest → extract clauses → rules + LLM → return findings (with provenance)**

Anything beyond document-level (cases, strategy, observability dashboards) is tracked as **post-MVP** work.

---

## ⚙️ Functionality Overview

| Module | Description |
|---------|-------------|
| **Documents** | Upload, parse, and store legal documents (contracts, NDAs, policies). |
| **Review** | Clause extraction, rule checks, summarization, and risk scoring (rules + LLM). |
| **Cases (planned)** | Aggregate multiple documents into a case; extract entities & issues. |
| **Strategy (planned)** | Generate next-action insights (negotiation, compliance, risk mitigation). |
| **Explain (planned)** | Surface model provenance, evidence spans, and rationale metadata. |
| **Jobs (optional)** | Background processing via Celery for async LLM and parsing tasks. |
| **Metrics (post-MVP)** | Observability and cost tracking (tokens, cost, latency). |

**Data Flow (target architecture):**

![Workflow Diagram](./docs/ai_legal_article_workflow_d.png)

```
Document → Findings → Case → Issues → Strategy → Explainability
```

---

## 🧩 Tech Stack

| Layer | Technology |
|--------|-------------|
| **Backend** | Django + Django REST Framework (DRF) |
| **Auth** | JWT via `djangorestframework-simplejwt` |
| **Database** | SQLite (dev) → PostgreSQL 16 (prod, pgvector optional) |
| **Object Storage** | AWS S3 (presigned uploads) *(post-MVP)* |
| **Background Tasks** | Celery + Redis *(optional)* |
| **Frontend** | Minimal HTML or lightweight React dashboard *(optional)* |
| **LLM Interface** | OpenAI (GPT-4o) with JSON schema validation |
| **Infrastructure** | Docker + Terraform (AWS ECS + RDS + S3) *(post-MVP)* |
| **CI/CD** | GitHub Actions (lint, test, deploy) |
| **Post-MVP** | Prometheus + Grafana for observability |

---

## 🧱 Architecture Overview

```
ai-legal-assistant/
├── apps/
│   ├── accounts/     # JWT auth (optional for MVP demo mode)
│   ├── documents/    # Uploads, parsing, ingestion
│   ├── review/       # Clause analysis (rules + LLM)
│   ├── cases/        # (planned) Multi-document aggregation
│   ├── strategy/     # (planned) Strategy mapping and issue generation
│   ├── explain/      # (planned) Evidence and model provenance
│   ├── jobs/         # (optional) Celery orchestration
│   └── metrics/      # (post-MVP) Observability
├── docs/
│   ├── MVP_Checklist.md
│   └── AI_Legal_Assistant_Article_2025_10_29.md
├── infra/
│   ├── docker/
│   ├── terraform/
│   └── github-actions/
└── README.md
```

---

## 🧠 API Endpoints

### MVP (document-level)

| Endpoint | Method | Description |
|-----------|---------|-------------|
| `/v1/documents/upload` | POST | Upload or ingest a document (PDF/text) |
| `/v1/review/run` | POST | Run clause extraction + rules + LLM analysis |
| `/v1/documents/{id}/findings` | GET | Retrieve clause-level findings for a document |

### Post-MVP (planned)

| Endpoint | Method | Description |
|-----------|---------|-------------|
| `/v1/cases/create` | POST | Create case with multiple documents |
| `/v1/cases/{id}/aggregate` | GET | Aggregate findings → issues/entities |
| `/v1/strategy/suggest` | POST | Generate strategy suggestions |
| `/v1/explain/{finding_id}` | GET | Retrieve provenance and rationale |

---

## 📊 Database Schema (Core)

| Table | Description |
|--------|-------------|
| `documents` | Uploaded legal texts |
| `findings` | Clause-level results (risk, summary, evidence, model, confidence) |
| *(post-MVP)* `cases` | Case containers (multi-document grouping) |
| *(post-MVP)* `case_docs` | Link table (case ↔ documents) |
| *(post-MVP)* `entities` | Extracted parties, dates, or amounts |
| *(post-MVP)* `issues` | Aggregated reasoning results |
| *(optional)* `jobs` | LLM run logs (tokens, cost, model) |

---

## 🧭 Roadmap

| Phase | Focus | Deliverables |
|--------|--------|--------------|
| **MVP** | Document analysis | Upload → Extract → Analyze → Findings API |
| **Phase 2** | Case reasoning | Case containers, aggregation, entities/issues |
| **Phase 3** | Strategy & explainability | Strategy suggestions, evidence/provenance views |
| **Phase 4** | Observability & governance | Cost dashboards, audit logs, rate limits |

---

## 🧑‍💻 Contributors

- [**Marc McAllister**](https://www.linkedin.com/in/marc-mcallister-41506b3/) — Lead Developer & Architect  
- Contributions welcome!

---

## 🪶 License

MIT License © 2025 Marc McAllister
