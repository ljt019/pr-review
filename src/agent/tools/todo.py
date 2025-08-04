from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import load_tool_description
from agent.utils.param_parser import ParameterParser
from agent.utils.todo_manager import get_todo_manager


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
        try:
            parsed_params = ParameterParser.parse_params(params)
            todos_param = ParameterParser.get_required_param(parsed_params, "todos")

            # Parse todos list
            if isinstance(todos_param, str):
                try:
                    import json5
                    todos_list = json5.loads(todos_param)
                except Exception:
                    return "Error: todos must be a valid JSON array"
            else:
                todos_list = todos_param

            if not isinstance(todos_list, list):
                return "Error: todos must be an array"

            todo_manager = get_todo_manager()
            todo_manager.update_from_list(todos_list)

            summary = todo_manager.get_summary()
            return f"Updated todo list: {summary}"

        except Exception as e:
            return f"Error: {str(e)}"

    def _pretty_print_todos(self):
        """Pretty print todos for debugging"""
        todo_manager = get_todo_manager()
        todos = todo_manager.get_all_todos()
        # Debug prints removed
        pass


@register_tool("todo_read")
class TodoReadTool(BaseTool):
    description = load_tool_description("todoRead")
    parameters = []  # No parameters needed

    def call(self, params: str, **kwargs) -> str:
        """Read and display current todos"""
        todo_manager = get_todo_manager()
        return todo_manager.format_todos()
