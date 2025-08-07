import difflib

from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import (
    load_tool_description,
    run_in_container,
    normalize_path,
    to_workspace_relative,
)
from agent.utils.param_parser import ParameterParser

DEFAULT_READ_LIMIT = 2000
MAX_LINE_LENGTH = 2000

# Common binary file extensions to detect
BINARY_EXTENSIONS = {
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".a",
    ".o",
    ".pyc",
    ".pyo",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".svg",
    ".webp",
    ".ico",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".tar",
    ".gz",
    ".rar",
    ".7z",
    ".bz2",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".bin",
    ".dat",
    ".db",
    ".sqlite",
    ".sqlite3",
}


@register_tool("cat")
class CatTool(BaseTool):
    description = load_tool_description("cat")
    parameters = [
        {
            "name": "filePath",
            "type": "string",
            "description": "Path to the file to read",
            "required": True,
        },
        {
            "name": "offset",
            "type": "integer",
            "description": "Line number to start reading from (0-based offset, optional)",
            "required": False,
        },
        {
            "name": "limit",
            "type": "integer",
            "description": "Number of lines to read (defaults to 2000, optional)",
            "required": False,
        },
    ]

    def call(self, params: str, **kwargs) -> str:
        try:
            parsed_params = ParameterParser.parse_params(params)

            original_path = ParameterParser.get_required_param(parsed_params, "filePath")
            
            # Normalize the path to handle relative paths
            file_path = normalize_path(original_path)

            offset = ParameterParser.get_optional_param(parsed_params, "offset", 0)
            limit = ParameterParser.get_optional_param(
                parsed_params, "limit", DEFAULT_READ_LIMIT
            )

            # Check if file is likely binary by extension
            if self._is_binary_file(file_path):
                return f"Error: Cannot read binary file: {original_path}\nThis appears to be a binary file based on its extension."

            # First check if file exists
            check_cmd = f'test -f "{file_path}" && echo "exists" || echo "not_found"'
            exists_result = run_in_container(check_cmd)

            if "not_found" in exists_result:
                # Try to suggest similar files
                suggestions = self._get_file_suggestions(file_path, original_path)
                if suggestions:
                    return f"Error: File not found: {original_path}\n\nDid you mean one of these?\n{suggestions}"
                else:
                    return f"Error: File not found: {original_path}"

            # Check if file is empty first
            size_cmd = f'wc -c < "{file_path}" 2>/dev/null || echo "0"'
            size_result = run_in_container(size_cmd)

            try:
                file_size = int(size_result.strip())
                if file_size == 0:
                    return "File is empty."
            except (ValueError, AttributeError):
                pass

            # Read the file with line numbers using cat -n format
            if offset == 0:
                # Read from beginning
                cat_cmd = f'cat -n "{file_path}" | head -{limit}'
            else:
                # Read specific range - use tail/head approach for better compatibility
                start_line = offset + 1  # Convert 0-based offset to 1-based line number
                end_line = offset + limit
                cat_cmd = f'tail -n +{start_line} "{file_path}" | head -{limit} | nl -v {start_line}'

            result = run_in_container(cat_cmd)

            if result.startswith("Error:"):
                return result

            # Process the output to maintain cat -n format but apply truncation
            lines = result.split("\n")
            formatted_lines = []

            for line in lines:
                if line.strip():  # Skip empty lines from command output
                    # Line should be in format "     N\tcontent"
                    if "\t" in line:
                        line_num_part, content = line.split("\t", 1)
                        # Truncate long lines as specified
                        if len(content) > MAX_LINE_LENGTH:
                            content = content[:MAX_LINE_LENGTH] + "..."
                        formatted_lines.append(f"{line_num_part}\t{content}")
                    else:
                        # Handle edge case where line doesn't have tab
                        if len(line) > MAX_LINE_LENGTH:
                            line = line[:MAX_LINE_LENGTH] + "..."
                        formatted_lines.append(line)

            if not formatted_lines:
                return "File is empty."

            # Check if there are more lines beyond what we read
            total_lines_cmd = f'wc -l < "{file_path}"'
            total_result = run_in_container(total_lines_cmd)

            output = "\n".join(formatted_lines)

            try:
                total_lines = int(total_result.strip())
                lines_read = len(formatted_lines)
                if total_lines > offset + lines_read:
                    output += f"\n\n(File has {total_lines} total lines. Use 'offset' parameter to read beyond line {offset + lines_read})"
            except (ValueError, AttributeError):
                pass

            return output

        except Exception as e:
            return f"Error: {str(e)}"

    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is likely binary based on extension"""
        file_path_lower = file_path.lower()
        return any(file_path_lower.endswith(ext) for ext in BINARY_EXTENSIONS)

    def _get_file_suggestions(self, file_path: str, original_path: str) -> str:
        """Get suggestions for similar file names when file not found"""
        try:
            # Extract directory and filename
            if "/" in file_path:
                directory = "/".join(file_path.split("/")[:-1])
                filename = file_path.split("/")[-1]
            else:
                directory = "."
                filename = file_path

            # List files in directory
            ls_cmd = f'ls "{directory}" 2>/dev/null'
            ls_result = run_in_container(ls_cmd)

            if ls_result.startswith("Error:"):
                return ""

            files = [f.strip() for f in ls_result.split("\n") if f.strip()]

            # Use difflib to find close matches
            close_matches = difflib.get_close_matches(filename, files, n=3, cutoff=0.6)

            # Also check for case-insensitive substring matches
            filename_lower = filename.lower()
            substring_matches = [
                file
                for file in files
                if filename_lower in file.lower() and file not in close_matches
            ]

            # Combine both types of matches
            all_suggestions = (
                close_matches + substring_matches[: 3 - len(close_matches)]
            )

            # Format with relative paths
            suggestions = []
            for file in all_suggestions[:3]:
                full_path = f"{directory}/{file}" if directory != "." else file
                suggestions.append(to_workspace_relative(full_path))

            return "\n".join(suggestions) if suggestions else ""

        except Exception:
            return ""
