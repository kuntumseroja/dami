"""Semantic chunking (2.2) + hybrid retrieval / RRF / rerank (2.3)."""
import pytest

from app.adapters.reranker import LexicalReranker
from app.domain.models import Chunk
from app.use_cases.chunking import semantic_chunks, split_blocks
from app.use_cases.retrieval import rrf_fuse


# --- 2.2 semantic chunking ----------------------------------------------------

def test_numbered_clauses_become_separate_blocks():
    text = "Pasal 1\nKetentuan umum.\n\nPasal 2\nLingkup.\n\n3. Poin tambahan."
    blocks = split_blocks(text)
    assert any(b.startswith("Pasal 1") for b in blocks)
    assert any(b.startswith("Pasal 2") for b in blocks)
    assert any(b.startswith("3.") for b in blocks)


def test_clause_never_split_across_chunks():
    # clauses long enough that the set exceeds the target → multiple chunks
    pad = "dengan ketentuan dan penjelasan yang cukup panjang untuk memaksa pemisahan"
    text = "\n\n".join(f"{i}. Klausa nomor {i} {pad}." for i in range(1, 60))
    chunks = semantic_chunks(text)
    assert len(chunks) >= 2                      # actually chunked
    for i in range(1, 60):
        clause = f"{i}. Klausa nomor {i} {pad}."
        holders = [c for c in chunks if clause in c]
        assert holders, f"clause {i} split or lost"   # whole clause intact in some chunk


def test_empty_text_yields_no_chunks():
    assert semantic_chunks("") == []
    assert semantic_chunks("   \n  ") == []


# --- 2.3 RRF fusion -----------------------------------------------------------

def _c(ref, content="x"):
    doc, idx = ref.split("#")
    return Chunk(document_id=doc, case_id="cN", doc_type="submission",
                 chunk_index=int(idx), content=content)


def test_rrf_rewards_agreement_across_lists():
    dense = [_c("d#0"), _c("d#1"), _c("d#2")]
    sparse = [_c("d#2"), _c("d#3")]            # d#2 appears in both
    fused = rrf_fuse([dense, sparse], k=4)
    refs = [c.ref for c in fused]
    assert refs[0] == "d#2"                     # agreed-upon item ranks first
    assert set(refs) == {"d#0", "d#1", "d#2", "d#3"}   # union, deduped


# --- 2.3 reranker -------------------------------------------------------------

@pytest.mark.asyncio
async def test_reranker_promotes_term_coverage():
    chunks = [
        _c("d#0", "tidak relevan sama sekali"),
        _c("d#1", "nilai appraisal divestasi aset Rp420 miliar"),
        _c("d#2", "appraisal saja"),
    ]
    out = await LexicalReranker().rerank("appraisal divestasi aset", chunks, k=3)
    assert out[0].ref == "d#1"                  # covers all 3 query terms
    assert out[-1].ref == "d#0"                 # covers none
