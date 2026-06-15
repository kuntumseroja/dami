# Showcase — NOTA Drafting (end to end)

A repeatable demo of the drafting flow: which **doc files** to use, how to **enter the form**, and what to expect. Scenario: **PTPN III asset divestiture (Rp420 bn)** — the seeded Case A.

## 0. Prerequisites

```bash
cp .env.example .env            # set ANTHROPIC_API_KEY (line 3)
docker compose up -d            # or ./start.sh   → app on :3010, API on :8010
backend/.venv/bin/python scripts/generate_samples.py   # makes samples/*.pdf|docx
backend/.venv/bin/python scripts/seed.py               # creates 3 cases + ingests files
```

## 1. The document files (the case package)

The drafting flow needs a **submission package** ingested on a case. The showcase uses the generated PTPN III package in [`samples/`](../samples):

| File | doc_type | Role in the draft |
|---|---|---|
| `A1_surat_permohonan_divestasi.pdf` | `submission` | the request letter — entity, value (Rp420 bn), dates, counterparty |
| `A2_lampiran_valuasi.pdf` | `submission` | valuation annex — book value, appraisal, gain (has the planted 130% error) |
| `A3_draf_nota_dinas.docx` | `review_note` | a prior draft note (has the planted Rp415 bn / date mismatch) |

> These are real PDFs/DOCX in Bahasa Indonesia + English. Bring your own by uploading any PDF/DOCX/TXT with `doc_type = submission`.

## 2. Run it in the UI

1. **Dashboard** (`localhost:3010`) → *New case* → e.g. "Divestasi Kebun Sei Meranti — PTPN III". Copy the `case_id`.
2. **NOTA Drafting** tab → fill the form:
   - **Case ID** — paste the `case_id`
   - **Submission documents** — drag the three files from `samples/` onto the drop zone (each uploads with `doc_type = submission`; pick a **classification**, e.g. *confidential*)
   - **Instructions** (optional) — e.g. *"Fokus pada ringkasan transaksi divestasi dan dasar valuasi."*
3. Click **Generate first draft**. (~35–50 s on Sonnet 4.6.)

If you seeded via `scripts/seed.py`, the files are already ingested — skip the upload and just enter the `case_id`.

## 3. Run it by API (same result)

```bash
CID=case_xxxxxxxx     # from the dashboard or seed output

# draft only
curl -s -X POST http://localhost:8010/api/agents/draft \
  -H "X-User-Id: drafter-1" -H "X-User-Roles: drafter,reviewer" -H "X-User-Entity: DAM" \
  -H "Content-Type: application/json" \
  -d "{\"case_id\":\"$CID\",\"instructions\":\"Fokus pada ringkasan transaksi divestasi dan dasar valuasi.\"}"

# or the whole package: extract → route → draft → consistency
curl -s -X POST http://localhost:8010/api/agents/pipeline/$CID \
  -H "X-User-Id: drafter-1" -H "X-User-Roles: drafter,reviewer" -H "X-User-Entity: DAM"
```

## 4. What you get (live output, claude-sonnet-4-6)

A NOTA with the **descriptive sections AI-drafted, each cited**, and the **judgment sections left blank**:

| Section | Result |
|---|---|
| Latar Belakang | AI draft · `sources: doc#0` |
| Ringkasan Permohonan | AI draft — Surat 042/PTPN-III/DIV/VI/2026, Rp420 bn appraisal |
| Dasar Hukum & Referensi | **[DATA TIDAK TERSEDIA — mohon dilengkapi]** — package has no legal refs; AI refuses to invent them |
| Kronologi & Status | AI draft · cited |
| Data Pendukung | AI draft · cited |
| **Analisis & Pertimbangan** | **blank — human judgment** |
| **Rekomendasi** | **blank — human judgment** |

Three things to point out in a demo:

1. **Every drafted sentence carries a source** (`doc#chunk`) — nothing ungrounded.
2. **Insufficient-source honesty** — the legal-basis section flags missing data instead of hallucinating regulations.
3. **Judgment stays human** — the AI is structurally blocked from the Analysis/Recommendation sections.

Then open the **Consistency** tab (or read the pipeline's `consistency` block) to watch it catch the two planted defects (Rp415-vs-420 and 130%-vs-13.2%), and **Audit** to see each agent step with its model (haiku → haiku → sonnet → opus) and trace id.

## Notes

- The form's per-paragraph **Accept / Edit / Reject** controls are Sprint 3.2 (planned); today the draft renders read-only with sources.
- Drafting needs `ANTHROPIC_API_KEY` set; ingestion/routing-rules do not.
