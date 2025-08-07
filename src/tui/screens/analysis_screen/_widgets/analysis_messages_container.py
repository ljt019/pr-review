"""Analysis messages container widget"""

from textual.app import ComposeResult
from textual.containers import VerticalScroll


class AnalysisMessagesContainer(VerticalScroll):
    """Scrollable container for analysis messages that integrates with agent service"""

    def __init__(self):
        super().__init__(id="messages-container", classes="scrollbar_styles")

    def compose(self) -> ComposeResult:
        """Empty initial composition - messages are added dynamically via message renderer"""
        return []