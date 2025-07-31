import json5
import uuid
from typing import List, Dict, Any
from qwen_agent.tools.base import BaseTool, register_tool
from bug_bot.tools import load_tool_description

# Shared storage for todos
_todos: List[Dict[str, Any]] = []

@register_tool('todo_write')
class TodoWriteTool(BaseTool):
    description = load_tool_description('todoWrite')
    parameters = [
        {
            'name': 'todos',
            'type': 'string',
            'description': 'JSON array of todo objects with content and status, e.g. [{"content": "task 1", "status": "incomplete"}, {"content": "task 2", "status": "complete"}]',
            'required': True
        }
    ]

    def call(self, params: str, **kwargs) -> str:
        global _todos
        try:
            parsed_params = json5.loads(params)
            todos_param = parsed_params.get('todos')
            if not todos_param:
                return "Error: todos parameter is required"
            
            # Parse todos list
            if isinstance(todos_param, str):
                try:
                    todos_list = json5.loads(todos_param)
                except:
                    return "Error: todos must be a valid JSON array"
            else:
                todos_list = todos_param
            
            if not isinstance(todos_list, list):
                return "Error: todos must be an array"
            
            # Replace entire todo list
            _todos.clear()
            
            for todo_item in todos_list:
                # Handle both string format (for creating new todos) and object format (for updates)
                if isinstance(todo_item, str):
                    # Simple string - create new incomplete todo
                    todo_id = f"todo_{uuid.uuid4().hex[:8]}"
                    new_todo = {
                        'id': todo_id,
                        'content': todo_item.strip(),
                        'status': 'incomplete'
                    }
                elif isinstance(todo_item, dict):
                    # Object format with content and status
                    content = todo_item.get('content')
                    status = todo_item.get('status', 'incomplete')
                    todo_id = todo_item.get('id', f"todo_{uuid.uuid4().hex[:8]}")
                    
                    if not content:
                        return "Error: Each todo object must have 'content'"
                    if status not in ['incomplete', 'complete']:
                        return f"Error: Invalid status '{status}'. Must be 'incomplete' or 'complete'"
                    
                    new_todo = {
                        'id': todo_id,
                        'content': content.strip(),
                        'status': status
                    }
                else:
                    return f"Error: Each todo must be a string or object, got {type(todo_item)}"
                
                _todos.append(new_todo)
            
            # Pretty print and return
            self._pretty_print_todos()
            incomplete_count = len([t for t in _todos if t['status'] == 'incomplete'])
            return f"Updated todo list: {len(_todos)} total, {incomplete_count} incomplete"
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _pretty_print_todos(self):
        """Pretty print the todo list"""
        lines = []
        for todo in _todos:
            checkbox = "[x]" if todo['status'] == 'complete' else "[]"
            lines.append(f"{checkbox} - {todo['content']}")
        
        formatted_todos = "\n".join([f"  - {line}" for line in lines]) if lines else "       No todos"
        
        print(f"🛠️ Todo Write")
        print(f"  - todos:")
        print(f"{formatted_todos}\n")

@register_tool('todo_read')
class TodoReadTool(BaseTool):
    description = load_tool_description('todoRead')
    parameters = []  # No parameters needed
    
    def call(self, params: str, **kwargs) -> str:
        """Read and display current todos"""
        lines = []
        for todo in _todos:
            checkbox = "[x]" if todo['status'] == 'complete' else "[]"
            lines.append(f"{checkbox} - {todo['content']}")
        
        result = "\n".join(lines) if lines else "No todos"
        
        # Pretty print
        formatted_todos = "\n".join([f"  - {line}" for line in lines]) if lines else "       No todos"
        print(f"🛠️ Todo Read")
        print(f"  - todos:")
        print(f"{formatted_todos}\n")
        
        return result

