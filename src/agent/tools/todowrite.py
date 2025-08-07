import json

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
            formatted_todos = todo_manager.format_todos()
            # Emit machine-readable JSON after the text block for UI consumption
            todos_json = [
                {
                    "id": t.id,
                    "content": t.content,
                    "status": t.status,
                    "cancelled": t.cancelled,
                }
                for t in todo_manager.get_all_todos()
            ]
            return (
                f"Updated todo list: {summary}\n{formatted_todos}\n\n"
                f"<!--JSON-->{json.dumps({'todos': todos_json})}<!--/JSON-->"
            )

        except Exception as e:
            return f"Error: {str(e)}"
