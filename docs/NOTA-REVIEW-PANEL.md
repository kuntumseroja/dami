# NOTA Review Panel — A Multi-Agent Governance Review System

**Design exploration.** How to make a panel of AI agents *discuss, debate, correct, and check* a NOTA draft — across accuracy, legal, financial, risk, and other governance dimensions — before a human signs off. Grounded in the multi-agent-review literature and in SOE corporate-action governance practice.

A NOTA is, in effect, a **corporate-action governance memo for a state-owned enterprise** — the internal review note that supports a decision to dispose of, acquire, invest in, or lease an asset. It is the document on which an SOE officer stakes personal liability. So "review" here is not copy-editing; it is the second-line governance challenge that today consumes ~30% of senior reviewers' time and is the platform's highest-stakes surface.

---

## 1. The reframing: a NOTA review is an investment-committee review

Once we treat the NOTA as a corporate-action memo, the question "what should the AI panel check?" has an authoritative answer from governance practice rather than from intuition. The review dimensions below are drawn from the OECD *Guidelines on Corporate Governance of State-Owned Enterprises* (2024), Indonesia's BUMN Minister Regulation **PER-2/MBU/02/2023** (the operative local rulebook), the IIA **Three Lines Model**, and standard investment-committee due-diligence practice.

### The governance rubric (what every NOTA is checked against)

| # | Dimension | What the reviewer checks | Governance source |
|---|---|---|---|
| 1 | **Legal & regulatory compliance** | Conformity with law and BUMN/Danantara regulation; required follow-up of audit/regulator findings | OECD 2024; PER-2/2023 |
| 2 | **Delegation-of-authority / threshold** | Does the action's value/class map to the correct approving organ? Authority explicit, not assumed; no blanket power-of-attorney | PER-2/2023; DoA matrix |
| 3 | **Financial & valuation soundness** | Valuation basis, projections, downside/exit, recognised accounting standards | OECD materiality; IC practice |
| 4 | **Risk assessment & mitigation** | Material foreseeable risks identified *with* mitigations; scaled to complexity | OECD 2024; PER-2/2023 |
| 5 | **Conflict-of-interest / related-party** | RPT disclosed; conflicts declared; the good-faith, no-conflict record that anchors the business-judgment-rule protection Danantara executives rely on | OECD RPT; PER-2/2023 |
| 6 | **Completeness & disclosure** | Standard format; all material matters disclosed; decision-ready | OECD disclosure; IC practice |
| 7 | **Precedent & strategy consistency** | Aligned with mandate / investment policy; consistent with comparable prior decisions | IC best practice |
| 8 | **Factual accuracy vs. source** | Every claim resolves to the submission package — the platform's grounding gate | Platform FR-1 |

Two structural principles from the same sources shape *how* the panel is wired, not just what it checks:

- **Three Lines Model (IIA, 2020).** The drafting team is the *first line* (owns the action). The review panel is the *second line* — independent challenge, structurally separate from the proposer. The audit trail is the *third line* — assurance. The panel must therefore be visibly **not the drafter**, and its challenge must be real.
- **Four-eyes / maker-checker.** A critical action needs a distinct initiator and approver. The AI panel is a force-multiplier for the *checker* role — but the checker of record stays human. The panel produces findings and a recommendation; a person approves.

> The single most important consequence: **the AI never owns the decision.** It sharpens the human's judgment and removes the mechanical 80% — exactly the platform's existing "rules decide, AI explains; humans keep the judgment" stance, now extended to review.

---

## 2. What the research says — and where it bites

Multi-agent review is well-studied, and the evidence is genuinely double-edged. The design has to bank the gains while engineering out the documented failure modes.

### The case *for* a panel

- **Multi-agent debate improves factuality and reasoning.** Du et al. (2023, MIT) showed that several model instances answering independently, then revising over rounds after reading each other's reasoning, beat single-model and self-reflection baselines on reasoning and factual-validity benchmarks — the canonical "debate helps" result.
- **Self-critique loops lift quality cheaply.** Self-Refine (Madaan et al., 2023) — one model as generator→critic→refiner — and Reflexion (Shinn et al., 2023) — verbal self-feedback in episodic memory — both improve outputs with no training.
- **Principle-guided critique works.** Constitutional AI (Bai et al., Anthropic 2022) critiques and revises outputs against a *written list of principles*. Our governance rubric **is** that constitution — each reviewer critiques against named OECD/BUMN clauses.
- **Anthropic's own multi-agent research system** (orchestrator + parallel specialist subagents + a separate citation pass) "outperformed single-agent Claude Opus 4 by 90.2%" on their internal eval — strong evidence for the orchestrator-worker-with-verifier shape we adopt.

