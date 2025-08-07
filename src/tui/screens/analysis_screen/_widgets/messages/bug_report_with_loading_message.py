"""Bug report with loading message widget"""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ..bug_report_header import BugReportHeader
from ..bug_report_stats import BugReportStats
from ..bug_report_content import BugReportContent


class BugReportWithLoadingMessage(Static):
    """Combined widget that shows loading state then bug report"""

    def __init__(self, bug_report: dict, is_loading: bool = True):
        super().__init__("", classes="agent-tool-message")
        self.bug_report = bug_report
        self.is_loading = is_loading

    def update_with_report(self, bug_report: dict) -> None:
        """Update the widget with actual bug report data and switch to display mode"""
        self.bug_report = bug_report
        self.is_loading = False
        self.refresh(recompose=True)

    def compose(self) -> ComposeResult:
        if self.is_loading:
            yield Vertical(
                Static("Generating bug report...", classes="loading-message"),
            )
        else:
            bugs = self.bug_report.get("bugs", [])
            files_analyzed = self.bug_report.get("files_analyzed", 0)

            yield Vertical(
                BugReportHeader(),
                BugReportStats(len(bugs), files_analyzed),
                BugReportContent(self.bug_report),
            )