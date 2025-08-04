#!/usr/bin/env python3
"""
Sniff TUI Application using Textual
"""

import os
from typing import Optional

import typer
from dotenv import load_dotenv
from textual.app import App
from textual.binding import Binding

from src.paths import get_tui_path

from .screens import APIKeyScreen, ModelSelectScreen, StartScreen

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

    def __init__(self):
        super().__init__(ansi_color=True)
        self.selected_model = None

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
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show version"
    ),
):
    """Sniffer"""
    if version:
        print("Sniff TUI v0.1.0")
        raise typer.Exit()

    # Run the TUI
    if ctx.invoked_subcommand is None:
        # Install screens
        tui = SnifferTUI()
        tui.install_screen(APIKeyScreen(), name="api_key")
        tui.install_screen(ModelSelectScreen(), name="model_select")
        tui.install_screen(StartScreen(), name="main")
        tui.run()


if __name__ == "__main__":
    app()
