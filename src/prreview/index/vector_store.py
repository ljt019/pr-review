from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

import hnswlib
import numpy as np
from sqlitedict import SqliteDict

Metadata = Tuple[str, int, int]  # file_path, start_line, end_line


class VectorStore:
    """Simple wrapper around hnswlib with SQLite metadata."""

    def __init__(self, index_path: Path, meta_path: Path, dim: int):
        self.index_path = Path(index_path)
        self.meta_path = Path(meta_path)
        self.dim = dim

        self.index = hnswlib.Index(space="cosine", dim=dim)
        if self.index_path.exists():
            self.index.load_index(str(self.index_path))
        else:
            self.index.init_index(max_elements=100_000, ef_construction=200, M=16)
        self.meta_db = SqliteDict(self.meta_path, autocommit=True)
        self.next_id = int(self.meta_db.get("_next_id", 0))

    def _persist(self) -> None:
        self.meta_db["_next_id"] = self.next_id
        self.meta_db.commit()
        self.index.save_index(str(self.index_path))

    def add_vectors(self, vectors: Iterable[np.ndarray], metadata: Iterable[Metadata]) -> None:
        vectors = list(vectors)
        metas = list(metadata)
        if not vectors:
            return
        ids = list(range(self.next_id, self.next_id + len(vectors)))
        self.index.add_items(np.vstack(vectors), ids)
        for i, meta in zip(ids, metas):
            self.meta_db[str(i)] = meta
        self.next_id += len(vectors)
        self._persist()

    def query(self, vector: np.ndarray, k: int) -> List[Metadata]:
        if self.next_id == 0:
            return []
        ids, _ = self.index.knn_query(vector, k=k)
        result = []
        for idx in ids[0]:
            meta = self.meta_db.get(str(idx))
            if meta:
                result.append(meta)
        return result


__all__ = ["VectorStore", "Metadata"]
