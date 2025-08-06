from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import load_tool_description, run_in_container, normalize_path
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
            "description": "Absolute path to list (defaults to root /)",
            "required": False,
        },
        {
            "name": "ignore",
            "type": "array",
            "description": "Array of glob patterns to ignore",
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
                original_path = ParameterParser.get_optional_param(parsed_params, "path", ".")
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
            tree_structure = self._build_tree_structure(files, path, original_path)

            # Check if results were truncated
            if len(files) >= LIMIT:
                tree_structure += f"\n\n(Results limited to {LIMIT} files. Use glob for more specific searches.)"

            return tree_structure

        except Exception as e:
            return f"Error: {str(e)}"

    def _build_tree_structure(self, files, base_path, display_path):
        """Build a hierarchical tree structure from file paths"""
        # Organize files by directory
        dirs = {}

        for file_path in files:
            # Remove base path prefix for cleaner display
            if base_path != "/" and file_path.startswith(base_path + "/"):
                rel_path = file_path[len(base_path) + 1 :]
            elif base_path == "/" and file_path.startswith("/"):
                rel_path = file_path[1:] if file_path != "/" else ""
            else:
                rel_path = file_path

            if "/" in rel_path:
                dir_part = "/".join(rel_path.split("/")[:-1])
                file_part = rel_path.split("/")[-1]
            else:
                dir_part = ""
                file_part = rel_path

            if dir_part not in dirs:
                dirs[dir_part] = []
            dirs[dir_part].append(file_part)

        # Sort directories and files
        for dir_path in dirs:
            dirs[dir_path].sort()

        # Build tree output
        output = []

        # Show base path (use display path for user-friendly output)
        output.append(f"{display_path}")

        # Sort directories by depth and name
        sorted_dirs = sorted(dirs.keys(), key=lambda x: (x.count("/"), x))

        for dir_path in sorted_dirs:
            if dir_path == "":
                # Files in root directory
                for file_name in dirs[dir_path]:
                    output.append(f"  {file_name}")
            else:
                # Subdirectory
                depth = dir_path.count("/") + 1
                indent = "  " * depth
                dir_name = dir_path.split("/")[-1]
                output.append(f"{indent}{dir_name}/")

                # Files in this directory
                file_indent = "  " * (depth + 1)
                for file_name in dirs[dir_path]:
                    output.append(f"{file_indent}{file_name}")

        return "\n".join(output)
