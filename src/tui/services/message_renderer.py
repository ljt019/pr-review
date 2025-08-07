"""Service for rendering messages in the UI, separating rendering logic from business logic."""

import logging
from typing import Dict, Optional

from textual.app import App
from textual.widget import Widget

from agent.messaging import (
    AgentMessage as BaseAgentMessage,
    MessageType,
    ToolExecutionMessage,
    StreamStartMessage,
    StreamChunkMessage,
    StreamEndMessage,
    BugReportMessage,
)
from tui.utils.json_detector import json_detector
from tui.screens.analysis_screen._widgets.bug_report_widgets import BugReportContainer
from tui.screens.analysis_screen._widgets.message_box import BotMessage, MessageBox
from tui.screens.analysis_screen._widgets.tool_indicator import ToolIndicator
from tui.screens.analysis_screen._widgets.center_screen import CenterWidget
from tui.screens.analysis_screen._widgets.messages.grep_tool_message import GrepToolMessage
from tui.screens.analysis_screen._widgets.messages.cat_tool_message import CatToolMessage
from tui.screens.analysis_screen._widgets.messages.ls_tool_message import LsToolMessage
from tui.screens.analysis_screen._widgets.messages.glob_tool_message import GlobToolMessage
from tui.screens.analysis_screen._widgets.messages.agent_write_todo_message import AgentWriteTodoMessage
from tui.screens.analysis_screen._widgets.messages.agent_read_todo_message import AgentReadTodoMessage
from tui.screens.analysis_screen._widgets.messages.bug_report_with_loading_message import BugReportWithLoadingMessage
from tui.screens.analysis_screen._widgets.messages.agent_message import AgentMessage

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
        self.current_streaming_widget: Optional[MessageBox] = None
        self.tool_indicators: Dict[str, ToolIndicator] = {}
        self.report_placeholder: Optional[ToolIndicator] = None
        self.analysis_message_count = 0
        self.analyzed_files: set = set()
    
    def render_message(self, message: BaseAgentMessage) -> None:
        """Render any agent message based on its type."""
        if message.message_type == MessageType.TOOL_EXECUTION:
            self.render_tool_execution(message)
        elif message.message_type == MessageType.STREAM_START:
            self.render_stream_start(message)
        elif message.message_type == MessageType.STREAM_CHUNK:
            self.render_stream_chunk(message)
        elif message.message_type == MessageType.STREAM_END:
            self.render_stream_end(message)
        elif message.message_type == MessageType.BUG_REPORT:
            self.render_bug_report(message)
    
    def render_tool_execution(self, message: ToolExecutionMessage) -> None:
        """Render a tool execution message."""
        # Create appropriate widget based on tool type
        if message.tool_name == "grep":
            widget = CenterWidget(GrepToolMessage(message))
        elif message.tool_name == "cat":
            widget = CenterWidget(CatToolMessage(message))
        elif message.tool_name == "ls":
            widget = CenterWidget(LsToolMessage(message))
        elif message.tool_name == "glob":
            widget = CenterWidget(GlobToolMessage(message))
        elif message.tool_name in ["todo_write", "todo_read"]:
            # Handle todo tools by parsing todo state from result and creating appropriate widget
            todos = self._parse_todo_state_from_result(message.result)
            if todos:
                if message.tool_name == "todo_write":
                    widget = CenterWidget(AgentWriteTodoMessage(todos))
                else:  # todo_read
                    widget = CenterWidget(AgentReadTodoMessage(todos))
                self._add_widget(widget)
            else:
                # Fallback to tool indicator if parsing fails
                tool_indicator = ToolIndicator(message.tool_name, str(message.arguments))
                if not message.success:
                    self.app.call_from_thread(tool_indicator.mark_failed, message.error or "Unknown error")
                else:
                    self.app.call_from_thread(tool_indicator.mark_completed)
                self._add_widget(tool_indicator)
            return
        else:
            # Fallback to ToolIndicator for other tools
            tool_indicator = ToolIndicator(message.tool_name, str(message.arguments))
            if not message.success:
                self.app.call_from_thread(tool_indicator.mark_failed, message.error or "Unknown error")
            else:
                self.app.call_from_thread(tool_indicator.mark_completed)
            self._add_widget(tool_indicator)
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
            
            lines = result.strip().split('\n')
            todos = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('[] - ') or line.startswith('[x] - '):
                    # Parse todo item
                    is_complete = line.startswith('[x]')
                    content = line[5:]  # Remove "[] - " or "[x] - "
                    
                    todos.append({
                        "id": f"todo_{len(todos)}",  # Simple ID
                        "content": content,
                        "status": "completed" if is_complete else "pending"
                    })
            
            return todos
        except Exception:
            return []

    def render_stream_start(self, message: StreamStartMessage) -> None:
        """Start rendering a streaming message."""
        if message.content_type == "analysis":
            self.analysis_message_count += 1
            # Use the new AgentMessage widget wrapped in CenterWidget
            self.current_streaming_widget = CenterWidget(AgentMessage(""))
            self.current_streaming_widget.add_class("streaming")
            self._add_widget(self.current_streaming_widget)

    def render_stream_chunk(self, message: StreamChunkMessage) -> None:
        """Render a streaming message chunk."""
        if not self.current_streaming_widget:
            return
        
        # Get the AgentMessage widget from the CenterWidget
        agent_message = self.current_streaming_widget.children[0]
        if not hasattr(agent_message, '_content'):
            agent_message._content = ""
        
        # Accumulate content
        agent_message._content += message.chunk
        
        # Update the widget's renderable content
        self.app.call_from_thread(
            agent_message.update, agent_message._content
        )
        
        # Check for JSON detection (simplified - just look for opening brace)
        if (
            not self.report_placeholder
            and "{" in agent_message._content
            and "summary" in agent_message._content.lower()
        ):
            self._handle_json_detection()

    def render_stream_end(self, message: StreamEndMessage) -> None:
        """End rendering of a streaming message."""
        if not self.current_streaming_widget:
            return
            
        self.app.call_from_thread(
            self.current_streaming_widget.remove_class, "streaming"
        )
        
        # Process final JSON if detected
        if self.report_placeholder:
            agent_message = self.current_streaming_widget.children[0]
            if hasattr(agent_message, '_content'):
                self._process_final_json(agent_message._content)
            
        self.current_streaming_widget = None


    def render_bug_report(self, message: BugReportMessage) -> None:
        """Render a bug report message."""
        # Create bug report widget with the report data
        bug_report_widget = CenterWidget(BugReportWithLoadingMessage(message.report_data))
        
        # Replace placeholder if one exists
        if self.report_placeholder:
            self.app.call_from_thread(self.report_placeholder.remove)
            self.report_placeholder = None
        
        self._add_widget(bug_report_widget)
    
    def render_error(self, error_message: str) -> None:
        """Render a simple error message (legacy method)."""
        error_widget = CenterWidget(AgentMessage(f"❌ Error: {error_message}"))
        self._add_widget(error_widget)

    def _add_widget(self, widget: Widget) -> None:
        """Add a widget to the messages container."""
        self.app.call_from_thread(self.messages_container.mount, widget)
        self.app.call_from_thread(
            self.messages_container.scroll_end, animate=False
        )

    def _find_matching_tool_key(self, tool_name: str) -> Optional[str]:
        """Find the most recent tool call for a given tool name."""
        for key in reversed(list(self.tool_indicators.keys())):
            if key.startswith(f"{tool_name}_"):
                widget = self.tool_indicators[key]
                # For new widgets, always return (they don't track completion)
                # For old ToolIndicators, check completion status
                if not hasattr(widget, 'completed') or not widget.completed:
                    return key
        return None
    
    def _parse_grep_results(self, grep_output: str) -> list[tuple[str, int, str]]:
        """Parse grep output into (file_path, line_number, content) tuples."""
        results = []
        for line in grep_output.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Try to parse grep output format: filename:line_number:content
            parts = line.split(':', 2)
            if len(parts) >= 3:
                try:
                    file_path = parts[0]
                    line_number = int(parts[1])
                    content = parts[2]
                    results.append((file_path, line_number, content))
                except ValueError:
                    # If line number parsing fails, treat as simple match
                    results.append((line, 0, line))
            else:
                # Fallback for non-standard format
                results.append((line, 0, line))
        
        return results
    
    def _track_analyzed_file_from_tool(self, message: ToolExecutionMessage) -> None:
        """Extract and track file path from successful cat tool execution."""
        try:
            if message.tool_name == "cat" and message.arguments:
                # Extract file path from arguments
                if isinstance(message.arguments, dict):
                    file_path = message.arguments.get("filePath") or message.arguments.get("file")
                    if file_path:
                        self.analyzed_files.add(file_path)
        except Exception:
            # Don't let file tracking errors break the UI
            pass

    def _handle_json_detection(self) -> None:
        """Handle when JSON is detected in the streaming content."""
        # Add generating report indicator using new widget
        # Create a temporary bug report with loading state
        temp_bug_report = {
            "summary": "Generating bug report...",
            "bugs": [],
            "files_analyzed": len(self.analyzed_files)
        }
        generating_widget = CenterWidget(BugReportWithLoadingMessage(temp_bug_report))
        self._add_widget(generating_widget)
        self.report_placeholder = generating_widget

    def _process_final_json(self, content: str) -> None:
        """Process the final JSON content and render the bug report."""
        split = json_detector.split_content(content)
        
        if split.has_json:
            # Hide the original AgentMessage that contains the raw JSON
            if self.current_streaming_widget:
                self.app.call_from_thread(self.current_streaming_widget.remove)
            
            self.app.call_from_thread(
                self._render_bug_report,
                split.json_content,
                self.report_placeholder,
            )

    def _render_bug_report(self, json_content: str, placeholder_widget: Optional[Widget]) -> None:
        """Render the bug report from JSON content."""
        try:
            json_data = json_detector.parse_json(json_content)
            
            if json_data:
                # Inject files_analyzed count into the JSON data
                json_data["files_analyzed"] = len(self.analyzed_files)
                
                # Create new bug report widget
                bug_report_widget = CenterWidget(BugReportWithLoadingMessage(json_data))
                
                # Replace placeholder
                if placeholder_widget:
                    placeholder_widget.remove()
                    
                # Add the report
                self.messages_container.mount(bug_report_widget)
                self.messages_container.scroll_end(animate=False)
            else:
                # JSON parsing failed
                if placeholder_widget:
                    placeholder_widget.remove()
                    
                error_widget = CenterWidget(AgentMessage("❌ Error parsing bug report JSON"))
                self.messages_container.mount(error_widget)
                
        except Exception as e:
            if placeholder_widget:
                placeholder_widget.remove()
                
            error_widget = CenterWidget(AgentMessage(f"❌ Error processing bug report: {str(e)}"))
            self.messages_container.mount(error_widget)