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
        yield CenterWidget(CatToolMessage({"file": "src/tasks/cleanup.py"}))
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
from textual.containers import Horizontal, Vertical  # noqa
from textual.widgets import Markdown  # noqa


class CatToolMessage(Static):
    """Tool call made by the agent to *cat* files using Markdown code fencing"""

    file_content: str = """import os
import shutil
import time

def cleanup_tmp():
    # Bug: Deletes entire /tmp subdirs without filtering (security/resource_management)
    base = "/tmp"
    for name in os.listdir(base):
        path = os.path.join(base, name)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except Exception:
            # Bug: Swallowing exceptions hides failures (error_handling)
            pass

def rotate_logs():
    # Bug: Inefficient rotation copies entire file repeatedly (performance)
    log = "/tmp/app.log"
    if not os.path.exists(log):
        return
    ts = int(time.time())
    shutil.copy(log, f"/tmp/app.{ts}.log")"""

    def __init__(self, tool_args: dict):
        super().__init__("", classes="agent-tool-message")
        self.tool_args = tool_args

    def compose(self) -> ComposeResult:
        # Get file extension for syntax highlighting
        file_path = self.tool_args.get("file", "")
        file_ext = file_path.split(".")[-1] if "." in file_path else "text"

        # Add line numbers to the content and truncate long lines
        lines = self.file_content.split("\n")
        line_count = len(lines)
        line_num_width = len(str(line_count))
        max_line_width = 80  # Maximum width for code lines

        numbered_lines = []
        for i, line in enumerate(lines, 1):
            line_num = str(i).rjust(line_num_width)

            # Truncate line if too long to prevent horizontal scrolling
            available_width = (
                max_line_width - line_num_width - 3
            )  # Account for line number and separator
            if len(line) > available_width and available_width > 0:
                truncated_line = line[: available_width - 3] + "..."
            else:
                truncated_line = line

            numbered_lines.append(f"{line_num}  {truncated_line}")

        numbered_content = "\n".join(numbered_lines)

        # Create markdown with code fence for syntax highlighting
        markdown_content = f"```{file_ext}\n{numbered_content}\n```"

        # Create the markdown widget with Catppuccin theme
        markdown_widget = Markdown(markdown_content, classes="code-markdown")
        markdown_widget.code_dark_theme = (
            "catppuccin-mocha"  # Set Catppuccin Mocha theme
        )

        yield Vertical(
            Horizontal(
                Label("⚯ Cat", classes="tool-title"),
                Label(
                    f" {self.tool_args.get('file', 'unknown')}", classes="tool-content"
                ),
                classes="tool-horizontal",
            ),
            markdown_widget,
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
