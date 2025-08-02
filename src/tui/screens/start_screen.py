"""Main application screen for Bug Bot TUI"""

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll, Horizontal
from textual.screen import Screen
from textual.widgets import Static, LoadingIndicator
from textual import work

from bug_bot.bug_bot import (
    BugBot,
    MessageStart,
    MessageToken,
    MessageEnd,
    ModelOptions,
    ToolCallMessage,
    ToolResultMessage,
)
from paths import get_assets_path
from tui.widgets.message_box import MessageBox, BotMessage
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
        model = self.selected_model or getattr(self.app, 'selected_model', 'Unknown')
        
        yield Container(
            Static(f"🐛 Bug Bot Analysis - Model: {model}", classes="header"),
            VerticalScroll(
                id="messages-container"
            ),
            classes="main-container"
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
                self.update_output,
                f"❌ Error: Test file '{zipped_codebase}' not found"
            )
            return
        
        # Map selected model to enum
        model_map = {
            "Qwen3 480B A35B Coder": ModelOptions.QWEN3_480B_A35B_CODER,
            "Qwen3 235B A22B Instruct": ModelOptions.QWEN3_235B_A22B_INSTRUCT,
            "Qwen3 30B A3B Instruct": ModelOptions.QWEN3_30B_A3B_INSTRUCT,
        }
        model_option = model_map.get(self.selected_model, ModelOptions.QWEN3_30B_A3B_INSTRUCT)
        
        try:
            with BugBot(zipped_codebase=zipped_codebase, model_option=model_option) as bot:
                current_streaming_widget = None
                tool_indicators = {}  # Map tool_name to indicator for updating
                
                for message in bot.run_streaming():
                    if isinstance(message, ToolCallMessage):
                        # Add minimal tool indicator in the chat flow
                        tool_indicator = ToolIndicator(message.tool_name)
                        tool_indicators[message.tool_name] = tool_indicator
                        self.app.call_from_thread(self.add_message_widget, tool_indicator)
                    
                    elif isinstance(message, ToolResultMessage):
                        # Mark the tool as completed (but don't show result)
                        if message.tool_name in tool_indicators:
                            tool_indicator = tool_indicators[message.tool_name]
                            self.app.call_from_thread(tool_indicator.mark_completed)
                    
                    elif isinstance(message, MessageStart):
                        # Start a new streaming analysis message
                        if message.message_type == "analysis":
                            analysis_msg = BotMessage(role="analysis", content="")
                            current_streaming_widget = MessageBox(analysis_msg)
                            current_streaming_widget.add_class("streaming")
                            self.app.call_from_thread(self.add_message_widget, current_streaming_widget)
                    
                    elif isinstance(message, MessageToken):
                        # Append token to current streaming message
                        if current_streaming_widget:
                            self.app.call_from_thread(
                                current_streaming_widget.append_chunk,
                                message.token
                            )
                    
                    elif isinstance(message, MessageEnd):
                        # Streaming complete
                        if current_streaming_widget:
                            self.app.call_from_thread(
                                current_streaming_widget.remove_class,
                                "streaming"
                            )
                            current_streaming_widget = None
                    
        except Exception as e:
            error_msg = BotMessage(role="analysis", content=f"❌ Error during analysis: {str(e)}")
            error_widget = MessageBox(error_msg)
            self.app.call_from_thread(self.add_message_widget, error_widget)
    
    def add_message_widget(self, widget) -> None:
        """Add a message widget to the container and auto-scroll."""
        self.messages_container.mount(widget)
        
        # Always scroll to bottom to prevent layout shifts
        self.messages_container.scroll_end(animate=False)
    
    def action_back_to_model_select(self) -> None:
        """Go back to model selection screen"""
        self.app.pop_screen()