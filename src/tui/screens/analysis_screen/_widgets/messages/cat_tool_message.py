"""Cat tool message widget"""

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Static

from agent.messaging import ToolExecutionMessage
from tui.utils.args import get_arg

from .common import make_markdown


class CatToolMessage(Static):
    """Tool call made by the agent to *cat* files using Markdown code fencing"""

    file_content: str = ""

    def __init__(self, tool_message: ToolExecutionMessage, file_content=None):
        super().__init__("", classes="agent-tool-message cat-tool-message")
        self.tool_message = tool_message
        if file_content is not None:
            self.file_content = file_content
        elif tool_message.result and tool_message.success:
            self.file_content = tool_message.result

    def compose(self) -> ComposeResult:
        file_path = get_arg(
            self.tool_message.arguments, ["filePath", "file_path", "file", "path"], ""
        )
        file_ext = file_path.split(".")[-1] if "." in file_path else "text"

        # Render code using Rich Syntax with NO gutter/line-number separator
        # We already include line numbers in content from cat -n
        lexer = file_ext if file_ext else "text"
        syntax = Syntax(
            self.file_content,
            lexer,
            theme="catppuccin-mocha",
            line_numbers=False,
            word_wrap=False,
        )
        # Remove theme-specified background to preserve transparent UI background
        try:
            # Rich 14 exposes background color on the theme object
            theme_obj = getattr(syntax, "_theme", None)
            if theme_obj is not None and hasattr(theme_obj, "background_color"):
                theme_obj.background_color = None
        except Exception:
            pass

        yield Vertical(
            Horizontal(
                Label("⚯ Cat", classes="tool-title"),
                Label(f" {file_path or 'unknown'}", classes="tool-content"),
                classes="tool-horizontal",
            ),
            Static(syntax, classes="code-syntax"),
        )
