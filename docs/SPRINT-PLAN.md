# Sprint Plan — DAM Governance Intelligence Platform

**Horizon:** 12 weeks · 6 sprints × 2 weeks
**Goal:** Ship the phase-1 quick-wins mandate to pilot, with measured progress toward the ~30% productivity target.
**Baseline:** Scaffold commit `e148142` — agents, RAG skeleton, rule engine, workflow engine, Carbon frontend, all verified.

**Design contract:** every UI deliverable follows the IBM token spec at [docs/design/DESIGN-IBMC.md](design/DESIGN-IBMC.md), codified as [frontend/src/styles/tokens.scss](../frontend/src/styles/tokens.scss). Sharp corners (`0px`), IBM Plex Sans 300/400/600 only, 8px spacing scale, 48px touch targets, WCAG AA.

---

## Success metrics (tracked from Sprint 2 onward)

| Metric | Baseline | Target (end of Sprint 6) |
|---|---|---|
| Time to first NOTA draft | manual (~hours) | < 5 min, ≥ 70% of descriptive content accepted without rewrite |
| Senior time on consistency reconciliation | ~30% of time | ≤ 10% — checker catches issues pre-review |
| Low-risk requests fully automated | 0% | ≥ 80% of eligible (RSK-001) flows untouched by humans |
| Routing decisions with full rule trace | n/a | 100% |
| Drafting grounding (statements with source refs) | n/a | ≥ 95%, 0 ungrounded facts in pilot |
| Retrieval relevance (golden-set nDCG@5) | n/a | ≥ 0.8 |

---

## Sprint 1 — Architecture hardening & persistence

*Theme: make the scaffold production-shaped before features pile on (Clean/Hexagonal architecture).*

| # | Story | Acceptance criteria |
|---|---|---|
| 1.1 | Restructure backend into clean-architecture layers: `domain/` (entities + ports), `use_cases/`, `adapters/` (Postgres, MinIO, Claude, pgvector), `infrastructure/` | Domain layer imports no framework; agents depend on `LLMGatewayPort`, `RetrieverPort`, `AuditPort` interfaces; existing tests still pass |
| 1.2 | Replace in-memory case store with Postgres (cases, documents, drafts, findings, sign-offs tables + migrations) | Restart-safe; workflow checkpoint test passes against DB |
| 1.3 | Store original uploads in MinIO; `storage_key` populated on ingest | Round-trip upload → download verified |
| 1.4 | AuthN/AuthZ skeleton: OIDC-ready auth middleware, roles `drafter / reviewer / approver / auditor / admin`; sign-off identity captured from auth context, not form field | Advancing a checkpoint without `approver` role → 403; audit records real identity |
| 1.5 | Frontend token foundation: all pages consume `tokens.scss` custom properties only (no hardcoded hex/px); buttons & inputs at 48px min height; type ramp applied | Visual audit checklist against DESIGN-IBMC §4/§5 passes |
| 1.6 | CI: GitHub Actions — ruff + pytest + frontend build on every push | Pipeline green |

**Exit:** the platform survives restarts, knows who's acting, and the codebase has seams (ports) for everything external.

---

## Sprint 2 — RAG production maturity

*Theme: retrieval quality is the ceiling on every agent; raise it and prove it.*

| # | Story | Acceptance criteria |
|---|---|---|
| 2.1 | Swap hash embeddings for an approved enterprise embedding model behind `EmbedderPort` (env-selected) | Config flag switches provider; dims handled via migration |
| 2.2 | Semantic chunking: respect headings/clauses/tables of governance docs (PDF & DOCX structure-aware), 512–1024 tokens, 10–20% overlap | Chunk boundaries never split a numbered clause; unit tests on sample NOTA/SOP docs |
| 2.3 | Hybrid retrieval: pgvector dense + Postgres full-text (BM25-style) with reciprocal-rank fusion | Hybrid beats dense-only on golden set |
| 2.4 | Reranking stage behind `RerankerPort` (cross-encoder or LLM-rerank fallback) | Top-5 after rerank ≥ top-10 before, measured |
| 2.5 | Evaluation harness: golden question set from real (sanitized) DAM documents; nDCG@5, recall@10, faithfulness spot-checks; runs in CI nightly | Dashboarded metrics; regression fails the build |
| 2.6 | Citation integrity: every drafted sentence carries chunk refs; UI renders click-through to source excerpt | Clicking a source ref opens the exact excerpt |

**Exit:** retrieval measurably good and regression-protected; every AI statement traceable to a source the user can open.

---

## Sprint 3 — Drafting & consistency quality

*Theme: the two flagship agents go from demo to dependable.*

| # | Story | Acceptance criteria |
|---|---|---|
| 3.1 | Template store: per-template section structures (descriptive vs judgment) managed in DB; drafting agent consumes the template, not hardcoded headings | New template → new NOTA structure with zero code change |
| 3.2 | Grounding verifier: post-draft pass flags any sentence not supported by its cited chunks; unsupported text rendered with a warning state (token `--ibm-warning`) | 0 silently-ungrounded sentences in test set |
| 3.3 | Section review UX: accept / edit / regenerate per section in the Drafting workspace; edits stored as learning signal | Reviewer completes a full NOTA cycle in UI; diff history persisted |
| 3.4 | Consistency at scale: pairwise comparison strategy for >2 documents (master-vs-derived first), finding dedup, severity calibration on labelled examples | Findings stable across reruns (±1); no duplicate findings |
| 3.5 | Version control & propagation: master document hierarchy; on master change, mark derived artefacts stale; propagation diff view ("what must change where") | Editing the submission flags every stale derived doc with the affected excerpts |
| 3.6 | Consistency UI per DESIGN-IBMC: side-by-side excerpts, severity badges (pill radius `12px`, semantic colors), elevated cards (Level 2) | Visual audit passes |

