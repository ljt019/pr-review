from textual.widgets import Label
from paths import get_tui_path



class InstructionText(Label):
    """A label that displays instructions for the user."""

    def __init__(self, text: str):
        super().__init__(text)
        