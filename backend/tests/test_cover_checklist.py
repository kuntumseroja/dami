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


def test_lease_sop_drops_feasibility_and_dekom(client):
    # Lease (SOP-DAM-003): no FS, no Dekom required → cover + request is complete
    cid = _case_with(client, [
        ("B0_lembar_pengantar.txt", "cover_sheet"),
        ("B1_surat_permohonan_sewa.txt", "submission"),
    ])
    rep = client.get(f"/api/cases/{cid}/checklist?sop=SOP-DAM-003", headers=DRAFTER).json()
    keys = {it["key"] for it in rep["items"]}
    assert "supporting" not in keys and "dekom" not in keys     # not applicable
    assert rep["complete"] is True


def test_mna_sop_requires_legal_and_dekom(client):
    # M&A (SOP-DAM-005): legal + Dekom are REQUIRED, so a bare package is incomplete
    cid = _case_with(client, [
        ("H0_lembar_pengantar.txt", "cover_sheet"),
        ("H1_surat_permohonan_merger.txt", "submission"),
        ("H2_feasibility_study.txt", "submission"),
    ])
    rep = client.get(f"/api/cases/{cid}/checklist?sop=SOP-DAM-005", headers=DRAFTER).json()
    items = _items(rep)
    assert items["legal"]["required"] is True
    assert items["dekom"]["required"] is True
    assert rep["complete"] is False
    assert items["legal"]["label"] in rep["missing"]


async def test_checklist_uses_routing_decision_sop():
    # Without an explicit sop, the profile comes from the case's routing decision.
    from app.adapters.repo_memory import InMemoryCaseRepository
    from app.domain.models import DocumentType, GovernanceDocument
    from app.use_cases.cover_checklist import build_cover_checklist

    repo = InMemoryCaseRepository()
    await repo.save_document(GovernanceDocument(
        id="d1", case_id="c1", doc_type=DocumentType.COVER_SHEET,
        title="lembar_pengantar.pdf"))
    await repo.save_document(GovernanceDocument(
        id="d2", case_id="c1", doc_type=DocumentType.SUBMISSION,
        title="surat_permohonan_sewa.pdf"))
    await repo.save_artefact("c1", "routing_decision",
                             {"applicable_sop": "SOP-DAM-003 — Asset Utilization / Leasing"})

    rep = await build_cover_checklist("c1", repository=repo)
    assert rep.sop == "SOP-DAM-003"                # picked up from routing artefact
    keys = {it.key for it in rep.items}
    assert keys.isdisjoint({"supporting", "dekom"})   # lease profile drops these
    assert rep.complete is True
