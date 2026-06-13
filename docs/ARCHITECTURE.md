# Architecture

## Design principles

1. **Rules decide, AI explains.** Routing, eligibility, and approval thresholds are evaluated by a deterministic YAML rulebook ([config/sop/routing-rules.yaml](../config/sop/routing-rules.yaml)). The LLM never makes a governance decision — it drafts descriptive text, finds inconsistencies, and explains rule outcomes. This is the personal-liability shield: every outcome is reproducible from the rulebook.

2. **Ground everything.** Agents may only use facts present in retrieved `<source>` blocks. Each drafted section and each consistency finding carries its source refs (`document_id#chunk`). Insufficient sources produce an explicit `[DATA TIDAK TERSEDIA]` marker, never invented content.

3. **Humans keep the judgment.** NOTA drafts split sections into `descriptive` (AI-generated, ~80%) and `judgment` (always empty, reserved for the reviewer, ~20%).

4. **Everything is audited.** A single append-only audit log records every AI call, rule firing, ingestion, and workflow transition with a trace id; `/api/cases/{id}/trace` reconstructs the full decision provenance per case.

5. **Risk-based automation.** The `Case` entity enforces human sign-off checkpoints at evaluation/board/decision stages for medium and high-risk cases; low-risk cases flow through automatically. Sign-off identity always comes from the authenticated user, never from request input.

6. **Clean architecture.** Dependencies point inward: `domain` (entities, ports, SOP rules — framework-free) ← `use_cases` (agent and workflow logic against ports) ← `adapters` (Claude, Postgres, pgvector, MinIO, JSONL audit) ← `infrastructure` (config, DI container, security) ← `api` (thin controllers). New external dependencies enter only through a port in `domain/ports.py`.

## Layout (clean architecture)

| Layer | Path | Contents |
|---|---|---|
| Domain | `backend/app/domain/` | `models.py` (Case with checkpoint rule, documents, drafts, findings, User/Role), `ports.py` (LLMGateway, Embedder, VectorStore, CaseRepository, ObjectStorage, AuditLog), `rules.py` (deterministic SOP rule engine + `config/sop/*.yaml`) |
| Use cases | `backend/app/use_cases/` | `ingest_document`, `extract_fields`, `draft_nota`, `check_consistency`, `route_request`, `run_pipeline` (orchestrator), `manage_case` (create/advance/risk-tier), `retrieval` helper |
| Adapters | `backend/app/adapters/` | `llm_claude` (single audited model entry), `vector_pgvector` (+ in-memory twin), `repo_postgres` (cases/documents/artefacts tables; + in-memory twin), `storage_minio` (+ local twin), `embedder_hash` (Sprint-2 swap), `audit_jsonl` |
| Infrastructure | `backend/app/infrastructure/` | `config.py` (adapter selection: `REPO_BACKEND`, `STORAGE_BACKEND`, `AUTH_MODE`), `container.py` (composition root), `security.py` (dev-header auth + OIDC seam, `require_roles`) |
| API | `backend/app/api/routes.py` | Thin controllers; role guards per endpoint |
| Frontend | `frontend/` | React + IBM Carbon; all styling via `src/styles/tokens.scss` (CI-enforced) |

Every adapter has an in-memory/local twin, so the full test suite runs in milliseconds without infrastructure and identically against Postgres + pgvector in CI.

## Roles

`drafter` (ingest, draft), `reviewer` (ingest, draft, consistency, risk tier), `approver` (checkpoint sign-offs, risk tier), `auditor` (traces), `admin` (all). Dev mode reads `X-User-Id` / `X-User-Roles` headers; production switches `AUTH_MODE=oidc` (IdP wiring is the marked seam in `security.py`).

## Provider & deployment portability

**Current stack: Claude API + self-hosted Postgres/pgvector/MinIO (Docker Compose).** Three future targets are standing constraints — none is in use today, all must remain reachable without core rework:

1. **watsonx** (model provider)
2. **AWS** (infrastructure)
3. **Databricks** (data/AI platform)

The mechanism is the same for all three: every external dependency sits behind a port in `domain/ports.py`, so moving a target means writing an adapter and flipping config — additive, never a rework.

