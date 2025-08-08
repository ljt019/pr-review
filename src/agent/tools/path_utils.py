from __future__ import annotations


def normalize_path(path: str) -> str:
    """Normalize to absolute path in /workspace."""
    if not path:
        return "/workspace"
    if path in (".", "./"):
        return "/workspace"
    if path.startswith("/"):
        return path
    if path.startswith("./"):
        path = path[2:]
    return f"/workspace/{path}"


def to_workspace_relative(path: str) -> str:
    """Convert absolute to /workspace-relative (or '.' for root)."""
    if path.startswith("/workspace/"):
        return path[11:]
    if path == "/workspace":
        return "."
    return path
