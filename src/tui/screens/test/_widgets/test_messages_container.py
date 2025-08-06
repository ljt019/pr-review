"""Test messages container widget"""

from textual.app import ComposeResult
from textual.containers import VerticalScroll

from .center_screen import CenterWidget
from .messages.grep_tool_message import GrepToolMessage
from .messages.cat_tool_message import CatToolMessage
from .messages.ls_tool_message import LsToolMessage
from .messages.glob_tool_message import GlobToolMessage
from .messages.agent_write_todo_message import AgentWriteTodoMessage
from .messages.agent_read_todo_message import AgentReadTodoMessage
from .messages.bug_report_with_loading_message import BugReportWithLoadingMessage


class TestMessagesContainer(VerticalScroll):
    """Scrollable container for test messages that mimics analysis screen"""

    def __init__(self):
        super().__init__(id="test-messages-container", classes="scrollbar_styles")

    def compose(self) -> ComposeResult:
        """Compose the container with realistic message sequence"""
        todo_list = ["Analyze authentication mechanisms", "Check for SQL injection"]

        yield CenterWidget(GrepToolMessage({"pattern": "import.*requests"}))
        yield CenterWidget(CatToolMessage({"file": "src/network/client.py"}))
        yield CenterWidget(LsToolMessage({"path": "src/vulnerabilities/"}))
        yield CenterWidget(GlobToolMessage({"pattern": "**/*.py"}))
        yield CenterWidget(
            AgentWriteTodoMessage({"todo": "Analyze authentication mechanisms"})
        )
        yield CenterWidget(AgentReadTodoMessage(todo_list))
        yield CenterWidget(GrepToolMessage({"pattern": "password.*="}))
        yield CenterWidget(CatToolMessage({"file": "src/auth/login.py"}))
        
        example_bug_report = {
            "summary": "The codebase is Black, a popular Python code formatter. The code is well-structured and follows modern Python best practices with proper type hints, dataclasses, and dependency management. Security vulnerabilities are minimal as it's not a web application, with input validation handled appropriately. Code quality is generally excellent with only minor issues in function length and a few edge cases. Performance is efficient for its purpose, though there's a potential optimization in configuration parsing. Error handling is adequate but could be improved with more specific exception types and better edge case handling.",
            "bugs": [
                {
                    "title": "Inadequate error handling in format_file_in_place",
                    "description": "The format_file_in_place function catches NothingChanged exception but doesn't properly handle it, potentially leading to unexpected behavior when formatting code that hasn't changed.",
                    "file": "black.py",
                    "line": "672",
                    "severity": "major",
                    "category": "error-handling",
                    "recommendation": "Refactor the error handling to properly propagate NothingChanged exceptions or handle them with appropriate logging and status reporting.",
                },
                {
                    "title": "Generic exception handling in format_file_contents",
                    "description": "The format_file_contents function uses a broad try-except block that catches general Exception, which could mask important errors and make debugging difficult.",
                    "file": "black.py",
                    "line": "744",
                    "severity": "major",
                    "category": "error-handling",
                    "recommendation": "Replace the general Exception catch with more specific exception types to improve error visibility and debugging capabilities.",
                },
                {
                    "title": "Missing validation in format_stdin_to_stdout",
                    "description": "The format_stdin_to_stdout function doesn't validate the write_back parameter value, which could lead to unexpected behavior if an invalid value is passed.",
                    "file": "black.py",
                    "line": "720",
                    "severity": "major",
                    "category": "validation",
                    "recommendation": "Add validation for the write_back parameter to ensure it contains a valid value from the WriteBack enum before proceeding with formatting.",
                },
            ],
            "files_analyzed": 3,
        }
        yield CenterWidget(BugReportWithLoadingMessage(example_bug_report))