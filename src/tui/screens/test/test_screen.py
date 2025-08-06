"""Test screen for experimenting with widgets"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen

from ._widgets.test_messages_container import TestMessagesContainer


class TestScreen(Screen):
    """Test screen for widget experimentation"""

    BINDINGS = [
        Binding("escape", "back", "Back", priority=True),
    ]

    todo_list: list[str] = ["Analyze the codebase", "Write the code"]

    def compose(self) -> ComposeResult:
        """Compose the test screen with realistic chat-style scrollable interface"""
        from textual.containers import Center, Container
        from textual.widgets import Static

        yield Container(
            Static("qwen/qwen3-480b-a35b-coder", classes="header"),
            Center(TestMessagesContainer(), classes="messages-center"),
            classes="main-container",
        )

    def action_back(self) -> None:
        """Go back to previous screen"""
        self.app.pop_screen()
