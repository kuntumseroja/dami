"""Seed the running DAM platform with realistic demo cases + documents.

Creates thirteen SOE corporate-action cases and ingests their submission
packages (the PDFs/DOCX from generate_samples.py) through the live API, so
the app has reality-shaped data to demo across every delegation tier and the
full spectrum of corporate actions: asset disposal (with a planted valuation
error), low-risk lease (automated), equity investment, global bond issuance,
M&A acquisition, refinery capex / PSN, asset write-off, bank merger /
consolidation (BSI), controlling-stake acquisition (Freeport), rights issue
(SIG), spin-off (Telkomsigma), IPO (Pertamina Geothermal), and dissolution
(Merpati) — mirroring real Indonesian SOE transactions.

Prereqs:
  1. backend/.venv/bin/python scripts/generate_samples.py   (makes samples/)
  2. the stack running (docker compose up  OR  ./start.sh)
Run:
  backend/.venv/bin/python scripts/seed.py
Optional env: DAM_API_BASE (default http://localhost:8010)
"""
import os
import sys
from pathlib import Path

import httpx

BASE = os.environ.get("DAM_API_BASE", "http://localhost:8010")
SAMPLES = Path(__file__).resolve().parents[1] / "samples"

# A DAM drafter (dev-auth headers). Entity DAM is the Phase-1 tenant.
HEAD = {"X-User-Id": "seed-drafter", "X-User-Roles": "drafter,reviewer", "X-User-Entity": "DAM"}

CASES = [
    {
        "title": "Divestasi Kebun Sei Meranti — PTPN III (asset disposal)",
        "classification": "confidential",
        "docs": [
            ("A1_surat_permohonan_divestasi.pdf", "submission"),
            ("A2_lampiran_valuasi.pdf", "submission"),
            ("A3_draf_nota_dinas.docx", "review_note"),
        ],
    },
    {
        "title": "Sewa gudang TPK Surabaya — Pelindo (asset lease, low-risk)",
        "classification": "internal",
        "docs": [("B1_surat_permohonan_sewa.pdf", "submission")],
    },
    {
        "title": "Penyertaan modal JV pariwisata — InJourney (investment)",
        "classification": "restricted",
        "docs": [
            ("C1_surat_permohonan_penyertaan_modal.pdf", "submission"),
            ("C2_tesis_investasi.pdf", "submission"),
        ],
    },
    {
        "title": "Penerbitan obligasi global — PLN (debt issuance)",
        "classification": "confidential",
        "docs": [
            ("D1_surat_permohonan_obligasi.pdf", "submission"),
            ("D2_term_sheet.pdf", "submission"),
        ],
    },
    {
        "title": "Akuisisi saham pengendali tambang nikel — MIND ID (M&A)",
        "classification": "restricted",
        "docs": [("E1_surat_permohonan_akuisisi.pdf", "submission")],
    },
    {
        "title": "Belanja modal kilang Tuban / PSN — Pertamina (capex)",
        "classification": "confidential",
        "docs": [
            ("F1_surat_permohonan_capex.pdf", "submission"),
            ("F2_ringkasan_proyek.pdf", "submission"),
        ],
    },
    {
        "title": "Penghapusan aset kapal tua — Pelni (asset write-off)",
        "classification": "internal",
        "docs": [("G1_surat_permohonan_penghapusan.pdf", "submission")],
    },
    {
        "title": "Merger bank syariah BUMN → BSI — konsolidasi (merger)",
        "classification": "restricted",
        "docs": [("H1_surat_permohonan_merger.pdf", "submission")],
    },
    {
        "title": "Akuisisi saham pengendali Freeport — MIND ID (acquisition)",
        "classification": "restricted",
        "docs": [("I1_surat_permohonan_akuisisi_freeport.pdf", "submission")],
    },
    {
        "title": "Rights issue akuisisi Semen Baturaja — SIG (rights issue)",
        "classification": "confidential",
        "docs": [("J1_surat_permohonan_rights_issue.pdf", "submission")],
    },
    {
        "title": "Spin-off pusat data Telkomsigma — Telkom (spin-off)",
        "classification": "confidential",
        "docs": [("K1_surat_permohonan_spinoff.pdf", "submission")],
    },
    {
        "title": "IPO panas bumi di BEI — Pertamina Geothermal (IPO)",
        "classification": "confidential",
        "docs": [("L1_surat_permohonan_ipo.pdf", "submission")],
    },
    {
        "title": "Pembubaran perseroan non-operasi — Merpati (dissolution)",
        "classification": "restricted",
        "docs": [("M1_surat_permohonan_pembubaran.pdf", "submission")],
    },
]


def main() -> int:
    try:
        if httpx.get(f"{BASE}/health", timeout=5).json().get("status") != "ok":
            raise RuntimeError
    except Exception:
        print(f"ERROR: API not reachable at {BASE}. Start the stack first "
              "(docker compose up  or  ./start.sh).")
        return 1
    if not SAMPLES.exists() or not any(SAMPLES.iterdir()):
        print("ERROR: samples/ is empty. Run scripts/generate_samples.py first.")
        return 1

    with httpx.Client(base_url=BASE, headers=HEAD, timeout=60) as c:
        for spec in CASES:
            case = c.post("/api/cases", data={"title": spec["title"]}).json()
            cid = case["case_id"]
            print(f"\ncase {cid}  {spec['title']}")
            for fname, doc_type in spec["docs"]:
                path = SAMPLES / fname
                if not path.exists():
                    print(f"  ! missing {fname} — skipped")
                    continue
                r = c.post(
                    "/api/documents/ingest",
                    data={"doc_type": doc_type, "case_id": cid,
                          "classification": spec["classification"]},
                    files={"file": (fname, path.read_bytes())},
                )
                r.raise_for_status()
                res = r.json()
                print(f"  ingested {fname:<42} → {res['document_id']} "
                      f"({res['chunks_indexed']} chunks)")

    print("\nSeed complete. Open the Dashboard at http://localhost:3010")
    print("Tip: Case A's valuation annex has a planted 13%-vs-130% error and the "
          "draft note an amount/date mismatch — for the reconciliation & "
          "consistency demos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
