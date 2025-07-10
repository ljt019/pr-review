# index/indexer.py — Milestone-0 bare-bones version
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


def index_repo(repo_path: Path, db_path: Path) -> None:
    """Index *repo_path* and persist basic metadata in *db_path*."""
    repo = Path(repo_path)
    with SqliteDict(db_path, autocommit=True) as db:
        for path in repo.rglob("*"):
            if path.is_file():
                rel = path.relative_to(repo).as_posix()
                try:
                    end_line = sum(1 for _ in path.open(errors="replace"))
                except OSError:
                    end_line = 0
                db[rel] = (1, end_line)


def load_metadata(db_path: Path) -> Dict[str, Metadata]:
    """Return a dict view of stored metadata."""
    with SqliteDict(db_path, flag="r") as db:
        return dict(db)


__all__ = ["index_repo", "load_metadata", "Metadata"]
