"""Inline todo message widget for displaying todo state in chat flow."""

from __future__ import annotations

from typing import Any, Dict, List

from textual.app import ComposeResult
from textual.widgets import Label, Static

from .current_todo_list import CurrentTodoList


class TodoMessageWidget(Static):
    """Widget for displaying todo state with a tool header, matching other tool messages."""

    def __init__(self, todos_data: List[Dict[str, Any]], tool_name: str, **kwargs):
        super().__init__("", classes="agent-tool-message", **kwargs)
        self.todos_data = todos_data
        self.tool_name = tool_name

    def compose(self) -> ComposeResult:
        # Title reflects read vs write
        if self.tool_name == "todo_write":
            yield Label("✎ Todo Write", classes="tool-title")
        else:
            yield Label("⚯ Todo Read", classes="tool-title")

        if self.todos_data:
            yield CurrentTodoList(self.todos_data)
        else:
            yield Label("No todos", classes="tool-content")
