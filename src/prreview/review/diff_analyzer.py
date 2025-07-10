# review/diff_analyzer.py — Milestone-0 bare-bones version
"""Extract zero-context hunks (file, start, end) for a Git diff.

This will get smarter later, but is enough for Tier-0 testing.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import List, Tuple

import git  # GitPython

# (file_path, start_line, end_line)
Hunk = Tuple[Path, int, int]

_HUNK_RE = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def diff_hunks(repo_path: Path, base: str, head: str) -> List[Hunk]:
    """Return minimal hunks between *base* and *head* (unified=0)."""
    repo = git.Repo(repo_path)
    diff_txt: str = repo.git.diff(f"{base}..{head}", unified=0)

    hunks: List[Hunk] = []
    current_file: Path | None = None
    for line in diff_txt.splitlines():
        if line.startswith("+++ b/"):  # new-file marker
            current_file = Path(line[6:])
        elif line.startswith("@@") and current_file is not None:
            m = _HUNK_RE.match(line)
            if m:
                start = int(m.group(1))
                length = int(m.group(2) or "1")
                hunks.append((current_file, start, start + length - 1))
    return hunks


__all__ = ["diff_hunks", "Hunk"]
