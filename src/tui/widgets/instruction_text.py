from textual.widgets import Label
from paths import get_path

class InstructionText(Label):
    """A label that displays instructions for the user."""

    CSS_PATH = str(get_path("widgets", "instruction_text.tcss"))

    def __init__(self, text: str):
        super().__init__(text)
        self.classes = "instruction_text"