### The case for *caution* (the part most designs ignore)

- **Debate can make accuracy *worse*.** Wynn et al. (2025), *"Talk Isn't Always Cheap"*: models "frequently shift from correct to incorrect answers in response to peer reasoning, favoring agreement over challenging flawed reasoning" — accuracy can drop **even when stronger models outnumber weaker ones**. Drivers: sycophancy and social conformity.
- **Confidence cascades & belief entrenchment.** A confidently-wrong agent pulls the group toward its error; homogeneous agents reinforce shared mistakes rather than catching them.
- **LLM-as-judge is biased.** Zheng et al. (2023): judges show **position bias** (favor the first answer), **verbosity bias** (favor longer), and **self-enhancement bias** (favor their own model family).
- **Multi-agent is expensive.** Anthropic reports multi-agent systems use **~15× the tokens** of a single chat, and warns it is a poor fit when agents must share context or have many dependencies. Reserve it for where the value justifies the cost.

### How the cautions become design rules

| Failure mode | Mitigation in this design |
|---|---|
| Sycophancy / conformity (Wynn) | **Heterogeneous lenses** (different dimensions, different model families/tiers) + an explicit **skeptical stance** prompt — each reviewer is told to find problems, not to approve. |
| Confidence cascades | Confidence **hidden until after** independent scoring; **one** cross-examination round only, so peers inform but don't homogenize. |
| Position / verbosity / self-enhancement bias (Zheng) | Chair **randomizes finding order**, **ignores length**, and is drawn from a **different model family** than the reviewers. |
| Persuasive-but-wrong findings | **Every finding must cite a resolvable source span or a fired rule id** — uncited findings are dropped (the platform's FR-1 grounding gate, applied to critique). |
| Cost (~15×) | **Risk-tier gating**: low-risk NOTAs get a single self-critique pass; only high-value/high-risk actions convene the full debating panel. |
| Determinism where law demands it | Delegation-of-authority **thresholds are decided by the rule engine, not the panel** — the AI explains the rule outcome, never re-litigates it. |

---

## 3. The panel architecture

The flow mirrors a real investment-committee review: independent specialist reads, a bounded round of challenge, then a chair who adjudicates and hands a recommendation to the human approver.

```
            ┌──────────────────────────────────────────────────────────────┐
  NOTA      │  ROUND 1 — Independent review (parallel, blind to each other) │
  draft  ─► │   Legal/Compliance · Financial/Valuation · Risk ·            │
  + sources │   Governance/Disclosure · Accuracy Verifier                  │
            │   each scores ONLY its dimensions, every finding cited        │
            └───────────────┬──────────────────────────────────────────────┘
                            │  findings (with source spans / rule ids)
            ┌───────────────▼──────────────────────────────────────────────┐
  rule      │  ROUND 2 — Cross-examination (ONE round, bounded)            │
  engine ─► │   reviewers see peers' findings once; may challenge or       │
  (DoA      │   concede WITH REASONS; dissent is recorded, not smoothed     │
  thresholds)└───────────────┬──────────────────────────────────────────────┘
                            │  findings + challenges + dissent log
            ┌───────────────▼──────────────────────────────────────────────┐
            │  ROUND 3 — Adjudication (Chair = LLM-judge w/ bias controls)  │
            │   dedupe · resolve disagreement · score severity ·          │
            │   drop uncited · classify Critical/Major/Minor ·            │
            │   produce recommendation + open questions                    │
            └───────────────┬──────────────────────────────────────────────┘
                            │  Review report (findings, dissent, recommendation)
            ┌───────────────▼──────────────────────────────────────────────┐
            │  HUMAN APPROVER  (four-eyes checker — owns the decision)      │
            │   accept / edit / reject each finding · sign off             │
            └──────────────────────────────────────────────────────────────┘
   Every message in every round is written to the append-only audit trail.
```

### The roles (see [config/review-panel.yaml](../config/review-panel.yaml))

- **Specialist reviewers**, one per dimension cluster — Legal & Compliance, Financial & Valuation, Risk, Governance & Disclosure — each a *distinct lens*. Heterogeneity is load-bearing: it is what makes debate help (Wynn) rather than converge on a confident error. Each runs on the best model role for its job (the **reasoning** tier — DeepSeek-R1 / Opus — for legal/financial/risk; a strong general model for disclosure), via the existing `config/models.yaml` router.
- **Accuracy verifier** — the Constitutional-AI-style grounding check: every factual claim in the draft must resolve to a span in the submission. Runs on the fast **extraction** tier.
- **Review Chair (adjudicator)** — the LLM-as-judge, with Zheng's bias controls baked in (order randomization, length-blind, cross-family). The chair never invents findings; it dedupes, resolves dissent, scores severity, and **drops any finding without a citation**.
- **The rule engine** — not an agent. Delegation-of-authority and approval-threshold questions (dimension 2) are answered deterministically and fed in; the panel may explain them but cannot override them.
- **The human approver** — the four-eyes checker of record. The panel hands up a recommendation; the person decides and signs. This is the liability firewall.

### Why this shape and not "N agents free-chat"

Free-form multi-agent chat is exactly the configuration Wynn and Anthropic warn against — high cost, conformity drift, hard to audit. The structure here is deliberately **MetaGPT-style SOP-driven** (Hong et al., 2023): fixed roles, structured artifacts passed between bounded rounds, a single adjudication step. It is the *evaluator-optimizer* and *orchestrator-worker* patterns from Anthropic's "Building Effective Agents," composed — not an open debate club.

---

## 4. Mapping onto the existing platform

The panel is not a new architecture — it slots into the clean-architecture seams already built. Nothing in the domain or other use cases changes.

| Concern | Existing seam it reuses |
|---|---|
| Per-reviewer model selection | `config/models.yaml` roles (reasoning / extraction / drafting) + the `LLMGateway` router (Sprint 2.9) |
| Grounding every finding | the FR-1 hard source-traceability gate (Sprint 2.5) — findings are held to the same standard as drafted text |
| Deterministic threshold dimension | `domain/rules.py` rule engine — already "rules decide, AI explains" |
| Severity taxonomy & resolution | the consistency-checker's Critical/Warning/Informational + resolution workflow (Sprint 3.4/3.5) — the panel emits the same finding shape |
| Human accept/edit/reject + four-eyes | the paragraph-review actions and authenticated sign-off (Sprint 3.2, 1.4) |
| Full debate audit | the append-only `AuditLog` — every reviewer message, challenge, and chair decision recorded with model + version (the FR-10 agent-action-log seed) |
| Risk-tier gating of panel depth | the `Case.risk_tier` checkpoint logic (Sprint 1) |

Concretely, this becomes a `ReviewPanel` port + a `run_review_panel` use case that orchestrates the rounds, with a `panel_review` artefact persisted per case — the same way `draft_nota` and `check_consistency` already work. It is the natural successor to the current single-pass consistency checker and the bridge to the Phase-2 **agentic governance** vision (FR-10): agents that draft, validate, and flag, with humans intervening only on exceptions.

---

## 5. Phasing — earn the cost

Because the full panel costs roughly an order of magnitude more than a single pass, it is introduced in tiers, gated by the risk the NOTA already carries:

| Tier | What runs | When |
|---|---|---|
| **Self-critique** (cheapest) | One model, Self-Refine generate→critique→refine on the draft | Low-risk NOTAs (RSK-001), or as a fast pre-check on every draft |
| **Specialist review** | Parallel specialist reviewers + accuracy verifier + chair; *no* cross-examination | Medium-risk |
| **Full debating panel** | All rounds incl. cross-examination + dissent log | High-value / high-risk corporate actions, board-bound cases |

This maps directly onto the existing risk-tier engine and keeps the ~15× cost where it earns its keep — the strategic, board-level decisions where a missed legal or valuation flaw is the highest-consequence failure.

**Suggested delivery:** prototype the panel as a Sprint 3 enhancement of the consistency checker (specialist-review tier), then graduate to the full debating panel in the Phase-2 agentic-governance work. It depends on the multi-model router (Sprint 2.9) and the grounding gate (Sprint 2.5) being in place first.

---

## 6. Open questions for DAM

1. **Which dimensions are board-mandated vs. advisory?** The rubric defaults severities; DAM compliance should ratify which findings can *block* progression (as the consistency checker's Critical gate already does).
2. **Reviewer model approval.** The reasoning-tier self-host models (DeepSeek-R1) need the same Q2 sign-off as the rest of the model mix; until then the panel runs on the managed tier.
3. **Dissent retention.** Three Lines / audit practice argues for keeping the full dissent log; confirm retention class under the 7-year audit policy.
4. **Human-in-the-loop placement.** Does the panel run before the human review queue (pre-filtering) or alongside it (augmenting the senior reviewer)? Recommendation: pre-filter for low/medium risk, augment for high risk.

---

## References

**Multi-agent review & critique**
- Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., Mordatch, I. (2023). *Improving Factuality and Reasoning in Language Models through Multiagent Debate.* arXiv:2305.14325. https://arxiv.org/abs/2305.14325
- Zheng, L., Chiang, W.-L., Sheng, Y., et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* NeurIPS 2023. arXiv:2306.05685. https://arxiv.org/abs/2306.05685
- Madaan, A., Tandon, N., Gupta, P., et al. (2023). *Self-Refine: Iterative Refinement with Self-Feedback.* NeurIPS 2023. arXiv:2303.17651. https://arxiv.org/abs/2303.17651
- Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., Yao, S. (2023). *Reflexion: Language Agents with Verbal Reinforcement Learning.* NeurIPS 2023. arXiv:2303.11366. https://arxiv.org/abs/2303.11366
- Bai, Y., Kadavath, S., Kundu, S., et al. (Anthropic) (2022). *Constitutional AI: Harmlessness from AI Feedback.* arXiv:2212.08073. https://arxiv.org/abs/2212.08073
- Hong, S., Zhuge, M., Chen, J., et al. (2023). *MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework.* ICLR 2024. arXiv:2308.00352. https://arxiv.org/abs/2308.00352
- Wu, Q., Bansal, G., Zhang, J., et al. (2023). *AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation.* arXiv:2308.08155. https://arxiv.org/abs/2308.08155
- Li, G., Hammoud, H., Itani, H., Khizbullin, D., Ghanem, B. (2023). *CAMEL: Communicative Agents for "Mind" Exploration.* NeurIPS 2023. arXiv:2303.17760. https://arxiv.org/abs/2303.17760
- Qian, C., Cong, X., Liu, W., et al. (2023). *ChatDev: Communicative Agents for Software Development.* arXiv:2307.07924. https://arxiv.org/abs/2307.07924
- Wynn, A., Satija, H., Hadfield, G. (2025). *Talk Isn't Always Cheap: Understanding Failure Modes in Multi-Agent Debate.* arXiv:2509.05396. https://arxiv.org/abs/2509.05396
- Anthropic (2024). *Building Effective Agents.* https://www.anthropic.com/engineering/building-effective-agents
- Anthropic (2025). *How we built our multi-agent research system.* https://www.anthropic.com/engineering/built-multi-agent-research-system

**SOE corporate-action governance**
- OECD (2024). *Guidelines on Corporate Governance of State-Owned Enterprises.* https://www.oecd.org/en/publications/oecd-guidelines-on-corporate-governance-of-state-owned-enterprises-2024_18a24f43-en.html
- Republic of Indonesia (2023). *BUMN Minister Regulation PER-2/MBU/02/2023* — governance & significant corporate activities of SOEs. (Commentary: Assegaf Hamzah & Partners. https://www.ahp.id/navigating-corporate-governance-and-risk-management-requirements-in-the-bumn-omnibus-regulation/)
- Makarim & Taira (2025). *Danantara: Indonesia's New Sovereign Wealth Fund.* https://www.lexology.com/library/detail.aspx?g=080436c6-2eff-44dd-88d3-9414f8928b16
- Institute of Internal Auditors (2020). *The IIA's Three Lines Model.* https://www.theiia.org/globalassets/site/about-us/advocacy/three-lines-model-updated.pdf
- *Maker-checker / four-eyes principle.* https://en.wikipedia.org/wiki/Maker-checker

> **Caveat on Danantara specifics:** publicly verifiable detail covers the statutory shell (Law 19/2003 third amendment, Feb 2025; three-board structure; BPK audit; mandatory audit committee and risk/governance SOPs; the business-judgment-rule protection). Internal delegation-of-authority thresholds and the NOTA/IC review workflow are organisation-internal and not public; the rubric above is anchored on OECD + the operative BUMN regulation and should be ratified against DAM's own SOPs (PRD open question Q3).
