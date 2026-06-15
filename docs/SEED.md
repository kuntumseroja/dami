# Running locally: API key &amp; seed data

## 1. The LLM API key (`.env`)

The key lives in **`.env` at the repo root** (created from `.env.example`; `.env` is gitignored — never committed). Edit line 3:

```ini
ANTHROPIC_API_KEY=sk-ant-...      # ← replace with your real key
DAM_MODEL=claude-opus-4-8
```

How each run mode picks it up:

| Run mode | How `.env` is loaded |
|---|---|
| **Docker** (`docker compose up`) | Compose auto-loads `.env` for `${ANTHROPIC_API_KEY}` substitution into the backend container |
| **Local** (`./start.sh`) | `start.sh` sources root `.env` before launching uvicorn (it prints whether the key is set) |

The key is only needed for the **agent endpoints** (draft / consistency / route / pipeline / review panel). Everything else — ingest, persistence, storage, auth, workflow, dashboards — runs without it (ingestion uses the local hash embedder).

> If a container was started before you set the key, restart it so it picks up the value: `docker compose up -d backend`.

## 2. Realistic seed data (with real PDFs)

Two scripts produce reality-shaped data — SOE corporate-action submission packages, in Bahasa Indonesia with English glosses, using real Indonesian SOE names and plausible IDR figures.

```bash
# one-time: generator needs reportlab
backend/.venv/bin/pip install -e "backend[seed]"

# 1) generate the sample documents into samples/  (PDFs + DOCX)
backend/.venv/bin/python scripts/generate_samples.py

# 2) make sure the stack is up (docker compose up  OR  ./start.sh), then seed
backend/.venv/bin/python scripts/seed.py
```

### What you get (3 cases across the delegation-of-authority tiers)

| Case | Action | Value | Tier it exercises | Documents |
|---|---|---|---|---|
| **A** PTPN III | Asset disposal (Kebun Sei Meranti) | Rp420 bn | board-of-directors / high-risk | submission letter (PDF), valuation annex (PDF), draft board note (DOCX) |
| **B** Pelindo | Asset lease (warehouse) | Rp750 mn | below-threshold / low-risk / automated | submission letter (PDF) |
| **C** InJourney | Equity investment (JV) | Rp1.2 tn | board-of-commissioners / high-risk | submission letter (PDF), investment thesis (PDF) |

### Planted defects (for the demos)

- **Case A valuation annex** states a gain of **"130%"** where the figures give **13.2%** (Rp49 bn on a Rp371 bn book value) — the target for the **financial reconciliation agent** (Sprint 3.11), which must recompute and flag it.
- **Case A draft board note** cites **Rp415 bn / 5 June** vs the submission's **Rp420 bn / 3 June** — the target for the **cross-document consistency checker** (FR-2).

These make the highest-value modules self-evident in a walkthrough — the showcase narrative in [PRD-ADDENDUM-2026-06-15.md](PRD-ADDENDUM-2026-06-15.md) §4.

> The generated `samples/` files are committed so the data is reusable without reportlab. Re-run the generator only to change the scenarios.
