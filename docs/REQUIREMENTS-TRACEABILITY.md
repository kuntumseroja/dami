# Requirements traceability — DAM quick-wins mandate

Target: ~30% productivity improvement.

| # | Requirement | Implementation | Status |
|---|---|---|---|
| 1 | AI-assisted drafting engine (NOTA first drafts from submissions/templates/historical notes; descriptive only, human keeps judgment) | `app/agents/drafting.py` — RAG-grounded structured drafting; judgment sections emitted empty | Scaffolded |
| 2 | Cross-document consistency checker (review vs board vs decision vs communication; inconsistencies, outdated refs, missing updates) | `app/agents/consistency.py` — structured findings with quoted excerpts and resolutions | Scaffolded |
| 3 | Version control + single source of truth (master hierarchy, propagation) | `GovernanceDocument` schema (`is_master`, `parent_doc_id`, `version`); consistency agent treats submission as master | Schema + agent convention; propagation logic TODO |
| 4 | Rule-based eligibility & routing ("approval required?", "which SOP?") from delegation of authority + thresholds | `app/workflow/rules.py` + `config/sop/routing-rules.yaml` | Scaffolded, tested |
| 5 | Secure AI sandbox (no leakage, no external training, auditability) | `app/agents/base.py` single entry point; `app/core/audit.py` append-only log; local embeddings | Scaffolded |
| 6 | Integrated workflow + document orchestration (submission → evaluation → board → decision → communication, checkpoints) | `app/workflow/engine.py` + `app/agents/orchestrator.py` | Scaffolded, tested |
| 7 | SOP digitization + decision routing engine (SOPs, decision trees, escalation) | YAML rulebook in `config/sop/`; extend with one file per SOP | Scaffolded |
| 8 | Risk-based automation segmentation (low → automated, complex → human-in-the-loop) | `RiskTier` + risk rules + checkpoint enforcement in workflow engine | Scaffolded, tested |
| 9 | (Long-term) Enterprise governance platform across BPI (DAM/DIM/DSI) | Multi-tenant artefact/workflow standardization — not in scope for phase 1 | Roadmap |
| 10 | (Long-term) Agentic governance (agents draft/validate/route/flag; humans only where needed) | `orchestrator.py` is the seed: full agent pipeline per case, gated by risk tier | Seed |

## Pain-point mapping

- **A. Multiple versions of truth** → #2, #3
- **B. Over-documentation / defensive artefacts** → #1 (AI does the 80% descriptive load)
- **C. Fragmented workflow / unclear routing** → #4, #6, #7
- **D. Repetitive drafting burden** → #1 + ingestion/extraction pipeline
- **E. Uncontrolled AI / data environment** → #5
- **F. Personal liability** → #4 (codified rules), #8 (human removed from low-risk), audit trail (every decision reconstructable)
