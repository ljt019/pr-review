"""Glob tool message widget"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Markdown, Static


class GlobToolMessage(Static):
    """Tool call made by the agent to *glob* files / patterns with polished file matches display"""

    example_files = [
        "src/agent/__init__.py",
        "src/agent/agent.py",
        "src/agent/messages.py",
        "src/tui/__init__.py",
        "src/tui/services/__init__.py",
        "src/tui/services/agent_service.py",
        "src/tui/services/message_renderer.py",
        "src/tui/screens/analysis_screen/analysis_screen.py",
        "src/tui/screens/api_key/api_key_screen.py",
        "src/tui/screens/model_select/model_select_screen.py",
        "src/tui/widgets/ascii_art.py",
        "src/tui/widgets/instruction_text.py",
    ]

    def __init__(self, tool_args: dict, matched_files=None):
        super().__init__("", classes="agent-tool-message")
        self.tool_args = tool_args
        self.matched_files = matched_files or self.example_files

    def compose(self) -> ComposeResult:
        pattern = self.tool_args.get("pattern", "")
        file_count = len(self.matched_files)

        md_lines = [
            f"**{file_count} files** matched pattern",
            "",
        ]

        for file_path in self.matched_files:
            md_lines.append(f"- **{file_path}**")

        if not self.matched_files:
            md_lines = ["**No files matched** the pattern"]

        markdown_content = "\n".join(md_lines)

        markdown_widget = Markdown(markdown_content, classes="search-markdown")
        markdown_widget.code_dark_theme = "catppuccin-mocha"
        markdown_widget.BULLETS = ["🖹 ", "🖹 ", "🖹 ", "🖹 ", "🖹 "]

        yield Vertical(
            Horizontal(
                Label("⌕ Glob", classes="tool-title"),
                Label(f' "{pattern}"', classes="tool-content"),
                classes="tool-horizontal",
            ),
            markdown_widget,
        )