# Architecture

## Design principles

1. **Rules decide, AI explains.** Routing, eligibility, and approval thresholds are evaluated by a deterministic YAML rulebook ([config/sop/routing-rules.yaml](../config/sop/routing-rules.yaml)). The LLM never makes a governance decision — it drafts descriptive text, finds inconsistencies, and explains rule outcomes. This is the personal-liability shield: every outcome is reproducible from the rulebook.

2. **Ground everything.** Agents may only use facts present in retrieved `<source>` blocks. Each drafted section and each consistency finding carries its source refs (`document_id#chunk`). Insufficient sources produce an explicit `[DATA TIDAK TERSEDIA]` marker, never invented content.

3. **Humans keep the judgment.** NOTA drafts split sections into `descriptive` (AI-generated, ~80%) and `judgment` (always empty, reserved for the reviewer, ~20%).

4. **Everything is audited.** A single append-only audit log (`app/core/audit.py`) records every AI call, rule firing, ingestion, and workflow transition with a trace id. The explainability module reconstructs the full decision trace per case or per trace id.

5. **Risk-based automation.** The workflow engine enforces human sign-off checkpoints at evaluation/board/decision stages for medium and high-risk cases; low-risk cases flow through automatically.

## Components

| Component | Path | Responsibility |
|---|---|---|
| Workflow engine | `backend/app/workflow/engine.py` | Stage machine: submission → evaluation → board → decision → communication, with risk-tier checkpoints |
| SOP rule engine | `backend/app/workflow/rules.py` + `config/sop/*.yaml` | Deterministic SOP selection, delegation-of-authority approval thresholds, risk segmentation |
| Extraction agent | `backend/app/agents/extraction.py` | Structured field extraction from submissions (structured outputs, null-on-absent) |
| Drafting agent | `backend/app/agents/drafting.py` | Descriptive NOTA sections, grounded in RAG, judgment sections left empty |
| Consistency agent | `backend/app/agents/consistency.py` | Cross-document inconsistencies / outdated references / missing updates with quoted excerpts |
| Routing agent | `backend/app/agents/routing.py` | Wraps the rule engine; LLM produces the plain-language explanation only |
| Orchestrator | `backend/app/agents/orchestrator.py` | Runs extraction → routing → drafting → consistency per case |
| RAG | `backend/app/rag/` | pgvector store, embedding interface (swap-in enterprise embedder), retriever with case/doc-type filters |
| Ingestion | `backend/app/ingestion/pipeline.py` | PDF/DOCX/TXT parse → chunk → embed → index |
| Audit & explainability | `backend/app/core/audit.py`, `backend/app/explainability/trace.py` | Append-only JSONL audit, trace reconstruction |
| Frontend | `frontend/` | React + IBM Carbon: Dashboard, Drafting, Consistency, Routing, Audit |

## Secure AI sandbox posture

- Single audited entry point to the model (`app/agents/base.py`); model id configured via `DAM_MODEL` (default `claude-opus-4-8`, adaptive thinking).
- Enterprise API terms: prompts/outputs are not used for model training.
- Documents stay in MinIO/Postgres inside the deployment boundary; only retrieved excerpts needed for the task are sent to the model.
- Hash-based local embeddings by default — zero external embedding dependency until an enterprise embedder is approved.
- Full audit trail satisfies the auditability requirement; replace JSONL with WORM storage for production.

## Production hardening (known gaps in this scaffold)

- Workflow case store is in-memory → move to Postgres tables.
- AuthN/AuthZ (SSO, role-based sign-off identity) not yet wired.
- MinIO upload of original files is configured but the storage call is left to implement in the ingestion pipeline.
- Embeddings are hash-based placeholders — swap in an enterprise embedding model for real retrieval quality.
