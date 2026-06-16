"""Semantic, structure-aware chunking (Sprint 2.2, FR-1).

Governance docs (NOTA, SOP, valuation annexes) are structured: headings,
numbered clauses, lettered sub-points, tables. Splitting them by character
count breaks a clause mid-sentence and wrecks retrieval. This chunker:

  * splits text into structural BLOCKS (a heading, a numbered/lettered clause,
    or a paragraph) — Bahasa Indonesia + English markers (Pasal, Ayat, 1., a),
    (i), bullets, ALL-CAPS headings);
  * packs blocks into chunks up to a target size, NEVER splitting a single
    clause across two chunks;
  * carries the last block as overlap so context spans the boundary;
  * falls back to sentence splitting only when one block alone exceeds the cap.

No model call — deterministic, testable.
"""
import re

TARGET_CHARS = 3500          # ~900 tokens (≈4 chars/token) — within 512–1024-token band
HARD_CAP = 4200              # a chunk never exceeds this
OVERLAP_BLOCKS = 1           # carry the trailing block into the next chunk

# A line that STARTS a new structural block.
_CLAUSE = re.compile(
    r"""^\s*(
        Pasal\s+\d+ | Ayat\s*\(?\d+ |          # Indonesian statute refs
        BAB\s+[IVXLC]+ |                        # chapter
        \d+[\.\)] |                             # 1.  1)
        \(\d+\) | \([a-z]\) | \([ivx]+\) |       # (1) (a) (i)
        [a-z][\.\)]\s | [IVX]+[\.\)]\s |         # a.  IV.
        [-•▪]\s                                  # bullets
    )""",
    re.VERBOSE,
)


def _is_heading(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 90:
        return False
    # ALL-CAPS-ish heading (letters mostly upper), or ends with ':'
    letters = [c for c in s if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        return True
    return s.endswith(":")


def split_blocks(text: str) -> list[str]:
    """Group lines into structural blocks (clause / heading / paragraph)."""
    blocks: list[str] = []
    cur: list[str] = []

    def flush():
        if cur:
            blocks.append("\n".join(cur).strip())
            cur.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():            # blank line ends a paragraph block
            flush()
            continue
        if _CLAUSE.match(line) or _is_heading(line):
            flush()                     # new clause/heading starts a block
        cur.append(line)
    flush()
    return [b for b in blocks if b]


def _sentence_split(block: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", block)
    return [p.strip() for p in parts if p.strip()] or [block]


def semantic_chunks(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    blocks = split_blocks(text)
    chunks: list[str] = []
    cur: list[str] = []
    size = 0

    def flush():
        nonlocal cur, size
        if cur:
            chunks.append("\n\n".join(cur).strip())
            cur, size = [], 0

    for block in blocks:
        # A single oversized block: emit current, then split it by sentence.
        if len(block) > HARD_CAP:
            flush()
            piece: list[str] = []
            psize = 0
            for sent in _sentence_split(block):
                if psize + len(sent) > TARGET_CHARS and piece:
                    chunks.append(" ".join(piece))
                    piece, psize = [], 0
                piece.append(sent)
                psize += len(sent) + 1
            if piece:
                chunks.append(" ".join(piece))
            continue

        if size + len(block) > TARGET_CHARS and cur:
            tail = cur[-OVERLAP_BLOCKS:] if OVERLAP_BLOCKS else []
            flush()
            cur = list(tail)                 # overlap carries context across the boundary
            size = sum(len(b) for b in cur)
        cur.append(block)
        size += len(block)

    flush()
    return chunks
