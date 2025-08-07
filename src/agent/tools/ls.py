import shlex
from pathlib import Path

from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import (
    load_tool_description,
    normalize_path,
    run_in_container,
)
from agent.utils.param_parser import ParameterParser

# Common development directories to ignore for cleaner output
IGNORE_PATTERNS = [
    "node_modules/",
    "__pycache__/",
    ".git/",
    "dist/",
    "build/",
    "target/",
    "vendor/",
    "bin/",
    "obj/",
    ".idea/",
    ".vscode/",
    ".zig-cache/",
    "zig-out",
    ".coverage",
    "coverage/",
    "tmp/",
    "temp/",
    ".cache/",
    "cache/",
    "logs/",
    ".venv/",
    "venv/",
    "env/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".tox/",
    ".DS_Store",
    "Thumbs.db",
]

LIMIT = 100


@register_tool("ls")
class LsTool(BaseTool):
    description = load_tool_description("ls")
    parameters = [
        {
            "name": "path",
            "type": "string",
            "description": "Directory to list (defaults to current directory)",
            "required": False,
        },
        {
            "name": "ignore",
            "type": "array",
            "description": 'Patterns to exclude (e.g., ["*.log", "temp"])',
            "required": False,
        },
    ]

    def call(self, params: str, **kwargs) -> str:
        try:
            # Handle empty params case
            if not params or params.strip() == "":
                # Default to workspace root when no path is provided
                path = "/workspace"
                original_path = "."
                ignore_patterns = []
            else:
                parsed_params = ParameterParser.parse_params(params)
                original_path = ParameterParser.get_optional_param(
                    parsed_params, "path", "."
                )
                # Normalize the path to handle relative paths
                path = normalize_path(original_path)
                ignore_patterns = ParameterParser.get_optional_param(
                    parsed_params, "ignore", []
                )

            # Combine default ignore patterns with user-provided ones
            all_ignore_patterns = IGNORE_PATTERNS + ignore_patterns

            # Use find to get all files recursively, excluding ignored patterns
            path_quoted = shlex.quote(path)
            ignore_conditions = []
            for pattern in all_ignore_patterns:
                if pattern.endswith("/"):
                    pattern_quoted = shlex.quote(f"*/{pattern}*")
                    ignore_conditions.append(f"-path {pattern_quoted} -prune -o")
                else:
                    pattern_quoted = shlex.quote(pattern)
                    ignore_conditions.append(f"-name {pattern_quoted} -prune -o")

            ignore_clause = " ".join(ignore_conditions) if ignore_conditions else ""
            find_cmd = f"find {path_quoted} {ignore_clause} -type f -print 2>/dev/null | head -{LIMIT}"

            result = run_in_container(find_cmd)

            if result.startswith("Error:"):
                return f"Error listing path '{original_path}': {result}"

            files = [line.strip() for line in result.split("\n") if line.strip()]

            if not files:
                # Try a simpler ls command to see if path exists
                simple_check = run_in_container(
                    f'ls -la {path_quoted} 2>/dev/null || echo "PATH_NOT_FOUND"'
                )
                if "PATH_NOT_FOUND" in simple_check:
                    return (
                        f"Path '{original_path}' does not exist. Provide a valid path."
                    )
                else:
                    return f"Path '{original_path}' exists but contains no files (all files may be filtered out by ignore patterns)"

            # Build a compact list of directories and files relative to the requested path
            rel_files = []
            dir_set = set()
            base_path = Path(path)
            for file_path in sorted(files):
                try:
                    rel = Path(file_path).relative_to(base_path)
                except Exception:
                    # If relative fails, skip this entry
                    continue
                rel_files.append(rel)
                # Accumulate parent directories
                parent = rel.parent
                while parent and str(parent) != ".":
                    dir_set.add(str(parent).replace("\\", "/"))
                    parent = parent.parent

            # Include the immediate path itself if it has subentries
            # (no explicit entry added for base path)

            dirs = sorted(dir_set)
            files_rel_str = [str(p).replace("\\", "/") for p in rel_files]

            # Compose entries with trailing slash for directories
            entries = [f"{d}/" for d in dirs] + files_rel_str
            if len(entries) > LIMIT:
                entries = entries[:LIMIT]
                entries.append("")
                entries.append(
                    f"(Results limited to {LIMIT} entries. Use glob for more specific searches.)"
                )

            return "\n".join(entries)

        except Exception as e:
            return f"Error: {str(e)}"
