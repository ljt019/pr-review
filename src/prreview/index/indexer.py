"""Repository indexer storing simple file metadata.

This minimal milestone implementation records each file's total line count
in a SQLite-backed dictionary for later retrieval.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, List

import numpy as np

from prreview.embed.embedding import EmbeddingModel
from prreview.index.vector_store import VectorStore, Metadata as VecMeta

from sqlitedict import SqliteDict

# (start_line, end_line)
Metadata = Tuple[int, int]


class Indexer:
    """Repository indexer persisting basic line counts and embeddings."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.vector_path = self.db_path.with_suffix(".hnsw")
        self.vector_meta = self.db_path.with_suffix(".vec.sqlite")

        self.embedder = EmbeddingModel()
        self.store = VectorStore(self.vector_path, self.vector_meta, self.embedder.dim)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def run(self, repo_path: Path | str) -> None:
        """Index *repo_path* and persist/refresh metadata in *self.db_path*."""
        repo = Path(repo_path)
        with SqliteDict(self.db_path, autocommit=True) as db:
            for path in repo.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(repo).as_posix()
                try:
                    text = path.read_text(errors="replace")
                except OSError:
                    continue
                end_line = text.count("\n") + 1
                db[rel] = (1, end_line)

                # ------------------------------------------------------------------
                # Embeddings for Tier 2 retrieval
                # ------------------------------------------------------------------
                vector = self.embedder.encode(text)
                self.store.add_vectors([vector], [(rel, 1, end_line)])

    def load_metadata(self) -> Dict[str, Metadata]:
        """Return the entire metadata mapping as a regular dictionary."""
        with SqliteDict(self.db_path, flag="r") as db:
            return dict(db)


# Re-export for convenience
__all__ = ["Indexer", "Metadata"]
