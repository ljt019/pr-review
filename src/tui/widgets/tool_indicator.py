"""Minimal tool call indicator widget."""

from textual.reactive import reactive
from textual.widget import Widget
from rich.text import Text


class ToolIndicator(Widget):
    """A minimal widget to show tool calls without taking up much space."""
    
    def __init__(self, tool_name: str, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.completed = False
    
    def render(self) -> Text:
        """Render a compact tool indicator."""
        if self.completed:
            return Text(f"[DONE] {self.tool_name}", style="dim")
        else:
            return Text(f"[RUNNING] {self.tool_name}", style="dim")
    
    def mark_completed(self) -> None:
        """Mark the tool as completed."""
        self.completed = True
        self.refresh()