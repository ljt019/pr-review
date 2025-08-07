"""Main title widget with ASCII block letters for Sniff"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static
from textual_pyfiglet import FigletWidget


class SniffMainTitle(Static):
    """ASCII block letters title widget for 'Sniff' with centered layout"""
    
    def __init__(self):
        super().__init__(classes="sniff-main-title-container")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="sniff-title-horizontal"):
            yield Static("", classes="spacer")  # Left spacer
            yield FigletWidget("SNIFF", font="big", classes="sniff-main-title")
            yield Static("", classes="spacer")  # Right spacer