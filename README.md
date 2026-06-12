# DAM Governance Intelligence Platform — Danantara

AI-assisted governance document platform for Danantara's DAM directorate, built for the IBM engagement. Targets **~30% productivity improvement** on governance document workflows (NOTA drafting, consistency checking, SOP routing) with a controlled, auditable, explainable AI environment.

Built in **IBM Carbon Design System** style — IBM Plex typography, Carbon components, soft-blue palette on white.

---

## Why this exists — pain points addressed

| Pain point | Platform capability |
|---|---|
| **A. Inconsistency / multiple versions of truth** — ~30% of senior time spent reconciling documents | Cross-document **Consistency Checker** agent + master document hierarchy with propagation logic (single source of truth) |
| **B. Over-documentation for liability avoidance** — 80% of NOTA content is descriptive boilerplate | **AI Drafting Engine** generates descriptive sections from submissions, templates, and historical notes; humans retain the 20% judgment sections |
| **C. Fragmented workflow / unclear SOP routing** | **Rule-based eligibility & routing engine** — digitized SOPs, decision trees, delegation-of-authority thresholds answer "does this need approval?" and "which SOP applies?" deterministically |
| **D. Manual, repetitive drafting burden** | Drafting agent + document **ingestion/extraction pipeline** (RAG) pulls data from submissions automatically |
| **E. No controlled AI / data environment** | Self-hosted **secure AI sandbox**: enterprise Claude API (no training on data), grounded RAG to reduce hallucination, full audit trail on every AI action |
| **F. Personal liability risk** | **Risk-based automation segmentation**: low-risk flows fully automated by codified rules (human removed); complex flows human-in-the-loop. Every decision carries an **explainability trace** (sources, rules fired, model rationale) |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend — React + IBM Carbon Design System                    │
│  Dashboard · Drafting Workspace · Consistency · Routing · Audit │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST (FastAPI)
┌────────────────────────────┴────────────────────────────────────┐
│  Backend — FastAPI                                              │
│                                                                 │
│  ┌──────────────┐  ┌────────────────────────────────────────┐  │
│  │ Workflow     │  │ Agent Orchestrator                     │  │
│  │ Engine       │──│  · Extraction agent                    │  │
│  │ (submission→ │  │  · Drafting agent (NOTA)               │  │
│  │  evaluation→ │  │  · Consistency agent                   │  │
│  │  board→      │  │  · Routing agent (rules + explanation) │  │
│  │  decision→   │  └───────────────┬────────────────────────┘  │
│  │  comms)      │                  │                           │
│  └──────┬───────┘  ┌───────────────┴────────────────────────┐  │
│         │          │ RAG — pgvector retrieval over ingested │  │
│  ┌──────┴───────┐  │ submissions, templates, historical     │  │
│  │ SOP rules    │  │ NOTAs, SOPs                            │  │
│  │ (YAML        │  └────────────────────────────────────────┘  │
│  │  decision    │  ┌────────────────────────────────────────┐  │
│  │  trees)      │  │ Explainability + Audit trail           │  │
│  └──────────────┘  └────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
        PostgreSQL + pgvector          MinIO (document store)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/REQUIREMENTS-TRACEABILITY.md](docs/REQUIREMENTS-TRACEABILITY.md).

## Quick start

```bash
# 1. Configure
cp .env.example .env          # set ANTHROPIC_API_KEY

# 2. Run everything
docker compose up --build

# Frontend → http://localhost:5173
# API docs → http://localhost:8000/docs
```

### Local development

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Repository layout

```
backend/
  app/
    agents/          # Multi-agent intelligence (drafting, consistency, routing, extraction)
    rag/             # Embeddings, pgvector store, retriever
    ingestion/       # Document ingestion + extraction pipeline
    workflow/        # State machine + SOP rule engine (risk segmentation)
    explainability/  # Decision traces — sources, rules fired, rationale
    core/            # Config, audit logging
    api/             # REST routes
    models/          # Pydantic schemas (NOTA, submission, findings, routing)
config/sop/          # Digitized SOPs as YAML decision trees
frontend/            # React + @carbon/react (IBM Carbon Design System)
docs/                # Architecture & requirements traceability
```

## Roadmap

- **Phase 1 (this repo)** — quick wins: drafting engine, consistency checker, version control / SSOT, rule-based routing, secure sandbox, workflow orchestration, SOP digitization, risk segmentation.
- **Phase 2** — enterprise governance platform shared across the BPI ecosystem (DAM / DIM / DSI): standardized artefacts, workflows, decision logic.
- **Phase 3** — agentic governance: agents draft, validate, route, and flag autonomously; humans intervene only where risk requires.
