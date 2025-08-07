"""Agent read todo message widget"""

from textual.app import ComposeResult
from textual.widgets import Label, Static

from ..current_todo_list import CurrentTodoList


class AgentReadTodoMessage(Static):
    """Tool call made by the agent to *read* the current todo list"""

    def __init__(self, todos: list[dict]):
        """Accepts a list of todo dictionaries with structure:
        [{'content': str, 'status': str, 'id': str, ...}, ...]
        """
        super().__init__("", classes="agent-tool-message")
        self.todos = todos

    def compose(self) -> ComposeResult:
        yield Label("⚯ Todo Read", classes="tool-title")
        if self.todos:
            # Pass full todo objects to CurrentTodoList for proper rendering
            yield CurrentTodoList(self.todos)