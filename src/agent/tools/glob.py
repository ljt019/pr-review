import shlex

from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import (
    load_tool_description,
    normalize_path,
    run_in_container,
    to_workspace_relative,
)
from agent.utils.param_parser import ParameterParser


@register_tool("glob")
class GlobTool(BaseTool):
    description = load_tool_description("glob")
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

            # Build ripgrep command to list files with glob filtering
            # Use --files to list tracked files and --glob for pattern
            search_path_quoted = shlex.quote(search_path)

            # Special-case patterns that mean "all files"
            if pattern in ["*", "**", "**/*"]:
                rg_cmd = f"rg --files {search_path_quoted} | head -50"
                count_cmd = f"rg --files {search_path_quoted} | wc -l"
            else:
                pattern_quoted = shlex.quote(pattern)
                rg_cmd = f"rg --files --glob {pattern_quoted} {search_path_quoted} | head -50"
                count_cmd = (
                    f"rg --files --glob {pattern_quoted} {search_path_quoted} | wc -l"
                )

            result = run_in_container(rg_cmd)

            if result.startswith("Error:"):
                return result

            lines = [line.strip() for line in result.split("\n") if line.strip()]

            if not lines:
                return f"No files found matching pattern '{pattern}' in {original_path}"

            # Convert absolute paths back to relative for display
            display_lines = [to_workspace_relative(line) for line in lines]

            # Check if we hit the limit
            if len(display_lines) == 50:
                total_result = run_in_container(count_cmd)
                try:
                    total_count = int(total_result.strip())
                    if total_count > 50:
                        display_lines.append("")
                        display_lines.append(
                            f"(Showing 50 of {total_count} files. Consider using a more specific pattern.)"
                        )
                except Exception:
                    pass

            return "\n".join(display_lines)

        except Exception as e:
            return f"Error: {str(e)}"
