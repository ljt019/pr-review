from textual.widgets import Label
from src.paths import get_widget_path

class InstructionText(Label):
    """A label that displays instructions for the user."""

    CSS_PATH = str(get_widget_path("instruction_text.tcss"))

    def __init__(self, text: str):
        super().__init__(text)
        self.classes = "instruction_text"
