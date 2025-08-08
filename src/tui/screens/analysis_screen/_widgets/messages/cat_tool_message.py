"""Cat tool message widget"""

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.widgets import Static

from agent.messaging import ToolExecutionMessage
from tui.utils.args import get_arg

from .base_tool_message import BaseToolMessage


class CatToolMessage(BaseToolMessage):
    """Tool call made by the agent to cat files using Rich Syntax"""

    file_content: str = ""

    def __init__(self, tool_message: ToolExecutionMessage, file_content=None):
        super().__init__(tool_message, extra_classes="cat-tool-message")
        if file_content is not None:
            self.file_content = file_content
        elif tool_message.result and tool_message.success:
            self.file_content = tool_message.result

    def get_title(self) -> str:
        return "⚯ Cat"

    def get_subtitle(self) -> str:
        file_path = get_arg(
            self.tool_message.arguments, ["filePath", "file_path", "file", "path"], ""
        )
        return f" {file_path or 'unknown'}"

    def create_body(self) -> Static:
        # Detect lexer from file extension; content already includes line numbers
        file_path = get_arg(
            self.tool_message.arguments, ["filePath", "file_path", "file", "path"], ""
        )
        file_ext = file_path.split(".")[-1] if "." in file_path else "text"
        lexer = file_ext if file_ext else "text"
        syntax = Syntax(
            self.file_content,
            lexer,
            theme="catppuccin-mocha",
            line_numbers=False,
            word_wrap=False,
        )
        try:
            theme_obj = getattr(syntax, "_theme", None)
            if theme_obj is not None and hasattr(theme_obj, "background_color"):
                theme_obj.background_color = None
        except Exception:
            pass
        return Static(syntax, classes="code-syntax")
