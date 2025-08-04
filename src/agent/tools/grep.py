from typing import Optional

from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import load_tool_description, run_in_container
from agent.utils.param_parser import ParameterParser


@register_tool("grep")
class GrepTool(BaseTool):
    description = load_tool_description("grep")
    parameters = [
        {
            "name": "pattern",
            "type": "string",
            "description": "Search pattern (literal text or regex)",
            "required": True,
        },
        {
            "name": "directory",
            "type": "string",
            "description": "Directory to search (default: .)",
            "required": False,
        },
        {
            "name": "include_files",
            "type": "string",
            "description": 'File patterns to include (e.g., "*.py", "*.{js,ts}")',
            "required": False,
        },
        {
            "name": "exclude_files",
            "type": "string",
            "description": 'File patterns to exclude (e.g., "*.pyc", "node_modules/*")',
            "required": False,
        },
        {
            "name": "case_sensitive",
            "type": "boolean",
            "description": "Case sensitive search",
            "required": False,
        },
        {
            "name": "use_regex",
            "type": "boolean",
            "description": "Treat pattern as regex",
            "required": False,
        },
        {
            "name": "max_results",
            "type": "integer",
            "description": "Max results to return (default: 100)",
            "required": False,
        },
        {
            "name": "context_lines",
            "type": "integer",
            "description": "Number of context lines before/after matches",
            "required": False,
        },
    ]

    def call(self, params: str, **kwargs) -> str:
        try:
            parsed_params = ParameterParser.parse_params(params)
            pattern = ParameterParser.get_required_param(parsed_params, "pattern")

            directory = ParameterParser.get_optional_param(parsed_params, "directory", ".")
            include_files = ParameterParser.get_optional_param(parsed_params, "include_files")
            exclude_files = ParameterParser.get_optional_param(parsed_params, "exclude_files")
            case_sensitive = ParameterParser.get_optional_param(parsed_params, "case_sensitive", False)
            use_regex = ParameterParser.get_optional_param(parsed_params, "use_regex", False)
            max_results = ParameterParser.get_optional_param(parsed_params, "max_results", 100)
            context_lines = ParameterParser.get_optional_param(parsed_params, "context_lines", 0)

            return self._ripgrep_search(
                pattern,
                directory,
                include_files,
                exclude_files,
                case_sensitive,
                use_regex,
                max_results,
                context_lines,
            )

        except Exception as e:
            return f"Error: {str(e)}"

    def _ripgrep_search(
        self,
        pattern: str,
        directory: str = ".",
        include_files: Optional[str] = None,
        exclude_files: Optional[str] = None,
        case_sensitive: bool = False,
        use_regex: bool = False,
        max_results: int = 100,
        context_lines: int = 0,
    ) -> str:
        """Fast ripgrep search in container."""
        cmd = ["rg", "--line-number", "--with-filename", "--no-heading"]

        # Add flags
        if not case_sensitive:
            cmd.append("--ignore-case")
        if max_results > 0:
            cmd.extend(["--max-count", str(max_results)])
        if context_lines > 0:
            cmd.extend(["--context", str(context_lines)])
        if use_regex:
            cmd.append("--regex")

        # Handle file patterns
        if include_files:
            if include_files.startswith("*."):
                # Simple extension like *.py
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

        # Add pattern and directory
        cmd.append(pattern)
        if directory != ".":
            cmd.append(directory)

        command = " ".join(
            f'"{part}"' if " " in str(part) else str(part) for part in cmd
        )
        return run_in_container(command)
