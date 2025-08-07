#!/usr/bin/env python3
"""
Sniff TUI Application using Textual
"""

import logging
import os

import typer
from dotenv import load_dotenv
from textual.app import App
from textual.binding import Binding

from paths import get_tui_path

from .screens import AnalysisScreen, APIKeyScreen, ModelSelectScreen

# Load .env file
load_dotenv()


def load_css_path_list(path: str) -> list[str]:
    """Load a list of CSS paths"""
    from pathlib import Path

    tui_path = Path(get_tui_path(""))

    # Use rglob to recursively find all .tcss files
    css_path_list = [str(p) for p in tui_path.rglob("*.tcss")]

    return css_path_list


class SnifferTUI(App):
    """Sniffer TUI Application"""

    CSS_PATH = load_css_path_list(str(get_tui_path("")))

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, log_conversation: bool = False):
        super().__init__(ansi_color=True)
        self.selected_model = None
        self.log_conversation = log_conversation

    def on_mount(self) -> None:
        """Set up the app when it starts"""
        # Check if API key already exists
        if os.path.exists(".env") and os.getenv("OPEN_ROUTER_API_KEY"):
            self.push_screen("model_select")
        else:
            self.push_screen("api_key")

    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


# CLI interface
app = typer.Typer(help="Sniff Code Review Agent")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v"),
    debug: bool = typer.Option(False, "--log", "-l", help="Enable debug logging"),
):
    """Sniffer"""
    if version:
        print("Sniff TUI v0.1.0")
        raise typer.Exit()

    # Configure logging if debug flag is set
    if debug:
        # Create logs directory if it doesn't exist
        import os

        os.makedirs("logs", exist_ok=True)

        # Clear any existing log file
        log_file = "logs/sniff_messages.txt"
        with open(log_file, "w") as f:
            f.write("")

        # Disable all external library logging to prevent noise
        logging.getLogger("httpx").setLevel(logging.CRITICAL)
        logging.getLogger("httpcore").setLevel(logging.CRITICAL)
        logging.getLogger("urllib3").setLevel(logging.CRITICAL)
        logging.getLogger("requests").setLevel(logging.CRITICAL)

        # Set root logger to WARNING to suppress most noise
        logging.basicConfig(
            level=logging.WARNING,
            format="%(message)s",
            handlers=[],  # No handlers for root logger
            force=True,
        )

        # Configure only our specific message logger
        message_logger = logging.getLogger("sniff.messages")
        message_logger.setLevel(logging.INFO)
        message_logger.propagate = False  # Don't propagate to root logger

        # Clear any existing handlers
        message_logger.handlers.clear()

        # Add our clean handler
        message_handler = logging.FileHandler(log_file)
        message_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        message_logger.addHandler(message_handler)

    # Run the TUI
    if ctx.invoked_subcommand is None:
        tui = SnifferTUI(log_conversation=False)  # Disable conversation logging
        tui.install_screen(APIKeyScreen(), name="api_key")
        tui.install_screen(ModelSelectScreen(), name="model_select")
        tui.install_screen(AnalysisScreen(), name="main")
        tui.run()


if __name__ == "__main__":
    app()
