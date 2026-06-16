"""Document preview + guarded removal (hybrid editability policy).

SOE submission packages are immutable (master); analyst-attached supporting
material can be removed before the NOTA is finalized.
"""
from tests.conftest import DRAFTER


def _make_case_with_docs(client):
    case_id = client.post("/api/cases", data={"title": "Doc lifecycle"},
                          headers=DRAFTER).json()["case_id"]
    # SOE submission → master (locked)
    client.post(
        "/api/documents/ingest",
        files={"file": ("submission.txt", b"Permohonan divestasi senilai Rp420.000.000.000")},
        data={"doc_type": "submission", "case_id": case_id},
        headers=DRAFTER,
    )
    # analyst-attached supporting material → non-master (removable)
    client.post(
        "/api/documents/ingest",
        files={"file": ("extra_analysis.txt", b"Catatan analis tambahan untuk konteks")},
        data={"doc_type": "supporting", "case_id": case_id},
        headers=DRAFTER,
    )
    docs = client.get(f"/api/cases/{case_id}/documents", headers=DRAFTER).json()
    master = next(d for d in docs if d["is_master"])
    supporting = next(d for d in docs if not d["is_master"])
    return case_id, master, supporting


def test_preview_streams_original_with_inline_disposition(client):
    _, master, _ = _make_case_with_docs(client)
    r = client.get(f"/api/documents/{master['id']}/file", headers=DRAFTER)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/plain")
    assert "inline" in r.headers["content-disposition"]
    assert b"Rp420" in r.content


def test_master_submission_cannot_be_removed(client):
    case_id, master, _ = _make_case_with_docs(client)
    r = client.delete(f"/api/cases/{case_id}/documents/{master['id']}", headers=DRAFTER)
    assert r.status_code == 409                      # locked
    docs = client.get(f"/api/cases/{case_id}/documents", headers=DRAFTER).json()
    assert any(d["id"] == master["id"] for d in docs)  # still there


def test_supporting_document_can_be_removed(client):
    case_id, _, supporting = _make_case_with_docs(client)
    r = client.delete(f"/api/cases/{case_id}/documents/{supporting['id']}", headers=DRAFTER)
    assert r.status_code == 200, r.text
    docs = client.get(f"/api/cases/{case_id}/documents", headers=DRAFTER).json()
    assert all(d["id"] != supporting["id"] for d in docs)   # gone from registry
    # and gone from the retrieval index (preview now 404s)
    assert client.get(f"/api/documents/{supporting['id']}/file",
                      headers=DRAFTER).status_code == 404
