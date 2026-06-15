# Sprint Plan — DAM Governance Intelligence Platform

**Aligned to:** [dam-prd.pdf](../dam-prd.pdf) (PRD v1.0, June 2026) + [PRD-ADDENDUM-2026-06-15.md](PRD-ADDENDUM-2026-06-15.md) (stakeholder capability session) — FR ids, acceptance criteria (AC-x.y), quality metrics, and NFRs below are the PRD's, verbatim where quantitative; `addendum Ax` tags trace stories to the session.
**Horizon:** 12 weeks · 6 sprints × 2 weeks
**Goal:** Phase 1 quick wins to pilot — minimum **30% productivity improvement** in governance document preparation (PRD §1).
**Baseline:** Sprint 1 complete — clean architecture + the foundational seams that let **every Phase 1 (FR-1…8) and Phase 2 (FR-9, FR-10) requirement** land without rework. See the Sprint 1 section below.

**Design contract:** every UI deliverable follows [docs/design/DESIGN-IBMC.md](design/DESIGN-IBMC.md) via [tokens.scss](../frontend/src/styles/tokens.scss).

---

## Success metrics (PRD §3.2 — tracked from Sprint 2, baseline frozen per PRD measurement methodology)

| Metric | Baseline | Phase 1 target | PRD source |
|---|---|---|---|
| Overall governance document preparation time | current | **−30% minimum** | §3.2 |
| Senior analyst time on consistency checking | ~30% | **<10%** | §3.2 |
| NOTA first-draft generation time | manual hours | **<5 min** (standard pkg ≤50 pp; <10 min large) | §3.2, FR-1 |
| Cross-document inconsistency rate at sign-off | significant | **near zero (system-flagged)** | §3.2 |
| Unnecessary approval routing incidents | present | **eliminated for rule-based cases** | §3.2 |
| Controlled AI environment adoption | 0% (public tools) | **100% team migration** | §3.2 |
| Audit trail completeness | absent | **100% of actions logged** | §3.2, NFR |
| Source Traceability Rate | n/a | **100% — hard gate, unsourced sentences never rendered** | FR-1 |
| Descriptive Section Coverage | n/a | **≥95%** | FR-1 |
| Analyst Acceptance Rate / Post-Edit Distance | n/a | **≥60% pilot, ≥75% @3mo / <15% word-change** | FR-1 |
| Judgment Section Contamination | n/a | **zero (hard block; any occurrence = Sev-1)** | FR-1 |
| Checker precision / recall | n/a | **≥90% / ≥85% overall; ≥95% on Critical types** | FR-2 |
| Consistency check latency | n/a | **<2 min (4-artefact file)** | FR-2, NFR |
| Routing decision latency | n/a | **<30 s** | NFR |

---

## Sprint 1 — Foundations for Phase 1 **and** Phase 2 ✅ complete

*Scope was deliberately widened beyond "make it run": Sprint 1 also lays the cross-cutting seams that every later FR — including the Phase 2 BPI-wide platform (FR-9) and agentic governance (FR-10) — depends on. These are the things that are cheap to build into the foundation and ruinous to retrofit, so they ship first even though the features that use them come later.*

