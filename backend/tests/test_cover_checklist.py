"""Auto-reconciled cover-sheet completeness checklist."""
from tests.conftest import DRAFTER


def _case_with(client, docs):
    cid = client.post("/api/cases", data={"title": "Checklist"},
                      headers=DRAFTER).json()["case_id"]
    for fname, dtype in docs:
        client.post(
            "/api/documents/ingest",
            files={"file": (fname, b"isi dokumen untuk pengujian")},
            data={"doc_type": dtype, "case_id": cid},
            headers=DRAFTER,
        )
    return cid


def _items(report):
    return {it["key"]: it for it in report["items"]}


def test_incomplete_when_required_docs_missing(client):
    # only a cover sheet → request + supporting still missing
    cid = _case_with(client, [("A0_lembar_pengantar.txt", "cover_sheet")])
    rep = client.get(f"/api/cases/{cid}/checklist", headers=DRAFTER).json()
    assert rep["complete"] is False
    assert _items(rep)["cover_sheet"]["present"] is True
    assert _items(rep)["request"]["present"] is False
    assert "Surat permohonan / Nota Dinas" in rep["missing"]


def test_complete_when_required_docs_present(client):
    cid = _case_with(client, [
        ("N0_lembar_pengantar.txt", "cover_sheet"),
        ("N1_nota_dinas.txt", "submission"),
        ("N2_feasibility_study.txt", "submission"),
    ])
    rep = client.get(f"/api/cases/{cid}/checklist", headers=DRAFTER).json()
    assert rep["complete"] is True
    assert rep["missing"] == []


def test_collateral_detected_by_filename(client):
    cid = _case_with(client, [
        ("N0_lembar_pengantar.txt", "cover_sheet"),
        ("N1_nota_dinas.txt", "submission"),
        ("N2_feasibility_study.txt", "submission"),
        ("N3_kajian_hukum.txt", "submission"),
        ("N4_surat_rekomendasi_dekom.txt", "submission"),
    ])
    rep = client.get(f"/api/cases/{cid}/checklist", headers=DRAFTER).json()
    items = _items(rep)
    assert items["legal"]["present"] is True       # kajian hukum
    assert items["dekom"]["present"] is True        # rekomendasi dekom
    assert rep["complete"] is True
