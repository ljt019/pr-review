"""Ls tool message widget"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Static

from agent.messaging import ToolExecutionMessage
from tui.utils.args import get_arg

from .common import make_markdown


class LsToolMessage(Static):
    """Tool call made by the agent to *ls* files with file tree display"""

    example_output = [
        ("src/", "directory"),
        ("src/agent/", "directory"),
        ("src/agent/__init__.py", "file"),
        ("src/agent/agent.py", "file"),
        ("src/agent/messages.py", "file"),
        ("src/tui/", "directory"),
        ("src/tui/screens/", "directory"),
        ("src/tui/screens/analysis_screen/", "directory"),
        ("src/tui/screens/analysis_screen/analysis_screen.py", "file"),
        ("src/tui/screens/test/", "directory"),
        ("src/tui/screens/test/test_screen.py", "file"),
        ("src/tui/widgets/", "directory"),
        ("src/tui/widgets/ascii_art.py", "file"),
        ("src/tui/widgets/instruction_text.py", "file"),
        ("README.md", "file"),
        ("pyproject.toml", "file"),
    ]

    def __init__(self, tool_message: ToolExecutionMessage, directory_output=None):
        super().__init__("", classes="agent-tool-message")
        self.tool_message = tool_message
        # Prepare parsed entries from tool result; fallback to examples
        if tool_message.result and tool_message.success:
            self.entries = self._parse_ls_output(tool_message.result)
        else:
            # Use example entries
            self.entries = [p for p, _ in self.example_output]

    def compose(self) -> ComposeResult:
        # Group entries by directory and render a nested Markdown list
        groups = self._group_entries_by_dir(self.entries)
        md_lines = []
        if not groups:
            markdown_content = "(no files)"
        else:
            for directory, files in groups.items():
                # Top-level bullet: directory
                md_lines.append(f"- **{directory}**")
                # Nested bullets: files
                for file_name in files:
                    md_lines.append(f"  - {file_name}")
            markdown_content = "\n".join(md_lines)

        yield Vertical(
            Horizontal(
                Label("☰ Ls", classes="tool-title"),
                Label(f" {self._get_path()}", classes="tool-content"),
                classes="tool-horizontal",
            ),
            self._markdown(markdown_content),
        )

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
