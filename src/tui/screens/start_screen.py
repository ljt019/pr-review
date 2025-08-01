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
        Binding("b", "back_to_model_select", "Back to Model Select", priority=True),
    ]
    
    def __init__(self, selected_model: str = None):
        super().__init__()
        self.selected_model = selected_model
    
    def compose(self) -> ComposeResult:
        # Get the selected model from the app or the parameter
        model = self.selected_model or getattr(self.app, 'selected_model', 'Unknown')
        
        yield Container(
            Static(
                f"🎉 Welcome to Bug Bot!\n\n"
                f"Selected Model: {model}\n\n"
                "This is where the main app will go...\n\n"
                "Press 'b' to go back to model selection\n"
                "Press Ctrl+C to exit",
                classes="main-content"
            )
        )
    
    def action_back_to_model_select(self) -> None:
        """Go back to model selection screen"""
        self.app.pop_screen()