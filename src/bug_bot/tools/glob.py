import json5
from qwen_agent.tools.base import BaseTool, register_tool
from bug_bot.tools import run_in_container, load_tool_description

@register_tool('glob')
class GlobTool(BaseTool):
    description = load_tool_description('glob')
    parameters = [
        {
            'name': 'pattern',
            'type': 'string',
            'description': 'Glob pattern to match files (e.g., "**/*.py", "test_*.js", "*.{json,yml}")',
            'required': True
        },
        {
            'name': 'path',
            'type': 'string',
            'description': 'Directory to search in (defaults to current directory)',
            'required': False
        }
    ]

    def call(self, params: str, **kwargs) -> str:
        try:
            parsed_params = json5.loads(params)
            pattern = parsed_params.get('pattern')
            if not pattern:
                return "Error: pattern parameter is required"
            
            search_path = parsed_params.get('path', '.')
            
            self._pretty_print_tool(pattern, search_path)
            
            # Build an appropriate find command
            # Special-case patterns that mean "all files"
            if pattern in ["*", "**", "**/*"]:
                find_cmd = f'find "{search_path}" -type f -printf "%T@ %p\\n" 2>/dev/null | sort -rn | head -50 | cut -d" " -f2-'
            else:
                # General pattern: use -path so that wildcards match full path components
                # Replace any leading "**/" with "*/" because find's wildcard traverses directories by default
                normalized_pattern = pattern.replace("**/", "*/").replace("**", "*")
                find_cmd = (
                    f'find "{search_path}" -type f -path "*{normalized_pattern}*" '
                    f'-printf "%T@ %p\\n" 2>/dev/null | sort -rn | head -50 | cut -d" " -f2-'
                )
            
            result = run_in_container(find_cmd)
            
            if result.startswith("Error:"):
                return result
            
            lines = [line.strip() for line in result.split('\n') if line.strip()]
            
            if not lines:
                return f"No files found matching pattern '{pattern}' in {search_path}"
            
            # Check if we hit the limit
            file_count = len(lines)
            output_lines = lines.copy()
            
            if file_count == 50:
                # Check if there are more files
                count_cmd = f'find "{search_path}" -name "{pattern}" -type f 2>/dev/null | wc -l'
                count_result = run_in_container(count_cmd)
                try:
                    total_count = int(count_result.strip())
                    if total_count > 50:
                        output_lines.append("")
                        output_lines.append(f"(Showing 50 of {total_count} files. Consider using a more specific pattern.)")
                except:
                    pass
            
            return '\n'.join(output_lines)
            
        except Exception as e:
            return f"Error: {str(e)}"

    def _pretty_print_tool(self, pattern: str, path: str):
        print(f"🛠️ Globbing")
        print(f"  - pattern: {pattern}")
        if path != '.':
            print(f"  - path: {path}")
        print()
