from typing import Optional

from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import load_tool_description, run_in_container, normalize_path
from agent.utils.param_parser import ParameterParser


@register_tool("grep")
class GrepTool(BaseTool):
    description = load_tool_description("grep")
    parameters = [
        {
            "name": "pattern",
            "type": "string",
            "description": "Search pattern (supports full regex syntax, defaults to '.' to match all)",
            "required": False,
        },
        {
            "name": "directory",
            "type": "string",
            "description": "Directory to search (defaults to current directory)",
            "required": False,
        },
        {
            "name": "include",
            "type": "string",
            "description": "File patterns to include (e.g., *.py, *.js)",
            "required": False,
        },
    ]

    def call(self, params: str, **kwargs) -> str:
        try:
            parsed_params = ParameterParser.parse_params(params)
            pattern = ParameterParser.get_optional_param(parsed_params, "pattern", ".")

            original_directory = ParameterParser.get_optional_param(
                parsed_params, "directory", "."
            )
            # Normalize the directory path
            directory = normalize_path(original_directory)
            include = ParameterParser.get_optional_param(parsed_params, "include")

            return self._search_files(pattern, directory, original_directory, include)

        except Exception as e:
            return f"Error: {str(e)}"

    def _search_files(
        self, pattern: str, directory: str, original_directory: str, include: Optional[str] = None
    ) -> str:
        """Search for files containing pattern and return file paths sorted by modification time."""
        cmd = ["rg", "--files-with-matches", "--sort", "modified"]

        # Handle file patterns for filtering
        if include:
            if include.startswith("*."):
                # Simple extension like *.py
                ext = include[2:]
                if ext in [
                    "py",
                    "js",
                    "ts",
                    "tsx",
                    "jsx",
                    "java",
                    "cpp",
                    "c",
                    "go",
                    "rs",
                    "rb",
                    "php",
                    "sh",
                    "html",
                    "css",
                    "md",
                ]:
                    cmd.extend(["--type", ext])
                else:
                    cmd.extend(["--glob", include])
            else:
                cmd.extend(["--glob", include])

        # Add pattern and directory
        cmd.append(pattern)
        if directory != ".":
            cmd.append(directory)

        # Properly quote all arguments to handle special characters in patterns
        quoted_cmd = []
        for i, part in enumerate(cmd):
            if i == 0:  # rg command itself
                quoted_cmd.append(str(part))
            else:
                # Quote all other arguments (patterns, paths, etc.)
                quoted_cmd.append(f'"{part}"')
        command = " ".join(quoted_cmd)
        result = run_in_container(command)

        # If no matches found, provide a helpful message
        if not result.strip():
            return f"No files found containing pattern: {pattern}"

        # Convert absolute paths back to relative for display
        lines = result.strip().split("\n")
        display_lines = []
        for line in lines:
            if line.startswith("/workspace/"):
                display_lines.append(line[11:])  # Remove "/workspace/"
            elif line == "/workspace":
                display_lines.append(".")
            else:
                display_lines.append(line)
        
        return "\n".join(display_lines)