| # | Story | Serves | Status |
|---|---|---|---|
| 1.1 | Clean architecture — `domain` (entities, ports, SOP rules) / `use_cases` / `adapters` / `infrastructure`; every external dependency behind a port with an in-memory/local twin | all FR; FR-9 modularity (PRD §10.1), FR-10 orchestrator seam | ✅ `cf56385` |
| 1.2 | Postgres persistence — cases, documents, artefacts; restart-safe; identical suite on pgvector | all FR | ✅ |
| 1.3 | MinIO/S3 object storage — originals preserved; **entity-namespaced keys** | FR-1/FR-3 evidence; FR-9 tenant isolation | ✅ |
| 1.4 | AuthN/AuthZ — roles `drafter/reviewer/approver/auditor/admin` + **`bpi_oversight`**; sign-off identity from auth context; OIDC seam | FR-5 RBAC; FR-9 cross-entity oversight | ✅ |
| 1.5 | Frontend IBM-Carbon token compliance (CI-enforced) | all UI | ✅ |
| 1.6 | CI — ruff + dual-backend tests + frontend build + token gate | all | ✅ |
| **1.7** | **Multi-tenancy seam (Phase 2 FR-9)** — `BPIEntity` (DAM/DIM/DSI) on `User`, `Case`, `GovernanceDocument`, `Chunk`; repositories + vector store scope by entity; routes enforce tenant isolation (own entity only, unless admin/oversight); storage keys namespaced | **FR-9** | ✅ added |
| **1.8** | **Data classification seam (Phase 1 FR-5 / §11.1)** — `DataClassification` (public→restricted) on every document, set at intake, persisted; the value the model router's RTE-002 policy keys off to force the self-host tier | **FR-5** | ✅ added |
| **1.9** | **Audit & rule-engine seams** — append-only audit already records `actor` (incl. `agent`/`rule_engine`) with model + identity (FR-10 agent action log seed; §11.2); SOP/threshold/model logic in config layers (`config/sop/*.yaml`, `config/models.yaml`) editable without release (PRD §10.1 configurable-not-hardcoded) | FR-4/7/8, FR-10, §10.1 | ✅ in place |

**Why widen Sprint 1:** multi-tenancy and data classification are schema- and contract-level concerns. Bolting an `entity` column onto a live single-tenant system, or a classification gate onto an already-flowing pipeline, means a migration plus an audit of every query and every model call. Adding them to the foundation costs a field and a filter. Phase 1 runs single-entity DAM with these seams dormant-but-present; Phase 2 activates DIM/DSI and the BPI oversight dashboard with **no schema migration**.

**Verification:** 11/11 tests green on both in-memory and Postgres backends, including tenant isolation (a DAM user cannot list, fetch, or advance a DIM case; BPI oversight sees across entities) and document classification round-trip.

**Still deferred to later sprints (correctly):** the *features* that ride these seams — FR-9 shared template/SOP libraries and the BPI dashboard, FR-10 autonomous monitoring and the exception-only review interface — remain Phase 2. Sprint 1 guarantees they attach without reopening the core.

---

## Sprint 2 — RAG maturity & the grounding gate (FR-1 core, FR-5, FR-6 alignment)

*Retrieval quality is the ceiling on FR-1/FR-2; the PRD makes grounding a hard gate, not a warning.*

