"""Agent read todo message widget"""

from textual.app import ComposeResult
from textual.widgets import Label, Static

from ..current_todo_list import CurrentTodoList


class AgentReadTodoMessage(Static):
    """Tool call made by the agent to *read* the current todo list"""

    def __init__(self, todo_list: list[str]):
        super().__init__("", classes="agent-tool-message")
        self.todo_list = todo_list

    def compose(self) -> ComposeResult:
        yield Label("⚯ Todo Read", classes="tool-title")
        yield CurrentTodoList(self.todo_list)