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

    def render_tool_call(self, message: ToolCallMessage) -> None:
        """Render a tool call message."""
        indicator_key = message.call_id or f"{message.tool_name}_{len(self.tool_indicators)}"
        
        # Only create if we haven't seen this call_id before
        if indicator_key not in self.tool_indicators:
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
                # For todo messages, we'll create a placeholder that gets updated later
                tool_indicator = ToolIndicator(message.tool_name, message.arguments)
                self.tool_indicators[indicator_key] = tool_indicator
                self._add_widget(tool_indicator)
                return
            else:
                # Fallback to original ToolIndicator for other tools
                tool_indicator = ToolIndicator(message.tool_name, message.arguments)
                self.tool_indicators[indicator_key] = tool_indicator
                self._add_widget(tool_indicator)
                return
            
            # For the new widgets, we store them but don't need completion tracking
            self.tool_indicators[indicator_key] = widget
            self._add_widget(widget)

    def render_tool_result(self, message: ToolResultMessage) -> None:
        """Render a tool result message."""
        # Track files analyzed from successful cat operations
        if message.tool_name == "cat" and not message.result.startswith("Error:"):
            self._track_analyzed_file(message)
        
        # Find and update the matching tool widget
        matching_key = self._find_matching_tool_key(message.tool_name)
        
        if matching_key:
            widget = self.tool_indicators[matching_key]
            
            # Handle different widget types
            if hasattr(widget, 'mark_completed'):
                # Old ToolIndicator style
                self.app.call_from_thread(widget.mark_completed)
            elif message.tool_name == "cat" and hasattr(widget, 'children') and len(widget.children) > 0:
                # Update CatToolMessage with actual file content
                cat_widget = widget.children[0]  # Get the CatToolMessage from CenterWidget
                if hasattr(cat_widget, 'file_content'):
                    cat_widget.file_content = message.result
                    # Trigger a recompose to show the new content
                    self.app.call_from_thread(cat_widget.refresh, recompose=True)
            elif message.tool_name == "grep" and hasattr(widget, 'children') and len(widget.children) > 0:
                # Update GrepToolMessage with actual search results
                grep_widget = widget.children[0]  # Get the GrepToolMessage from CenterWidget  
                if hasattr(grep_widget, 'search_results'):
                    # Parse grep results - this would need actual parsing logic
                    grep_widget.search_results = self._parse_grep_results(message.result)
                    # Trigger a recompose to show the new content
                    self.app.call_from_thread(grep_widget.refresh, recompose=True)

    def render_todo_state(self, message: TodoStateMessage) -> None:
        """Render todo state update."""
        if not message.todos:
            return
            
        # Find the most recent todo tool indicator and replace it with new widget
        for key in reversed(list(self.tool_indicators.keys())):
            widget = self.tool_indicators[key]
            if hasattr(widget, 'tool_name') and widget.tool_name in ["todo_write", "todo_read"]:
                # Remove the old indicator
                self.app.call_from_thread(widget.remove)
                
                # Create new todo widget based on type
                if widget.tool_name == "todo_write":
                    new_widget = CenterWidget(AgentWriteTodoMessage(message.todos))
                else:  # todo_read
                    new_widget = CenterWidget(AgentReadTodoMessage(message.todos))
                
                # Replace in our tracking dict and add to UI
                self.tool_indicators[key] = new_widget
                self._add_widget(new_widget)
                break

    def render_message_start(self, message: MessageStart) -> None:
        """Start rendering a streaming message."""
        if message.message_type == "analysis":
            self.analysis_message_count += 1
            # Use the new AgentMessage widget wrapped in CenterWidget
            self.current_streaming_widget = CenterWidget(AgentMessage(""))
            self.current_streaming_widget.add_class("streaming")
            self._add_widget(self.current_streaming_widget)

    def render_message_token(self, message: MessageToken) -> None:
        """Render a streaming message token."""
        if not self.current_streaming_widget:
            return
        
        # Get the AgentMessage widget from the CenterWidget
        agent_message = self.current_streaming_widget.children[0]
        if not hasattr(agent_message, '_content'):
            agent_message._content = ""
        
        # Accumulate content
        agent_message._content += message.token
        
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

    def render_message_end(self, message: MessageEnd) -> None:
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

    def render_error(self, error_message: str) -> None:
        """Render an error message."""
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