from typing import Optional

from pydantic_ai.tools import Tool

from agent.tools import load_tool_description, run_in_container


def grep(
    pattern: str,
    directory: str = ".",
    include_files: Optional[str] = None,
    exclude_files: Optional[str] = None,
    case_sensitive: bool = False,
    use_regex: bool = False,
    max_results: int = 100,
    context_lines: int = 0,
) -> str:
    """Search for a pattern in files using ripgrep.

    Args:
        pattern: Search pattern (literal text or regex)
        directory: Directory to search (default: .)
        include_files: File patterns to include (e.g., "*.py")
        exclude_files: File patterns to exclude
        case_sensitive: Perform case sensitive search
        use_regex: Treat pattern as regex
        max_results: Max results to return
        context_lines: Number of context lines before/after matches
    """
    try:
        cmd = ["rg", "--line-number", "--with-filename", "--no-heading"]
        if not case_sensitive:
            cmd.append("--ignore-case")
        if max_results > 0:
            cmd.extend(["--max-count", str(max_results)])
        if context_lines > 0:
            cmd.extend(["--context", str(context_lines)])
        if use_regex:
            cmd.append("--regex")

        if include_files:
            if include_files.startswith("*."):
                ext = include_files[2:]
                if ext in [
                    "py",
                    "js",
                    "ts",
                    "java",
                    "cpp",
                    "c",
                    "go",
                    "rs",
                    "rb",
                    "php",
                    "sh",
                ]:
                    cmd.extend(["--type", ext])
                else:
                    cmd.extend(["--glob", include_files])
            else:
                cmd.extend(["--glob", include_files])
        if exclude_files:
            cmd.extend(["--glob", f"!{exclude_files}"])

        cmd.append(pattern)
        if directory != ".":
            cmd.append(directory)

        command = " ".join(
            f'"{part}"' if " " in str(part) else str(part) for part in cmd
        )
        return run_in_container(command)
    except Exception as e:
        return f"Error: {str(e)}"


grep_tool = Tool(grep, name="grep", description=load_tool_description("grep"))
