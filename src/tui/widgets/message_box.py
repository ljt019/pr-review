"""Message widget for streaming bug bot responses - adapted from Elia chatbox."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.syntax import Syntax
from textual.reactive import reactive
from textual.widget import Widget


@dataclass
class BotMessage:
    """A message from the bug bot."""
    role: Literal["analysis"] 
    content: str


class MessageBox(Widget, can_focus=True):
    """A widget for displaying bug bot messages with streaming support."""
    
    def __init__(self, message: BotMessage, **kwargs):
        super().__init__(**kwargs)
        self.message = message
    
    def on_mount(self) -> None:
        """Style the message based on its role."""
        self.add_class("analysis-message")
        self.border_title = "💭 Analysis"
    
    def render(self) -> RenderableType:
        """Render the message content."""
        # Analysis as markdown
        return Markdown(self.message.content, code_theme="monokai")
    
    def append_chunk(self, chunk: str) -> None:
        """Append a chunk of text to the end of the message."""
        self.message.content += chunk
        self.refresh(layout=True)
    
    def update_content(self, new_content: str) -> None:
        """Replace the entire message content."""
        self.message.content = new_content
        self.refresh(layout=True)