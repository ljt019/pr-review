import json5
import uuid
from datetime import datetime
from typing import List, Dict, Any
from qwen_agent.tools.base import BaseTool, register_tool


@register_tool('task_manager')
class TaskManagerTool(BaseTool):
    description = 'Manage todo items during task execution'
    parameters = [
        {
            'name': 'action',
            'type': 'string',
            'description': 'Action to perform: add, add_multiple, update, complete, list, remove',
            'required': True
        },
        {
            'name': 'content',
            'type': 'string',
            'description': 'Content for new todos or updates',
            'required': False
        },
        {
            'name': 'todo_id',
            'type': 'string',
            'description': 'ID of existing todo for updates/completion',
            'required': False
        },
        {
            'name': 'status',
            'type': 'string',
            'description': 'Status: incomplete, complete',
            'required': False
        },
        {
            'name': 'priority',
            'type': 'string',
            'description': 'Priority: high, low',
            'required': False
        },
        {
            'name': 'todos',
            'type': 'string',
            'description': 'For add_multiple: JSON array like [{"content": "task 1"}, {"content": "task 2"}]',
            'required': False
        }
    ]

    # Class-level storage for todos (shared across instances)
    _todos: List[Dict[str, Any]] = []

    def call(self, params: str, **kwargs) -> str:
        try:
            parsed_params = json5.loads(params)
            action = parsed_params.get('action')
            if not action:
                return "Error: action parameter is required"
            
            # Execute the action first
            if action == 'add':
                result = self._add_todo(parsed_params)
            elif action == 'add_multiple':
                result = self._add_multiple_todos(parsed_params)
            elif action == 'update':
                result = self._update_todo(parsed_params)
            elif action == 'complete':
                result = self._complete_todo(parsed_params)
            elif action == 'list':
                result = self._list_todos()
            elif action == 'remove':
                result = self._remove_todo(parsed_params)
            else:
                return f"Error: Invalid action '{action}'. Must be: add, add_multiple, update, complete, list, remove"

            # Only pretty print if the action succeeded (no "Error:" in result)
            if not result.startswith("Error:"):
                self._pretty_print_after_action(action)
            return result
            
        except Exception as e:
            return f"Error: {str(e)}"

    def _add_todo(self, params: Dict[str, Any]) -> str:
        """Add a new todo item."""
        content = params.get('content')
        if not content:
            return "Error: content is required when adding a todo"
        
        priority = params.get('priority', 'high')
        if priority not in ['high', 'low']:
            return f"Error: Invalid priority '{priority}'. Must be high or low"
        
        # Generate simple ID
        todo_id = f"todo_{uuid.uuid4().hex[:8]}"
        
        new_todo = {
            'id': todo_id,
            'content': content,
            'status': 'incomplete',
            'priority': priority
        }
        
        self._todos.append(new_todo)
        return f"Added todo {todo_id}: {content} (priority: {priority})"

    def _add_multiple_todos(self, params: Dict[str, Any]) -> str:
        """Add multiple todo items at once."""
        todos_param = params.get('todos')
        if not todos_param:
            return "Error: todos parameter is required for add_multiple"
        
        try:
            todos_list = json5.loads(todos_param) if isinstance(todos_param, str) else todos_param
        except:
            return "Error: todos parameter must be valid JSON list"
        
        if not isinstance(todos_list, list):
            return "Error: todos must be a list"
        
        added_ids = []
        default_priority = params.get('priority', 'high')
        
        for todo_data in todos_list:
            if not isinstance(todo_data, dict) or 'content' not in todo_data:
                return "Error: Each todo must be a dict with 'content' field"
            
            content = todo_data['content']
            priority = todo_data.get('priority', default_priority)
            
            if priority not in ['high', 'low']:
                return f"Error: Invalid priority '{priority}'"
            
            todo_id = f"todo_{uuid.uuid4().hex[:8]}"
            
            new_todo = {
                'id': todo_id,
                'content': content,
                'status': 'incomplete',
                'priority': priority
            }
            
            self._todos.append(new_todo)
            added_ids.append(todo_id)
        
        return f"Added {len(added_ids)} todos (IDs: {', '.join(added_ids)})"

    def _update_todo(self, params: Dict[str, Any]) -> str:
        """Update an existing todo item."""
        todo_id = params.get('todo_id')
        if not todo_id:
            return "Error: todo_id is required for updates"
        
        # Find the todo
        todo = None
        for t in self._todos:
            if t['id'] == todo_id:
                todo = t
                break
        
        if not todo:
            return f"Error: Todo with ID '{todo_id}' not found"
        
        changes = []
        
        # Update status
        status = params.get('status')
        if status:
            if status not in ['incomplete', 'complete']:
                return f"Error: Invalid status '{status}'"
            todo['status'] = status
            changes.append(f"status to {status}")
        
        # Update priority
        priority = params.get('priority')
        if priority:
            if priority not in ['high', 'low']:
                return f"Error: Invalid priority '{priority}'"
            todo['priority'] = priority
            changes.append(f"priority to {priority}")
        
        # Update content
        content = params.get('content')
        if content:
            todo['content'] = content
            changes.append(f"content to '{content}'")
        
        if not changes:
            return "Error: At least one of status, priority, or content must be provided"
        
        change_summary = ", ".join(changes)
        return f"Updated todo {todo_id}: {change_summary}"

    def _complete_todo(self, params: Dict[str, Any]) -> str:
        """Mark a todo as completed."""
        todo_id = params.get('todo_id')
        if not todo_id:
            return "Error: todo_id is required to mark as complete"
        
        for todo in self._todos:
            if todo['id'] == todo_id:
                todo['status'] = 'complete'
                return f"Marked todo {todo_id} as complete: {todo['content']}"
        
        return f"Error: Todo with ID '{todo_id}' not found"

    def _list_todos(self) -> str:
        """List all current todos in pretty format."""
        if not self._todos:
            return "No todos"
        
        lines = []
        for todo in self._todos:
            checkbox = "[x]" if todo['status'] == 'complete' else "[]"
            lines.append(f"{checkbox} - {todo['content']}")
        
        return "\n".join(lines)

    def _remove_todo(self, params: Dict[str, Any]) -> str:
        """Remove a todo item."""
        todo_id = params.get('todo_id')
        if not todo_id:
            return "Error: todo_id is required to remove a todo"
        
        for i, todo in enumerate(self._todos):
            if todo['id'] == todo_id:
                content = todo['content']
                self._todos.pop(i)
                return f"Removed todo {todo_id}: {content}"
        
        return f"Error: Todo with ID '{todo_id}' not found"
    
    def _pretty_print_after_action(self, action: str):
        """Pretty print after action is completed with fresh state."""
        current_list = self._list_todos()
        
        # Format the todo list with proper indentation
        if current_list == "No todos":
            formatted_todos = "  - todos:\n       No todos"
        else:
            # Split the list and add proper indentation
            todo_lines = current_list.split('\n')
            formatted_lines = ["  - todos:"]
            for line in todo_lines:
                formatted_lines.append(f"  - {line}")
            formatted_todos = '\n'.join(formatted_lines)

        match action:
            case 'add':
                print(f"🛠️ Add Todo")
                print(f"{formatted_todos}\n")
            case 'add_multiple':
                print(f"🛠️ Add Multiple Todos")
                print(f"{formatted_todos}\n")
            case 'update':
                print(f"🛠️ Update Todo")
                print(f"{formatted_todos}\n")
            case 'complete':
                print(f"🛠️ Complete Todo")
                print(f"{formatted_todos}\n")
            case 'list':
                print(f"🛠️ List Todos")
                print(f"{formatted_todos}\n")
            case 'remove':
                print(f"🛠️ Remove Todo")
                print(f"{formatted_todos}\n")

    def _pretty_print_tool(self, action: str):
        current_list = self._list_todos()
        
        # Format the todo list with proper indentation
        if current_list == "No todos":
            formatted_todos = "  - todos:\n       No todos"
        else:
            # Split the list and add proper indentation
            todo_lines = current_list.split('\n')
            formatted_lines = ["  - todos:"]
            for line in todo_lines:
                formatted_lines.append(f"  - {line}")
            formatted_todos = '\n'.join(formatted_lines)

        match action:
            case 'add':
                print(f"🛠️ Add Todo")
                print(f"{formatted_todos}\n")
            case 'add_multiple':
                print(f"🛠️ Add Multiple Todos")
                print(f"{formatted_todos}\n")
            case 'update':
                print(f"🛠️ Update Todo")
                print(f"{formatted_todos}\n")
            case 'complete':
                print(f"🛠️ Complete Todo")
                print(f"{formatted_todos}\n")
            case 'list':
                print(f"🛠️ List Todos")
                print(f"{formatted_todos}\n")
            case 'remove':
                print(f"🛠️ Remove Todo")
                print(f"{formatted_todos}\n")

"""    
Wrong Way

🛠️ Add Multiple Todos
  - todos: [] - List root directory structure
[] - Read key configuration files (README.md, pyproject.toml, requirements.txt)
[] - Identify all source code directories
[] - Read all source code files
[] - Search for security vulnerabilities and code smells
[] - Generate comprehensive review report

🛠️ Add Multiple Todos
No todos

Correct Way

🛠️ Add Multiple Todos
  - todos: 
  - [] List root directory structure
  - []Read key configuration files (README.md, pyproject.toml, requirements.txt)
  - [] Identify all source code directories
  - [] Read all source code files
  - [] Search for security vulnerabilities and code smells
  - [] Generate comprehensive review report

🛠️ Add Multiple Todos
  - todos:
       No todos
"""