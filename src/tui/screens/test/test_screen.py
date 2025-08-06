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
        """Compose the test screen with realistic chat-style scrollable interface"""
        from textual.containers import Center, Container
        from textual.widgets import Static

        # Create layout like analysis screen
        yield Container(
            Static("qwen/qwen3-480b-a35b-coder", classes="header"),
            Center(TestMessagesContainer(), classes="messages-center"),
            classes="main-container",
        )

    def action_back(self) -> None:
        """Go back to previous screen"""
        self.app.pop_screen()


############ Test Messages Container ############

from textual.containers import VerticalScroll  # noqa


class TestMessagesContainer(VerticalScroll):
    """Scrollable container for test messages that mimics analysis screen"""

    def __init__(self):
        super().__init__(id="test-messages-container", classes="scrollbar_styles")

    def compose(self) -> ComposeResult:
        """Compose the container with realistic message sequence"""
        # Access the TestScreen's todo_list through the screen
        todo_list = ["Analyze authentication mechanisms", "Check for SQL injection"]

        # Start with simple test
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
        # Add combined bug report widget with loading state
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
    """Tool call made by the agent to *grep* files / patterns with polished search results"""

    # Example grep output for styling
    example_matches = [
        ("src/agent/agent.py", 15, "def run_analysis(self):"),
        ("src/agent/agent.py", 28, "    analysis_results = []"),
        (
            "src/tui/services/message_renderer.py",
            45,
            "def render_analysis_message(self):",
        ),
        ("src/tui/services/message_renderer.py", 67, "    self.analysis_count += 1"),
        ("README.md", 12, "## Analysis Features"),
        ("README.md", 34, "Run analysis with: `sniff analyze`"),
        ("pyproject.toml", 8, 'name = "analysis-tool"'),
        ("src/utils/helpers.py", 23, "def analyze_code_quality():"),
    ]

    def __init__(self, tool_args: dict, search_results=None):
        super().__init__("", classes="agent-tool-message")
        self.tool_args = tool_args
        self.search_results = search_results or self.example_matches

    def compose(self) -> ComposeResult:
        pattern = self.tool_args.get("pattern", "")
        match_count = len(self.search_results)

        # Group results by file for better organization
        files_dict = {}
        for file_path, line_num, content in self.search_results:
            if file_path not in files_dict:
                files_dict[file_path] = []
            files_dict[file_path].append((line_num, content.strip()))

        # Build markdown content
        md_lines = [
            f"\n**{match_count} matches** found across **{len(files_dict)} files**",
            f"",
        ]

        # Add results as a structured markdown list
        for file_path, matches in files_dict.items():
            # File as top-level list item
            md_lines.append(f"- **{file_path}**")
            for line_num, content in matches:
                md_lines.append(f"  - Line **{line_num}**: `{content}`")
            md_lines.append("")  # Space between files

        markdown_content = "\n".join(md_lines)

        # Create the markdown widget with custom bullets
        markdown_widget = Markdown(markdown_content, classes="search-markdown")
        markdown_widget.code_dark_theme = "catppuccin-mocha"
        # Override bullet symbols to use file icon for top level
        markdown_widget.BULLETS = ["🖹 ", "• ", "‣ ", "⭑ ", "⭑ "]

        yield Vertical(
            Horizontal(
                Label("⌕ Grep", classes="tool-title"),
                Label(f' "{pattern}"', classes="tool-content"),
                classes="tool-horizontal",
            ),
            markdown_widget,
        )


############################################


############ In-Progress Widget 6 ############

from textual.widgets import Static  # noqa
from textual.containers import Horizontal  # noqa


