"""Service for rendering messages in the UI, separating rendering logic from business logic."""

import logging
from typing import Dict, Optional

from textual.app import App
from textual.widget import Widget

from agent.messages import (
    MessageEnd,
    MessageStart,
    MessageToken,
    TodoStateMessage,
    ToolCallMessage,
    ToolResultMessage,
)
from tui.utils.json_detector import json_detector
from tui.screens.analysis_screen._widgets.bug_report_widgets import BugReportContainer
from tui.screens.analysis_screen._widgets.message_box import BotMessage, MessageBox
from tui.screens.analysis_screen._widgets.tool_indicator import ToolIndicator

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

    def render_tool_call(self, message: ToolCallMessage) -> None:
        """Render a tool call message."""
        indicator_key = message.call_id or f"{message.tool_name}_{len(self.tool_indicators)}"
        
        # Only create if we haven't seen this call_id before
        if indicator_key not in self.tool_indicators:
            tool_indicator = ToolIndicator(message.tool_name, message.arguments)
            self.tool_indicators[indicator_key] = tool_indicator
            self._add_widget(tool_indicator)

    def render_tool_result(self, message: ToolResultMessage) -> None:
        """Render a tool result message."""
        # Track files analyzed from successful cat operations
        if message.tool_name == "cat" and not message.result.startswith("Error:"):
            self._track_analyzed_file(message)
        
        # Find and mark the matching tool as completed
        matching_key = self._find_matching_tool_key(message.tool_name)
        
        if matching_key:
            tool_indicator = self.tool_indicators[matching_key]
            self.app.call_from_thread(tool_indicator.mark_completed)

    def render_todo_state(self, message: TodoStateMessage) -> None:
        """Render todo state update."""
        if not message.todos:
            return
            
        # Find the most recent todo tool
        for key in reversed(list(self.tool_indicators.keys())):
            tool_indicator = self.tool_indicators[key]
            if tool_indicator.tool_name in ["todo_write", "todo_read"]:
                self.app.call_from_thread(
                    tool_indicator.set_todo_data, message.todos
                )
                break

    def render_message_start(self, message: MessageStart) -> None:
        """Start rendering a streaming message."""
        if message.message_type == "analysis":
            self.analysis_message_count += 1
            analysis_msg = BotMessage(role="analysis", content="")
            self.current_streaming_widget = MessageBox(analysis_msg)
            self.current_streaming_widget.add_class("streaming")
            self._add_widget(self.current_streaming_widget)

    def render_message_token(self, message: MessageToken) -> None:
        """Render a streaming message token."""
        if not self.current_streaming_widget:
            return
            
        # Check if JSON was already detected
        if self.current_streaming_widget.message.has_json_detected:
            # Just accumulate content
            self.current_streaming_widget.message.content += message.token
        else:
            # Normal streaming
            self.app.call_from_thread(
                self.current_streaming_widget.append_chunk, message.token
            )
            
            # Check if JSON was just detected
            if (
                self.current_streaming_widget.message.has_json_detected
                and not self.report_placeholder
            ):
                self._handle_json_detection()

    def render_message_end(self, message: MessageEnd) -> None:
        """End rendering of a streaming message."""
        if not self.current_streaming_widget:
            return
            
        self.app.call_from_thread(
            self.current_streaming_widget.remove_class, "streaming"
        )
        
        # Process final JSON if detected
        if (
            self.current_streaming_widget.message.has_json_detected
            and self.report_placeholder
        ):
            self._process_final_json()
            
        self.current_streaming_widget = None

    def render_error(self, error_message: str) -> None:
        """Render an error message."""
        error_msg = BotMessage(
            role="analysis", content=f"❌ Error: {error_message}"
        )
        error_widget = MessageBox(error_msg)
        self._add_widget(error_widget)

    def _add_widget(self, widget: Widget) -> None:
        """Add a widget to the messages container."""
        self.app.call_from_thread(self.messages_container.mount, widget)
        self.app.call_from_thread(
            self.messages_container.scroll_end, animate=False
        )

    def _find_matching_tool_key(self, tool_name: str) -> Optional[str]:
        """Find the most recent uncompleted tool call for a given tool name."""
        for key in reversed(list(self.tool_indicators.keys())):
            if key.startswith(f"{tool_name}_"):
                tool_indicator = self.tool_indicators[key]
                if not tool_indicator.completed:
                    return key
        return None
    
    def _track_analyzed_file(self, message: ToolResultMessage) -> None:
        """Extract and track file path from successful cat tool results."""
        try:
            # Find the corresponding tool call to get the file path
            matching_key = self._find_matching_tool_key(message.tool_name)
            if matching_key:
                tool_indicator = self.tool_indicators[matching_key]
                # Parse the arguments to extract the file path
                import json
                try:
                    args = json.loads(tool_indicator.arguments)
                    file_path = args.get("filePath")
                    if file_path:
                        self.analyzed_files.add(file_path)
                except (json.JSONDecodeError, KeyError):
                    # Failed to parse arguments - try extracting from display text
                    display_text = tool_indicator.display_text
                    if display_text and " cat " in display_text:
                        # Extract file path from display text like "⚯ cat path/to/file.py"
                        parts = display_text.split(" cat ", 1)
                        if len(parts) > 1:
                            file_path = parts[1].strip()
                            if file_path:
                                self.analyzed_files.add(file_path)
        except Exception:
            # Don't let file tracking errors break the UI
            pass

    def _handle_json_detection(self) -> None:
        """Handle when JSON is detected in the streaming content."""
        self.app.call_from_thread(
            self.current_streaming_widget.extract_json_content
        )
        
        # Add generating report indicator
        generating_widget = ToolIndicator("generating_report")
        generating_widget.display_text = "✎ Generating bug report..."
        generating_widget.add_class("inline-report")
        generating_widget.mark_completed()
        self._add_widget(generating_widget)
        self.report_placeholder = generating_widget

    def _process_final_json(self) -> None:
        """Process the final JSON content and render the bug report."""
        split = json_detector.split_content(
            self.current_streaming_widget.message.content
        )
        
        if split.has_json:
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
                
                # Create and populate bug report container
                report_container = BugReportContainer()
                report_container.load_from_json(json_data)
                
                # Replace placeholder
                if placeholder_widget:
                    placeholder_widget.remove()
                    
                # Add the report
                self.messages_container.mount(report_container)
                self.messages_container.scroll_end(animate=False)
            else:
                # JSON parsing failed
                if placeholder_widget:
                    placeholder_widget.remove()
                    
                error_msg = BotMessage(
                    role="analysis", content="❌ Error parsing bug report JSON"
                )
                error_widget = MessageBox(error_msg)
                self.messages_container.mount(error_widget)
                
        except Exception as e:
            if placeholder_widget:
                placeholder_widget.remove()
                
            error_msg = BotMessage(
                role="analysis", content=f"❌ Error processing bug report: {str(e)}"
            )
            error_widget = MessageBox(error_msg)
            self.messages_container.mount(error_widget)