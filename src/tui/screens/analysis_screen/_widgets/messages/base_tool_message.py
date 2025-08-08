"""Base widget for rendering tool messages with a common header and body layout."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Static

from agent.messaging import ToolExecutionMessage


class BaseToolMessage(Static):
    """Common layout for tool messages.

    Subclasses should override get_title(), get_subtitle(), and create_body().
    """

    def __init__(
        self, tool_message: ToolExecutionMessage, extra_classes: str | None = None
    ):
        classes = "agent-tool-message" + (f" {extra_classes}" if extra_classes else "")
        super().__init__("", classes=classes)
        self.tool_message = tool_message

    # Header title, e.g., "⌕ Grep"
    def get_title(self) -> str:
        return "Tool"

    # Header subtitle, e.g., ' "pattern"' or " ./src"
    def get_subtitle(self) -> str:
        return ""

    # Body widget with tool-specific content
    def create_body(self) -> Static:
        return Static("")

    def compose(self) -> ComposeResult:
        yield Vertical(
            Horizontal(
                Label(self.get_title(), classes="tool-title"),
                Label(self.get_subtitle(), classes="tool-content"),
                classes="tool-horizontal",
            ),
            self.create_body(),
        )
