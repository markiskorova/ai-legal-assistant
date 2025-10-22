# ⚖️ AI Legal Assistant

**AI Legal Assistant** is a modular, transparent, and extensible web application that demonstrates how large language models can *augment* — not replace — legal reasoning.

It provides a structured, explainable interface for:
- Clause extraction and classification  
- Contract risk analysis and redline suggestions  
- Plain-language clause summaries  
- Multi-document case reasoning and strategy mapping  
- Evidence provenance and explainability

---

## 🧭 Purpose

The goal of this project is to build an **AI-native legal reasoning platform** — a proof-of-concept that combines deterministic rule-based checks with LLM-driven insights.  
It is designed for research, portfolio demonstration, or as a foundation for legal-tech SaaS products like Eve Legal or LegalOn.

**Key Principles**
- **Explainable:** Every finding links to evidence and rationale.  
- **Auditable:** Model version, prompt revision, and confidence are tracked.  
- **Modular:** Each domain (review, case, strategy, explain) is its own app.  
- **Extensible:** Built with Django’s modular app structure and clean APIs.

---

## ⚙️ Functionality Overview

| Module | Description |
|---------|--------------|
| **Documents** | Upload, parse, and store legal documents (contracts, NDAs, policies). |
| **Review** | Clause extraction, classification, summarization, and risk scoring. |
| **Cases** | Aggregate multiple documents into a single case; extract entities and issues. |
| **Strategy** | Generate next-action insights (negotiation, compliance, risk mitigation). |
| **Explain** | Surface model provenance, evidence spans, and rationale metadata. |
| **Jobs (optional)** | Background processing via Celery for async LLM and parsing tasks. |
| **Metrics (post-MVP)** | Observability and cost tracking via Prometheus + Grafana. |

**Data Flow:**
```
Document → Findings → Case → Issues → Strategy → Explainability
```

---

## 🧩 Tech Stack

| Layer | Technology |
|--------|-------------|
| **Backend** | Django + Django REST Framework (DRF) |
| **Auth** | JWT via `djangorestframework-simplejwt` |
| **Database** | SQLite (dev) → PostgreSQL 16 (prod) |
| **Object Storage** | AWS S3 (presigned uploads) |
| **Background Tasks** | Celery + Redis (optional) |
| **Frontend** | Minimal HTML or lightweight React dashboard |
| **LLM Interface** | OpenAI GPT-4o with JSON schema validation |
| **Infrastructure** | Docker + Terraform (AWS ECS + RDS + S3) |
| **CI/CD** | GitHub Actions (lint, test, deploy) |
| **Post-MVP** | Prometheus + Grafana for observability |

---

## 🧱 Architecture Overview

```
ai-legal-assistant/
├── apps/
│   ├── accounts/     # JWT auth
│   ├── documents/    # Uploads, parsing, S3 handling
│   ├── review/       # Clause analysis (rules + LLM)
│   ├── cases/        # Multi-document aggregation
│   ├── strategy/     # Strategy mapping and issue generation
│   ├── explain/      # Evidence and model provenance
│   ├── jobs/         # Celery orchestration (optional)
│   └── metrics/      # Post-MVP observability
├── infra/
│   ├── docker/
│   ├── terraform/
│   └── github-actions/
└── README.md
```

---

## 🧠 API Endpoints (MVP)

| Endpoint | Method | Description |
|-----------|---------|-------------|
| `/v1/documents/upload` | POST | Upload or fetch presigned URL |
| `/v1/review/run` | POST | Run rule + LLM analysis |
| `/v1/documents/{id}/findings` | GET | Retrieve clause-level findings |
| `/v1/cases/create` | POST | Create case with multiple documents |
| `/v1/cases/{id}/aggregate` | GET | Aggregate findings → issues |
| `/v1/strategy/suggest` | POST | Generate strategy suggestions |
| `/v1/explain/{finding_id}` | GET | Retrieve provenance and rationale |

---

## 📊 Database Schema (Core)

| Table | Description |
|--------|-------------|
| `documents` | Uploaded legal texts |
| `findings` | Clause-level results (risk, summary, evidence, model, confidence) |
| `cases` | Case containers (multi-document grouping) |
| `case_docs` | Link table (case ↔ documents) |
| `entities` | Extracted parties, dates, or amounts |
| `issues` | Aggregated reasoning results |
| `jobs` | LLM run logs (tokens, cost, model) |

---

## 🔍 Observability & Governance

- **LLM Provenance:** Model, prompt revision, confidence score logged.  
- **Cost Tracking:** Tokens, time, and cost per document tracked in DB.  
- **Auditability:** Findings linked to rules or model output.  
- **Security:** JWT-based auth; future RBAC per case.  
- **Post-MVP:** File hygiene (clamav) and rate limits.

---

## 🚀 Deployment

| Environment | Components |
|--------------|-------------|
| **Local Dev** | Docker Compose (web + Postgres + Redis) |
| **Production** | AWS ECS + RDS + S3 (via Terraform) |
| **CI/CD** | GitHub Actions pipeline for lint/test/deploy |

---

## 🧭 Roadmap

| Phase | Focus | Deliverables |
|--------|--------|--------------|
| **MVP** | Document analysis | Upload → Extract → Analyze → Summarize |
| **Phase 2** | Case reasoning | Case aggregation, entities, issues |
| **Phase 3** | Strategy & explainability | Strategy suggestions, provenance API |
| **Phase 4** | Observability & governance | Cost dashboards, audit logs, rate limits |

---

## 💡 Positioning

> “AI Legal Assistant is an open, modular simulation of an AI-native legal reasoning platform — combining document-level analysis, case reasoning, and explainable strategy insights using modern LLM infrastructure.”

---

## 🧑‍💻 Contributors

- **Marc McAllister** — Lead Developer & Architect  
- Contributions welcome!

---

## 🪶 License

MIT License © 2025 Marc McAllister

---

