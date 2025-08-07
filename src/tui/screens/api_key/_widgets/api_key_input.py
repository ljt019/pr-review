from textual.app import ComposeResult
from textual.widgets import Input
from textual.containers import Horizontal

class ApiKeyInput(Horizontal):
    """Input widget for API key"""

    def compose(self) -> ComposeResult:
        """Compose the API key input widget."""
        yield Input(password=True, placeholder="Enter your OpenRouter API key", id="api_key")
        self.add_class("input-wrapper")