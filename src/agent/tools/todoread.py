from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import load_tool_description
from agent.utils.todo_manager import get_todo_manager


@register_tool("todo_read")
class TodoReadTool(BaseTool):
    description = load_tool_description("todoRead")
    parameters = []  # No parameters needed - input should be left blank

    def call(self, params: str, **kwargs) -> str:
        """Read and display current todos. Takes no parameters - input should be blank."""
        # Handle completely empty input as specified in todoread.txt
        if params and params.strip() not in {"", "{}", "[]", "null"}:
            return (
                "Error: This tool takes no parameters. Leave the input blank or empty."
            )

        todo_manager = get_todo_manager()
        todos = todo_manager.get_all_todos()

        # Return empty list if no todos exist
        if not todos:
            return "No todos currently exist."

        return todo_manager.format_todos()
