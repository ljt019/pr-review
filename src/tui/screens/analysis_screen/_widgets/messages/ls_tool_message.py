"""Ls tool message widget"""

from textual.app import ComposeResult
from textual.widgets import Static

from agent.messaging import ToolExecutionMessage
from tui.utils.args import get_arg

from .base_tool_message import BaseToolMessage
from .common import make_markdown, parse_json_block, subtitle_from_args


class LsToolMessage(BaseToolMessage):
    """Tool call made by the agent to ls files with file tree display"""

    def __init__(self, tool_message: ToolExecutionMessage, directory_output=None):
        super().__init__(tool_message)
        if tool_message.result and tool_message.success:
            self.entries = self._parse_ls_output(tool_message.result)
        else:
            self.entries = []

    def get_title(self) -> str:
        return "☰ Ls"

    def get_subtitle(self) -> str:
        return subtitle_from_args(
            self.tool_message.arguments,
            ["path", "directory", "dir"],
            quote=False,
            default=" .",
        )

    def create_body(self) -> Static:
        # Group entries by directory and render a nested Markdown list
        # Prefer JSON block if available
        payload = parse_json_block(self.tool_message.result)
        if payload and isinstance(payload, dict) and "entries" in payload:
            entries = payload.get("entries", [])
            groups = self._group_entries_by_dir(entries)
        else:
            groups = self._group_entries_by_dir(self.entries)
        md_lines = []
        if groups:
            for directory, files in groups.items():
                md_lines.append(f"- **{directory}**")
                for file_name in files:
                    md_lines.append(f"  - {file_name}")
            markdown_content = "\n".join(md_lines)
        else:
            markdown_content = "(no files)"
        return self._markdown(markdown_content)

    def _get_path(self) -> str:
        """Extract path from tool message arguments."""
        path = get_arg(self.tool_message.arguments, ["path", "directory", "dir"], ".")
        return path if path else "."

    def _parse_ls_output(self, ls_output: str) -> list[str]:
        entries: list[str] = []
        for line in ls_output.split("\n"):
            line = line.strip()
            if not line:
                continue
            entries.append(line)
        return entries

    def _markdown(self, content: str):
        md = make_markdown(content, classes="search-markdown")
        # Set bullet icons: top-level (folders) and second-level (files)
        try:
            md.BULLETS = ["🗀 ", "🖹 ", "‣ ", "⭑ ", "⭑ "]
        except Exception:
            pass
        return md

    def _group_entries_by_dir(self, entries: list[str]) -> dict[str, list[str]]:
        """Group files under their immediate parent directory.

        - Directories are entries ending with '/'.
        - Files are grouped by their parent directory (or './' for root).
        - Directory keys include trailing '/' (except root which is './').
        """
        from collections import defaultdict

        dir_to_files: dict[str, list[str]] = defaultdict(list)

        # Ensure we include directories observed in the listing
        observed_dirs: set[str] = set()

        for entry in entries:
            if entry.endswith("/"):
                observed_dirs.add(entry)
                continue
            # File: group under parent directory
            if "/" in entry:
                parent = entry.rsplit("/", 1)[0] + "/"
                observed_dirs.add(parent)
                file_name = entry.rsplit("/", 1)[1]
                dir_to_files[parent].append(file_name)
            else:
                # Root-level file
                observed_dirs.add("./")
                dir_to_files["./"].append(entry)

        # Sort directories and files for stable rendering
        grouped: dict[str, list[str]] = {}
        for directory in sorted(observed_dirs):
            files = sorted(dir_to_files.get(directory, []))
            grouped[directory] = files

        return grouped
