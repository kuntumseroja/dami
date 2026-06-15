# Model Cost Model

How the platform keeps LLM spend proportionate to value: the **right tier per task role**, then the cost levers that matter for a document-heavy governance workload. Registry: [config/models.yaml](../config/models.yaml). Pricing per 1M tokens (Claude, current): **Opus 4.8 $5 / $25 · Sonnet 4.6 $3 / $15 · Haiku 4.5 $1 / $5**. (Fable 5 $10 / $50 — not used here; its ceiling isn't needed.)

## Principle: cheapest tier that clears the quality bar

You don't pick one model — the `LLMGateway` router (Sprint 2.9) selects per role:

| Role | Model | Rationale |
|---|---|---|
| Extraction | **Haiku 4.5** | schema-constrained, low reasoning, high volume, latency-sensitive |
| Routing explanation | **Haiku 4.5** | rules already decided; model only phrases |
| NOTA drafting | **Sonnet 4.6** | quality/cost sweet spot for formal bilingual register; ⅗ Opus output price |
| Drafting (board-bound) | **Opus 4.8** | risk-tier-gated escalation for high-stakes cases only |
| Consistency / reasoning lens | **Opus 4.8** | highest-consequence step — a missed Critical reaches a board |
| Reconciliation (3.11) | **Haiku 4.5 + calculator tool** | LLM locates numbers; a deterministic tool does the math |
| Multimodal / scanned | **Opus 4.8 vision** or local **Gemma** | only when OCR confidence is low |

Spend Opus where reasoning is load-bearing (consistency + the review-panel legal/financial lenses); Sonnet for drafting; Haiku for the mechanical high-volume steps.

## Cost levers (in order of impact for this workload)

1. **Prompt caching (~90% off the cached prefix).** Stable system prompts (drafting rules, the 8-type consistency taxonomy, SOP context) and the per-case submission context are reused across draft → consistency → review panel. Cache once per case; downstream agents read at ~0.1×. Highest-ROI change; verify with `usage.cache_read_input_tokens`.
2. **Risk-tier gating.** Low-risk cases (e.g. the Pelindo lease, Rp750 mn, automated) skip the Opus panel — self-critique on Sonnet suffices. High-risk (disposal, investment) earn the full Opus panel. Directly bounds the ~15× multi-agent cost.
3. **Batch API (50% off)** for non-interactive work: historical-NOTA RAG indexing, the 20-case regression evals, overnight document-backlog processing.
4. **Tiering** (the table above): Haiku/Sonnet instead of Opus on the steps that don't need it.

## Per-NOTA-case estimate

Observed from the live Case-A pipeline (~22k input / 6k output for the 4-step run on a small package; a real 50-page package is ~2–4×):

| Strategy | ~Cost per case (small → 50-pp) | Note |
|---|---|---|
| All-Opus (demo default) | ~$0.25 → ~$0.75 | overkill on extract/route |
| **Tiered mix** (above) | **~$0.10 → ~$0.30** | ~60% cheaper, quality preserved where it matters |
| **Tiered + prompt caching** | **~$0.05 → ~$0.15** | recommended pilot setting |

At a pilot volume of, say, 500 cases/month, that's roughly **$25–75/month** on the tiered+cached setting vs. ~$125–375 all-Opus — the model spend is not the binding constraint; review quality and data residency are.

## Managed vs. self-host (sovereignty, not only price)

This is an Indonesian SOE under a data-residency NFR, so the tier choice is partly a sovereignty decision:

- **Managed Claude** (or **Claude Platform on AWS** in-region) — best intelligence-per-rupiah at low/medium volume; per-token, no infra. Right for the pilot and likely production if an approved in-boundary endpoint exists.
- **Self-host pool** (Qwen3-235B drafting, DeepSeek-R1 reasoning, Mistral extraction, Gemma multimodal) — required if data cannot leave the boundary, or economical at high sustained volume where GPU cost amortizes below per-token. Cost flips to fixed GPU spend.

The `LLMGateway` router switches per-role between these via config — no code change — so this stays a policy/config decision pending PRD Q1/Q2.

## Document processing (no LLM tokens)

OCR/structure runs **fully local**, so it adds **zero per-token cost**: Granite-Docling (structure + OCR) primary, Tesseract fallback OCR, multimodal model only as last resort for the hardest pages. The only document-processing LLM spend is that rare multimodal escalation.

> **Bottom line for the pilot:** Haiku (extract/route) + Sonnet 4.6 (draft) + Opus 4.8 (consistency & reasoning), prompt caching on, risk-tier gating on → **~$0.05–0.15 per NOTA**, with intelligence concentrated where a missed finding is most costly.
