"""Main application screen for Bug Bot TUI"""

import asyncio
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import LoadingIndicator, Static

from bug_bot.bug_bot import (
    BugBot,
    MessageEnd,
    MessageStart,
    MessageToken,
    ModelOptions,
    TodoStateMessage,
    ToolCallMessage,
    ToolResultMessage,
)
from paths import get_assets_path
from tui.utils.json_detector import json_detector
from tui.widgets.bug_report_widgets import BugReportContainer, ReportPlaceholder
from tui.widgets.message_box import BotMessage, MessageBox
from tui.widgets.todo_message_widget import TodoMessageWidget
from tui.widgets.tool_indicator import ToolIndicator


class StartScreen(Screen):
    """Main application screen"""

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("b", "back_to_model_select", "Back to Model Select", priority=True),
    ]

    def __init__(self, selected_model: str = None):
        super().__init__()
        self.selected_model = selected_model
        self.output_container = None
        self.tool_count = 0

    def compose(self) -> ComposeResult:
        # Get the selected model from the app or the parameter
        model = self.selected_model or getattr(self.app, "selected_model", "Unknown")

        yield Container(
            Static(f"{model}", classes="header"),
            Center(VerticalScroll(id="messages-container"), classes="messages-center"),
            classes="main-container",
        )

    def on_mount(self) -> None:
        """Start the bug bot analysis when screen mounts"""
        self.messages_container = self.query_one("#messages-container", VerticalScroll)
        self.run_bug_analysis()

    @work(thread=True)
    def run_bug_analysis(self) -> None:
        """Run the bug bot analysis in a worker thread"""
        # Use the toy-webserver.zip for testing
        zipped_codebase = get_assets_path("toy-webserver.zip")

        if not Path(zipped_codebase).exists():
            self.app.call_from_thread(
                self.update_output, f"❌ Error: Test file '{zipped_codebase}' not found"
            )
            return

        # Map selected model to enum
        model_map = {
            "Qwen3 480B A35B Coder": ModelOptions.QWEN3_480B_A35B_CODER,
            "Qwen3 235B A22B Instruct": ModelOptions.QWEN3_235B_A22B_INSTRUCT,
            "Qwen3 30B A3B Instruct": ModelOptions.QWEN3_30B_A3B_INSTRUCT,
        }
        model_option = model_map.get(
            self.selected_model, ModelOptions.QWEN3_30B_A3B_INSTRUCT
        )

        try:
            with BugBot(
                zipped_codebase=zipped_codebase, model_option=model_option
            ) as bot:
                current_streaming_widget = None
                tool_indicators = {}  # Map call_id to indicator for updating
                report_placeholder = None
                analysis_message_count = (
                    0  # Track how many analysis messages we've created
                )

                for message in bot.run_streaming():
                    if isinstance(message, ToolCallMessage):
                        # Add minimal tool indicator in the chat flow
                        # Use call_id if available, otherwise fall back to tool_name for backwards compatibility
                        indicator_key = message.call_id or f"{message.tool_name}_{len(tool_indicators)}"
                        
                        # Only create if we haven't seen this call_id before
                        if indicator_key not in tool_indicators:
                            tool_indicator = ToolIndicator(message.tool_name, message.arguments)
                            tool_indicators[indicator_key] = tool_indicator
                            self.app.call_from_thread(
                                self.add_message_widget, tool_indicator
                            )

                    elif isinstance(message, ToolResultMessage):
                        # Mark the tool as completed - find the most recent tool call for this tool name
                        # Look for call_id that starts with the tool name
                        matching_key = None
                        for key in reversed(list(tool_indicators.keys())):
                            if key.startswith(f"{message.tool_name}_"):
                                tool_indicator = tool_indicators[key]
                                if not tool_indicator.completed:
                                    matching_key = key
                                    break
                        
                        if matching_key:
                            tool_indicator = tool_indicators[matching_key]
                            self.app.call_from_thread(tool_indicator.mark_completed)

                    elif isinstance(message, TodoStateMessage):
                        # Show todo state as an inline message in the chat
                        if message.todos:  # Only show if there are todos
                            todo_widget = TodoMessageWidget(message.todos)
                            self.app.call_from_thread(
                                self.add_message_widget, todo_widget
                            )

                    elif isinstance(message, MessageStart):
                        # Start a new streaming analysis message
                        if message.message_type == "analysis":
                            # Always create a NEW analysis message widget
                            analysis_message_count += 1
                            analysis_msg = BotMessage(role="analysis", content="")
                            current_streaming_widget = MessageBox(analysis_msg)
                            current_streaming_widget.add_class("streaming")
                            self.app.call_from_thread(
                                self.add_message_widget, current_streaming_widget
                            )

                    elif isinstance(message, MessageToken):
                        # Append token to current streaming message
                        if current_streaming_widget:
                            # First, check if JSON was already detected
                            if current_streaming_widget.message.has_json_detected:
                                # JSON already detected - don't append more tokens
                                # Just continue collecting for final processing
                                current_streaming_widget.message.content += (
                                    message.token
                                )
                            else:
                                # Normal streaming - add token and check for JSON
                                self.app.call_from_thread(
                                    current_streaming_widget.append_chunk, message.token
                                )

                                # Check if JSON was just detected
                                if (
                                    current_streaming_widget.message.has_json_detected
                                    and not report_placeholder
                                ):
                                    # JSON detected! Extract content and add placeholder
                                    self.app.call_from_thread(
                                        current_streaming_widget.extract_json_content
                                    )
                                    report_placeholder = ReportPlaceholder()
                                    self.app.call_from_thread(
                                        self.add_message_widget, report_placeholder
                                    )

                    elif isinstance(message, MessageEnd):
                        # Streaming complete - handle final JSON processing
                        if current_streaming_widget:
                            self.app.call_from_thread(
                                current_streaming_widget.remove_class, "streaming"
                            )

                            # Check if we need to process JSON
                            if (
                                current_streaming_widget.message.has_json_detected
                                and report_placeholder
                            ):
                                # JSON was detected during streaming, get the full content
                                from tui.utils.json_detector import json_detector

                                split = json_detector.split_content(
                                    current_streaming_widget.message.content
                                )
                                if split.has_json:
                                    self.app.call_from_thread(
                                        self.process_final_json,
                                        split.json_content,
                                        report_placeholder,
                                    )

                            current_streaming_widget = None

        except Exception as e:
            error_msg = BotMessage(
                role="analysis", content=f"❌ Error during analysis: {str(e)}"
            )
            error_widget = MessageBox(error_msg)
            self.app.call_from_thread(self.add_message_widget, error_widget)
        finally:
            # Analysis complete - no additional cleanup needed for inline todos
            pass

    def add_message_widget(self, widget) -> None:
        """Add a message widget to the container and auto-scroll."""
        self.messages_container.mount(widget)

        # Always scroll to bottom to prevent layout shifts
        self.messages_container.scroll_end(animate=False)

    def process_final_json(self, json_content: str, placeholder_widget) -> None:
        """Process the final JSON and replace placeholder with styled report."""
        try:
            # Parse the JSON
            json_data = json_detector.parse_json(json_content)

            if json_data:
                # Create the bug report container
                report_container = BugReportContainer()
                report_container.load_from_json(json_data)

                # Replace the placeholder with the actual report
                if placeholder_widget:
                    placeholder_widget.remove()

                # Add the styled report
                self.messages_container.mount(report_container)
                self.messages_container.scroll_end(animate=False)
            else:
                # JSON parsing failed - show error in placeholder
                if placeholder_widget:
                    placeholder_widget.remove()

                error_msg = BotMessage(
                    role="analysis", content="❌ Error parsing bug report JSON"
                )
                error_widget = MessageBox(error_msg)
                self.messages_container.mount(error_widget)

        except Exception as e:
            # Something went wrong - show error
            if placeholder_widget:
                placeholder_widget.remove()

            error_msg = BotMessage(
                role="analysis", content=f"❌ Error processing bug report: {str(e)}"
            )
            error_widget = MessageBox(error_msg)
            self.messages_container.mount(error_widget)

    def action_back_to_model_select(self) -> None:
        """Go back to model selection screen"""
        self.app.pop_screen()