| Port | Current adapter | AWS target | Databricks target | watsonx target |
|---|---|---|---|---|
| `LLMGateway` | Claude API (`llm_claude.py`, `claude-opus-4-8`) + role-routed self-host pool (see Model mix below) | Claude Platform on AWS / Bedrock; self-host pool on EKS GPU / SageMaker | Databricks Model Serving (managed + self-host pool) | watsonx.ai inference |
| `Embedder` | Hash placeholder (Sprint 2 swaps) | Bedrock / SageMaker endpoint | Databricks Model Serving embeddings | watsonx embeddings |
| `VectorStore` | pgvector (`vector_pgvector.py`) | RDS/Aurora Postgres + pgvector | Databricks Vector Search | pgvector (co-located) |
| `CaseRepository` | Postgres (`repo_postgres.py`) | RDS/Aurora Postgres | Lakebase / Postgres-compatible | Postgres |
| `ObjectStorage` | MinIO (`storage_minio.py`, S3 API) | **S3 — same S3 API, config-only change** | Unity Catalog volumes / S3 | COS (S3 API) |
| `AuditLog` | JSONL (`audit_jsonl.py`) | S3 Object Lock (WORM, Sprint 6.4) | Delta append-only table | COS Object Lock |
| Compute | Docker Compose | EKS/ECS (containers unchanged) | Databricks Apps / jobs + external containers | Code Engine/OpenShift |

## Model mix & routing

The `LLMGateway` is a **router**, not a single client. Registry: [config/models.yaml](../config/models.yaml). Managed primary (Claude) with a **self-hosted fallback pool** routed per task role, served vLLM-class behind an OpenAI-compatible endpoint (portable to on-prem GPU, AWS EKS/SageMaker, Databricks Model Serving):

| Task role | Used by | Primary (managed) | Fallback (self-host) |
|---|---|---|---|
| Drafting | NOTA descriptive sections (FR-1) | `claude-opus-4-8` | **Qwen3-235B-A22B** (or Qwen3-32B small-footprint) |
| Reasoning specialist | Consistency analysis, contradiction detection (FR-2) | `claude-opus-4-8` | **DeepSeek-R1-Distill-Qwen-32B** |
| Fast extraction / classification | Field extraction, doc classification, routing explanation (FR-4) | `claude-haiku-4-5` | **Mistral Small 3.x** |
| Multimodal / edge | Scanned or image-heavy documents; edge / air-gapped sites | — | **Gemma 3 27B** (upgrade path: Gemma 4) |

Routing policies (audited per call with the policy id that fired):
- **RTE-001** managed-tier outage or rate-limit exhaustion → role fallback model
- **RTE-002** document classification above threshold → self-host tier **forced** (links to Sprint 6.1 data classification)
- **RTE-003** every routed call logs role, tier, model, version (PRD §11.2)
- **RTE-004** fallback models pass the same grounding gate (FR-1) and the 2.4 regression suite **before activation** — no model joins the pool unevaluated

Model-independent invariants: the 100% source-traceability gate, the judgment-section prohibition, and audit logging apply to every model in the mix. Reasoning-model thinking traces are logged to audit, never rendered to users.

Rules that keep this true:

- **No provider/platform feature may leak through a port.** Prompts, structured-output contracts, citation formats, SQL, and storage semantics are defined at the use-case layer in neutral terms. A load-bearing single-provider capability requires an explicit decision recorded here.
- **Everything ships as containers** with config-only environment differences (the 12-factor seam already enforced by `infrastructure/config.py` adapter selection).
- **Postgres dialect discipline**: no extensions beyond pgvector; SQL stays ANSI-compatible where possible so RDS/Aurora and Postgres-compatible targets are drop-ins.
- The PRD's integration touchpoint "IBM enterprise AI infrastructure (watsonx or equivalent)" and open question Q1 (on-prem / private cloud / managed) select **adapters and a deployment profile, not an architecture**.

## Secure AI sandbox posture

- Single audited entry point to the model (`adapters/llm_claude.py`); model id configured via `DAM_MODEL` (default `claude-opus-4-8`, adaptive thinking, structured outputs).
- Enterprise API terms: prompts/outputs are not used for model training.
- Documents stay in MinIO/Postgres inside the deployment boundary; only retrieved excerpts needed for the task are sent to the model. Originals are preserved at `cases/{case_id}/{document_id}/{filename}`.
- Hash-based local embeddings by default — zero external embedding dependency until an enterprise embedder is approved (Sprint 2).
- Full audit trail satisfies the auditability requirement; WORM storage lands in Sprint 6.

## Known gaps (tracked in SPRINT-PLAN.md)

- Embeddings are hash-based placeholders → Sprint 2 (enterprise embedder, hybrid retrieval, reranking, eval harness).
- OIDC validation is a seam, not an implementation → wire the IdP before pilot.
- Audit log is JSONL on disk → WORM object storage in Sprint 6.
