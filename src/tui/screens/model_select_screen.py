"""Model selection screen for Bug Bot TUI"""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Center
from textual.widgets import OptionList, Label
from textual.widgets.option_list import Option
from textual.binding import Binding
from paths import get_screen_path
from ..widgets.ascii_art import ASCIIArt


class ModelSelectScreen(Screen):
    """Screen for model selection"""
    
    CSS_PATH = str(get_screen_path("model_select_screen.tcss"))
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("enter", "select_model", "Select", priority=True),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Center(
                Vertical(
                    ASCIIArt(),
                    OptionList(
                        Option("Qwen3 30B A3B", id="qwen3-30b-a3b"),
                        Option("Qwen3 235B A22B", id="qwen3-235b-a22b"),
                        Option("Qwen3 480B A35B", id="qwen3-480b-a35b"),
                        id="model_select"
                    ),
                    Label("Press Enter to select", classes="instruction-text"),
                    classes="input-container"
                )
            )
        )
    
    def action_select_model(self) -> None:
        """Handle Enter key to select model"""
        option_list = self.query_one("#model_select", OptionList)
        if option_list.highlighted is not None:
            selected_model = option_list.get_option_at_index(option_list.highlighted).id
            self.app.selected_model = selected_model
            self.app.switch_screen("main")