| # | Story | PRD ref | Acceptance criteria |
|---|---|---|---|
| 2.1 | Approved enterprise embedding model behind `Embedder` port. **Provider strategy: Claude API now; watsonx is a future deployment option, not a current dependency** — the port keeps either reachable without core changes (resolve **Q2** with IBM delivery lead) | FR-5, Q1/Q2 | Config-switched provider; no governance text leaves the boundary; a watsonx adapter would be additive only |
| 2.2 | Semantic chunking — structure-aware (headings/clauses/tables) for PDF & DOCX, 512–1024 tokens | FR-1 | Numbered clauses never split; bilingual test docs |
| 2.3 | Hybrid retrieval (dense + full-text, reciprocal-rank fusion) + reranking stage behind `RerankerPort` | FR-1 | Hybrid+rerank beats dense-only on golden set |
| 2.4 | **20-case regression test suite** (anonymized historical NOTAs) + eval harness in CI: RAG Retrieval Relevance **≥0.75 avg / P10 ≥0.60**; model updates blocked on >3pp regression | FR-1 metrics, AC-1.6 | Nightly CI job; scorecard output; update gate enforced |
| 2.5 | **Hard source-traceability gate**: every generated sentence carries a resolvable citation; unsourced sentences suppressed and replaced with *"Low confidence — manual input required"* | FR-1 (100% rate), AC-1.3 | Zero unsourced sentences rendered, validated at generation time |
| 2.6 | Insufficient-source flagging: section gaps marked "Insufficient source material" (engine distinguishes its errors from missing inputs) | FR-1 coverage metric | Coverage ≥95% measured against template section list |
| 2.7 | **Workflow lifecycle alignment** to PRD: submission intake → eligibility check → NOTA drafting → internal review → board preparation → decision → communication dispatch; entry/exit conditions per stage | FR-6 | `Case` stage machine matches PRD stages; migration for existing rows; tests updated |
| 2.8 | Draft Generation Latency SLA instrumentation: P95 <5 min standard / <10 min large, measured over 30-day window | FR-1, AC-1.1, NFR | Latency recorded per draft; dashboard query |
| 2.9 | **Multi-model router (both tiers per role)** behind `LLMGateway` per [config/models.yaml](../config/models.yaml): online API — drafting/reasoning `claude-opus-4-8`, extraction `claude-haiku-4-5`, multimodal `claude-opus-4-8` vision; self-host — Qwen3-235B-A22B/32B, DeepSeek-R1-Distill-Qwen-32B, Mistral Small 3.x, Gemma 3 27B (→ Gemma 4); vLLM OpenAI-compatible serving adapter; policies RTE-001…005 (outage fallback, classification-forced tier, per-call audit, eval-gated activation, edge profile pins self-host) | FR-5, §11.2, R1/R2 | Router selects by role + tier policy; any model entering a role passes grounding gate + 2.4 regression suite; every call audited with role/tier/model/version/policy |
| 2.10 | **Document understanding pipeline**: Granite-Docling structure parsing (layout, tables, reading order, clause structure → structured markdown) + Tesseract **OCR + ICR** (`ind`+`eng`; printed **and handwriting** per stakeholder session A2) for scanned pages; routing born-digital → Docling, scanned → OCR/ICR → Docling, low-confidence → multimodal role; feeds semantic chunking (2.2) | FR-1 ingestion, NFR data residency (fully local), addendum A2 | Scanned Bahasa Indonesia submission (incl. handwritten annotations) produces a structured, chunkable text layer; clause structure preserved end-to-end; pipeline runs with zero external calls |
| 2.11 | **OneDrive / SharePoint document interface** ✅ seam built: `DocumentSource` port + Microsoft Graph adapter (OneDrive drive today, SharePoint library as governed target) + local twin; `sync_from_source` pulls items through the standard ingestion pipeline (same chunking, entity scope, classification, audit). Sprint 2 hardens: delta sync, app-registration least-privilege, egress allow-list | §10.2 (OneDrive migration), R6 | List + pull from a M365 library into a case; system becomes the governed intake channel; tokens never enter the sandbox |

**Exit:** drafting is grounded with a hard gate, measured, and regression-protected; workflow speaks the PRD's language; the platform survives a managed-tier outage on the self-host pool.

---

## Sprint 3 — FR-1/FR-2/FR-3 to full PRD spec

