"""Ls tool message widget"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Static


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

    def __init__(self, tool_args: dict, directory_output=None):
        super().__init__("", classes="agent-tool-message")
        self.tool_args = tool_args
        self.directory_output = directory_output or self.example_output

    def compose(self) -> ComposeResult:
        tree_lines = []
        for path, item_type in self.directory_output:
            depth = path.count("/") - (1 if path.endswith("/") else 0)
            indent = "  " * depth

            if item_type == "directory":
                icon = "🗀"
                name = path.rstrip("/").split("/")[-1] + "/"
            else:
                icon = "🖹"
                name = path.split("/")[-1]

            tree_lines.append(f"{indent}{icon} {name}")

        tree_content = "\n".join(tree_lines)

        yield Vertical(
            Horizontal(
                Label("☰ Ls", classes="tool-title"),
                Label(f" {self.tool_args.get('path', '.')}", classes="tool-content"),
                classes="tool-horizontal",
            ),
            Static(tree_content, classes="file-tree"),
        )