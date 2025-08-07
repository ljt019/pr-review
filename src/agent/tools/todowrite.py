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
            "description": 'JSON array for todo management. For initial creation: ["task 1", "task 2"]. For updates: [{"content": "task 1", "status": "completed"}, {"content": "task 2", "status": "in_progress", "cancelled": false}, {"content": "task 3", "status": "pending", "cancelled": true}]. Status options: "pending", "in_progress", "completed". Set "cancelled": true to cancel a todo (keeps status but adds strikethrough).',
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
            
            # Return summary + formatted todo list for UI display
            result = f"Updated todo list: {summary}\n"
            
            # Add formatted todo items
            todos = todo_manager.get_all_todos()
            for todo in todos:
                # Determine status symbol
                if todo.status == "completed":
                    status_marker = "[x]"  # completed
                elif todo.status == "in_progress":
                    status_marker = "[>]"  # in progress
                else:  # pending
                    status_marker = "[]"   # pending
                
                # Apply strikethrough if cancelled
                if todo.cancelled:
                    result += f"{status_marker} - ~~{todo.content}~~\n"
                else:
                    result += f"{status_marker} - {todo.content}\n"
            
            return result.rstrip()

        except Exception as e:
            return f"Error: {str(e)}"

    def _pretty_print_todos(self):
        """Pretty print todos for debugging"""
        todo_manager = get_todo_manager()
        todos = todo_manager.get_all_todos()
        # Debug prints removed
        pass