from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import load_tool_description, run_in_container, normalize_path
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
            original_path = ParameterParser.get_optional_param(parsed_params, "path", ".")
            # Normalize the path to handle relative paths
            search_path = normalize_path(original_path)

            # Build an appropriate find command
            # Special-case patterns that mean "all files"
            if pattern in ["*", "**", "**/*"]:
                find_cmd = f'find "{search_path}" -type f 2>/dev/null | head -50'
            else:
                # General pattern: use -path so that wildcards match full path components
                # Replace any leading "**/" with "*/" because find's wildcard traverses directories by default
                normalized_pattern = pattern.replace("**/", "*/").replace("**", "*")
                find_cmd = f'find "{search_path}" -type f -path "*{normalized_pattern}*" 2>/dev/null | head -50'

            result = run_in_container(find_cmd)

            if result.startswith("Error:"):
                return result

            lines = [line.strip() for line in result.split("\n") if line.strip()]

            if not lines:
                return f"No files found matching pattern '{pattern}' in {original_path}"
            
            # Convert absolute paths back to relative for display
            display_lines = []
            for line in lines:
                if line.startswith("/workspace/"):
                    display_lines.append(line[11:])  # Remove "/workspace/"
                elif line == "/workspace":
                    display_lines.append(".")
                else:
                    display_lines.append(line)

            # Check if we hit the limit
            file_count = len(display_lines)

            if file_count == 50:
                # Check if there are more files
                count_cmd = f'find "{search_path}" -name "{pattern}" -type f 2>/dev/null | wc -l'
                count_result = run_in_container(count_cmd)
                try:
                    total_count = int(count_result.strip())
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
