"""Bug report message widget"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Markdown, Static


class BugReportMessage(Static):
    """Tool message displaying a structured bug report with markdown formatting"""

    def __init__(self, bug_report: dict):
        super().__init__("", classes="agent-tool-message")
        self.bug_report = bug_report

    def compose(self) -> ComposeResult:
        summary = self.bug_report.get("summary", "No summary available")
        bugs = self.bug_report.get("bugs", [])
        files_analyzed = self.bug_report.get("files_analyzed", 0)

        md_lines = [
            "## Summary",
            "",
            f"{summary}",
            "",
            f"**Files analyzed:** {files_analyzed}",
            f"**Issues found:** {len(bugs)}",
            "",
        ]

        if bugs:
            md_lines.append("## Issues")
            md_lines.append("")

            severity_groups = {"major": [], "minor": [], "critical": [], "low": []}
            for bug in bugs:
                severity = bug.get("severity", "unknown").lower()
                if severity in severity_groups:
                    severity_groups[severity].append(bug)
                else:
                    severity_groups["minor"].append(bug)

            for severity in ["critical", "major", "minor", "low"]:
                if severity_groups[severity]:
                    severity_emoji = {
                        "critical": "🔴",
                        "major": "🟡",
                        "minor": "🟢",
                        "low": "⚪",
                    }

                    md_lines.append(
                        f"### {severity_emoji[severity]} {severity.title()} Issues"
                    )
                    md_lines.append("")

                    for bug in severity_groups[severity]:
                        title = bug.get("title", "Unknown issue")
                        description = bug.get("description", "No description")
                        file_path = bug.get("file", "unknown")
                        line = bug.get("line", "unknown")
                        category = bug.get("category", "unknown")
                        recommendation = bug.get("recommendation", "No recommendation")

                        md_lines.extend(
                            [
                                f"#### {title}",
                                "",
                                f"**Location:** `{file_path}:{line}`",
                                f"**Category:** {category}",
                                "",
                                f"{description}",
                                "",
                                f"**Recommendation:** {recommendation}",
                                "",
                                "---",
                                "",
                            ]
                        )
        else:
            md_lines.append("**No issues found** ✅")

        markdown_content = "\n".join(md_lines)

        markdown_widget = Markdown(markdown_content, classes="bug-report-markdown")
        markdown_widget.code_dark_theme = "catppuccin-mocha"

        yield Vertical(
            Horizontal(
                Label("🐛 Bug Report", classes="tool-title"),
                Label(f" {len(bugs)} issues found", classes="tool-content"),
                classes="tool-horizontal",
            ),
            markdown_widget,
        )