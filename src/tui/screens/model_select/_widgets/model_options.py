from textual.widgets import OptionList
from textual.widgets.option_list import Option

from agent.agent import ModelOptions
from paths import get_widget_path


class ModelOptionsWidget(OptionList):
    """A widget that displays model options for selection."""

    CSS_PATH = str(get_widget_path("model_options.tcss"))

    def __init__(self):
        super().__init__(
            Option("Qwen3 30B A3B", id=ModelOptions.QWEN3_30B_A3B_INSTRUCT.value),
            Option("Qwen3 235B A22B", id=ModelOptions.QWEN3_235B_A22B_INSTRUCT.value),
            Option("Qwen3 480B A35B", id=ModelOptions.QWEN3_480B_A35B_CODER.value),
            id="model_select",
            classes="model_options",
        )
