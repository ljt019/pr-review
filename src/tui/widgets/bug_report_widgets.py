"""Styled widgets for displaying bug reports from JSON."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any

from rich.console import RenderableType
from rich.text import Text
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
        """Render the bug with minimal styling."""
        content = Text()
        
        # Bug title with severity indicator
        severity_labels = {
            "critical": "[CRITICAL]",
            "high": "[HIGH]", 
            "medium": "[MEDIUM]",
            "low": "[LOW]"
        }
        label = severity_labels.get(self.bug.severity.lower(), "[MEDIUM]")
        
        content.append(f"{label} {self.bug.title}\n", style="bold")
        content.append(f"   {self.bug.file_path}", style="dim")
        
        if self.bug.line_number:
            content.append(f":{self.bug.line_number}", style="dim")
        
        content.append(f"\n   {self.bug.description}\n", style="")
        
        if self.bug.code_snippet:
            content.append(f"   Code: {self.bug.code_snippet}\n", style="dim")
        
        return content


class NitpickWidget(Widget):
    """Widget for displaying a code nitpick."""
    
    def __init__(self, nitpick: Nitpick, **kwargs):
        super().__init__(**kwargs)
        self.nitpick = nitpick
    
    def render(self) -> RenderableType:
        """Render the nitpick with minimal styling."""
        content = Text()
        
        content.append(f"[NITPICK] {self.nitpick.title}\n", style="bold")
        content.append(f"   {self.nitpick.file_path}", style="dim")
        
        if self.nitpick.line_number:
            content.append(f":{self.nitpick.line_number}", style="dim")
        
        content.append(f"\n   {self.nitpick.description}\n", style="")
        
        if self.nitpick.suggestion:
            content.append(f"   Suggestion: {self.nitpick.suggestion}\n", style="dim")
        
        return content


class SummaryWidget(Widget):
    """Widget for displaying the analysis summary."""
    
    def __init__(self, summary: str, stats: Dict[str, int], **kwargs):
        super().__init__(**kwargs)
        self.summary = summary
        self.stats = stats
    
    def render(self) -> RenderableType:
        """Render the summary with minimal styling."""
        content = Text()
        
        content.append("Analysis Summary\n", style="bold")
        
        if self.summary:
            content.append(f"   {self.summary}\n\n", style="")
        
        # Add stats as simple text
        for key, value in self.stats.items():
            content.append(f"   {key.replace('_', ' ').title()}: {value}\n", style="dim")
        
        return content


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
        """Render the generating message with minimal styling."""
        content = Text()
        content.append("Generating bug report...\n", style="bold")
        content.append("   Analyzing findings and formatting results", style="dim")
        
        return content