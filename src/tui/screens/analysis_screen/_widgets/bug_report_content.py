"""Bug report content widget"""

from textual.app import ComposeResult
from textual.widgets import Markdown, Static


class BugReportContent(Static):
    """Bug report main content with issues"""

    def __init__(self, bug_report: dict):
        super().__init__("", classes="bug-report-content")
        self.bug_report = bug_report

    def _get_severity_breakdown(self, bugs):
        """Generate a severity breakdown string"""
        if not bugs:
            return "None"

        severity_counts = {"critical": 0, "major": 0, "minor": 0, "low": 0}
        for bug in bugs:
            severity = bug.get("severity", "unknown").lower()
            if severity in severity_counts:
                severity_counts[severity] += 1

        breakdown_parts = []
        for severity, count in severity_counts.items():
            if count > 0:
                breakdown_parts.append(f"{count} {severity}")

        return ", ".join(breakdown_parts) if breakdown_parts else "None"

    def compose(self) -> ComposeResult:
        summary = self.bug_report.get("summary", "No summary available")
        bugs = self.bug_report.get("bugs", [])

        md_lines = [
            "---",
            "",
            "## Summary",
            "",
            f"{summary}",
            "",
        ]

        if bugs:
            severity_groups = {"critical": [], "major": [], "minor": [], "low": []}

            for bug in bugs:
                severity = bug.get("severity", "unknown").lower()
                if severity in severity_groups:
                    severity_groups[severity].append(bug)
                else:
                    severity_groups["minor"].append(bug)

            md_lines.extend(
                [
                    "## Findings",
                    "",
                ]
            )

            for severity in ["critical", "major", "minor", "low"]:
                if severity_groups[severity]:
                    count = len(severity_groups[severity])

                    md_lines.extend(
                        [
                            f"### {severity.title()} Severity Issues ({count})",
                            "",
                        ]
                    )

                    for i, bug in enumerate(severity_groups[severity], 1):
                        title = bug.get("title", "Unknown issue")
                        description = bug.get("description", "No description")
                        file_path = bug.get("file", "unknown")
                        line = bug.get("line", "unknown")
                        category = bug.get("category", "unknown")
                        recommendation = bug.get("recommendation", "No recommendation")

                        bullet_info = f"- **Location**: `{file_path}:{line}`\n- **Category**: *{category}*\n- **Severity**: **{severity.upper()}**"

                        md_lines.extend(
                            [
                                f"#### {i}. {title}",
                                "",
                                bullet_info,
                                "",
                                "**Problem**",
                                "",
                                f"{description}",
                                "",
                                "**Recommendation**",
                                "",
                                f"{recommendation}",
                                "",
                                "---",
                                "",
                            ]
                        )
        else:
            md_lines.extend(
                [
                    "## Result",
                    "",
                    "> **✓ No security issues found**",
                    "",
                    "The analyzed codebase appears to be free of common security vulnerabilities.",
                ]
            )

        markdown_content = "\n".join(md_lines)

        markdown_widget = Markdown(
            markdown_content, classes="clean-bug-report-markdown"
        )
        markdown_widget.code_dark_theme = "catppuccin-mocha"
        markdown_widget.BULLETS = ["• ", "‣ ", "⁃ ", "◦ ", "▪ "]

        yield markdown_widget