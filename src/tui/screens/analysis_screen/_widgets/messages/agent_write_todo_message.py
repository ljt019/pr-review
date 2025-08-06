"""Agent write todo message widget"""

from textual.app import ComposeResult
from textual.widgets import Label, Static

from ..current_todo_list import CurrentTodoList


class AgentWriteTodoMessage(Static):
    """Tool call made by the agent to *write* todos"""

    def __init__(self, todos: list[dict]):
        """Accepts a list of todo dictionaries with structure:
        [{'content': str, 'status': str, 'id': str, ...}, ...]
        """
        super().__init__("", classes="agent-tool-message")
        self.todos = todos

    def compose(self) -> ComposeResult:
        yield Label("✎ Todo Write", classes="tool-title")
        if self.todos:
            # Convert todo dict structure to simple strings for display
            todo_strings = [todo.get('content', 'No content') for todo in self.todos]
            yield CurrentTodoList(todo_strings)