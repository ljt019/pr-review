"""Model selection screen for Bug Bot TUI"""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Center
from textual.widgets import OptionList
from textual.binding import Binding

from ..widgets.ascii_art import ASCIIArt
from ..widgets.model_options import ModelOptionsWidget
from ..widgets.instruction_text import InstructionText

class ModelSelectScreen(Screen):
    """Screen for model selection"""
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("enter", "select_model", "Select", priority=True),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Center(
                Vertical(
                    ASCIIArt(),
                    ModelOptionsWidget(),
                    InstructionText("Press Enter to select"),
                    classes="model_select_screen_vertical"
                ),
                classes="model_select_screen_center"
            ),
            classes="model_select_screen_container"
        )
    
    def action_select_model(self) -> None:
        """Handle Enter key to select model"""
        option_list = self.query_one("#model_select", OptionList)
        if option_list.highlighted is not None:
            selected_option = option_list.get_option_at_index(option_list.highlighted)
            self.app.selected_model = selected_option.id
            self.app.push_screen("main")
    
    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle option selection via mouse/enter"""
        self.app.selected_model = event.option.id
        self.app.push_screen("main")