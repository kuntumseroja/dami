# AI Governance &amp; Information Security

The DAM platform is a governance system — its own AI and data handling must be governed at least as rigorously as the documents it processes. This page consolidates the controls that are otherwise spread across the architecture, the model registry, and the sprint plan, and maps each to its PRD clause. It is the reference for the legal/compliance review the PRD requires before go-live (§10.1, §11.2).

---

## Part 1 — AI Governance

### Principle: the AI never owns a decision

| Control | How it works | Where | PRD |
|---|---|---|---|
| **Rules decide, AI explains** | SOP selection, approval thresholds, and risk tiers are evaluated by a deterministic rulebook; the model only phrases the explanation and can never override a fired rule | `domain/rules.py`, `use_cases/route_request.py` | §10.1, FR-4 |
| **RAG-grounded generation, hard gate** | Every generated sentence must cite a retrievable source passage; an unsourced sentence is **suppressed** and replaced with "Low confidence — manual input required" — never shown | Sprint 2.5 (drafting use case) | §10.1, FR-1, R1 |
| **Humans keep the judgment** | NOTA descriptive sections are AI-drafted (~80%); judgment sections are reserved for humans and a scan blocks any AI text there as a Severity-1 incident | `draft_nota.py`, Sprint 3.3 | FR-1 |
| **Confidence scores surfaced** | AI confidence is shown alongside generated content so reviewers prioritise effort | Sprint 5.5 | §11.2 |

### Principle: every AI action is attributable and reproducible

| Control | How it works | Where | PRD |
|---|---|---|---|
| **Complete AI interaction log** | Every model call is audited with role, tier, **model id + version**, the authenticated identity, retrieved sources, and fired rules | `adapters/audit_jsonl.py`, all use cases | §11.2, NFR auditability |
| **Model-change governance** | No model version changes in production without documented approval; any model entering a role must pass the 20-case regression suite first (router policy RTE-004) | `config/models.yaml`, Sprint 2.4/2.9 | §11.2 |
| **Per-case provenance** | Any output is reconstructable to its inputs, sources, rules, and sign-offs in ≤2 clicks | `/api/cases/{id}/trace`, Sprint 5.4 | §10.1 |
| **Reasoning traces logged, not shown** | Reasoning-model (DeepSeek-R1) thinking is captured to the audit trail but never rendered to users | model mix | §11.2 |

### Principle: the AI environment is controlled

| Control | How it works | Where | PRD |
|---|---|---|---|
| **No external training, no leakage** | Inference runs inside the DAM boundary; the managed tier uses enterprise terms (no training on data); the self-host tier keeps everything local | model mix, FR-5 posture | FR-5, R2 |
| **Two-tier model mix, role-routed** | Managed (Claude) + self-host (Qwen3 / DeepSeek-R1 / Mistral / Gemma) per task role; classification can force the self-host tier (RTE-002) | `config/models.yaml` | FR-5 |
| **Red-team / adversarial cycle** | Hallucination rates, boundary cases, and prompt-injection-via-document-content tested before go-live and at each major model update | Sprint 6.3 | §11.2, R1 |
| **Public-AI prohibition** | Formal policy cutover plus a network-level block on submission content to external AI endpoints once the sandbox is live | Sprint 6.2 | §11.3, R2 |

### AI lifecycle gate (per model, per role)

```
candidate model → 20-case regression suite (≥0.75 avg / P10 ≥0.60, ≤3pp regression)
              → grounding-gate conformance (100% traceability holds)
              → red-team pass (hallucination + injection)
              → documented approval recorded in audit
              → activated in config/models.yaml (RTE-004)
```

---

## Part 2 — Information Security

### Data residency &amp; isolation

| Control | Specification | Where | PRD |
|---|---|---|---|
| **Data residency** | All governance content processed and stored within DAM-approved infrastructure; no external transmission beyond the enterprise model endpoint and the M365 system of record | deployment profile | NFR, FR-5 |
| **Model isolation** | Inference in an isolated compute environment; no shared inference with external tenants | self-host tier / private managed | NFR |
| **Tenant isolation** | Entity scoping (DAM/DIM/DSI) on every record; repositories, vector store, and storage filter by entity; cross-tenant access returns not-found | Sprint 1.7 (`BPIEntity`) | FR-9 |
| **Data classification** | Every document classified at intake (public → restricted); classification gates which model tier may process it | Sprint 1.8 / 6.1 | FR-5, §11.1 |

### Access control &amp; identity

| Control | Specification | Where | PRD |
|---|---|---|---|
| **RBAC** | Roles `drafter / reviewer / approver / auditor / admin / bpi_oversight`, least-privilege per route, integrated with DAM's identity provider (OIDC seam) | `infrastructure/security.py` | NFR, FR-5 |
| **Authenticated sign-off** | Checkpoint sign-off identity comes from the authenticated user, never request input | `manage_case.advance_case` | FR-6, liability |
| **Document source auth** | OneDrive/SharePoint access is app-only (client credentials) via Microsoft Graph; tokens never enter the sandbox | `adapters/source_graph.py` | §10.2 |

### Document repository &amp; intake

| Control | Specification | Where | PRD |
|---|---|---|---|
| **OneDrive / SharePoint interface** | Documents pulled from the M365 library (OneDrive today; SharePoint library as the governed target) through the standard ingestion pipeline — same chunking, classification, entity scoping, and audit as uploads | `DocumentSource` port, `source_graph.py`, `sync_source.py` | §10.2 |
| **System as the only intake channel** | Governed document types flow through the platform with system-generated ids; ungoverned file-share collaboration is disabled for them | Sprint 3.8 / 4 | R6 |

### Audit, retention &amp; resilience

| Control | Specification | Where | PRD |
|---|---|---|---|
| **Tamper-evident audit** | Append-only log of every user/system/AI action with identity + timestamp; moves to WORM object storage | `audit_jsonl.py` → Sprint 6.4 | NFR auditability |
| **Retention** | Audit logs retained ≥ 7 years per Indonesian governance/financial regulation | Sprint 6.4 | NFR |
| **Availability &amp; backup** | 99.5% uptime in business hours; daily backup; 30-day point-in-time recovery | Sprint 6.5 | NFR reliability |
| **Encryption** | TLS in transit; storage/database encryption at rest provided by the deployment target (S3 SSE / RDS / MinIO encryption) | infra profile | NFR (security) |

### Network egress posture

- The container's outbound egress is allow-listed: the enterprise model endpoint, Microsoft Graph (document source), and the package mirror only.
- Under an **edge / air-gapped profile** (router policy RTE-005), all model roles pin to self-host, document understanding (Granite-Docling + Tesseract) runs locally, and the OneDrive/SharePoint source is detached — the platform operates with **zero external egress**.

---

## Review checklist (pre-go-live)

- [ ] Legal opinion on AI-assisted content in signed artefacts (PRD Q4) recorded in audit
- [ ] Audit-trail design reviewed by legal &amp; compliance (§10.1)
- [ ] Red-team report on hallucination + injection (§11.2)
- [ ] Data classification schema aligned to BPI policy (§11.1)
- [ ] Public-AI network block verified with BPI IT security (§11.3)
- [ ] Model registry + change-approval process signed off (§11.2)
- [ ] OneDrive/SharePoint app registration scoped to least privilege (read for intake; read/write only where filing is required)
