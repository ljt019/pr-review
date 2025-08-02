"""Widget for displaying the current todo state from the bug bot."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any

from rich.console import RenderableType
from rich.text import Text
from textual.widget import Widget


@dataclass
class TodoItem:
    """A single todo item from the bot."""
    content: str
    status: str  # "pending", "in_progress", "completed"
    priority: str = "medium"
    id: str = ""


class TodoStateWidget(Widget):
    """Widget for displaying the bot's current todo list."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.todos: List[TodoItem] = []
        self.visible = False
    
    def update_todos(self, todos_data: List[Dict[str, Any]]) -> None:
        """Update the todo list from bot data."""
        self.todos = []
        for todo_data in todos_data:
            todo = TodoItem(
                content=todo_data.get("content", ""),
                status=todo_data.get("status", "pending"),
                priority=todo_data.get("priority", "medium"),
                id=todo_data.get("id", "")
            )
            self.todos.append(todo)
        
        # Show widget if we have todos, hide if empty
        self.visible = len(self.todos) > 0
        self.refresh(layout=True)
    
    def render(self) -> RenderableType:
        """Render the todo list with minimal styling."""
        if not self.visible or not self.todos:
            return Text("")
        
        content = Text()
        content.append("Bot Planning\n", style="bold")
        
        for todo in self.todos:
            # Status indicator
            if todo.status == "completed":
                status_text = "[DONE]"
                style = "dim"
            elif todo.status == "in_progress":
                status_text = "[WORKING]"
                style = "bold"
            else:
                status_text = "[TODO]"
                style = "dim"
            
            content.append(f"   {status_text} {todo.content}\n", style=style)
        
        return content
    
    def hide_todos(self) -> None:
        """Hide the todo widget."""
        self.visible = False
        self.todos = []
        self.refresh(layout=True)