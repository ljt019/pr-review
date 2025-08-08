import shlex
from typing import List, Optional, Union

from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import (
    load_tool_description,
    normalize_path,
    run_in_container,
    to_workspace_relative,
)
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

            return self._search_files(pattern, directory, include)

        except Exception as e:
            return f"Error: {str(e)}"

    def _search_files(
        self,
        pattern: str,
        directory: str,
        include: Optional[Union[str, List[str]]] = None,
    ) -> str:
        """Search for matches with file, line number, and content."""
        cmd = [
            "rg",
            "-Hn",
            "--no-heading",
            "--no-fixed-strings",
            "--smart-case",
            "--max-columns=300",
        ]

        # Handle file patterns for filtering (string or list)
        includes: Optional[List[str]] = None
        if include:
            if isinstance(include, str):
                includes = [include]
            elif isinstance(include, list):
                includes = [g for g in include if isinstance(g, str) and g.strip()]

        if includes:
            for g in includes:
                cmd.extend(["--glob", g])

        # Add pattern and directory
        cmd.append(pattern)
        if directory != ".":
            cmd.append(directory)

        result = run_in_container(shlex.join(cmd))

        # If no matches found, provide a helpful message
        if not result or not result.strip():
            return f"No files found containing pattern: {pattern}"

        # Convert absolute paths back to relative for display
        lines = result.strip().split("\n")
        display_lines = [to_workspace_relative(line) for line in lines]

        return "\n".join(display_lines)