| # | Story | PRD ref | Acceptance criteria |
|---|---|---|---|
| 3.1 | Template store: NOTA template section lists (descriptive vs judgment) in DB; **mandatory fields/sections enforced — a missing mandatory field blocks completion rather than being silently inferred (addendum A3)**; **cover sheet a first-class template type (addendum A5)**; coverage measured per template | FR-1, addendum A3/A5 | New template → new structure, zero code change; missing mandatory field is flagged not invented; cover-sheet template available; AC-1.2 ≥95% coverage on 10 packages across 3 template types |
| 3.2 | **Paragraph-level accept / edit / reject** as discrete tracked actions; full audit record per action (user, timestamp, paragraph id, action, final content); **persistent AI-mistake disclaimer on every AI artifact, in-app and on export, audited (addendum A4)** | FR-1, AC-1.5, addendum A4 | Scripted accept/edit/reject sequence fully reconstructable from audit log; disclaimer present on every AI output and export |
| 3.3 | **Judgment-section contamination zero-gate**: automated scan blocks AI text in judgment sections without explicit analyst authorship; violations raise Sev-1 incident | FR-1, AC-1.4 | 5 test packages → zero contamination; human-authorship prompt visible |
| 3.4 | **Consistency taxonomy alignment** — 8 PRD types (numeric mismatch, date, entity name, stale version ref, missing propagated update, contradictory recommendation, scope deviation, structural omission, formatting) with **Critical/Warning/Informational** severities, configurable defaults | FR-2 | Domain model + checker prompt emit PRD taxonomy; severity overrides via config |
| 3.5 | **Resolution workflow**: Resolved / Accepted-as-is-with-justification / Deferred per flagged item, all logged; one-click "Incorrect flag" feedback loop | FR-2, AC-2.6 | Each action logged with identity + justification; weekly FP aggregation query |
| 3.6 | **Auto-trigger + acknowledgment**: consistency check runs automatically on senior-review-queue submission; file reaches senior inbox only after analyst acknowledges the report; MTT-acknowledgment metric (<4 bh alerting) | FR-2, AC-2.7 | Submitted file without completed+acknowledged report never appears in senior queue |
| 3.7 | **Board-stage Critical gate**: progression to board preparation blocked while unresolved Critical items exist; bypass only via dual-approval override, logged as compliance incident | FR-2, AC-2.5; NFR compliance | Stage transition denied with named Critical items; override path audited |
| 3.8 | **FR-3 version control**: full version history (author/timestamp/change summary), checkout/check-in locking, diff view between versions, immutability after review-queue submission, propagation check on master edit | FR-3 | Master edit surfaces out-of-sync sections in dependents; concurrent-edit conflict prevented; post-queue versions immutable |
| 3.9 | Checker injection-test harness: monthly 10-file injected-discrepancy runs; precision/recall per type (≥93% numeric per AC-2.2, ≥85% semantic recall per AC-2.3); baseline freeze + model-update gate | FR-2 metrics | Injection manifest + automated scoring; CI-runnable |
| 3.10 | **NOTA Review Panel — specialist-review tier** (design: [NOTA-REVIEW-PANEL.md](NOTA-REVIEW-PANEL.md), roster: [config/review-panel.yaml](../config/review-panel.yaml)): heterogeneous specialist reviewers (legal/compliance, financial/valuation, risk, governance/disclosure) + accuracy verifier + bias-controlled chair, scoring a draft against the governance rubric (OECD/BUMN dimensions). Chair report includes a **confidence + unresolved-issues / needs-human-review block (addendum A6)**. Every finding cited (FR-1 gate); thresholds from the rule engine, not the panel; risk-tier-gated depth; full debate audited. Successor to the single-pass checker; **full debating panel (cross-examination) is the Phase-2 / FR-10 bridge** | FR-2 (deepens), FR-10 seed, §10.1, addendum A6 | Specialist tier produces a cited review report a senior reviewer accepts/edits; no uncited finding survives; chair surfaces confidence + open issues; depth gated by risk tier; reviewers run on `models.yaml` reasoning tier |
| 3.11 | **Financial & statistical reconciliation agent (addendum A1)**: extracts numeric claims + their relationships, then **recomputes** percentages, totals, ratios, and growth rates with a **deterministic calculator / code-execution tool — never LLM mental math** — and flags any draft figure that disagrees beyond tolerance, citing source numbers + recomputed value. Panel role `financial_reconciliation` (DIM-CALC); distinct from valuation review | FR-2 (FR-2a), addendum A1 | Planted "13% vs 130%" / wrong numerator-denominator errors caught; arithmetic done by tool not model; each finding cites source figures and the recomputed result |

**Exit:** FR-1, FR-2, FR-3 meet their PRD acceptance criteria end-to-end with the measurement machinery the PRD demands; the review panel (incl. deterministic numeric reconciliation) deepens FR-2 toward the agentic-governance vision.

> **Showcase scenario (addendum §4):** the pilot demo runs one realistic package end-to-end — ingest (OCR/ICR) → extract to mandatory-field template → draft cover sheet (with disclaimer) → consistency check → numeric reconciliation (catch the planted error) → legal/compliance flag → supervisory chair confidence + open-issues summary → human four-eyes sign-off. A few high-impact modules done convincingly; no autonomous-decision claim. Drives Sprint 6.6.

---

## Sprint 4 — FR-4/FR-7/FR-8/FR-6 completion

