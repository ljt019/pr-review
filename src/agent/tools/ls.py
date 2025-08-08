import json
import shlex
from pathlib import Path

from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import (
    load_tool_description,
    normalize_path,
    run_in_container,
)
from agent.tools.rg_utils import rg_count_files, rg_list_files
from agent.utils.param_parser import ParameterParser

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

            # Use ripgrep to list files with only user-provided excludes
            files = rg_list_files(path, exclude_globs=ignore_patterns, limit=LIMIT)

            if not files:
                # Try a simpler ls command to see if path exists
                path_quoted = shlex.quote(path)
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

            text = "\n".join(entries)
            payload = {"entries": entries}
            return f"{text}\n\n<!--JSON-->" + json.dumps(payload) + "<!--/JSON-->"

        except Exception as e:
            return f"Error: {str(e)}"
