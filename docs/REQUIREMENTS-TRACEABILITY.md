# Requirements traceability — PRD ↔ implementation ↔ sprint plan

**Source of truth:** [dam-prd.pdf](../dam-prd.pdf) (PRD v1.0, June 2026). Requirement ids, priorities, acceptance criteria (AC-x.y), and metric thresholds below are the PRD's.
Status legend: ✅ meets PRD spec · 🟦 partial (working; gap named, delivery story scheduled) · ⬜ planned · 🗺 Phase 2.
Last updated after **Sprint 1** (`cf56385`) and PRD alignment.

## 1. Functional requirements (PRD §7–8) → implementation → delivery

| FR | Requirement (priority) | Implemented today | Known gaps vs PRD | Delivering stories | Done by |
|---|---|---|---|---|---|
| FR-1 | AI-Assisted Drafting Engine (P1) | `use_cases/draft_nota.py`: RAG-grounded descriptive drafting, judgment sections emitted empty, per-section source refs, drafts persisted + audited | Traceability is per-section, PRD demands **per-sentence 100% hard gate** (AC-1.3) with suppression placeholder; no paragraph accept/edit/reject (AC-1.5); no contamination scan (AC-1.4); no latency SLA measurement (AC-1.1); no 20-case regression suite (AC-1.6) | 2.2–2.6, 2.8, 3.1–3.3 | **Sprint 3** |
| FR-2 | Cross-Document Consistency Checker (P1) | `use_cases/check_consistency.py`: typed findings with excerpt pairs + resolutions, persisted + audited | Severity scheme is critical/major/minor — PRD prescribes **8-type taxonomy with Critical/Warning/Informational** (configurable); no resolution workflow (Resolved/Accepted-as-is/Deferred); no auto-trigger + acknowledgment gate (AC-2.7); no **board-stage Critical block** (AC-2.5); no precision/recall injection tests (AC-2.2/2.3) | 3.4–3.7, 3.9 | **Sprint 3** |
| FR-3 | Version Control + Single Source of Truth (P1) | `GovernanceDocument` hierarchy (`is_master`, `parent_doc_id`, `version`) persisted; submissions auto-master (test-asserted) | No version history records, checkout/check-in locking, diff view, post-queue immutability, or propagation check on master edit | 3.8 | **Sprint 3** |
| FR-4 | Rule-Based Eligibility & SOP Routing (P1) | `domain/rules.py` + YAML rulebook; rules decide / LLM explains; fired rule ids logged; routing tests green | Output lacks **pre-conditions + expected timeline**; no ambiguity→human-resolver path; rules not editable by SOP owners without release; rule *version* not recorded; no <30 s SLA measurement | 4.2–4.4 | **Sprint 4** |
| FR-5 | Secure Enterprise AI Sandbox (P1) | Single audited model entry (`adapters/llm_claude.py`), MinIO/Postgres boundary, RBAC skeleton, append-only audit; **data classification seam on every document (Sprint 1.8)** — set at intake, persisted, ready for the router's RTE-002 tier gate | Model/embedder pending Q1/Q2 approval (ports keep swappable); classification *enforcement* (tier gate), IT monitoring dashboard, network-level public-AI block, and red-team cycle still to build | 2.1, 5.3, 6.1–6.3 | **Sprint 6** |
| FR-6 | Integrated Workflow & Orchestration (P1) | Stage machine with risk-tier checkpoints in `Case` entity; authenticated sign-offs; Postgres-persisted; 403/identity tested | Stages don't match PRD lifecycle (**submission intake → eligibility check → NOTA drafting → internal review → board preparation → decision → communication dispatch**); no entry/exit conditions, owners, notifications, parallel workstreams + merge gates, SLA bottleneck alerts, status dashboard | 2.7, 4.7, 5.1 | **Sprint 4** (dashboard 5.1) |
| FR-7 | SOP Digitization & Decision Routing (P2) | YAML rulebook format, 3 scaffold SOPs, fired-rule audit | No authoring environment, SOP versioning/approval lifecycle (only-approved-active), migration coverage dashboard, or non-technical tree visualization; SOP version not recorded per evaluation | 4.1, 4.2, 4.4 | **Sprint 4** |
| FR-8 | Risk-Based Automation Segmentation (P2) | `RiskTier` rules drive checkpoints; role-gated overrides (tested); low-risk advances unattended | Scoring is amount+type only — PRD requires **multi-dimensional** (value, entity risk, novelty, precedent, regulatory exposure); thresholds need dual-approval; no automation-ratio metric; no auto-escalation/incident on automated-flow errors | 4.4–4.6, 4.8 | **Sprint 4** |
| FR-9 | BPI-wide Enterprise Platform (P3) | Port-based modular architecture + **multi-tenancy seam live (Sprint 1.7)**: `BPIEntity` (DAM/DIM/DSI) on user/case/document/chunk; repositories, vector store, and storage scope by entity; routes enforce tenant isolation; `bpi_oversight` role for cross-entity read — all tested | *Features* on the seam: shared template/SOP libraries, BPI aggregate dashboard, entity-specific customization | Phase 2 (seam in place — no schema migration needed) | 🟦 seam done |
| FR-10 | Agentic Governance System (P3) | `use_cases/run_pipeline.py` orchestrator seed; full agent action audit | Autonomous monitoring/triggering, validation agent, exception-only review interface | 4.8 proves the low-risk autonomous path; rest Phase 2 | 🗺 |

