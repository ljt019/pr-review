"""Main application screen for Bug Bot TUI"""

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static, LoadingIndicator
from textual import work

from bug_bot.bug_bot import (
    BugBot,
    BugReportMessage,
    ModelOptions,
    ToolCallMessage,
    ToolResultMessage,
)
from paths import get_assets_path


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
                Static("🚀 Starting analysis...\n", id="output"),
                id="scroll-container"
            ),
            classes="main-container"
        )
    
    def on_mount(self) -> None:
        """Start the bug bot analysis when screen mounts"""
        self.output_container = self.query_one("#output", Static)
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
                # Clear initial message and start streaming
                self.app.call_from_thread(self.clear_output)
                
                all_messages = []
                for message in bot.run_streaming():
                    all_messages.append(message)
                    
                    if isinstance(message, ToolCallMessage):
                        self.tool_count += 1
                        self.app.call_from_thread(
                            self.update_output,
                            f"🔧 [{self.tool_count}] {message.tool_name}"
                        )
                    elif isinstance(message, BugReportMessage):
                        # Only show meaningful content (skip very short fragments)
                        if len(message.content.strip()) > 10:
                            self.app.call_from_thread(
                                self.update_output,
                                f"💭 Analysis: {message.content[:100]}..." if len(message.content) > 100 else f"💭 {message.content}"
                            )
                    # Skip tool results
                
                # After streaming ends, show the final report
                if all_messages:
                    # Collect all BugReportMessage content and combine it
                    bug_report_parts = []
                    for msg in all_messages:
                        if isinstance(msg, BugReportMessage) and msg.content.strip():
                            bug_report_parts.append(msg.content.strip())
                    
                    if bug_report_parts:
                        # Combine all parts into final report
                        final_report = " ".join(bug_report_parts)
                        self.app.call_from_thread(
                            self.update_output,
                            f"\n{'='*60}\n🐛 FINAL BUG REPORT\n{'='*60}\n\n{final_report}\n{'='*60}"
                        )
                    
        except Exception as e:
            self.app.call_from_thread(
                self.update_output,
                f"\n❌ Error during analysis: {str(e)}"
            )
    
    def update_output(self, text: str) -> None:
        """Update the output container with new text"""
        current = self.output_container.renderable
        self.output_container.update(f"{current}\n{text}")
        
        # Auto-scroll to bottom
        scroll_container = self.query_one("#scroll-container", VerticalScroll)
        scroll_container.scroll_end()
    
    def clear_output(self) -> None:
        """Clear the output container"""
        self.output_container.update("")
        self.tool_count = 0
    
    def action_back_to_model_select(self) -> None:
        """Go back to model selection screen"""
        self.app.pop_screen()