"""Inline todo message widget for displaying todo state in chat flow."""

from __future__ import annotations
from typing import List, Dict, Any

from rich.console import RenderableType
from rich.text import Text
from textual.widget import Widget


class TodoMessageWidget(Widget):
    """Widget for displaying todo state inline in the chat flow."""
    
    def __init__(self, todos_data: List[Dict[str, Any]], **kwargs):
        super().__init__(**kwargs)
        self.todos_data = todos_data
    
    def render(self) -> RenderableType:
        """Render the todo list as an inline message."""
        if not self.todos_data:
            return Text("No todos", style="dim")
        
        content = Text()
        content.append("Todo List\n", style="bold")
        
        for todo in self.todos_data:
            # Checkbox indicator
            status = todo.get("status", "pending")
            if status == "completed":
                checkbox = "[x]"
                style = ""
            else:
                checkbox = "[ ]"  # Empty checkbox
                style = ""
            
            todo_content = todo.get("content", "")
            content.append(f"   {checkbox} {todo_content}\n", style=style)
        
        return content