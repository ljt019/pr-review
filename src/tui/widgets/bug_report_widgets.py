"""Styled widgets for displaying bug reports from JSON."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any

from rich.console import RenderableType
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from textual.widget import Widget
from textual.containers import Container
from textual.widgets import Static, LoadingIndicator


@dataclass
class Bug:
    """A bug found in the code."""
    title: str
    description: str
    file_path: str
    line_number: int | None = None
    severity: str = "medium"
    code_snippet: str | None = None


@dataclass
class Nitpick:
    """A code style/quality nitpick."""
    title: str
    description: str
    file_path: str
    line_number: int | None = None
    suggestion: str | None = None


class BugWidget(Widget):
    """Widget for displaying a single bug."""
    
    def __init__(self, bug: Bug, **kwargs):
        super().__init__(**kwargs)
        self.bug = bug
    
    def render(self) -> RenderableType:
        """Render the bug as a styled panel."""
        # Choose color based on severity
        severity_colors = {
            "critical": "red",
            "high": "red",
            "medium": "yellow", 
            "low": "blue"
        }
        color = severity_colors.get(self.bug.severity.lower(), "yellow")
        
        # Build content
        content = Text()
        content.append(f"📍 {self.bug.file_path}", style="cyan")
        
        if self.bug.line_number:
            content.append(f":{self.bug.line_number}", style="cyan")
        
        content.append("\n\n")
        content.append(self.bug.description, style="white")
        
        if self.bug.code_snippet:
            content.append("\n\n")
            content.append("Code:", style="bold")
            content.append(f"\n{self.bug.code_snippet}", style="dim")
        
        return Panel(
            content,
            title=f"🐛 {self.bug.title}",
            title_align="left",
            border_style=color,
            padding=(0, 1)
        )


class NitpickWidget(Widget):
    """Widget for displaying a code nitpick."""
    
    def __init__(self, nitpick: Nitpick, **kwargs):
        super().__init__(**kwargs)
        self.nitpick = nitpick
    
    def render(self) -> RenderableType:
        """Render the nitpick as a styled panel."""
        content = Text()
        content.append(f"📍 {self.nitpick.file_path}", style="cyan")
        
        if self.nitpick.line_number:
            content.append(f":{self.nitpick.line_number}", style="cyan")
        
        content.append("\n\n")
        content.append(self.nitpick.description, style="white")
        
        if self.nitpick.suggestion:
            content.append("\n\n")
            content.append("💡 Suggestion: ", style="bold green")
            content.append(self.nitpick.suggestion, style="green")
        
        return Panel(
            content,
            title=f"✨ {self.nitpick.title}",
            title_align="left", 
            border_style="blue",
            padding=(0, 1)
        )


class SummaryWidget(Widget):
    """Widget for displaying the analysis summary."""
    
    def __init__(self, summary: str, stats: Dict[str, int], **kwargs):
        super().__init__(**kwargs)
        self.summary = summary
        self.stats = stats
    
    def render(self) -> RenderableType:
        """Render the summary with stats."""
        # Create stats table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="bold")
        table.add_column(style="cyan")
        
        for key, value in self.stats.items():
            icon = {"bugs": "🐛", "nitpicks": "✨", "files_analyzed": "📁"}.get(key, "📊")
            table.add_row(f"{icon} {key.replace('_', ' ').title()}:", str(value))
        
        # Combine summary text and stats with newlines
        from rich.console import Group
        content = Group(
            Markdown(self.summary) if self.summary else Text(""),
            Text(""),  # Empty line separator
            table
        )
        
        return Panel(
            content,
            title="📋 Analysis Summary",
            title_align="left",
            border_style="green",
            padding=(1, 1)
        )


class BugReportContainer(Widget):
    """Container for the complete bug report."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bugs: List[Bug] = []
        self.nitpicks: List[Nitpick] = []
        self.summary = ""
        self.stats = {}
    
    def compose(self):
        """Compose the bug report from components."""
        # Summary first
        if self.summary or self.stats:
            yield SummaryWidget(self.summary, self.stats)
        
        # Then bugs
        for bug in self.bugs:
            yield BugWidget(bug)
        
        # Then nitpicks  
        for nitpick in self.nitpicks:
            yield NitpickWidget(nitpick)
    
    def load_from_json(self, json_data: Dict[str, Any]) -> None:
        """Load report data from JSON."""
        # Parse bugs
        for bug_data in json_data.get("bugs", []):
            bug = Bug(
                title=bug_data.get("title", "Untitled Bug"),
                description=bug_data.get("description", ""), 
                file_path=bug_data.get("file_path", ""),
                line_number=bug_data.get("line_number"),
                severity=bug_data.get("severity", "medium"),
                code_snippet=bug_data.get("code_snippet")
            )
            self.bugs.append(bug)
        
        # Parse nitpicks
        for nitpick_data in json_data.get("nitpicks", []):
            nitpick = Nitpick(
                title=nitpick_data.get("title", "Untitled Nitpick"),
                description=nitpick_data.get("description", ""),
                file_path=nitpick_data.get("file_path", ""),
                line_number=nitpick_data.get("line_number"),
                suggestion=nitpick_data.get("suggestion")
            )
            self.nitpicks.append(nitpick)
        
        # Parse summary and stats
        self.summary = json_data.get("summary", "")
        self.stats = {
            "bugs": len(self.bugs),
            "nitpicks": len(self.nitpicks), 
            "files_analyzed": json_data.get("files_analyzed", 0)
        }
        
        # Refresh the widget to show new data
        self.refresh(layout=True)


class ReportPlaceholder(Widget):
    """Placeholder widget shown while generating the report."""
    
    def render(self) -> RenderableType:
        """Render the generating message."""
        content = Text()
        content.append("🔄 Generating bug report...", style="yellow bold")
        content.append("\nAnalyzing findings and formatting results", style="dim")
        
        return Panel(
            content,
            title="📋 Bug Report",
            title_align="left",
            border_style="yellow",
            padding=(1, 2)
        )