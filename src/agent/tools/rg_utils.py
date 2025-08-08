import shlex
from typing import Iterable, List, Optional, Tuple

from agent.tools import run_in_container, to_workspace_relative


def _quote(value: str) -> str:
    return shlex.quote(value)


## Removed unused _to_exclude_glob helper


def rg_list_files(
    search_path: str,
    include_globs: Optional[Iterable[str]] = None,
    exclude_globs: Optional[Iterable[str]] = None,
    limit: Optional[int] = None,
) -> List[str]:
    """List files using ripgrep, respecting include/exclude globs.

    Returns absolute paths (as emitted by ripgrep inside the container).
    """
    cmd_parts = ["rg", "--files"]

    if include_globs:
        for g in include_globs:
            if g:
                cmd_parts += ["--glob", g]

    if exclude_globs:
        for g in exclude_globs:
            if g:
                cmd_parts += ["--glob", f"!{g}"]

    cmd_parts.append(_quote(search_path))
    cmd = " ".join(cmd_parts)

    if limit and limit > 0:
        cmd = f"{cmd} | head -{int(limit)}"

    raw = run_in_container(cmd)
    if not raw or not raw.strip() or raw.startswith("Error:"):
        return []

    return [line.strip() for line in raw.split("\n") if line.strip()]


def rg_count_files(
    search_path: str,
    include_globs: Optional[Iterable[str]] = None,
    exclude_globs: Optional[Iterable[str]] = None,
) -> Optional[int]:
    """Count files that match ripgrep filters."""
    cmd_parts = ["rg", "--files"]

    if include_globs:
        for g in include_globs:
            if g:
                cmd_parts += ["--glob", g]

    if exclude_globs:
        for g in exclude_globs:
            if g:
                cmd_parts += ["--glob", f"!{g}"]

    cmd_parts.append(_quote(search_path))
    cmd = " ".join(cmd_parts) + " | wc -l"

    raw = run_in_container(cmd)
    try:
        return int(raw.strip())
    except Exception:
        return None


def to_workspace_relative_lines(lines: Iterable[str]) -> List[str]:
    return [to_workspace_relative(line) for line in lines]
