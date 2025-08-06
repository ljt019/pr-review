"""Agent write todo message widget"""

from textual.app import ComposeResult
from textual.widgets import Label, Static

from ..current_todo_list import CurrentTodoList


class AgentWriteTodoMessage(Static):
    """Tool call made by the agent to *write* todos"""

    def __init__(self, tool_args: dict):
        """Accepts a dict that may contain either:
        • "todo": a single todo string the agent just wrote, OR
        • "todo_list": the full list of todos after the write.
        Both keys are optional so the widget can be reused flexibly.
        """
        super().__init__("", classes="agent-tool-message")
        self.single_todo: str | None = tool_args.get("todo")
        self.todo_list: list[str] | None = tool_args.get("todo_list")

    def compose(self) -> ComposeResult:
        yield Label("✎ Todo Write", classes="tool-title")
        if self.todo_list is not None:
            todos: list[str] = self.todo_list
        elif self.single_todo is not None:
            todos = [self.single_todo]
        else:
            todos = []
        if todos:
            yield CurrentTodoList(todos)