"""Service for rendering messages in the UI, separating rendering logic from business logic."""

import logging
from typing import Optional

from textual.app import App
from textual.widget import Widget

from agent.messaging import (
    AgentMessage as BaseAgentMessage,
)
from agent.messaging import (
    BugReportMessage,
    BugReportStartedMessage,
    MessageType,
    StreamChunkMessage,
    StreamEndMessage,
    StreamStartMessage,
    ToolExecutionMessage,
)
from agent.utils.todo_manager import parse_todos_json_block
from tui.screens.analysis_screen._widgets.center_screen import CenterWidget
from tui.screens.analysis_screen._widgets.messages.agent_message import AgentMessage
from tui.screens.analysis_screen._widgets.messages.bug_report_with_loading_message import (
    BugReportWithLoadingMessage,
)
from tui.screens.analysis_screen._widgets.messages.cat_tool_message import (
    CatToolMessage,
)
from tui.screens.analysis_screen._widgets.messages.glob_tool_message import (
    GlobToolMessage,
)
from tui.screens.analysis_screen._widgets.messages.grep_tool_message import (
    GrepToolMessage,
)
from tui.screens.analysis_screen._widgets.messages.ls_tool_message import (
    LsToolMessage,
)
from tui.screens.analysis_screen._widgets.todo_message_widget import TodoMessageWidget
from tui.screens.analysis_screen._widgets.tool_indicator import ToolIndicator

TOOL_WIDGET_MAP = {
    "grep": GrepToolMessage,
    "cat": CatToolMessage,
    "ls": LsToolMessage,
    "glob": GlobToolMessage,
}

logger = logging.getLogger(__name__)


