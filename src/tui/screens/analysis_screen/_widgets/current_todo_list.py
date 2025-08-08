"""Current todo list widget"""

from textual.app import ComposeResult
from textual.widgets import Label, Static


class CurrentTodoList(Static):
    """Current todo list"""

    def __init__(self, todos: list[dict]):
        super().__init__("", classes="current-todo-list")
        self.todos = todos

    def compose(self) -> ComposeResult:
        if not self.todos:
            return

        for i, todo in enumerate(self.todos):
            # Extract todo information
            content = todo.get("content", "No content")
            status = todo.get("status", "pending")
            cancelled = todo.get("cancelled", False)

            # Choose symbol based on status
            if status == "completed":
                symbol = "●"  # filled circle
            elif status == "in_progress":
                symbol = "◐"  # half circle
            else:  # pending
                symbol = "○"  # hollow circle

            # Apply strikethrough if cancelled
            if cancelled:
                content = f"~~{content}~~"

            # Format with proper indentation
            if i == 0:
                yield Label(f"  └ {symbol} {content}", classes="todo-entry")
            else:
                yield Label(f"    {symbol} {content}", classes="todo-entry")
