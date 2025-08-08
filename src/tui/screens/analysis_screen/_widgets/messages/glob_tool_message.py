"""Glob tool message widget"""

from textual.app import ComposeResult
from textual.widgets import Static

from agent.messaging import ToolExecutionMessage
from tui.utils.args import get_arg

from .base_tool_message import BaseToolMessage
from .common import make_markdown, parse_json_block, subtitle_from_args


class GlobToolMessage(BaseToolMessage):
    """Tool call made by the agent to glob files / patterns with polished file matches display"""

    def __init__(self, tool_message: ToolExecutionMessage, matched_files=None):
        super().__init__(tool_message)
        # Legacy path retained only for extremely old outputs; otherwise unused
        if matched_files is not None:
            self.matched_files = matched_files
        else:
            self.matched_files = []

    def get_title(self) -> str:
        return "⌕ Glob"

    def get_subtitle(self) -> str:
        return subtitle_from_args(
            self.tool_message.arguments,
            ["pattern", "glob_pattern", "file_pattern"],
            quote=True,
            default="",
        )

    def create_body(self) -> Static:
        payload = parse_json_block(self.tool_message.result)
        if payload and isinstance(payload, dict) and "files" in payload:
            files = payload.get("files", [])
            file_count = len(files)
            md_lines = [f"**{file_count} files** matched pattern", ""]
            for file_path in files:
                md_lines.append(f"- **{file_path}**")
            if not files:
                md_lines = ["**No files matched** the pattern"]
            markdown_content = "\n".join(md_lines)
            return make_markdown(
                markdown_content,
                classes="search-markdown",
                bullets=["🖹 ", "🖹 ", "🖹 ", "🖹 ", "🖹 "],
            )

        # Fallback: minimal message when JSON missing (should not happen since we control outputs)
        return make_markdown(
            "**No files matched** the pattern", classes="search-markdown"
        )
