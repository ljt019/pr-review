#!/usr/bin/env python3
"""
Bug Bot TUI Application using Textual
"""

import os
from dotenv import load_dotenv
from typing import Optional

from textual.app import App
from textual.binding import Binding
import typer
from paths import get_tui_path

from bug_bot.bug_bot import BugBot
from .screens import APIKeyScreen, ModelSelectScreen, StartScreen

# Load .env file
load_dotenv()

def load_css_path_list(path: str) -> list[str]:
    """Load a list of CSS paths"""
    css_path_list =[]

    widgets_path = get_tui_path("widgets")
    screens_path = get_tui_path("screens")
    tui_path = get_tui_path("")

    # search for all .tcss files in these three directories
    for root, dirs, files in os.walk(widgets_path):
        for file in files:
            if file.endswith(".tcss"):
                css_path_list.append(os.path.join(root, file))
    
    for root, dirs, files in os.walk(screens_path):
        for file in files:
            if file.endswith(".tcss"):
                css_path_list.append(os.path.join(root, file))
    
    for root, dirs, files in os.walk(tui_path):
        for file in files:
            if file.endswith(".tcss"):
                css_path_list.append(os.path.join(root, file))

    return css_path_list    
    
class BugBotTUI(App):
    """Bug Bot TUI Application"""
    
    CSS_PATH = load_css_path_list(get_tui_path(""))
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
    ]
    
    def __init__(self):
        super().__init__(ansi_color=True)
        self.selected_model = None
    
    def on_mount(self) -> None:
        """Set up the app when it starts"""
        # Check if API key already exists
        if os.path.exists('.env') and os.getenv('OPENROUTER_API_KEY'):
            self.push_screen("model_select")
        else:
            self.push_screen("api_key")
    
    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


# CLI interface
app = typer.Typer(help="Sniffer Code Review Agent")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, version: Optional[bool] = typer.Option(None, "--version", "-v", help="Show version")):
    """Bug Bot TUI Application"""
    if version:
        print("Bug Bot TUI v0.1.0")
        raise typer.Exit()
    
    # Run the TUI
    if ctx.invoked_subcommand is None:
        # Install screens
        tui = BugBotTUI()
        tui.install_screen(APIKeyScreen(), name="api_key")
        tui.install_screen(ModelSelectScreen(), name="model_select")
        tui.install_screen(StartScreen(), name="main")
        tui.run()


if __name__ == "__main__":
    app()