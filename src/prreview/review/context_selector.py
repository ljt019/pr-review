# review/context_selector.py
from pathlib import Path
from collections import namedtuple
from typing import List, Tuple

Chunk = namedtuple("Chunk", "file_path start_line end_line text")

CTX_LINES = 20  # simple surrounding window

def select_context(_, hunks: List[Tuple[Path, int, int]], repo_path: Path = None) -> List[Chunk]:
    """
    Very first draft: grab ±20 lines around every hunk.
    `db_path` param is ignored for now (placeholder for later Tier-1/2 work).
    """
    chunks = []
    for file_path, start, end in hunks:
        # Resolve path relative to the repository being analyzed
        if repo_path:
            path = repo_path / file_path
        else:
            path = Path(file_path)
        
        if not path.exists():
            continue
        lines = path.read_text(errors="replace").splitlines(keepends=True)
        lo = max(0, start - 1 - CTX_LINES)
        hi = min(len(lines), end + CTX_LINES)
        text = "".join(lines[lo:hi])
        chunks.append(Chunk(str(file_path), lo + 1, hi, text))  # Use original file_path for display
    return chunks
