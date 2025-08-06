"""Bug report header widget"""

from textual.app import ComposeResult
from textual.widgets import Static


class BugReportHeader(Static):
    """Bug report header with title"""

    def __init__(self):
        super().__init__("", classes="bug-report-header")

    def compose(self) -> ComposeResult:
        yield Static("Bug Report", classes="bug-report-title")