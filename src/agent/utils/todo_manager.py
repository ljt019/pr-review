import uuid
from dataclasses import dataclass
from typing import List


@dataclass
class TodoItem:
    """Simple representation of a todo entry."""

    id: str
    content: str
    status: str  # "pending", "in_progress", "completed"
    cancelled: bool = False  # Whether this todo is cancelled

    def __post_init__(self) -> None:
        valid_statuses = {
            "pending",
            "in_progress",
            "completed",
            "complete",
            "incomplete",
        }
        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{self.status}'. Must be one of {valid_statuses}"
            )

        # Convert legacy statuses for backward compatibility
        if self.status == "incomplete":
            self.status = "pending"
        elif self.status == "complete":
            self.status = "completed"


class TodoManager:
    """Manages todo items with thread-safe operations."""

    def __init__(self):
        self._todos: List[TodoItem] = []

    def clear(self) -> None:
        """Clear all todos."""
        self._todos.clear()

    def add_todo(
        self,
        content: str,
        status: str = "pending",
        todo_id: str = None,
        cancelled: bool = False,
    ) -> TodoItem:
        """Add a new todo item."""
        if todo_id is None:
            todo_id = f"todo_{uuid.uuid4().hex[:8]}"

        todo = TodoItem(
            id=todo_id, content=content.strip(), status=status, cancelled=cancelled
        )
        self._todos.append(todo)
        return todo

    def get_all_todos(self) -> List[TodoItem]:
        """Get all todos."""
        return self._todos.copy()

    def get_incomplete_todos(self) -> List[TodoItem]:
        """Get todos that are not completed and not cancelled."""
        return [t for t in self._todos if t.status != "completed" and not t.cancelled]

    def get_complete_todos(self) -> List[TodoItem]:
        """Get completed todos."""
        return [t for t in self._todos if t.status == "completed"]

    def update_from_list(self, todos_data: List) -> None:
        """Update todos from a list of data (strings or dicts)."""
        for todo_item in todos_data:
            if isinstance(todo_item, str):
                # New todo item - add it
                self.add_todo(content=todo_item)
            elif isinstance(todo_item, dict):
                content = todo_item.get("content")
                if not content:
                    raise ValueError("Each todo object must have 'content'")

                status = todo_item.get("status", "pending")
                todo_id = todo_item.get("id")
                cancelled = todo_item.get("cancelled", False)

                # Try to find existing todo by ID or content
                existing_todo = None
                if todo_id:
                    existing_todo = next(
                        (t for t in self._todos if t.id == todo_id), None
                    )
                if not existing_todo:
                    # Try to find by content if no ID match
                    existing_todo = next(
                        (t for t in self._todos if t.content == content), None
                    )

                if existing_todo:
                    # Update existing todo
                    existing_todo.status = status
                    existing_todo.cancelled = cancelled
                    if todo_id and existing_todo.id != todo_id:
                        existing_todo.id = todo_id
                else:
                    # Add new todo
                    self.add_todo(
                        content=content,
                        status=status,
                        todo_id=todo_id,
                        cancelled=cancelled,
                    )
            else:
                raise ValueError(
                    f"Each todo must be a string or object, got {type(todo_item)}"
                )

    def get_summary(self) -> str:
        """Get a summary of todo counts."""
        total = len(self._todos)
        incomplete = sum(
            1 for t in self._todos if t.status != "completed" and not t.cancelled
        )
        return f"{total} total, {incomplete} incomplete"

    def format_todos(self) -> str:
        """Format todos for display."""
        if not self._todos:
            return "No todos"

        lines = []
        for todo in self._todos:
            # Determine status symbol based on status
            if todo.status == "completed":
                checkbox = "[x]"  # filled circle (completed)
            elif todo.status == "in_progress":
                checkbox = "[>]"  # half circle (in progress)
            else:  # pending
                checkbox = "[]"  # hollow circle (pending)

            # Apply strikethrough if cancelled
            if todo.cancelled:
                line = f"{checkbox} - ~~{todo.content}~~"
            else:
                line = f"{checkbox} - {todo.content}"

            lines.append(line)

        return "\n".join(lines)


# Global instance for backward compatibility
_todo_manager = TodoManager()


def get_todo_manager() -> TodoManager:
    """Get the global todo manager instance."""
    return _todo_manager
