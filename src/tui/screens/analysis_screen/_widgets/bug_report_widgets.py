"""Styled widgets for displaying bug reports from JSON."""

from __future__ import annotations

from typing import Any, Dict

from textual.widget import Widget
from textual.widgets import Markdown


class BugReportContainer(Widget):
    """Container for the complete bug report using Markdown."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.markdown_content = ""

    def compose(self):
        """Compose the bug report as a Markdown widget."""
        yield Markdown(self.markdown_content)

    def load_from_json(self, json_data: Dict[str, Any]) -> None:
        """Load report data from JSON and convert to markdown."""
        md_lines = []

        # Title with subtle styling
        md_lines.append("# Bug Analysis Report")
        md_lines.append("---\n")

        # Summary
        summary = json_data.get("summary", "")
        if summary:
            md_lines.append("## Executive Summary\n")
            md_lines.append(f"> {summary}\n")

        # Statistics with clean formatting
        bugs = json_data.get("bugs", [])
        files_analyzed = json_data.get("files_analyzed", 0)

        md_lines.append("### Analysis Metrics\n")
        md_lines.append("| Metric | Count |")
        md_lines.append("|--------|-------|")
        md_lines.append(f"| **Issues Found** | {len(bugs)} |")
        md_lines.append(f"| **Files Analyzed** | {files_analyzed} |\n")

        # Bugs section with clean formatting
        if bugs:
            md_lines.append("## Critical Issues\n")
            for i, bug_data in enumerate(bugs, 1):
                severity = bug_data.get("severity", "medium").upper()
                severity_marker = {
                    "CRITICAL": "▌",
                    "HIGH": "▌",
                    "MEDIUM": "▌",
                    "LOW": "▌",
                }.get(severity, "▌")

                md_lines.append(
                    f"### {severity_marker} {bug_data.get('title', 'Untitled Bug')}"
                )
                md_lines.append("")
                location_line = f"**Severity:** `{severity}` • **Location:** `{bug_data.get('file', 'Unknown')}`"

                if bug_data.get("line"):
                    location_line += f" • **Line:** `{bug_data.get('line')}`"

                md_lines.append(location_line)

                md_lines.append(
                    f"\n{bug_data.get('description', 'No description provided.')}"
                )

                if bug_data.get("code_snippet"):
                    md_lines.append(f"\n```python\n{bug_data.get('code_snippet')}\n```")

                md_lines.append("")  # Empty line between bugs

        # If no issues found
        if not bugs:
            md_lines.append("## Analysis Complete\n")
            md_lines.append(
                "> No critical issues were identified in the analyzed codebase."
            )

        self.markdown_content = "\n".join(md_lines)

        # Refresh the widget to show new data
        self.refresh(layout=True)