## 2. Non-functional requirements (PRD §9) → delivery

| NFR | Spec | Status / story |
|---|---|---|
| NOTA draft latency | <5 min standard (<10 min large), P95 over 30 days | ⬜ 2.8 |
| Consistency check latency | <2 min (4-artefact set) | ⬜ 3.9 instrumentation |
| Routing latency | <30 s from intake | ⬜ 4.3 |
| Data residency | All processing in DAM-approved infra, no external transmission | 🟦 boundary exists; Q1/Q2 + 6.2 close it |
| Model isolation | Isolated compute, no shared inference | ⬜ Q2 + 6.1 |
| Access control | RBAC via DAM IdP, least privilege | 🟦 roles enforced; OIDC seam → IdP wiring pre-pilot |
| Full action log | Every user/system/AI action, tamper-evident | 🟦 append-only JSONL → 6.4 tamper-evident |
| Log retention | ≥7 years (Indonesian governance/financial regs) | ⬜ 6.4 |
| Availability / backup | 99.5% business hours; daily backup, 30-day PITR | ⬜ 6.5 |
| Hallucination prevention | Unsourced generation **not permitted** | 🟦 prompt-level today → 2.5 hard gate |
| Training | Analyst workflow operable with <4 h training | ⬜ 5.6 |
| SOP enforcement | No file past routing without recorded SOP pathway decision | 🟦 decisions recorded → 2.7 stage gate makes it structural |

## 3. Pain points (PRD §5) → mitigations

| Pain | Mitigation | FRs |
|---|---|---|
| A — Inconsistency / multiple truths (~30% senior time) | Consistency checker + master hierarchy + board-stage Critical gate | FR-2, FR-3 |
| B — Over-documentation as liability shield | AI does the descriptive 80%; judgment structurally human; per-paragraph attribution | FR-1 |
| C — Fragmented workflow / routing (under- & over-routing) | Rule engine suppresses unnecessary approvals; ambiguity → designated resolver; PRD lifecycle with gates | FR-4, FR-6, FR-7 |
| D — Repetitive drafting (80% restatement) | Drafting engine + ingestion/extraction; <5 min first draft | FR-1 |
| E — Uncontrolled AI (hallucination, leakage, no audit) | Sandbox + 100% traceability gate + classification + network block + complete AI interaction log | FR-5, FR-1 |
| F — Personal liability (critical differentiator) | Codified rules with versions, dual-approval changes, authenticated sign-offs, automation removes humans from low-risk steps, 7-yr attributable audit | FR-4, FR-8, NFRs |

## 4. Sprint 1 evidence — foundations for Phase 1 + Phase 2 (11/11 tests, both backends)

| Story | Evidence |
|---|---|
| 1.1 Clean architecture | Framework-free `domain/`; ports-only use cases; adapter twins — enables PRD §10.1 "modular architecture" + "configurable rule engine" |
| 1.2 Postgres persistence | `cases`/`documents`/`artefacts` tables; suite green on pgvector/pg16 |
| 1.3 MinIO storage | Round-trip verified; entity-namespaced `storage_key` asserted in tests |
| 1.4 Auth skeleton | 401/403 tested; sign-off identity = authenticated approver; `bpi_oversight` role added |
| 1.5 Token compliance | Zero hardcoded hex (CI-enforced); DESIGN-IBMC tokens |
| 1.6 CI | ruff + dual-backend tests + build + token gate |
| **1.7 Multi-tenancy seam (FR-9)** | `BPIEntity` on user/case/document/chunk; tenant isolation tested — DAM user cannot list/fetch/advance a DIM case; oversight sees across entities |
| **1.8 Data classification seam (FR-5)** | `DataClassification` set at intake, persisted, round-trip tested; the value RTE-002 will gate model tier on |
| **1.9 Audit & config seams** | Append-only audit records actor (agent/rule_engine/human) + model + identity (FR-10 seed); SOP + model logic in config layers, no release to change (§10.1) |

## 5. PRD open questions gating delivery (§14)

Q1 infra model & Q2 approved models → Sprint 2 · Q3 SOP inventory → Sprint 4 (workshops Sprint 2) · Q4 legal opinion → pre-pilot (R7) · Q5 SOE submission format → Sprints 2/4 · Q6 pilot users → Sprint 6. Tracked in [SPRINT-PLAN.md](SPRINT-PLAN.md) §Dependencies.
