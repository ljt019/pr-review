"""Bug report statistics widget"""

from textual.app import ComposeResult
from textual.widgets import Static


class BugReportStats(Static):
    """Bug report statistics"""

    def __init__(self, issues_count: int, files_analyzed: int):
        super().__init__("", classes="bug-report-stats-container")
        self.issues_count = issues_count
        self.files_analyzed = files_analyzed

    def compose(self) -> ComposeResult:
        yield Static(
            f"{self.issues_count} issues found | {self.files_analyzed} files analyzed",
            classes="bug-report-stats",
        )