| # | Story | PRD ref | Acceptance criteria |
|---|---|---|---|
| 4.1 | **SOP authoring & lifecycle**: SOPs as versioned decision trees with effective date, owner, approval status; **only approved SOPs active**; migration coverage dashboard | FR-7, R5 | Unapproved SOP never routes; coverage dashboard live from day one |
| 4.2 | **Decision-tree visualization** for compliance officers (non-technical review/approval) + what-if simulator showing the evaluated path | FR-7, FR-4, R3 | Officer can review/approve a tree without touching YAML; simulator renders fired path |
| 4.3 | **Routing output completion**: applicable SOP + required approvals + **pre-conditions + expected processing timeline**; unnecessary approvals flagged and suppressed; **ambiguous cases flagged and routed to designated human resolver with supporting context** | FR-4 | Intake evaluation returns all four outputs in <30 s; ambiguity path tested |
| 4.4 | **Rule governance**: SOP owners edit rules without software release; **dual-approval on rule/threshold changes**; rule *version* recorded on every decision; simulation environment before production activation | FR-4, FR-8, R3 | Rule change without second approval impossible; every decision logs rule version |
| 4.5 | **Multi-dimensional risk scoring**: transaction value, entity risk rating, novelty, precedent availability, regulatory exposure; below-threshold on all dimensions → fully automated path; any dimension above → human-in-the-loop with score + flagged dimensions + precedents surfaced | FR-8 | Scoring model documented + configurable; automated-vs-assisted ratio on dashboard |
| 4.6 | **Automation safety**: any error/override/exception in an automated flow auto-escalates to a human reviewer and logs an incident | FR-8 | Fault injection → escalation + incident record |
| 4.7 | **FR-6 completion**: assignable stage owners, task notifications with context/deadline/documents, parallel workstreams with merge gates (drafting ∥ routing verification), bottleneck SLA alerts to supervisors | FR-6 | A stalled file past SLA alerts its supervisor; parallel streams merge-gated before board prep |
| 4.8 | Hands-free low-risk E2E: eligible request runs intake → communication dispatch with zero human touches; full audit reconstruction | FR-8, FR-10 seed | Demo case completes autonomously; trace complete |

**Exit:** FR-4, FR-6, FR-7, FR-8 meet PRD spec; the liability model (Pain F) is fully codified.

---

## Sprint 5 — Dashboards, explainability, usability (FR-5/FR-6 surfaces)

| # | Story | PRD ref | Acceptance criteria |
|---|---|---|---|
| 5.1 | **Real-time status dashboard**: per-file current stage, pending actions, elapsed time, projected completion — all stakeholders incl. SOE-visible status tracking | FR-6 | Live board reflects workflow state without refresh |
| 5.2 | **Management dashboard**: analyst acceptance rate, post-edit distance, automation ratio, checker FP rate — the PRD scorecard metrics | FR-1/FR-2/FR-8 metrics | Monthly IBM delivery scorecard derivable from dashboard |
| 5.3 | **AI monitoring dashboard for IT admins**: AI usage, data volume, model versions in service, access anomalies | FR-5 | Real-time view; model version changes require documented approval (§11.2) |
| 5.4 | Explainability view: per-case decision timeline with expandable traces, source links, fired rules + rule versions, sign-offs | §10.1 auditability, Pain F | Any output to full provenance in ≤2 clicks |
| 5.5 | AI confidence scores surfaced alongside generated content to prioritize review effort | §11.2 | Confidence visible per paragraph |
| 5.6 | Interaction/accessibility pass: loading/empty/error states, WCAG AA, keyboard nav, responsive 320/640/1024/1440 — per DESIGN-IBMC | NFR usability | Axe scan clean; **<4 h structured training** validated with a task-based walkthrough script |

**Exit:** every PRD-mandated surface (status, management, IT monitoring, explainability) exists and is token-compliant.

---

## Sprint 6 — Security hardening, ops, and the measured pilot

| # | Story | PRD ref | Acceptance criteria |
|---|---|---|---|
| 6.1 | **Data classification layer**: documents classified at intake; sensitivity level gates which model tier may process them; aligned to BPI policy | FR-5, §11.1 | Above-threshold document never reaches an unapproved tier |
| 6.2 | **Public-AI transition controls**: formal policy cutover + network-level block on submission content to external AI endpoints (with BPI IT security) | §11.3, R2 | Technical control verified; policy comms issued by DAM sponsors |
| 6.3 | **Red-team / adversarial testing cycle** before go-live (hallucination rates, boundary cases, prompt injection via document content); repeat at each major model update | §11.2, R1 | Red-team report; injection corpus blocked |
| 6.4 | **Audit hardening**: tamper-evident storage, **7-year retention**, every user/system/AI action attributable; legal & compliance review of audit design before go-live | NFR auditability, §10.1 | Retention policy configured; legal sign-off recorded |
| 6.5 | **Ops readiness**: 99.5% uptime target during DAM business hours, daily backups, 30-day point-in-time recovery, maintenance-window process; deployment automation (staging from scratch) | NFR reliability | Restore drill passes; staging rebuilt via pipeline |
| 6.6 | **Pilot** (resolve **Q6** pilot users/file types first): baseline snapshot end of week 2 per PRD methodology; daily metrics dashboard; week-4 analyst survey (≥3.5/5, ≥80% report time saved per AC-1.7); monthly scorecard; measure −30% target | §3.2, FR-1 measurement, AC-1.7 | Pilot report vs frozen baseline; go/no-go evidence for Phase 1 gate |

