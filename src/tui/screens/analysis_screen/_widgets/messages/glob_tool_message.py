"""Glob tool message widget"""

from textual.app import ComposeResult
from textual.widgets import Static

from agent.messaging import ToolExecutionMessage
from tui.utils.args import get_arg

from .base_tool_message import BaseToolMessage
from .common import make_markdown


class GlobToolMessage(BaseToolMessage):
    """Tool call made by the agent to glob files / patterns with polished file matches display"""

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
        super().__init__(tool_message)
        if matched_files is not None:
            self.matched_files = matched_files
        elif tool_message.result and tool_message.success:
            # Parse the glob result - simple split by lines
            self.matched_files = [
                f.strip() for f in tool_message.result.strip().split("\n") if f.strip()
            ]
        else:
            self.matched_files = self.example_files

    def get_title(self) -> str:
        return "⌕ Glob"

    def get_subtitle(self) -> str:
        pattern = get_arg(
            self.tool_message.arguments, ["pattern", "glob_pattern", "file_pattern"], ""
        )
        return f' "{pattern}"'

    def create_body(self) -> Static:
        file_count = len(self.matched_files)
        md_lines = [f"**{file_count} files** matched pattern", ""]
        for file_path in self.matched_files:
            md_lines.append(f"- **{file_path}**")
        if not self.matched_files:
            md_lines = ["**No files matched** the pattern"]
        markdown_content = "\n".join(md_lines)
        return make_markdown(
            markdown_content,
            classes="search-markdown",
            bullets=["🖹 ", "🖹 ", "🖹 ", "🖹 ", "🖹 "],
        )
