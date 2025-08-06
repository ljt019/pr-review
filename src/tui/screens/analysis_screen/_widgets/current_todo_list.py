"""Current todo list widget"""

from textual.app import ComposeResult
from textual.widgets import Label, Static


class CurrentTodoList(Static):
    """Current todo list"""

    def __init__(self, todo_list: list[str]):
        super().__init__("", classes="current-todo-list")
        self.todo_list = todo_list

    def compose(self) -> ComposeResult:
        yield Label(f"  └ ○ {self.todo_list[0]}", classes="tool-content")
        for todo in self.todo_list[1:]:
            yield Label(f"    ○ {todo}", classes="tool-content")