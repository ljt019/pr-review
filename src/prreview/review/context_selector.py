# review/context_selector.py
from pathlib import Path
from collections import namedtuple
from typing import List, Tuple, Set

from prreview.embed.embedding import EmbeddingModel
from prreview.index.vector_store import VectorStore

Chunk = namedtuple("Chunk", "file_path start_line end_line text")

CTX_LINES = 20  # simple surrounding window
ANN_K = 3


def select_context(db_path: Path, hunks: List[Tuple[Path, int, int]], repo_path: Path | None = None) -> List[Chunk]:
    """Return surrounding context plus ANN neighbours for each hunk."""

    chunks: List[Chunk] = []
    seen: Set[tuple[str, int, int]] = set()

    embedder = EmbeddingModel()
    store = VectorStore(db_path.with_suffix(".hnsw"), db_path.with_suffix(".vec.sqlite"), embedder.dim)

    for file_path, start, end in hunks:
        if repo_path:
            path = repo_path / file_path
        else:
            path = Path(file_path)

        if not path.exists():
            continue

        lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        lo = max(0, start - 1 - CTX_LINES)
        hi = min(len(lines), end + CTX_LINES)
        text = "".join(lines[lo:hi])
        
        # Fix common character substitutions that might occur due to encoding issues
        #text = text.replace('ä', '{').replace('å', '}').replace('Ä', '[').replace('Å', ']').replace('Ö', '::')
        
        key = (str(file_path), lo + 1, hi)
        if key not in seen:
            chunks.append(Chunk(*key, text))
            seen.add(key)

        # ------------------------------------------------------------------
        # Tier 2 semantic neighbours
        # ------------------------------------------------------------------
        hunk_text = "".join(lines[start - 1:end])
        vec = embedder.encode(hunk_text)
        for meta in store.query(vec, k=ANN_K):
            m_path = repo_path / meta[0] if repo_path else Path(meta[0])
            if not m_path.exists():
                continue
            m_lines = m_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            m_text = "".join(m_lines[meta[1] - 1: meta[2]])
            
            # Fix common character substitutions that might occur due to encoding issues
            m_text = m_text.replace('ä', '{').replace('å', '}').replace('Ä', '[').replace('Å', ']').replace('Ö', '::')
            
            m_key = (meta[0], meta[1], meta[2])
            if m_key not in seen:
                chunks.append(Chunk(meta[0], meta[1], meta[2], m_text))
                seen.add(m_key)

    return chunks
