"""Glob tool message widget"""

import json
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Markdown, Static

from agent.messaging import ToolExecutionMessage


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

    def __init__(self, tool_message: ToolExecutionMessage, matched_files=None):
        super().__init__("", classes="agent-tool-message")
        self.tool_message = tool_message
        if matched_files is not None:
            self.matched_files = matched_files
        elif tool_message.result and tool_message.success:
            # Parse the glob result - simple split by lines
            self.matched_files = [f.strip() for f in tool_message.result.strip().split('\n') if f.strip()]
        else:
            self.matched_files = self.example_files

    def compose(self) -> ComposeResult:
        try:
            # Handle dict arguments directly
            if isinstance(self.tool_message.arguments, dict):
                args = self.tool_message.arguments
            else:
                args = json.loads(self.tool_message.arguments)
            pattern = args.get("pattern", args.get("glob_pattern", args.get("file_pattern", "")))
        except (json.JSONDecodeError, AttributeError, TypeError):
            pattern = ""
        
        # If still empty, try to extract from tool_message directly
        if not pattern and hasattr(self.tool_message, 'arguments'):
            pattern = str(self.tool_message.arguments)[:50] + "..." if len(str(self.tool_message.arguments)) > 50 else str(self.tool_message.arguments)
        
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