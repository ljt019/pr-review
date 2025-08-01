"""API Key input screen for Bug Bot TUI"""

import os
from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Center, Horizontal
from textual.widgets import Input, Label
from textual.binding import Binding
from paths import get_screen_path
from ..widgets.ascii_art import ASCIIArt


class APIKeyScreen(Screen):
    """Screen for API key input"""
    
    CSS_PATH = str(get_screen_path("api_key_screen.tcss"))
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose screen widgets centered both horizontally and vertically."""
        # Follow the same pattern as ModelSelectScreen for consistency
        yield Container(
            Center(
                Vertical(
                    ASCIIArt(),
                    Horizontal(
                        Input(password=True, placeholder="Enter your OpenRouter API key", id="api_key", classes="input_wrapper"),
                        classes="input-wrapper"
                    ),
                    Label("Press Enter to continue", classes="instruction-text"),
                    classes="input-container"
                )
            )
        )
    
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input"""
        if event.input.id == "api_key":
            self.save_api_key()
    
    def save_api_key(self) -> None:
        """Save API key and move to next screen"""
        api_key = self.query_one("#api_key", Input).value.strip()
        if api_key:
            os.environ['OPENROUTER_API_KEY'] = api_key
            with open('.env', 'w') as file:
                file.write(f'OPENROUTER_API_KEY={api_key}\n')
            self.app.switch_screen("model_select")