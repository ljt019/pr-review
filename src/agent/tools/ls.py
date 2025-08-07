from pathlib import Path

from qwen_agent.tools.base import BaseTool, register_tool
from rich.console import Console
from rich.tree import Tree

from agent.tools import (
    load_tool_description,
    run_in_container,
    normalize_path,
    to_workspace_relative,
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
            "description": "Patterns to exclude (e.g., [\"*.log\", \"temp\"])",
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
            ignore_conditions = []
            for pattern in all_ignore_patterns:
                if pattern.endswith("/"):
                    # Directory pattern
                    ignore_conditions.append(f'-path "*/{pattern}*" -prune -o')
                else:
                    # File pattern
                    ignore_conditions.append(f'-name "{pattern}" -prune -o')

            ignore_clause = " ".join(ignore_conditions) if ignore_conditions else ""
            find_cmd = f'find "{path}" {ignore_clause} -type f -print 2>/dev/null | head -{LIMIT}'

            result = run_in_container(find_cmd)

            if result.startswith("Error:"):
                return f"Error listing path '{original_path}': {result}"

            files = [line.strip() for line in result.split("\n") if line.strip()]

            if not files:
                # Try a simpler ls command to see if path exists
                simple_check = run_in_container(
                    f'ls -la "{path}" 2>/dev/null || echo "PATH_NOT_FOUND"'
                )
                if "PATH_NOT_FOUND" in simple_check:
                    return (
                        f"Path '{original_path}' does not exist. Provide a valid path."
                    )
                else:
                    return f"Path '{original_path}' exists but contains no files (all files may be filtered out by ignore patterns)"

            # Build directory tree structure
            display_path = to_workspace_relative(original_path)
            tree_structure = self._build_tree_structure(files, path, display_path)

            # Check if results were truncated
            if len(files) >= LIMIT:
                tree_structure += f"\n\n(Results limited to {LIMIT} files. Use glob for more specific searches.)"

            return tree_structure

        except Exception as e:
            return f"Error: {str(e)}"

    def _build_tree_structure(self, files, base_path, display_path):
        """Build a hierarchical tree structure from file paths using rich."""
        tree = Tree(display_path)
        nodes = {Path(): tree}

        for file_path in sorted(files):
            rel_path = Path(file_path).relative_to(base_path)
            parts = rel_path.parts
            current = Path()
            node = tree
            for part in parts[:-1]:
                current /= part
                node = nodes.setdefault(current, nodes[current.parent].add(part))
            nodes[current / parts[-1]] = node.add(parts[-1])

        console = Console(color_system=None)
        with console.capture() as capture:
            console.print(tree)
        return capture.get().rstrip()