class GlobToolMessage(Static):
    """Tool call made by the agent to *glob* files / patterns with polished file matches display"""

    # Example glob output for styling
    example_files = [
        "src/agent/__init__.py",
        "src/agent/agent.py",
        "src/agent/messages.py",
        "src/tui/__init__.py",
        "src/tui/services/__init__.py",
        "src/tui/services/agent_service.py",
        "src/tui/services/message_renderer.py",
        "src/tui/screens/analysis_screen/analysis_screen.py",
        "src/tui/screens/api_key/api_key_screen.py",
        "src/tui/screens/model_select/model_select_screen.py",
        "src/tui/widgets/ascii_art.py",
        "src/tui/widgets/instruction_text.py",
    ]

    def __init__(self, tool_args: dict, matched_files=None):
        super().__init__("", classes="agent-tool-message")
        self.tool_args = tool_args
        self.matched_files = matched_files or self.example_files

    def compose(self) -> ComposeResult:
        pattern = self.tool_args.get("pattern", "")
        file_count = len(self.matched_files)

        # Build markdown content
        md_lines = [
            f"**{file_count} files** matched pattern",
            "",
        ]

        # Add files as a markdown list
        for file_path in self.matched_files:
            md_lines.append(f"- **{file_path}**")

        if not self.matched_files:
            md_lines = ["**No files matched** the pattern"]

        markdown_content = "\n".join(md_lines)

        # Create the markdown widget with custom file icon bullets
        markdown_widget = Markdown(markdown_content, classes="search-markdown")
        markdown_widget.code_dark_theme = "catppuccin-mocha"
        # Use file icon for all matched files
        markdown_widget.BULLETS = ["🖹 ", "🖹 ", "🖹 ", "🖹 ", "🖹 "]

        yield Vertical(
            Horizontal(
                Label("⌕ Glob", classes="tool-title"),
                Label(f' "{pattern}"', classes="tool-content"),
                classes="tool-horizontal",
            ),
            markdown_widget,
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
    """Tool call made by the agent to *ls* files with file tree display"""

    # Example directory output for styling
    example_output = [
        ("src/", "directory"),
        ("src/agent/", "directory"),
        ("src/agent/__init__.py", "file"),
        ("src/agent/agent.py", "file"),
        ("src/agent/messages.py", "file"),
        ("src/tui/", "directory"),
        ("src/tui/screens/", "directory"),
        ("src/tui/screens/analysis_screen/", "directory"),
        ("src/tui/screens/analysis_screen/analysis_screen.py", "file"),
        ("src/tui/screens/test/", "directory"),
        ("src/tui/screens/test/test_screen.py", "file"),
        ("src/tui/widgets/", "directory"),
        ("src/tui/widgets/ascii_art.py", "file"),
        ("src/tui/widgets/instruction_text.py", "file"),
        ("README.md", "file"),
        ("pyproject.toml", "file"),
    ]

    def __init__(self, tool_args: dict, directory_output=None):
        super().__init__("", classes="agent-tool-message")
        self.tool_args = tool_args
        self.directory_output = directory_output or self.example_output

    def compose(self) -> ComposeResult:
        # Create the file tree display
        tree_lines = []
        for path, item_type in self.directory_output:
            # Get the depth based on path separators
            depth = path.count("/") - (1 if path.endswith("/") else 0)
            indent = "  " * depth

            # Choose icon and styling based on type
            if item_type == "directory":
                icon = "🗀"
                name = path.rstrip("/").split("/")[-1] + "/"
            else:
                icon = "🖹"
                name = path.split("/")[-1]

            # Create the tree line
            tree_lines.append(f"{indent}{icon} {name}")

        # Join all lines into a single text block
        tree_content = "\n".join(tree_lines)

        yield Vertical(
            Horizontal(
                Label("☰ Ls", classes="tool-title"),
                Label(f" {self.tool_args.get('path', '.')}", classes="tool-content"),
                classes="tool-horizontal",
            ),
            Static(tree_content, classes="file-tree"),
        )


############################################


############ In-Progress Widget 9 - Bug Report Components ############

from textual.widgets import Static  # noqa
from textual.containers import Horizontal, Vertical  # noqa
from textual.widgets import Markdown  # noqa


class BugReportHeader(Static):
    """Bug report header with title"""

    def __init__(self):
        super().__init__("", classes="bug-report-header")

    def compose(self) -> ComposeResult:
        yield Static("Bug Report", classes="bug-report-title")


class BugReportStats(Static):
    """Bug report statistics"""

    def __init__(self, issues_count: int, files_analyzed: int):
        super().__init__("", classes="bug-report-stats-container")
        self.issues_count = issues_count
        self.files_analyzed = files_analyzed

    def compose(self) -> ComposeResult:
        yield Static(
            f"{self.issues_count} issues found | {self.files_analyzed} files analyzed",
            classes="bug-report-stats",
        )


class BugReportContent(Static):
    """Bug report main content with issues"""

    def __init__(self, bug_report: dict):
        super().__init__("", classes="bug-report-content")
        self.bug_report = bug_report

    def _get_severity_breakdown(self, bugs):
        """Generate a severity breakdown string"""
        if not bugs:
            return "None"

        severity_counts = {"critical": 0, "major": 0, "minor": 0, "low": 0}
        for bug in bugs:
            severity = bug.get("severity", "unknown").lower()
            if severity in severity_counts:
                severity_counts[severity] += 1

        breakdown_parts = []
        for severity, count in severity_counts.items():
            if count > 0:
                breakdown_parts.append(f"{count} {severity}")

        return ", ".join(breakdown_parts) if breakdown_parts else "None"

    def compose(self) -> ComposeResult:
        summary = self.bug_report.get("summary", "No summary available")
        bugs = self.bug_report.get("bugs", [])

        # Build markdown content with separator at top
        md_lines = [
            "---",
            "",
            "## Summary",
            "",
            f"{summary}",
            "",
        ]

        # Add bugs section with rich formatting
        if bugs:
            # Group bugs by severity for better organization
            severity_groups = {"critical": [], "major": [], "minor": [], "low": []}
            severity_colors = {
                "critical": "Red",
                "major": "Peach",
                "minor": "Yellow",
                "low": "Green",
            }

            for bug in bugs:
                severity = bug.get("severity", "unknown").lower()
                if severity in severity_groups:
                    severity_groups[severity].append(bug)
                else:
                    severity_groups["minor"].append(bug)

            md_lines.extend(
                [
                    "## Findings",
                    "",
                ]
            )

            # Display bugs by severity (critical -> major -> minor -> low)
            for severity in ["critical", "major", "minor", "low"]:
                if severity_groups[severity]:
                    color = severity_colors.get(severity, "Text")
                    count = len(severity_groups[severity])

                    md_lines.extend(
                        [
                            f"### {severity.title()} Severity Issues ({count})",
                            "",
                        ]
                    )

                    for i, bug in enumerate(severity_groups[severity], 1):
                        title = bug.get("title", "Unknown issue")
                        description = bug.get("description", "No description")
                        file_path = bug.get("file", "unknown")
                        line = bug.get("line", "unknown")
                        category = bug.get("category", "unknown")
                        recommendation = bug.get("recommendation", "No recommendation")

                        md_lines.extend(
                            [
                                f"#### {i}. {title}",
                                "",
                                f"**Location:** `{file_path}:{line}` • *{category}*",
                                "",
                                f"> **Problem:**  ",
                                f"> {description}",
                                "",
                                f"**Recommended Fix:**  ",
                                f"{recommendation}",
                                "",
                                "---",
                                "",
                            ]
                        )
        else:
            md_lines.extend(
                [
                    "## Result",
                    "",
                    "> **✓ No security issues found**",
                    "",
                    "The analyzed codebase appears to be free of common security vulnerabilities.",
                ]
            )

        markdown_content = "\n".join(md_lines)

        # Create the markdown widget
        markdown_widget = Markdown(
            markdown_content, classes="clean-bug-report-markdown"
        )
        markdown_widget.code_dark_theme = "catppuccin-mocha"

        yield markdown_widget


class BugReportWithLoadingMessage(Static):
    """Combined widget that shows loading state then bug report"""

    def __init__(self, bug_report: dict):
        super().__init__("", classes="agent-tool-message")
        self.bug_report = bug_report
        self.is_loading = True

    def on_mount(self) -> None:
        """Start the loading timer when widget mounts"""
        self.set_timer(10.0, self.show_bug_report)

    def show_bug_report(self) -> None:
        """Switch from loading to bug report display"""
        self.is_loading = False
        self.refresh(recompose=True)

    def compose(self) -> ComposeResult:
        if self.is_loading:
            # Show loading state
            yield Vertical(
                Static("Generating bug report...", classes="loading-message"),
            )
        else:
            # Show actual bug report using components
            bugs = self.bug_report.get("bugs", [])
            files_analyzed = self.bug_report.get("files_analyzed", 0)

            yield Vertical(
                BugReportHeader(),
                BugReportStats(len(bugs), files_analyzed),
                BugReportContent(self.bug_report),
            )


############ In-Progress Widget 10 - Original Bug Report ############

from textual.widgets import Static  # noqa
from textual.containers import Horizontal, Vertical  # noqa
from textual.widgets import Markdown  # noqa


class BugReportMessage(Static):
    """Tool message displaying a structured bug report with markdown formatting"""

    def __init__(self, bug_report: dict):
        super().__init__("", classes="agent-tool-message")
        self.bug_report = bug_report

    def compose(self) -> ComposeResult:
        # Extract report data
        summary = self.bug_report.get("summary", "No summary available")
        bugs = self.bug_report.get("bugs", [])
        files_analyzed = self.bug_report.get("files_analyzed", 0)

        # Build markdown content
        md_lines = [
            f"## Summary",
            f"",
            f"{summary}",
            f"",
            f"**Files analyzed:** {files_analyzed}",
            f"**Issues found:** {len(bugs)}",
            f"",
        ]

        # Add bugs section
        if bugs:
            md_lines.append("## Issues")
            md_lines.append("")

            # Group bugs by severity for better organization
            severity_groups = {"major": [], "minor": [], "critical": [], "low": []}
            for bug in bugs:
                severity = bug.get("severity", "unknown").lower()
                if severity in severity_groups:
                    severity_groups[severity].append(bug)
                else:
                    severity_groups["minor"].append(bug)

            # Display bugs by severity (critical -> major -> minor -> low)
            for severity in ["critical", "major", "minor", "low"]:
                if severity_groups[severity]:
                    severity_emoji = {
                        "critical": "🔴",
                        "major": "🟡",
                        "minor": "🟢",
                        "low": "⚪",
                    }

                    md_lines.append(
                        f"### {severity_emoji[severity]} {severity.title()} Issues"
                    )
                    md_lines.append("")

                    for bug in severity_groups[severity]:
                        title = bug.get("title", "Unknown issue")
                        description = bug.get("description", "No description")
                        file_path = bug.get("file", "unknown")
                        line = bug.get("line", "unknown")
                        category = bug.get("category", "unknown")
                        recommendation = bug.get("recommendation", "No recommendation")

                        md_lines.extend(
                            [
                                f"#### {title}",
                                f"",
                                f"**Location:** `{file_path}:{line}`",
                                f"**Category:** {category}",
                                f"",
                                f"{description}",
                                f"",
                                f"**Recommendation:** {recommendation}",
                                f"",
                                "---",
                                "",
                            ]
                        )
        else:
            md_lines.append("**No issues found** ✅")

        markdown_content = "\n".join(md_lines)

        # Create the markdown widget with bug report styling
        markdown_widget = Markdown(markdown_content, classes="bug-report-markdown")
        markdown_widget.code_dark_theme = "catppuccin-mocha"

        yield Vertical(
            Horizontal(
                Label("🐛 Bug Report", classes="tool-title"),
                Label(f" {len(bugs)} issues found", classes="tool-content"),
                classes="tool-horizontal",
            ),
            markdown_widget,
        )


############################################
