"""Grep tool message widget"""

import json
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Markdown, Static

from agent.messages import ToolCallMessage


class GrepToolMessage(Static):
    """Tool call made by the agent to *grep* files / patterns with polished search results"""

    example_matches = [
        ("src/agent/agent.py", 15, "def run_analysis(self):"),
        ("src/agent/agent.py", 28, "    analysis_results = []"),
        (
            "src/tui/services/message_renderer.py",
            45,
            "def render_analysis_message(self):",
        ),
        ("src/tui/services/message_renderer.py", 67, "    self.analysis_count += 1"),
        ("README.md", 12, "## Analysis Features"),
        ("README.md", 34, "Run analysis with: `sniff analyze`"),
        ("pyproject.toml", 8, 'name = "analysis-tool"'),
        ("src/utils/helpers.py", 23, "def analyze_code_quality():"),
    ]

    def __init__(self, tool_message: ToolCallMessage, search_results=None):
        super().__init__("", classes="agent-tool-message")
        self.tool_message = tool_message
        self.search_results = search_results or self.example_matches

    def compose(self) -> ComposeResult:
        try:
            args = json.loads(self.tool_message.arguments)
            pattern = args.get("pattern", args.get("search_pattern", ""))
        except (json.JSONDecodeError, AttributeError):
            pattern = ""
        
        # If still empty, try to extract from tool_message directly
        if not pattern and hasattr(self.tool_message, 'arguments'):
            pattern = str(self.tool_message.arguments)[:50] + "..." if len(str(self.tool_message.arguments)) > 50 else str(self.tool_message.arguments)
        match_count = len(self.search_results)

        files_dict = {}
        for file_path, line_num, content in self.search_results:
            if file_path not in files_dict:
                files_dict[file_path] = []
            files_dict[file_path].append((line_num, content.strip()))

        md_lines = [
            f"\n**{match_count} matches** found across **{len(files_dict)} files**",
            "",
        ]

        for file_path, matches in files_dict.items():
            md_lines.append(f"- **{file_path}**")
            for line_num, content in matches:
                md_lines.append(f"  - Line **{line_num}**: `{content}`")
            md_lines.append("")

        markdown_content = "\n".join(md_lines)

        markdown_widget = Markdown(markdown_content, classes="search-markdown")
        markdown_widget.code_dark_theme = "catppuccin-mocha"
        markdown_widget.BULLETS = ["🖹 ", "• ", "‣ ", "⭑ ", "⭑ "]

        yield Vertical(
            Horizontal(
                Label("⌕ Grep", classes="tool-title"),
                Label(f' "{pattern}"', classes="tool-content"),
                classes="tool-horizontal",
            ),
            markdown_widget,
        )