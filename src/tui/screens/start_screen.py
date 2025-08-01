"""Main application screen for Bug Bot TUI"""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual.binding import Binding
from paths import get_screen_path


class StartScreen(Screen):
    """Main application screen"""
    
    CSS_PATH = str(get_screen_path("start_screen.tcss"))
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static(
                f"🎉 Welcome to Bug Bot!\n\n"
                f"Selected Model: {getattr(self.app, 'selected_model', 'Unknown')}\n\n"
                "This is where the main app will go...\n\n"
                "Press Ctrl+C to exit",
                classes="main-content"
            )
        )