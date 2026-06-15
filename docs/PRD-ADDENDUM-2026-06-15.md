# PRD Addendum — Stakeholder Capability Session, 15 Jun 2026

**Status:** addendum to [dam-prd.pdf](../dam-prd.pdf) (PRD v1.0). **Source:** AI-capabilities highlight session with Danantara Asset Management ([transcription/20260615_160655.ai-capabilities-highlight-summary.md](../transcription/20260615_160655.ai-capabilities-highlight-summary.md)).

> **Provenance caveat (carried from the source):** the summary is machine-generated from a noisy Indonesian/English recording with some hallucinated repetition. The items below are the *clear, repeated* themes; exact wording, mandatory-field lists, and any numeric thresholds must be validated against the audio and ratified with DAM before external distribution.

The session **validated PRD v1.0's direction** — document-heavy investment workflow, AI drafting, consistency checking, multi-agent review, guardrails, the ~30% productivity goal, and the multi-platform stance (AWS / Databricks / Microsoft / IBM watsonx). This addendum records the points that **sharpen or extend** existing requirements, mapped to the FRs.

## 1. New & sharpened requirements

| # | Requirement (from session) | Maps to | Disposition |
|---|---|---|---|
| A1 | **Financial & statistical reconciliation** — independently *recompute* calculations, percentage changes, totals, and derived figures; catch errors like "13% vs 130%" or wrong numerator/denominator | **FR-2 (new sub-capability FR-2a)** | **New build** — dedicated reconciliation agent in the review panel; recomputes with a deterministic calculator tool, not LLM arithmetic. Sprint 3.11 / panel role `financial_reconciliation` |
| A2 | **ICR (handwriting)** in addition to printed OCR; document intake described as an already-trusted capability | **FR-1 ingestion / §10.2** | **Extend** the document-understanding pipeline (Granite-Docling + Tesseract) with an ICR path. Sprint 2.10 |
| A3 | **Mandatory fields & section rules defined up front** — "define mandatory fields and section rules before asking AI to infer everything"; required fields, input rules | **FR-1 (AC-1.2 coverage)** | **Sharpen** the template store: per-template mandatory sections/fields enforced; missing mandatory field blocks completion rather than being silently inferred. Sprint 3.1 |
| A4 | **AI-mistake disclaimers** on every AI-generated output; clear that drafts may contain errors and must be verified | **FR-1 / §11.2** | **New (small)** — a persistent, audited disclaimer on every AI artifact in the UI and exports. Sprint 3.2 / 5.4 |
| A5 | **Cover sheet** as an investment-note artifact type (cover sheet, summary, sector note, decision-support memo) | **FR-1 template store** | **Extend** template types — cover sheet is a first-class NOTA template. Sprint 3.1 |
| A6 | **Supervisory agent confidence + unresolved-issues summary** — a super-agent summarizes confidence, unresolved issues, and items needing human review | **FR-2 panel / §11.2** | **Already designed** — the review-panel Chair output + confidence scores (Sprint 5.5); add an explicit "unresolved issues / needs-human-review" block to the panel report |
| A7 | **Demo/showcase narrative** — a few high-impact modules first; "make stakeholders say 'I need this'" | delivery | **New artifact** — recorded as the showcase scenario below; drives the pilot demo (Sprint 6.6) |

## 2. Already covered by PRD v1.0 + prior addenda (validated, no change)

| Session theme | Where it already lives |
|---|---|
| AI drafting engine (first drafts, not decisions) | FR-1 |
| Cross-document consistency checking | FR-2 |
| Multi-agent orchestration (legal / financial / reconciliation / supervisory agents working in sequence) | NOTA Review Panel — [NOTA-REVIEW-PANEL.md](NOTA-REVIEW-PANEL.md), `config/review-panel.yaml`, Linear AI-162 |
| Checker/maker, human accountability, guardrails | Four-eyes sign-off (FR-6), grounding gate (FR-1), [AI-GOVERNANCE-AND-SECURITY.md](AI-GOVERNANCE-AND-SECURITY.md) |
| Platform options not locked early (AWS/Databricks/Microsoft/watsonx) | Provider & deployment portability — [ARCHITECTURE.md](ARCHITECTURE.md) |
| Data source granularity / protection | Data classification (FR-5/Sprint 1.8), tenant isolation (FR-9/Sprint 1.7), egress posture |
| OCR document intake | Granite-Docling + Tesseract (Sprint 2.10) |
| ~30% productivity | PRD §3.2 success metrics |

## 3. The financial reconciliation agent — design note

The session's clearest *new* capability, and the one with a subtle trap: **an arithmetic checker must not check arithmetic with an LLM.** Models miscompute percentages exactly the way humans do (the "13% vs 130%" class of error). So the reconciliation agent:

- **Extracts** the numeric claims and their stated relationships from the draft and the source submission (LLM, structured output).
- **Recomputes** each derived figure — percentage changes, totals, ratios, growth rates — with a **deterministic calculator / code-execution tool**, never the model's own mental math.
- **Flags** any draft figure that disagrees with the recomputed value beyond a rounding tolerance, citing both the source numbers and the recomputed result.
- Sits in the review panel as the `financial_reconciliation` role (distinct from `financial_reviewer`, which judges *valuation soundness*; this one checks *arithmetic correctness*).

This is the "rules decide, AI explains" philosophy applied to numbers: the computation is deterministic and reproducible; the model only locates the figures and phrases the finding.

## 4. Showcase scenario (drives the pilot demo)

A single end-to-end flow over one realistic investment-document package, chosen to make the value self-evident:

1. **Ingest** the package (OCR/ICR via the document-understanding pipeline).
2. **Extract** key facts — entity, sector, investment ask, figures, assumptions, duration, decision factors — against the mandatory-field template.
3. **Draft** a structured investment note / **cover sheet** (descriptive sections only; judgment blank; disclaimer shown).
4. **Consistency check** the note against source files and prior drafts.
5. **Reconcile** the numbers — recompute percentages and totals; flag the planted "13% vs 130%"-style error.
6. **Legal/compliance** lens flags risky wording / required disclaimers.
7. **Supervisory chair** summarizes confidence, unresolved issues, and what needs human review.
8. **Human** accepts/edits/rejects and signs (four-eyes).

Principle for the demo: **a few high-impact modules done convincingly**, not a tour of everything — and never a claim of autonomous decision-making.

## 5. Risks to clear before external presentation (from the session)

- Validate exact transcript wording against the audio.
- No autonomous-decision claims — position AI as an accelerator with controls.
- Define mandatory fields / section rules before the demo (A3).
- Clarify accountability taxonomy: source error vs. extraction error vs. calculation error vs. user-review failure — each is a distinct, audited failure class.
- Align the data-hosting/security narrative before naming any platform in client-facing material (the portability stance covers this; the *named* target is a DAM decision — PRD Q1/Q2).
