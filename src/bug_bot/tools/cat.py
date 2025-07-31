import json5
import re
from qwen_agent.tools.base import BaseTool, register_tool

from bug_bot.tools import run_in_container, load_tool_description

DEFAULT_READ_LIMIT = 2000
MAX_LINE_LENGTH = 2000

# Common binary file extensions to detect
BINARY_EXTENSIONS = {
    '.exe', '.dll', '.so', '.dylib', '.a', '.o', '.pyc', '.pyo',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.zip', '.tar', '.gz', '.rar', '.7z', '.bz2',
    '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv',
    '.bin', '.dat', '.db', '.sqlite', '.sqlite3'
}

@register_tool('cat')
class CatTool(BaseTool):
    description = load_tool_description('cat')
    parameters = [
        {
            'name': 'filePath',
            'type': 'string',
            'description': 'Path to the file to read',
            'required': True
        },
        {
            'name': 'offset',
            'type': 'integer',
            'description': 'Line number to start reading from (0-based, optional)',
            'required': False
        },
        {
            'name': 'limit',
            'type': 'integer',
            'description': 'Number of lines to read (defaults to 2000, optional)',
            'required': False
        }
    ]

    def call(self, params: str, **kwargs) -> str:
        try:
            parsed_params = json5.loads(params)
            file_path = parsed_params.get('filePath')
            if not file_path:
                return "Error: filePath parameter is required"
            
            offset = parsed_params.get('offset', 0)
            limit = parsed_params.get('limit', DEFAULT_READ_LIMIT)
            
            self._pretty_print_tool(file_path, offset, limit)
            
            # Check if file is likely binary by extension
            if self._is_binary_file(file_path):
                return f"Error: Cannot read binary file: {file_path}\nThis appears to be a binary file based on its extension."
            
            # First check if file exists
            check_cmd = f'test -f "{file_path}" && echo "exists" || echo "not_found"'
            exists_result = run_in_container(check_cmd)
            
            if "not_found" in exists_result:
                # Try to suggest similar files
                suggestions = self._get_file_suggestions(file_path)
                if suggestions:
                    return f"Error: File not found: {file_path}\n\nDid you mean one of these?\n{suggestions}"
                else:
                    return f"Error: File not found: {file_path}"
            
            # Read the file with line numbers
            if offset == 0 and limit == DEFAULT_READ_LIMIT:
                # Read entire file (up to default limit)
                cat_cmd = f'cat -n "{file_path}" | head -{DEFAULT_READ_LIMIT}'
            else:
                # Read specific range
                start_line = offset + 1  # cat -n uses 1-based indexing
                end_line = offset + limit
                cat_cmd = f'sed -n "{start_line},{end_line}p" "{file_path}" | cat -n'
            
            result = run_in_container(cat_cmd)
            
            if result.startswith("Error:"):
                return result
            
            # Format the output with proper line numbering
            lines = result.split('\n')
            formatted_lines = []
            
            for line in lines:
                if line.strip():  # Skip empty lines from command output
                    # Reformat line numbers to match TypeScript version (5-digit padding)
                    if '\t' in line:
                        line_num, content = line.split('\t', 1)
                        try:
                            num = int(line_num.strip()) + offset
                            # Truncate long lines
                            if len(content) > MAX_LINE_LENGTH:
                                content = content[:MAX_LINE_LENGTH] + "..."
                            formatted_lines.append(f"{num:05d}| {content}")
                        except ValueError:
                            formatted_lines.append(line)
                    else:
                        formatted_lines.append(line)
            
            if not formatted_lines:
                return f"Error: File appears to be empty or unreadable: {file_path}"
            
            # Check if there are more lines beyond what we read
            total_lines_cmd = f'wc -l < "{file_path}"'
            total_result = run_in_container(total_lines_cmd)
            
            output = "<file>\n" + '\n'.join(formatted_lines)
            
            try:
                total_lines = int(total_result.strip())
                if total_lines > offset + len(formatted_lines):
                    output += f"\n\n(File has more lines. Use 'offset' parameter to read beyond line {offset + len(formatted_lines)})"
            except (ValueError, AttributeError):
                pass
            
            output += "\n</file>"
            
            return output
            
        except Exception as e:
            return f"Error: {str(e)}"

    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is likely binary based on extension"""
        file_path_lower = file_path.lower()
        return any(file_path_lower.endswith(ext) for ext in BINARY_EXTENSIONS)

    def _get_file_suggestions(self, file_path: str) -> str:
        """Get suggestions for similar file names when file not found"""
        try:
            # Extract directory and filename
            if '/' in file_path:
                directory = '/'.join(file_path.split('/')[:-1])
                filename = file_path.split('/')[-1]
            else:
                directory = '.'
                filename = file_path
            
            # List files in directory
            ls_cmd = f'ls "{directory}" 2>/dev/null'
            ls_result = run_in_container(ls_cmd)
            
            if ls_result.startswith("Error:"):
                return ""
            
            files = [f.strip() for f in ls_result.split('\n') if f.strip()]
            
            # Find similar files (contains part of the requested filename)
            suggestions = []
            filename_lower = filename.lower()
            
            for file in files:
                file_lower = file.lower()
                if (filename_lower in file_lower or file_lower in filename_lower) and file != filename:
                    full_path = f"{directory}/{file}" if directory != '.' else file
                    suggestions.append(full_path)
            
            return '\n'.join(suggestions[:3]) if suggestions else ""
            
        except Exception:
            return ""

    def _pretty_print_tool(self, file_path: str, offset: int, limit: int):
        print(f"🛠️ Reading File")
        print(f"  - file: {file_path}")
        if offset > 0:
            print(f"  - offset: {offset}")
        if limit != DEFAULT_READ_LIMIT:
            print(f"  - limit: {limit}")
        print()