from pydantic_ai.tools import Tool
from agent.tools import load_tool_description, run_in_container


def glob(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern.

    Args:
        pattern: Glob pattern to match files (e.g., "**/*.py")
        path: Directory to search in (defaults to current directory)
    """
    try:
        if pattern in ["*", "**", "**/*"]:
            find_cmd = f'find "{path}" -type f 2>/dev/null | head -50'
        else:
            normalized_pattern = pattern.replace("**/", "*/").replace("**", "*")
            find_cmd = (
                f'find "{path}" -type f -path "*{normalized_pattern}*" 2>/dev/null | head -50'
            )

        result = run_in_container(find_cmd)
        if result.startswith("Error:"):
            return result

        lines = [line.strip() for line in result.split("\n") if line.strip()]
        if not lines:
            return f"No files found matching pattern '{pattern}' in {path}"

        file_count = len(lines)
        output_lines = lines.copy()
        if file_count == 50:
            count_cmd = f'find "{path}" -name "{pattern}" -type f 2>/dev/null | wc -l'
            count_result = run_in_container(count_cmd)
            try:
                total_count = int(count_result.strip())
                if total_count > 50:
                    output_lines.append("")
                    output_lines.append(
                        f"(Showing 50 of {total_count} files. Consider using a more specific pattern.)"
                    )
            except Exception:
                pass

        return "\n".join(output_lines)
    except Exception as e:
        return f"Error: {str(e)}"


glob_tool = Tool(glob, name="glob", description=load_tool_description("glob"))
