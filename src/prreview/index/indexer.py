"""Repository indexer storing simple file metadata.

This minimal milestone implementation records each file's total line count
in a SQLite-backed dictionary for later retrieval.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from sqlitedict import SqliteDict

# (start_line, end_line)
Metadata = Tuple[int, int]


class Indexer:
    """SQLite-backed repository indexer.

    The class persists basic metadata for every file in a repository –
    currently just the (start_line, end_line) tuple so that other
    components can quickly look up simple line-based statistics.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def run(self, repo_path: Path | str) -> None:
        """Index *repo_path* and persist/refresh metadata in *self.db_path*."""
        repo = Path(repo_path)
        with SqliteDict(self.db_path, autocommit=True) as db:
            for path in repo.rglob("*"):
                if path.is_file():
                    rel = path.relative_to(repo).as_posix()
                    try:
                        end_line = sum(1 for _ in path.open(errors="replace"))
                    except OSError:
                        end_line = 0
                    db[rel] = (1, end_line)

    def load_metadata(self) -> Dict[str, Metadata]:
        """Return the entire metadata mapping as a regular dictionary."""
        with SqliteDict(self.db_path, flag="r") as db:
            return dict(db)


# Re-export for convenience
__all__ = ["Indexer", "Metadata"]
