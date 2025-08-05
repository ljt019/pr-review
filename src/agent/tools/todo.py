from pydantic_ai.tools import Tool

from agent.tools import load_tool_description
from agent.utils.todo_manager import get_todo_manager


def todo_write(todos: str) -> str:
    """Write or update todos from a JSON array.

    Args:
        todos: JSON array of todo objects with content and status
    """
    try:
        if isinstance(todos, str):
            try:
                import json5
                todos_list = json5.loads(todos)
            except Exception:
                return "Error: todos must be a valid JSON array"
        else:
            todos_list = todos
        if not isinstance(todos_list, list):
            return "Error: todos must be an array"
        todo_manager = get_todo_manager()
        todo_manager.update_from_list(todos_list)
        summary = todo_manager.get_summary()
        return f"Updated todo list: {summary}"
    except Exception as e:
        return f"Error: {str(e)}"


def todo_read() -> str:
    """Read and display current todos."""
    todo_manager = get_todo_manager()
    return todo_manager.format_todos()


todo_write_tool = Tool(todo_write, name="todo_write", description=load_tool_description("todoWrite"))
todo_read_tool = Tool(todo_read, name="todo_read", description=load_tool_description("todoRead"))
