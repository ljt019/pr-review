"""Cat tool message widget"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Markdown, Static

from agent.messaging import ToolExecutionMessage
from tui.utils.args import get_arg


class CatToolMessage(Static):
    """Tool call made by the agent to *cat* files using Markdown code fencing"""

    file_content: str = ""

    def __init__(self, tool_message: ToolExecutionMessage, file_content=None):
        super().__init__("", classes="agent-tool-message")
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

        # Let Markdown handle the line numbers and syntax highlighting
        markdown_content = f"```{file_ext}\n{self.file_content}\n```"

        markdown_widget = Markdown(markdown_content, classes="code-markdown")
        markdown_widget.code_dark_theme = "catppuccin-mocha"

        yield Vertical(
            Horizontal(
                Label("⚯ Cat", classes="tool-title"),
                Label(f" {file_path or 'unknown'}", classes="tool-content"),
                classes="tool-horizontal",
            ),
            markdown_widget,
        )
