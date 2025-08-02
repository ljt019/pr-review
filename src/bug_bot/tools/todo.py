import uuid
from typing import Any, Dict, List

import json5
from qwen_agent.tools.base import BaseTool, register_tool

from bug_bot.tools import load_tool_description

# Shared storage for todos
_todos: List[Dict[str, Any]] = []


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
        print(f"[DEBUG] TodoWriteTool called with params: {params}")
        
        try:
            parsed_params = json5.loads(params)
            print(f"[DEBUG] Parsed params: {parsed_params}")
            
            todos_param = parsed_params.get("todos")
            print(f"[DEBUG] todos_param: {todos_param}")
            
            if not todos_param:
                print("[DEBUG] Error: todos parameter is required")
                return "Error: todos parameter is required"

            # Parse todos list
            if isinstance(todos_param, str):
                print(f"[DEBUG] todos_param is string, parsing: {todos_param}")
                try:
                    todos_list = json5.loads(todos_param)
                    print(f"[DEBUG] Parsed todos_list from string: {todos_list}")
                except Exception as e:
                    print(f"[DEBUG] Error parsing todos string: {e}")
                    return "Error: todos must be a valid JSON array"
            else:
                todos_list = todos_param
                print(f"[DEBUG] todos_param is not string: {todos_list}")

            if not isinstance(todos_list, list):
                print(f"[DEBUG] Error: todos_list is not a list, type: {type(todos_list)}")
                return "Error: todos must be an array"

            # Replace entire todo list
            _todos.clear()
            print(f"[DEBUG] Processing {len(todos_list)} todo items")

            for i, todo_item in enumerate(todos_list):
                print(f"[DEBUG] Processing todo item {i}: {todo_item}")
                
                # Handle both string format (for creating new todos) and object format (for updates)
                if isinstance(todo_item, str):
                    print(f"[DEBUG] Todo item {i} is string: {todo_item}")
                    # Simple string - create new incomplete todo
                    todo_id = f"todo_{uuid.uuid4().hex[:8]}"
                    new_todo = {
                        "id": todo_id,
                        "content": todo_item.strip(),
                        "status": "incomplete",
                    }
                    print(f"[DEBUG] Created new todo from string: {new_todo}")
                elif isinstance(todo_item, dict):
                    print(f"[DEBUG] Todo item {i} is dict: {todo_item}")
                    # Object format with content and status
                    content = todo_item.get("content")
                    status = todo_item.get("status", "incomplete")
                    todo_id = todo_item.get("id", f"todo_{uuid.uuid4().hex[:8]}")

                    if not content:
                        print(f"[DEBUG] Error: Todo item {i} missing content")
                        return "Error: Each todo object must have 'content'"
                    if status not in ["incomplete", "complete"]:
                        print(f"[DEBUG] Error: Todo item {i} invalid status: {status}")
                        return f"Error: Invalid status '{status}'. Must be 'incomplete' or 'complete'"

                    new_todo = {
                        "id": todo_id,
                        "content": content.strip(),
                        "status": status,
                    }
                    print(f"[DEBUG] Created new todo from dict: {new_todo}")
                else:
                    print(f"[DEBUG] Error: Todo item {i} invalid type: {type(todo_item)}")
                    return f"Error: Each todo must be a string or object, got {type(todo_item)}"

                _todos.append(new_todo)
                print(f"[DEBUG] Added todo to list, current count: {len(_todos)}")

            # Pretty print and return
            print(f"[DEBUG] Final todo list: {_todos}")
            self._pretty_print_todos()
            incomplete_count = len([t for t in _todos if t["status"] == "incomplete"])
            result = f"Updated todo list: {len(_todos)} total, {incomplete_count} incomplete"
            print(f"[DEBUG] Returning result: {result}")
            return result

        except Exception as e:
            print(f"[DEBUG] Exception in TodoWriteTool: {e}")
            import traceback
            traceback.print_exc()
            return f"Error: {str(e)}"

    def _pretty_print_todos(self):
        """Pretty print todos for debugging"""
        print(f"[DEBUG] Pretty printing {len(_todos)} todos:")
        for i, todo in enumerate(_todos):
            checkbox = "[x]" if todo["status"] == "complete" else "[ ]"
            print(f"[DEBUG]   {i}: {checkbox} {todo['content']} (id: {todo['id']})")


@register_tool("todo_read")
class TodoReadTool(BaseTool):
    description = load_tool_description("todoRead")
    parameters = []  # No parameters needed

    def call(self, params: str, **kwargs) -> str:
        """Read and display current todos"""
        lines = []
        for todo in _todos:
            checkbox = "[x]" if todo["status"] == "complete" else "[]"
            lines.append(f"{checkbox} - {todo['content']}")

        result = "\n".join(lines) if lines else "No todos"

        return result
