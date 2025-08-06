"""Main application screen for Sniff TUI"""

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from agent.agent import ModelOptions
from agent.messages import (
    MessageEnd,
    MessageStart,
    MessageToken,
    TodoStateMessage,
    ToolCallMessage,
    ToolResultMessage,
)
from tui.services import AgentService, MessageRenderer


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

        if model == "qwen/qwen3-coder":
            model = "qwen/qwen3-480b-a35b-coder"

        yield Container(
            Static(f"{model}", classes="header"),
            Center(VerticalScroll(id="messages-container"), classes="messages-center"),
            classes="main-container",
        )

    def on_mount(self) -> None:
        """Start the sniff agent analysis when screen mounts"""
        self.messages_container = self.query_one("#messages-container", VerticalScroll)
        self.run_bug_analysis()

    @work(thread=True)
    def run_bug_analysis(self) -> None:
        """Run the sniff agent analysis in a worker thread"""
        # Get model option
        model_option = AgentService.map_model_name_to_option(self.selected_model)

        # Create services
        agent_service = AgentService(model_option)
        renderer = MessageRenderer(self.app, self.messages_container)

        # Validate codebase
        is_valid, error_msg = agent_service.validate_codebase()
        if not is_valid:
            renderer.render_error(error_msg)
            return

        try:
            # Run analysis and render messages
            for message in agent_service.run_analysis():
                if isinstance(message, ToolCallMessage):
                    renderer.render_tool_call(message)

                elif isinstance(message, ToolResultMessage):
                    renderer.render_tool_result(message)

                elif isinstance(message, TodoStateMessage):
                    renderer.render_todo_state(message)

                elif isinstance(message, MessageStart):
                    renderer.render_message_start(message)

                elif isinstance(message, MessageToken):
                    renderer.render_message_token(message)

                elif isinstance(message, MessageEnd):
                    renderer.render_message_end(message)

        except Exception as e:
            renderer.render_error(f"Error during analysis: {str(e)}")

    def action_back_to_model_select(self) -> None:
        """Go back to model selection screen"""
        self.app.pop_screen()
