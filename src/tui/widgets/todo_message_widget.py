"""Inline todo message widget for displaying todo state in chat flow."""

from __future__ import annotations

from typing import Any, Dict, List

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
            status = todo.get("status", "incomplete")
            if status == "complete":
                checkbox = "●"  # Filled circle
                style = ""
            else:
                checkbox = "○"  # Empty circle
                style = ""

            todo_content = todo.get("content", "")
            # Truncate todo content to fit on one line (max 80 chars)
            max_length = 35
            if len(todo_content) > max_length:
                todo_content = todo_content[: max_length - 3] + "..."
            content.append(f"   {checkbox} {todo_content}\n", style=style)

        return content
