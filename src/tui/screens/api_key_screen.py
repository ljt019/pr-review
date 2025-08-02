"""API Key input screen for Bug Bot TUI"""

import os
from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Center, Horizontal
from textual.widgets import Input, Label
from textual.binding import Binding
from paths import get_screen_path
from ..widgets.ascii_art import ASCIIArt
from ..widgets.instruction_text import InstructionText
from ..widgets.api_key_input import ApiKeyInput

class APIKeyScreen(Screen):
    """Screen for API key input"""

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose screen widgets centered both horizontally and vertically."""
        yield Container(
            ASCIIArt(),
            ApiKeyInput(),
            InstructionText("Press Enter to continue"),
            classes="input-container"
        )
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input"""
        if event.input.id == "api_key":
            self.save_api_key()
    
    def save_api_key(self) -> None:
        """Save API key and move to next screen"""
        api_key = self.query_one("#api_key", Input).value.strip()
        if api_key:
            os.environ['OPEN_ROUTER_API_KEY'] = api_key
            with open('.env', 'w') as file:
                file.write(f'OPEN_ROUTER_API_KEY={api_key}\n')
            self.app.switch_screen("model_select")