**Exit:** pain points A (multiple truths) and B/D (drafting burden) are functionally solved end-to-end, with humans in control of judgment.

---

## Sprint 4 — Workflow, SOP digitization & risk automation

*Theme: codify the rulebook completely; remove humans from low-risk flows, safely.*

| # | Story | Acceptance criteria |
|---|---|---|
| 4.1 | Full SOP digitization: one YAML decision tree per real DAM SOP (with DAM SMEs), including escalation paths and exception branches | Rulebook reviewed and signed off by DAM governance lead |
| 4.2 | Rule simulation ("what-if") UI: enter request parameters, see fired rules and path through the decision tree before submitting | Tree visualization renders the evaluated path |
| 4.3 | Checkpoint notifications: pending sign-offs surface in a queue per role; email/webhook hooks | Approver sees a work queue; advancing requires their identity |
| 4.4 | Risk-tier override with mandatory justification, fully audited; override rate reported | Override without justification impossible; report lists all overrides |
| 4.5 | Orchestrator hardening: idempotent pipeline reruns, retries with backoff on model errors, partial-failure recovery | Killing the pipeline mid-run and rerunning produces a consistent state |
| 4.6 | End-to-end low-risk flow: eligible request goes submission → communication with zero human touches, every step audited | Demo case completes hands-free; audit trail reconstructs it completely |

**Exit:** pain points C (routing) and F (liability) addressed: every decision rule-grounded, low-risk flows human-free.

---

## Sprint 5 — UI polish, explainability & dashboard

*Theme: ui-design-pro pass over the whole surface, strictly inside the IBM token spec.*

| # | Story | Acceptance criteria |
|---|---|---|
| 5.1 | Dashboard upgrade: rich KPI cards — label small / value large (tabular-nums) / trend arrow + sparkline; each metric appears exactly once | KPI cards match DESIGN-IBMC card spec; no redundant metrics |
| 5.2 | Case detail page: workflow progress indicator, full-width artefact table, actions collapsed to overflow menu | Two-column layout; tables over card grids |
| 5.3 | Explainability view: per-case decision timeline (ingestion → extraction → routing → draft → consistency → sign-offs) with expandable traces, source links, fired rules | Any output reachable to its full provenance in ≤ 2 clicks |
| 5.4 | Interaction states everywhere: hover/active/disabled per token spec, loading skeletons, toast notifications, empty states, error states | No interaction without feedback; states match DESIGN-IBMC §4 exactly |
| 5.5 | Accessibility: WCAG AA contrast audit (4.5:1), keyboard nav, focus outlines (`2px solid #0F62FE`, offset 2px), 48px touch targets | Automated axe scan + manual keyboard pass clean |
| 5.6 | Responsive pass per DESIGN-IBMC §8 breakpoints (320/640/1024/1440) | Layouts verified at all four breakpoints |

**Exit:** the product looks and behaves like enterprise IBM software, and every AI decision is visually explainable.

---

## Sprint 6 — Security, observability & pilot

*Theme: production readiness and proof of the 30% target.*

| # | Story | Acceptance criteria |
|---|---|---|
| 6.1 | AI guardrails: prompt-injection defenses on ingested document content (source text fenced + instruction-stripping), output filters, per-user rate limits | Red-team prompt set blocked; documented |
| 6.2 | PII/confidentiality controls: configurable redaction before model calls; data-flow documentation for security review | Security checklist signed |
| 6.3 | Observability: token/cost tracking per agent per case, latency dashboards, model-call success rates, cache hit rates (prompt caching on stable system prompts) | Cost per NOTA draft visible; prompt cache read-rate > 0 verified |
| 6.4 | Audit hardening: move JSONL audit to WORM-capable storage (object-lock bucket), retention policy | Audit records immutable; retention configured |
| 6.5 | Deployment: Helm chart / compose-prod profile, backups, secrets management, DR runbook | Staging environment stood up from scratch via pipeline |
| 6.6 | Pilot: one real SOP flow with the DAM team, 2-week measurement of the success metrics vs baseline | Pilot report with measured productivity delta vs the 30% target |

**Exit:** pilot running on real cases with measured results; phase-2 (BPI-wide platform) scoping informed by data.

---

## Cross-cutting working agreements

- **Definition of Done:** code + tests + audit events + token-compliant UI + docs updated (ARCHITECTURE.md / traceability matrix).
- **Architecture rule:** new external dependencies enter only through a port in `domain/interfaces`; no framework imports in domain or use-case layers.
- **AI rule:** rules decide, AI explains. No LLM output ever gates a governance decision; every model call audited with sources.
- **Design rule:** no hex, px, shadow, or radius outside `tokens.scss`. Deviations require documented rationale (DESIGN-IBMC §7).
- **Model config:** `claude-opus-4-8`, adaptive thinking, structured outputs via `messages.parse`; stable system prompts marked for prompt caching.

## Risks

| Risk | Mitigation |
|---|---|
| SOP content not available digitized | Sprint 4.1 SME workshops scheduled in Sprint 2; fallback = pilot with the 3 scaffolded SOPs |
| Enterprise embedding model approval delays | Port abstraction (2.1) lets pilot run on interim approved model; hash fallback keeps dev unblocked |
| Bahasa Indonesia retrieval quality | Golden set is bilingual from day one (2.5); chunking tests include Indonesian legal phrasing |
| Reviewer trust in AI drafts | Grounding verifier (3.2) + per-sentence citations (2.6) make rejection cheap and visible |
| Scope creep toward phase-2 (DIM/DSI) | Traceability matrix is the contract; phase-2 items live in roadmap only |