**Exit:** Phase 1 go-live gate evidence complete: all FR acceptance criteria + NFRs verified, pilot measured.

---

## PRD dependencies to resolve (Open Questions §14)

| Q | Question | Owner | Needed by |
|---|---|---|---|
| Q1 | Infrastructure model (on-prem / private cloud / IBM managed). **Portability constraint: future deployment on AWS and Databricks (and watsonx) must remain feasible** — see ARCHITECTURE.md → Provider & deployment portability | BPI IT / IBM | Sprint 2 (2.1); 6.5 deployment automation stays container-based + config-only per target |
| Q2 | Approved AI model(s) for sandbox. **Decision to date: Claude API (claude-opus-4-8) now; watsonx not in use but must remain deployable later** | IBM Delivery Lead | Sprint 2 (2.1) — `LLMGateway`/`Embedder` ports make a future watsonx adapter additive, never a rework |
| Q3 | Complete SOP inventory + Phase-1 priority SOPs | DAM Legal/Compliance | Sprint 4 (4.1) — schedule SME workshops in Sprint 2 |
| Q4 | Legal opinion on AI-generated content in signed artefacts | DAM Legal | Before pilot go-live (6.6), tracks R7 |
| Q5 | SOE submission format/protocol, standard template | DAM / SOE Relations | Sprint 2 (2.2 chunking), Sprint 4 intake |
| Q6 | Pilot users + governance file types | DAM Senior Leadership | Sprint 6 (6.6) |

## Risks (PRD §12 register, mapped to mitigating stories)

| # | Risk | Sev/Likelihood | Mitigation in plan |
|---|---|---|---|
| R1 | AI hallucination in artefacts | Critical / Medium | 2.5 hard traceability gate · 3.2 acceptance gate per paragraph · 6.3 red-team cycle |
| R2 | Data leak to external AI provider | Critical / Low post-sandbox | 2.1 in-boundary models · 6.2 network-level block |
| R3 | Rule-engine misconfiguration → wrong routing | High / Medium | 4.4 dual-approval + simulation env · audit of all decisions with rule version |
| R4 | User resistance / adoption | Medium / Medium | 3.2 review UX keeps analysts in control · 6.6 willing-analyst pilot, early metric sharing |
| R5 | Incomplete SOP digitization | Medium / High | 4.1 coverage dashboard day one · 4.3 ambiguity → human resolver until SOP encoded |
| R6 | Version-control bypass via file shares | Medium / Medium | 3.8 system as only intake channel, system-generated doc ids; OneDrive policy per §10.2 |
| R7 | Liability concerns block sign-off | High / Medium | Q4 legal opinion pre-pilot · 3.2/3.3 explicit AI-vs-human attribution everywhere |

## Out of scope (PRD §13 — enforced in reviews)

Submission preparation for SOEs · formal regulatory filings · financial modeling/valuation · any generation in judgment sections · public-facing communications · DIM/DSI onboarding (Phase 2 PRD).

## Working agreements (unchanged from Sprint 1, plus)

- **Rules decide, AI explains** — no LLM output gates a governance decision (PRD §10.1 "human in the loop for judgment, system for process").
- **RAG over hallucination** — generation not grounded in a retrieved passage is *blocked*, not warned (PRD §10.1).
- **Configurable rules, not hardcoded logic** — SOP/threshold changes are config with dual-approval, never releases (PRD §10.1).
- New external dependencies only through `domain/ports.py`; no hex/px outside `tokens.scss`; every model call audited with sources and model version (§11.2).