class MessageRenderer:
    """Handles rendering of agent messages in the UI."""

    def __init__(self, app: App, messages_container: Widget):
        """Initialize the renderer.

        Args:
            app: The Textual app instance
            messages_container: The container widget for messages
        """
        self.app = app
        self.messages_container = messages_container
        self.current_streaming_wrapper: Optional[CenterWidget] = None
        self.current_agent_message: Optional[AgentMessage] = None
        self.report_placeholder: Optional[ToolIndicator] = None
        self.analysis_message_count = 0
        self.analyzed_files: set = set()
        self._bug_report_widget = (
            None  # Reference to the bug report widget for updating
        )

    def render_message(self, message: BaseAgentMessage) -> None:
        """Render any agent message based on its type using dispatch mapping."""
        dispatch_map = {
            MessageType.TOOL_EXECUTION: self.render_tool_execution,
            MessageType.STREAM_START: self.render_stream_start,
            MessageType.STREAM_CHUNK: self.render_stream_chunk,
            MessageType.STREAM_END: self.render_stream_end,
            MessageType.BUG_REPORT_STARTED: self.render_bug_report_started,
            MessageType.BUG_REPORT: self.render_bug_report,
        }

        handler = dispatch_map.get(message.message_type)
        if handler:
            handler(message)  # type: ignore[arg-type]
        else:
            logger.warning("Unknown message type: %s", message.message_type)

    def render_tool_execution(self, message: ToolExecutionMessage) -> None:
        """Render a tool execution message."""
        # Create appropriate widget based on tool type
        if message.tool_name in TOOL_WIDGET_MAP:
            widget = CenterWidget(TOOL_WIDGET_MAP[message.tool_name](message))
        elif message.tool_name in ["todo_write", "todo_read"]:
            # Prefer machine-readable todos embedded in the result
            todos = parse_todos_json_block(message.result)
            if not todos:
                # Fallback to text parsing for backward compatibility
                todos = self._parse_todo_state_from_result(message.result)
            if todos:
                widget = CenterWidget(
                    TodoMessageWidget(todos, tool_name=message.tool_name)
                )
                self._add_widget(widget)
            else:
                self._render_tool_indicator(message)
            return
        else:
            # Fallback to ToolIndicator for other tools
            self._render_tool_indicator(message)
            return

        # Track analyzed files from cat operations
        if message.tool_name == "cat" and message.success and message.result:
            self._track_analyzed_file_from_tool(message)

        self._add_widget(widget)

    def _parse_todo_state_from_result(self, result: str) -> list[dict]:
        """Parse todo state from tool result string."""
        if not result:
            return []

        try:
            # The todo tools return todo state info - extract it
            # Example result: "Updated todo list: 6 total, 6 incomplete\n[] - Task 1\n[] - Task 2"
            # or "[] - Task 1\n[] - Task 2\n[x] - Task 3"

            lines = result.strip().split("\n")
            todos = []

            for line in lines:
                line = line.strip()
                if any(
                    line.startswith(marker) for marker in ["[] - ", "[x] - ", "[>] - "]
                ):
                    # Parse todo item
                    if line.startswith("[x] - "):
                        status = "completed"
                        content = line[6:]  # Remove "[x] - "
                    elif line.startswith("[>] - "):
                        status = "in_progress"
                        content = line[6:]  # Remove "[>] - "
                    else:  # line.startswith('[] - ')
                        status = "pending"
                        content = line[5:]  # Remove "[] - "

                    # Check if content has strikethrough (cancelled)
                    cancelled = content.startswith("~~") and content.endswith("~~")
                    if cancelled:
                        content = content[2:-2]  # Remove strikethrough markers

                    todos.append(
                        {
                            "id": f"todo_{len(todos)}",  # Simple ID
                            "content": content,
                            "status": status,
                            "cancelled": cancelled,
                        }
                    )

            return todos
        except Exception:
            return []

    # Removed unused JSON parsing helper for todos (UI consumes JSON blocks directly)

    def render_stream_start(self, message: StreamStartMessage) -> None:
        """Start rendering a streaming message."""
        # Always create a new streaming widget for each stream start
        if message.content_type == "analysis":
            self.analysis_message_count += 1

        # Create stream AgentMessage wrapped in CenterWidget and keep references
        agent_message = AgentMessage("")
        wrapper = CenterWidget(agent_message)
        wrapper.add_class("streaming")
        self.current_streaming_wrapper = wrapper
        self.current_agent_message = agent_message
        self._add_widget(wrapper)

    def render_stream_chunk(self, message: StreamChunkMessage) -> None:
        """Render a streaming message chunk."""
        if not self.current_agent_message:
            return

        # Append content via public API
        self.app.call_from_thread(
            self.current_agent_message.append_chunk, message.content
        )

        # Keep the end in view with Textual's built-in deferral
        self.app.call_from_thread(
            lambda: self.messages_container.scroll_end(animate=False, immediate=False)
        )

    def render_stream_end(self, message: StreamEndMessage) -> None:
        """End rendering of a streaming message."""
        if not self.current_streaming_wrapper:
            return

        self.app.call_from_thread(
            self.current_streaming_wrapper.remove_class, "streaming"
        )

        self.current_streaming_wrapper = None
        self.current_agent_message = None

    def render_bug_report_started(self, message: BugReportStartedMessage) -> None:
        """Render a bug report started message - show loading placeholder."""
        # Hide any current streaming widget that might contain partial JSON
        if self.current_streaming_wrapper:
            self.app.call_from_thread(self.current_streaming_wrapper.remove)
            self.current_streaming_wrapper = None
            self.current_agent_message = None

        # Create a temporary bug report with loading state
        temp_bug_report = {
            "summary": "Generating bug report...",
            "bugs": [],
            "files_analyzed": message.files_analyzed,
        }
        loading_bug_report_widget = BugReportWithLoadingMessage(
            temp_bug_report, is_loading=True
        )
        generating_widget = CenterWidget(loading_bug_report_widget)
        self._add_widget(generating_widget)
        self.report_placeholder = generating_widget
        self._bug_report_widget = (
            loading_bug_report_widget  # Keep reference for updating
        )

    def render_bug_report(self, message: BugReportMessage) -> None:
        """Render a bug report message."""
        # Inject files_analyzed count into report_data
        report_data_with_count = message.report_data.copy()
        report_data_with_count["files_analyzed"] = message.files_analyzed

        # Update the existing loading widget with actual report data
        if self._bug_report_widget:
            # Replace the loading widget with a fresh, non-loading widget and scroll it into view
            def _replace_and_scroll() -> None:
                try:
                    # Remove the old placeholder wrapper if it exists
                    if self.report_placeholder:
                        try:
                            self.report_placeholder.remove()
                        except Exception:
                            pass

                    # Create and mount the final report widget
                    final_widget = CenterWidget(
                        BugReportWithLoadingMessage(
                            report_data_with_count, is_loading=False
                        )
                    )
                    self.messages_container.mount(final_widget)
                    # Align the report at the top of the viewport after next refresh
                    self.messages_container.call_after_refresh(
                        lambda: self.messages_container.scroll_to_widget(
                            final_widget, top=True, animate=False, immediate=True
                        )
                    )
                finally:
                    self._bug_report_widget = None
                    self.report_placeholder = None

            self.app.call_from_thread(_replace_and_scroll)
        else:
            # Fallback: create new widget if no loading widget exists
            bug_report_widget = CenterWidget(
                BugReportWithLoadingMessage(report_data_with_count, is_loading=False)
            )
            self._add_widget(bug_report_widget)

    def render_error(self, error_message: str) -> None:
        """Render a simple error message (legacy method)."""
        error_widget = CenterWidget(AgentMessage(f"Error: {error_message}"))
        self._add_widget(error_widget)

    def _add_widget(self, widget: Widget) -> None:
        """Add a widget to the messages container."""
        # Mount the widget
        self.app.call_from_thread(self.messages_container.mount, widget)

        # After mount, keep bottom in view using Textual's deferral
        self.app.call_from_thread(
            lambda: self.messages_container.scroll_end(animate=False, immediate=False)
        )

    # Removed legacy tool indicator tracking

    # Grep parsing is centralized in the grep widget helper

    def _track_analyzed_file_from_tool(self, message: ToolExecutionMessage) -> None:
        """Extract and track file path from successful cat tool execution."""
        try:
            if message.tool_name == "cat" and message.arguments:
                # Extract file path from arguments
                if isinstance(message.arguments, dict):
                    file_path = message.arguments.get(
                        "filePath"
                    ) or message.arguments.get("file")
                    if file_path:
                        self.analyzed_files.add(file_path)
        except Exception:
            # Don't let file tracking errors break the UI
            pass

    def _render_tool_indicator(self, message: ToolExecutionMessage) -> None:
        """Render a simple ToolIndicator widget for a tool execution."""
        tool_indicator = ToolIndicator(
            message.tool_name, message.arguments
        )  # pass dict where possible
        if not message.success:
            self.app.call_from_thread(
                tool_indicator.mark_failed, message.error or "Unknown error"
            )
        else:
            self.app.call_from_thread(tool_indicator.mark_completed)
        self._add_widget(tool_indicator)
