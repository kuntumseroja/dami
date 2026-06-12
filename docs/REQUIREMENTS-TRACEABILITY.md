# Requirements traceability — DAM quick-wins mandate

Target: ~30% productivity improvement.
Status legend: ✅ delivered · 🟦 partial (working, maturing in a planned sprint) · ⬜ planned · 🗺 roadmap (phase 2+).
Last updated after **Sprint 1** (commit `cf56385`).

## 1. Mandate requirements → implementation → verification

| # | Requirement | Implementation | Verification | Status | Remaining work |
|---|---|---|---|---|---|
| 1 | **AI-assisted drafting engine** — NOTA first drafts from submissions, templates, historical notes; descriptive sections only, human keeps judgment | `use_cases/draft_nota.py` — RAG-grounded structured drafting; judgment sections always emitted empty; drafts persisted as `nota_draft` artefacts; `POST /api/agents/draft` (drafter/reviewer roles) | System-prompt hard rules (source-only, no analysis, `[DATA TIDAK TERSEDIA]` on gaps); grounding refs per section | 🟦 | Sprint 3: template store (3.1), grounding verifier (3.2), section review UX (3.3) |
| 2 | **Cross-document consistency checker** — review vs board vs decision vs communication; inconsistencies, outdated refs, missing updates | `use_cases/check_consistency.py` — typed findings with quoted excerpts + resolutions, persisted as `consistency_report` artefacts; `POST /api/agents/consistency/{case_id}` | Structured output schema enforces excerpt-pair + severity per finding | 🟦 | Sprint 3: pairwise scale strategy, dedup, severity calibration (3.4) |
| 3 | **Version control + single source of truth** — master hierarchy, propagation | `domain/models.py:GovernanceDocument` (`is_master`, `parent_doc_id`, `version`); ingestion marks submissions master; `documents` table persists hierarchy; consistency agent treats submission as truth | `test_ingestion_stores_original_and_registers_document` asserts `is_master` | 🟦 | Sprint 3: stale-marking + propagation diff view (3.5) |
| 4 | **Rule-based eligibility & routing** — "approval required?", "which SOP?" from delegation of authority + thresholds | `domain/rules.py` + `config/sop/routing-rules.yaml` (SOP selection, approval thresholds APR-001…004, risk rules RSK-001…003); `use_cases/route_request.py` — rules decide, LLM only explains; decisions persisted | `test_routing_rules_low_value_lease_is_automated`, `test_routing_rules_high_value_needs_board` | ✅ (scaffold rulebook) | Sprint 4: full SOP digitization with SMEs (4.1), what-if simulator (4.2) |
| 5 | **Secure AI sandbox** — no leakage, no external training, auditability | `adapters/llm_claude.py` single audited model entry (`claude-opus-4-8`, adaptive thinking); originals stay in MinIO (`adapters/storage_minio.py`), data in Postgres; local hash embeddings until enterprise embedder approved; append-only audit (`adapters/audit_jsonl.py`) | MinIO round-trip verified; every use case writes an audit record with sources/model | 🟦 | Sprint 2: enterprise embedder (2.1); Sprint 6: injection guards (6.1), PII redaction (6.2), WORM audit (6.4) |
| 6 | **Integrated workflow + document orchestration** — submission → evaluation → board → decision → communication with checkpoints | `domain/models.py:Case.advance()` — checkpoint rule in the entity; `use_cases/manage_case.py` binds authenticated sign-off identity; `use_cases/run_pipeline.py` orchestrates extraction → routing → drafting → consistency; Postgres-persisted (`adapters/repo_postgres.py`) | `test_checkpoint_requires_approver_role` (403 without approver; sign-off actor = authenticated user), suite green on Postgres | ✅ | Sprint 4: notifications/queues (4.3), idempotent reruns (4.5) |
| 7 | **SOP digitization + decision routing engine** — SOPs, decision trees, escalation paths | YAML rulebook `config/sop/routing-rules.yaml` (3 SOPs + fallback); rule ids recorded per decision | Routing tests; `rules_fired` in every `RoutingDecision` and audit record | 🟦 | Sprint 4: one YAML tree per real SOP incl. escalation/exceptions (4.1), SME sign-off |
| 8 | **Risk-based automation segmentation** — low-risk fully automated, complex human-in-the-loop | `RiskTier` + risk rules (RSK-001…003) set tier from rules; `Case.requires_signoff` enforces checkpoints only for medium/high; role-gated tier override (`POST /api/cases/{id}/risk-tier`) | `test_risk_tier_change_requires_role`; checkpoint test; low-tier cases advance with no sign-off | ✅ | Sprint 4: justification-mandatory overrides + override reporting (4.4), hands-free E2E demo (4.6) |
| 9 | **Enterprise governance platform across BPI** (DAM/DIM/DSI) | — | — | 🗺 | Phase 2; informed by pilot data (Sprint 6.6) |
| 10 | **Agentic governance system** — agents draft/validate/route/flag; humans only where needed | `use_cases/run_pipeline.py` is the seed: full agent pipeline per case, gated by risk tier | Pipeline endpoint wired; agent steps audited with child traces | 🟦 (seed) | Phase 2/3; Sprint 4.6 proves the low-risk autonomous path |

