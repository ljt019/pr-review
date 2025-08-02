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

        # Title
        md_lines.append("# 🐛 Bug Report\n")

        # Summary
        summary = json_data.get("summary", "")
        if summary:
            md_lines.append("## 📊 Analysis Summary\n")
            md_lines.append(f"{summary}\n")

        # Statistics
        bugs = json_data.get("bugs", [])
        nitpicks = json_data.get("nitpicks", [])
        files_analyzed = json_data.get("files_analyzed", 0)

        md_lines.append("### 📈 Statistics\n")
        md_lines.append(f"- **Bugs Found**: {len(bugs)}")
        md_lines.append(f"- **Code Quality Issues**: {len(nitpicks)}")
        md_lines.append(f"- **Files Analyzed**: {files_analyzed}\n")

        # Bugs section
        if bugs:
            md_lines.append("## 🚨 Bugs Found\n")
            for i, bug_data in enumerate(bugs, 1):
                severity = bug_data.get("severity", "medium").upper()
                severity_emoji = {
                    "CRITICAL": "🔴",
                    "HIGH": "🟠",
                    "MEDIUM": "🟡",
                    "LOW": "🟢",
                }.get(severity, "🟡")

                md_lines.append(
                    f"### {severity_emoji} Bug #{i}: {bug_data.get('title', 'Untitled Bug')}"
                )
                md_lines.append(f"**Severity**: `{severity}`")
                md_lines.append(f"**File**: `{bug_data.get('file_path', 'Unknown')}`")

                if bug_data.get("line_number"):
                    md_lines.append(f"**Line**: {bug_data.get('line_number')}")

                md_lines.append(
                    f"\n{bug_data.get('description', 'No description provided.')}"
                )

                if bug_data.get("code_snippet"):
                    md_lines.append(f"\n```python\n{bug_data.get('code_snippet')}\n```")

                md_lines.append("")  # Empty line between bugs

        # Nitpicks section
        if nitpicks:
            md_lines.append("## 💡 Code Quality Issues\n")
            for i, nitpick_data in enumerate(nitpicks, 1):
                md_lines.append(
                    f"### Issue #{i}: {nitpick_data.get('title', 'Untitled Issue')}"
                )
                md_lines.append(
                    f"**File**: `{nitpick_data.get('file_path', 'Unknown')}`"
                )

                if nitpick_data.get("line_number"):
                    md_lines.append(f"**Line**: {nitpick_data.get('line_number')}")

                md_lines.append(
                    f"\n{nitpick_data.get('description', 'No description provided.')}"
                )

                if nitpick_data.get("suggestion"):
                    md_lines.append(
                        f"\n**💭 Suggestion**: {nitpick_data.get('suggestion')}"
                    )

                md_lines.append("")  # Empty line between nitpicks

        # If no issues found
        if not bugs and not nitpicks:
            md_lines.append("## ✅ No Issues Found\n")
            md_lines.append(
                "Great job! No bugs or code quality issues were detected in the analyzed code."
            )

        self.markdown_content = "\n".join(md_lines)

        # Refresh the widget to show new data
        self.refresh(layout=True)
