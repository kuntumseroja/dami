"""In-memory CaseRepository — tests and DB-less development."""
from app.domain.models import Case, GovernanceDocument, utcnow
from app.domain.ports import CaseRepository


class InMemoryCaseRepository(CaseRepository):
    def __init__(self) -> None:
        self._cases: dict[str, Case] = {}
        self._documents: dict[str, list[GovernanceDocument]] = {}
        self._artefacts: dict[str, list[dict]] = {}

    async def init(self) -> None:
        return None

    async def get(self, case_id: str) -> Case | None:
        case = self._cases.get(case_id)
        return case.model_copy(deep=True) if case else None

    async def save(self, case: Case) -> None:
        self._cases[case.case_id] = case.model_copy(deep=True)

    async def list_all(self, entity: str | None = None) -> list[Case]:
        return [
            c.model_copy(deep=True)
            for c in self._cases.values()
            if entity is None or c.entity.value == entity
        ]

    async def save_document(self, document: GovernanceDocument) -> None:
        self._documents.setdefault(document.case_id or "", []).append(document)

    async def list_documents(self, case_id: str) -> list[GovernanceDocument]:
        return list(self._documents.get(case_id, []))

    async def get_document(self, doc_id: str) -> GovernanceDocument | None:
        for docs in self._documents.values():
            for d in docs:
                if d.id == doc_id:
                    return d
        return None

    async def delete_document(self, doc_id: str) -> None:
        for case_id, docs in self._documents.items():
            self._documents[case_id] = [d for d in docs if d.id != doc_id]

    async def save_artefact(self, case_id: str, kind: str, payload: dict) -> None:
        self._artefacts.setdefault(case_id, []).append(
            {"kind": kind, "payload": payload, "created_at": utcnow().isoformat()}
        )

    async def list_artefacts(self, case_id: str, kind: str | None = None) -> list[dict]:
        rows = self._artefacts.get(case_id, [])
        return [r for r in rows if kind is None or r["kind"] == kind]
