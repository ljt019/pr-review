"""Test screen for experimenting with widgets"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Label

from ._widgets.center_screen import CenterWidget


class TestScreen(Screen):
    """Test screen for widget experimentation"""

    BINDINGS = [
        Binding("escape", "back", "Back", priority=True),
    ]

    todo_list: list[str] = ["Analyze the codebase", "Write the code"]

    def compose(self) -> ComposeResult:
        """Compose the test screen with centered widget"""
        # Create sample message string
        sample_message = "Time to start my analysis"

        yield CenterWidget(AgentMessage(sample_message))
        yield CenterWidget(AgentWriteTodoMessage({"todo": "Analyze the codebase"}))
        yield CenterWidget(AgentReadTodoMessage(self.todo_list))
        yield CenterWidget(GrepToolMessage({"pattern": "*.py"}))
        yield CenterWidget(GlobToolMessage({"pattern": "src/**/*.py"}))
        yield CenterWidget(CatToolMessage({"file": "src/tui/screens/test_screen.py"}))
        yield CenterWidget(LsToolMessage({"pattern": "src/**/*.py"}))

    def action_back(self) -> None:
        """Go back to previous screen"""
        self.app.pop_screen()


############ In-Progress Widget 1 ############

from textual.widgets import Static  # noqa


class AgentMessage(Static):
    """Message from the agent"""

    def __init__(self, message: str):
        super().__init__(message, classes="agent-message")


############################################

############ In-Progress Widget 2 ############

from textual.widgets import Static  # noqa


class AgentWriteTodoMessage(Static):
    """Tool call made by the agent to *write* todos"""

    def __init__(self, tool_args: dict):
        """Accepts a dict that may contain either:
        • "todo": a single todo string the agent just wrote, OR
        • "todo_list": the full list of todos after the write.
        Both keys are optional so the widget can be reused flexibly.
        """
        super().__init__("", classes="agent-tool-message")
        # Extract optional fields with graceful fall-backs
        self.single_todo: str | None = tool_args.get("todo")
        self.todo_list: list[str] | None = tool_args.get("todo_list")

    def compose(self) -> ComposeResult:
        yield Label("✎ Todo Write", classes="tool-title")
        # Always display via CurrentTodoList. If we only have one todo, wrap it
        # in a list so that the downstream widget sees a uniform structure.
        if self.todo_list is not None:
            todos: list[str] = self.todo_list
        elif self.single_todo is not None:
            todos = [self.single_todo]
        else:
            todos = []
        if todos:
            yield CurrentTodoList(todos)


############################################

############ In-Progress Widget 3 ############

from textual.widgets import Static  # noqa


class AgentReadTodoMessage(Static):
    """Tool call made by the agent to *read* the current todo list"""

    def __init__(self, todo_list: list[str]):
        super().__init__("", classes="agent-tool-message")
        self.todo_list = todo_list

    def compose(self) -> ComposeResult:
        yield Label("⚯ Todo Read", classes="tool-title")
        yield CurrentTodoList(self.todo_list)


############################################


############ In-Progress Widget 4 ############

from textual.widgets import Static  # noqa


class CurrentTodoList(Static):
    """Current todo list"""

    def __init__(self, todo_list: list[str]):
        super().__init__("", classes="current-todo-list")
        self.todo_list = todo_list

    def compose(self) -> ComposeResult:
        yield Label(f"  └ ○ {self.todo_list[0]}", classes="tool-content")
        for todo in self.todo_list[1:]:
            yield Label(f"    ○ {todo}", classes="tool-content")


############################################


############ In-Progress Widget 5 ############

from textual.widgets import Static  # noqa
from textual.containers import Horizontal  # noqa


class GrepToolMessage(Static):
    """Tool call made by the agent to *grep* files / patterns"""

    def __init__(self, tool_args: dict):
        super().__init__("", classes="agent-tool-message")
        self.tool_args = tool_args

    def compose(self) -> ComposeResult:
        # Build a horizontal container
        yield Horizontal(
            Label("⌕ Grep", classes="tool-title"),
            Label(f" {self.tool_args['pattern']}", classes="tool-content"),
            classes="tool-horizontal",
        )


############################################


############ In-Progress Widget 6 ############

from textual.widgets import Static  # noqa
from textual.containers import Horizontal  # noqa


class GlobToolMessage(Static):
    """Tool call made by the agent to *glob* files / patterns"""

    def __init__(self, tool_args: dict):
        super().__init__("", classes="agent-tool-message")
        self.tool_args = tool_args

    def compose(self) -> ComposeResult:
        # Build a horizontal container
        yield Horizontal(
            Label("⌕ Glob", classes="tool-title"),
            Label(f" {self.tool_args['pattern']}", classes="tool-content"),
            classes="tool-horizontal",
        )


############################################

############ In-Progress Widget 7 ############

from textual.widgets import Static  # noqa
from textual.containers import Horizontal  # noqa


class CatToolMessage(Static):
    """Tool call made by the agent to *cat* files"""

    def __init__(self, tool_args: dict):
        super().__init__("", classes="agent-tool-message")
        self.tool_args = tool_args

    def compose(self) -> ComposeResult:
        # Build a horizontal container
        yield Horizontal(
            Label("⚯ Cat", classes="tool-title"),
            Label(f" {self.tool_args['file']}", classes="tool-content"),
            classes="tool-horizontal",
        )


############################################


############ In-Progress Widget 8 ############

from textual.widgets import Static  # noqa
from textual.containers import Horizontal  # noqa


class LsToolMessage(Static):
    """Tool call made by the agent to *ls* files"""

    def __init__(self, tool_args: dict):
        super().__init__("", classes="agent-tool-message")
        self.tool_args = tool_args

    def compose(self) -> ComposeResult:
        # Build a horizontal container
        yield Horizontal(
            Label("☰ Ls", classes="tool-title"),
            Label(f" {self.tool_args['pattern']}", classes="tool-content"),
            classes="tool-horizontal",
        )


############################################
