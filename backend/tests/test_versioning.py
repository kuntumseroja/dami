"""Document version control (Sprint 3.8, FR-3)."""
import pytest

from app.adapters.audit_jsonl import JsonlAuditLog
from app.adapters.repo_memory import InMemoryCaseRepository
from app.domain.models import (
    DocumentImmutable,
    DocumentLocked,
    DocumentType,
    GovernanceDocument,
    NotLockHolder,
)
from app.use_cases import versioning


def _deps():
    return InMemoryCaseRepository(), JsonlAuditLog("./.test-data/audit")


@pytest.mark.asyncio
async def test_checkout_checkin_creates_version_history():
    repo, audit = _deps()
    await versioning.checkout("c1", "d1", user="u1", repository=repo, audit=audit)
    v1 = await versioning.checkin("c1", "d1", user="u1", content="line a\nline b",
                                  change_summary="first", repository=repo, audit=audit)
    assert v1.version == 1 and v1.author == "u1"
    await versioning.checkout("c1", "d1", user="u1", repository=repo, audit=audit)
    v2 = await versioning.checkin("c1", "d1", user="u1", content="line a\nline c",
                                  change_summary="edit b→c", repository=repo, audit=audit)
    assert v2.version == 2
    versions = await versioning.list_versions("c1", "d1", repository=repo)
    assert [v["version"] for v in versions] == [1, 2]


@pytest.mark.asyncio
async def test_concurrent_checkout_blocked():
    repo, audit = _deps()
    await versioning.checkout("c1", "d1", user="u1", repository=repo, audit=audit)
    with pytest.raises(DocumentLocked):
        await versioning.checkout("c1", "d1", user="u2", repository=repo, audit=audit)


@pytest.mark.asyncio
async def test_checkin_requires_lock_holder():
    repo, audit = _deps()
    await versioning.checkout("c1", "d1", user="u1", repository=repo, audit=audit)
    with pytest.raises(NotLockHolder):
        await versioning.checkin("c1", "d1", user="u2", content="x",
                                 change_summary="", repository=repo, audit=audit)


@pytest.mark.asyncio
async def test_diff_between_versions():
    repo, audit = _deps()
    await versioning.checkout("c1", "d1", user="u1", repository=repo, audit=audit)
    await versioning.checkin("c1", "d1", user="u1", content="line a\nline b",
                             change_summary="", repository=repo, audit=audit)
    await versioning.checkout("c1", "d1", user="u1", repository=repo, audit=audit)
    await versioning.checkin("c1", "d1", user="u1", content="line a\nline c",
                             change_summary="", repository=repo, audit=audit)
    diff = await versioning.diff_versions("c1", "d1", 1, 2, repository=repo)
    assert "-line b" in diff and "+line c" in diff


@pytest.mark.asyncio
async def test_immutable_after_review_submission():
    repo, audit = _deps()
    await versioning.checkout("c1", "d1", user="u1", repository=repo, audit=audit)
    await versioning.checkin("c1", "d1", user="u1", content="v1",
                             change_summary="", repository=repo, audit=audit)
    # simulate submit-to-review
    await repo.save_artefact("c1", "review_submission", {"acknowledged": False})
    assert await versioning.case_immutable("c1", repository=repo) is True
    with pytest.raises(DocumentImmutable):
        await versioning.checkout("c1", "d1", user="u1", repository=repo, audit=audit)


@pytest.mark.asyncio
async def test_master_edit_flags_propagation():
    repo, audit = _deps()
    await repo.save_document(GovernanceDocument(id="d1", case_id="c1",
                             doc_type=DocumentType.SUBMISSION, title="master.pdf",
                             is_master=True))
    # two versions of the master + a derived draft → dependents possibly stale
    for content in ("v1", "v2"):
        await versioning.checkout("c1", "d1", user="u1", repository=repo, audit=audit)
        await versioning.checkin("c1", "d1", user="u1", content=content,
                                 change_summary="", repository=repo, audit=audit)
    await repo.save_artefact("c1", "nota_draft", {"sections": []})
    status = await versioning.propagation_status("c1", "d1", repository=repo)
    assert status["is_master"] is True
    assert status["dependents_possibly_stale"] is True
    assert "nota_draft" in status["dependents"]
