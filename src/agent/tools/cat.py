import difflib
from pydantic_ai.tools import Tool

from agent.tools import load_tool_description, run_in_container

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


def _is_binary_file(file_path: str) -> bool:
    """Check if file is likely binary based on extension."""
    file_path_lower = file_path.lower()
    return any(file_path_lower.endswith(ext) for ext in BINARY_EXTENSIONS)


def _get_file_suggestions(file_path: str) -> str:
    """Get suggestions for similar file names when file not found."""
    try:
        # Extract directory and filename
        if "/" in file_path:
            directory = "/".join(file_path.split("/")[:-1])
            filename = file_path.split("/")[-1]
        else:
            directory = "."
            filename = file_path

        ls_cmd = f'ls "{directory}" 2>/dev/null'
        ls_result = run_in_container(ls_cmd)
        if ls_result.startswith("Error:"):
            return ""
        files = [f.strip() for f in ls_result.split("\n") if f.strip()]

        close_matches = difflib.get_close_matches(filename, files, n=3, cutoff=0.6)
        filename_lower = filename.lower()
        substring_matches = [
            file for file in files if filename_lower in file.lower() and file not in close_matches
        ]
        all_suggestions = close_matches + substring_matches[: 3 - len(close_matches)]
        if not all_suggestions:
            return ""
        return "\n".join(all_suggestions)
    except Exception:
        return ""


def cat(filePath: str, offset: int = 0, limit: int = DEFAULT_READ_LIMIT) -> str:
    """Read file contents with line numbers and pagination.

    Args:
        filePath: Path to the file to read
        offset: Line number to start reading from (0-based)
        limit: Number of lines to read
    """
    try:
        if _is_binary_file(filePath):
            return (
                f"Error: Cannot read binary file: {filePath}\n"
                "This appears to be a binary file based on its extension."
            )

        check_cmd = f'test -f "{filePath}" && echo "exists" || echo "not_found"'
        exists_result = run_in_container(check_cmd)
        if "not_found" in exists_result:
            suggestions = _get_file_suggestions(filePath)
            if suggestions:
                return f"Error: File not found: {filePath}\n\nDid you mean one of these?\n{suggestions}"
            else:
                return f"Error: File not found: {filePath}"

        if offset == 0 and limit == DEFAULT_READ_LIMIT:
            cat_cmd = f'cat -n "{filePath}" | head -{DEFAULT_READ_LIMIT}'
        else:
            start_line = offset + 1
            end_line = offset + limit
            cat_cmd = f'sed -n "{start_line},{end_line}p" "{filePath}" | cat -n'

        result = run_in_container(cat_cmd)
        if result.startswith("Error:"):
            return result

        lines = result.split("\n")
        formatted_lines = []
        for line in lines:
            if line.strip():
                if "\t" in line:
                    line_num, content = line.split("\t", 1)
                    try:
                        num = int(line_num.strip()) + offset
                        if len(content) > MAX_LINE_LENGTH:
                            content = content[:MAX_LINE_LENGTH] + "..."
                        formatted_lines.append(f"{num:05d}| {content}")
                    except ValueError:
                        formatted_lines.append(line)
                else:
                    formatted_lines.append(line)

        if not formatted_lines:
            return f"Error: File appears to be empty or unreadable: {filePath}"

        total_lines_cmd = f'wc -l < "{filePath}"'
        total_result = run_in_container(total_lines_cmd)
        output = "<file>\n" + "\n".join(formatted_lines)
        try:
            total_lines = int(total_result.strip())
            if total_lines > offset + len(formatted_lines):
                output += (
                    f"\n\n(File has more lines. Use 'offset' parameter to read beyond line {offset + len(formatted_lines)})"
                )
        except (ValueError, AttributeError):
            pass
        output += "\n</file>"
        return output
    except Exception as e:
        return f"Error: {str(e)}"


cat_tool = Tool(cat, name="cat", description=load_tool_description("cat"))
