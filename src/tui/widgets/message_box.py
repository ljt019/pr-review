"""Message widget for streaming bug bot responses - adapted from Elia chatbox."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.syntax import Syntax
from textual.reactive import reactive
from textual.widget import Widget
from tui.utils.json_detector import json_detector


@dataclass
class BotMessage:
    """A message from the bug bot."""
    role: Literal["analysis"] 
    content: str
    has_json_detected: bool = False
    json_extracted: bool = False


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
        content_to_render = self.message.content
        
        # If JSON was detected and extracted, only show the prefix text
        if self.message.json_extracted:
            split = json_detector.split_content(self.message.content)
            if split.has_json:
                content_to_render = split.prefix_text
        
        # Analysis as markdown - return empty Text if no content to avoid showing empty widget
        if not content_to_render.strip():
            from rich.text import Text
            return Text("")  # Return empty text instead of empty string
        return Markdown(content_to_render, code_theme="monokai")
    
    def append_chunk(self, chunk: str) -> None:
        """Append a chunk of text to the end of the message."""
        self.message.content += chunk
        
        # Check if JSON has been detected in the updated content
        if not self.message.has_json_detected:
            split = json_detector.split_content(self.message.content)
            if split.has_json:
                self.message.has_json_detected = True
        
        self.refresh(layout=True)
    
    def extract_json_content(self) -> str:
        """Extract and return the JSON part, mark as extracted."""
        split = json_detector.split_content(self.message.content)
        if split.has_json:
            self.message.json_extracted = True
            self.refresh(layout=True)  # Re-render to show only prefix text
            return split.json_content
        return ""
    
    def update_content(self, new_content: str) -> None:
        """Replace the entire message content."""
        self.message.content = new_content
        self.refresh(layout=True)