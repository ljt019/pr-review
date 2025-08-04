import uuid
from dataclasses import dataclass
from typing import List


@dataclass
class TodoItem:
    """Simple representation of a todo entry."""

    id: str
    content: str
    status: str  # "complete" or "incomplete"

    def __post_init__(self) -> None:
        if self.status not in {"complete", "incomplete"}:
            raise ValueError("Invalid status. Must be 'complete' or 'incomplete'")


class TodoManager:
    """Manages todo items with thread-safe operations."""
    
    def __init__(self):
        self._todos: List[TodoItem] = []
    
    def clear(self) -> None:
        """Clear all todos."""
        self._todos.clear()
    
    def add_todo(self, content: str, status: str = "incomplete", todo_id: str = None) -> TodoItem:
        """Add a new todo item."""
        if todo_id is None:
            todo_id = f"todo_{uuid.uuid4().hex[:8]}"
        
        todo = TodoItem(id=todo_id, content=content.strip(), status=status)
        self._todos.append(todo)
        return todo
    
    def get_all_todos(self) -> List[TodoItem]:
        """Get all todos."""
        return self._todos.copy()
    
    def get_incomplete_todos(self) -> List[TodoItem]:
        """Get only incomplete todos."""
        return [t for t in self._todos if t.status == "incomplete"]
    
    def get_complete_todos(self) -> List[TodoItem]:
        """Get only complete todos."""
        return [t for t in self._todos if t.status == "complete"]
    
    def update_from_list(self, todos_data: List) -> None:
        """Update todos from a list of data (strings or dicts)."""
        self.clear()
        
        for todo_item in todos_data:
            if isinstance(todo_item, str):
                self.add_todo(content=todo_item)
            elif isinstance(todo_item, dict):
                content = todo_item.get("content")
                if not content:
                    raise ValueError("Each todo object must have 'content'")
                
                status = todo_item.get("status", "incomplete")
                todo_id = todo_item.get("id")
                self.add_todo(content=content, status=status, todo_id=todo_id)
            else:
                raise ValueError(f"Each todo must be a string or object, got {type(todo_item)}")
    
    def get_summary(self) -> str:
        """Get a summary of todo counts."""
        total = len(self._todos)
        incomplete = len(self.get_incomplete_todos())
        return f"{total} total, {incomplete} incomplete"
    
    def format_todos(self) -> str:
        """Format todos for display."""
        if not self._todos:
            return "No todos"
        
        lines = []
        for todo in self._todos:
            checkbox = "[x]" if todo.status == "complete" else "[]"
            lines.append(f"{checkbox} - {todo.content}")
        
        return "\n".join(lines)


# Global instance for backward compatibility
_todo_manager = TodoManager()


def get_todo_manager() -> TodoManager:
    """Get the global todo manager instance."""
    return _todo_manager