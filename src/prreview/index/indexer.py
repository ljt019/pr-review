"""Repository indexer storing simple file metadata.

This minimal milestone implementation records each file's total line count
in a SQLite-backed dictionary for later retrieval.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, List
import hashlib

import numpy as np
import git

from prreview.embed.embedding import EmbeddingModel
from prreview.index.vector_store import VectorStore, Metadata as VecMeta

from sqlitedict import SqliteDict

# (start_line, end_line, file_hash, mtime)
Metadata = Tuple[int, int, str, float]


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

    def _compute_file_hash(self, content: str) -> str:
        """Compute a hash of file content for change detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def _get_tracked_files(self, repo: git.Repo) -> List[str]:
        """Get list of files tracked by git (respects .gitignore)."""
        try:
            # Get all tracked files using git ls-files
            tracked = repo.git.ls_files().splitlines()
            return tracked
        except git.GitCommandError:
            # Fallback if git command fails - just return empty list
            print("⚠️  Warning: Could not get tracked files from git")
            return []

    def run(self, repo_path: Path | str) -> None:
        """Index *repo_path* and persist/refresh metadata in *self.db_path*."""
        repo_path = Path(repo_path)
        processed_files = set()
        stats = {"new": 0, "updated": 0, "skipped": 0, "deleted": 0}
        
        # Initialize git repo
        try:
            repo = git.Repo(repo_path)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            print("❌ Error: Not a valid git repository. Indexing aborted.")
            return
        
        # Get list of tracked files
        tracked_files = self._get_tracked_files(repo)
        if not tracked_files:
            print("⚠️  No tracked files found in repository")
            return
            
        print(f"📁 Found {len(tracked_files)} tracked files to index")
        
        with SqliteDict(self.db_path, autocommit=True) as db:
            # First pass: process all tracked files
            for rel_path in tracked_files:
                path = repo_path / rel_path
                rel = rel_path.replace('\\', '/')  # Normalize path separators
                
                if not path.is_file():
                    # File might be listed but not exist (e.g., submodules)
                    continue
                    
                processed_files.add(rel)
                
                try:
                    # Get file stats
                    stat = path.stat()
                    mtime = stat.st_mtime
                    
                    # Check if file needs processing
                    existing_meta = db.get(rel)
                    if existing_meta and len(existing_meta) >= 4:
                        # File exists in DB, check if it's changed
                        _, _, old_hash, old_mtime = existing_meta
                        if mtime <= old_mtime:
                            # File hasn't been modified, skip
                            stats["skipped"] += 1
                            continue
                    
                    # Read and process the file
                    text = path.read_text(errors="replace")
                    file_hash = self._compute_file_hash(text)
                    
                    # Check if content actually changed (for cases where mtime changed but content didn't)
                    if existing_meta and len(existing_meta) >= 4:
                        _, _, old_hash, _ = existing_meta
                        if file_hash == old_hash:
                            # Update mtime but skip re-embedding
                            end_line = existing_meta[1]
                            db[rel] = (1, end_line, file_hash, mtime)
                            stats["skipped"] += 1
                            continue
                    
                    # File is new or changed, process it
                    end_line = text.count("\n") + 1
                    db[rel] = (1, end_line, file_hash, mtime)
                    
                    # Generate embedding
                    if existing_meta:
                        print(f"🔄 Updating: {rel}")
                        stats["updated"] += 1
                    else:
                        print(f"✨ New file: {rel}")
                        stats["new"] += 1
                    
                    vector = self.embedder.encode(text)
                    self.store.add_vectors([vector], [(rel, 1, end_line)])
                    
                except OSError as e:
                    print(f"⚠️  Skipping {rel}: {e}")
                    continue
                except UnicodeDecodeError as e:
                    print(f"⚠️  Skipping {rel}: Unicode decode error")
                    continue
            
            # Second pass: remove deleted files
            all_indexed_files = list(db.keys())
            for rel in all_indexed_files:
                if rel not in processed_files and not rel.startswith('_'):  # Skip internal keys
                    print(f"🗑️  Removing deleted file: {rel}")
                    del db[rel]
                    stats["deleted"] += 1
                    # Note: We can't easily remove from vector store without additional tracking
                    # This would require vector store to support deletion by metadata
            
            # Print summary
            total_files = len(processed_files)
            print(f"\n📊 Indexing complete:")
            print(f"   Total files: {total_files}")
            print(f"   ✨ New: {stats['new']}")
            print(f"   🔄 Updated: {stats['updated']}")
            print(f"   ⏭️  Skipped: {stats['skipped']}")
            print(f"   🗑️  Deleted: {stats['deleted']}")

    def load_metadata(self) -> Dict[str, Tuple[int, int]]:
        """Return the entire metadata mapping as a regular dictionary (excluding hash/mtime for compatibility)."""
        with SqliteDict(self.db_path, flag="r") as db:
            # Return only start_line and end_line for backward compatibility
            result = {}
            for key, value in db.items():
                if isinstance(value, tuple) and len(value) >= 2:
                    result[key] = (value[0], value[1])
            return result


# Re-export for convenience
__all__ = ["Indexer", "Metadata"]
