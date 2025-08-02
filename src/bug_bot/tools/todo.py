import uuid
from dataclasses import dataclass
from typing import Any, Dict, List

import json5
from qwen_agent.tools.base import BaseTool, register_tool

from bug_bot.tools import load_tool_description


@dataclass
class TodoItem:
    """Simple representation of a todo entry."""

    id: str
    content: str
    status: str  # "complete" or "incomplete"

    def __post_init__(self) -> None:
        if self.status not in {"complete", "incomplete"}:
            raise ValueError("Invalid status. Must be 'complete' or 'incomplete'")


# Shared storage for todos
_todos: List[TodoItem] = []


@register_tool("todo_write")
class TodoWriteTool(BaseTool):
    description = load_tool_description("todoWrite")
    parameters = [
        {
            "name": "todos",
            "type": "string",
            "description": 'JSON array of todo objects with content and status, e.g. [{"content": "task 1", "status": "incomplete"}, {"content": "task 2", "status": "complete"}]',
            "required": True,
        }
    ]

    def call(self, params: str, **kwargs) -> str:
        global _todos
        try:
            parsed_params = json5.loads(params)
            todos_param = parsed_params.get("todos")
            if not todos_param:
                return "Error: todos parameter is required"

            # Parse todos list
            if isinstance(todos_param, str):
                try:
                    todos_list = json5.loads(todos_param)
                except Exception:
                    return "Error: todos must be a valid JSON array"
            else:
                todos_list = todos_param

            if not isinstance(todos_list, list):
                return "Error: todos must be an array"

            _todos.clear()
            for todo_item in todos_list:
                if isinstance(todo_item, str):
                    todo = TodoItem(
                        id=f"todo_{uuid.uuid4().hex[:8]}",
                        content=todo_item.strip(),
                        status="incomplete",
                    )
                elif isinstance(todo_item, dict):
                    content = todo_item.get("content")
                    status = todo_item.get("status", "incomplete")
                    todo_id = todo_item.get("id", f"todo_{uuid.uuid4().hex[:8]}")
                    if not content:
                        return "Error: Each todo object must have 'content'"
                    try:
                        todo = TodoItem(id=todo_id, content=content.strip(), status=status)
                    except ValueError as e:
                        return f"Error: {e}"
                else:
                    return f"Error: Each todo must be a string or object, got {type(todo_item)}"

                _todos.append(todo)

            incomplete_count = len([t for t in _todos if t.status == "incomplete"])
            return f"Updated todo list: {len(_todos)} total, {incomplete_count} incomplete"

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error: {str(e)}"

    def _pretty_print_todos(self):
        """Pretty print todos for debugging"""
        print(f"[DEBUG] Pretty printing {len(_todos)} todos:")
        for i, todo in enumerate(_todos):
            checkbox = "[x]" if todo.status == "complete" else "[ ]"
            print(f"[DEBUG]   {i}: {checkbox} {todo.content} (id: {todo.id})")


@register_tool("todo_read")
class TodoReadTool(BaseTool):
    description = load_tool_description("todoRead")
    parameters = []  # No parameters needed

    def call(self, params: str, **kwargs) -> str:
        """Read and display current todos"""
        lines = []
        for todo in _todos:
            checkbox = "[x]" if todo.status == "complete" else "[]"
            lines.append(f"{checkbox} - {todo.content}")

        result = "\n".join(lines) if lines else "No todos"

        return result