## 2. Pain points → mitigations

| Pain point | Mitigation in platform | Requirements |
|---|---|---|
| **A. Inconsistency / multiple versions of truth** (~30% senior time on reconciliation) | Consistency agent + master-document hierarchy; submission is the canonical record | #2, #3 |
| **B. Over-documentation / defensive artefacts** (80% descriptive) | Drafting agent does the descriptive 80%; judgment sections structurally reserved for humans | #1 |
| **C. Fragmented workflow / unclear SOP routing** | Deterministic rulebook answers "which SOP / approval needed?"; workflow engine drives stage progression with checkpoints | #4, #6, #7 |
| **D. Manual repetitive drafting** | Ingestion + extraction pipeline feeds drafting; same data never re-typed | #1, RAG layer |
| **E. No controlled AI / data environment** | Self-hosted boundary (Postgres/MinIO), single audited model entry, grounded RAG, no training on data | #5 |
| **F. Personal liability** | Rules decide / AI explains; codified YAML rulebook with fired-rule ids; sign-off identity from authenticated user only; low-risk flows remove the human entirely; full per-case trace (`GET /api/cases/{id}/trace`) | #4, #8, audit |

## 3. Sprint 1 stories → evidence (commit `cf56385`)

| Story | Acceptance evidence |
|---|---|
| 1.1 Clean architecture | `domain/` has no framework imports; use cases depend on `domain/ports.py` only; adapters carry in-memory/local twins; 7/7 tests pass |
| 1.2 Postgres persistence | `cases`/`documents`/`artefacts` tables (`adapters/repo_postgres.py`); identical suite green vs pgvector/pg16; rows verified post-run |
| 1.3 MinIO storage | Round-trip verified on live MinIO; `storage_key` populated and asserted in ingestion test |
| 1.4 Auth skeleton | 401 unauthenticated (`test_unauthenticated_request_rejected_outside_dev`); 403 reviewer at checkpoint; sign-off actor = authenticated approver; OIDC seam in `infrastructure/security.py` |
| 1.5 Token compliance | Zero hardcoded hex in `src/` (CI grep gate); styling exclusively via `frontend/src/styles/tokens.scss`; 48px interactive elements |
| 1.6 CI | `.github/workflows/ci.yml`: ruff + memory tests + Postgres-service tests + frontend build + token gate |

## 4. Forward traceability (planned)

| Sprint | Requirements advanced |
|---|---|
| 2 — RAG maturity | #1, #2, #5 (retrieval quality is the ceiling on both agents; embedder inside the boundary) |
| 3 — Drafting & consistency quality | #1, #2, #3 (template store, grounding verifier, propagation) |
| 4 — Workflow & SOP completion | #4, #6, #7, #8 (full rulebook, simulator, queues, autonomous low-risk flow) |
| 5 — UI & explainability | #5, F (trace timeline UI), DESIGN-IBMC full compliance |
| 6 — Security & pilot | #5 hardening; measured proof of the 30% target |
