import shlex

from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import (
    load_tool_description,
    normalize_path,
    run_in_container,
    to_workspace_relative,
)
from agent.tools.rg_utils import (
    rg_count_files,
    rg_list_files,
    to_workspace_relative_lines,
)
from agent.utils.param_parser import ParameterParser


@register_tool("glob")
class GlobTool(BaseTool):
    description = load_tool_description("glob")
    LIMIT = 100
    parameters = [
        {
            "name": "pattern",
            "type": "string",
            "description": "Pattern to match files (e.g., **/*.py, *.js, test_*)",
            "required": True,
        },
        {
            "name": "path",
            "type": "string",
            "description": "Directory to search (defaults to current directory)",
            "required": False,
        },
    ]

    def call(self, params: str, **kwargs) -> str:
        try:
            parsed_params = ParameterParser.parse_params(params)
            pattern = ParameterParser.get_required_param(parsed_params, "pattern")
            original_path = ParameterParser.get_optional_param(
                parsed_params, "path", "."
            )
            # Normalize the path to handle relative paths
            search_path = normalize_path(original_path)

            # List files via ripgrep helper
            include_globs = None if pattern in ["*", "**", "**/*"] else [pattern]
            lines = rg_list_files(
                search_path, include_globs=include_globs, limit=self.LIMIT
            )

            if not lines:
                return f"No files found matching pattern '{pattern}' in {original_path}"

            # Convert absolute paths back to relative for display
            display_lines = to_workspace_relative_lines(lines)

            # Check if we hit the limit
            if len(display_lines) == self.LIMIT:
                total_count = rg_count_files(search_path, include_globs=include_globs)
                if total_count and total_count > self.LIMIT:
                    display_lines.append("")
                    display_lines.append(
                        f"(Showing {self.LIMIT} of {total_count} files. Consider using a more specific pattern.)"
                    )

            return "\n".join(display_lines)

        except Exception as e:
            return f"Error: {str(e)}"
