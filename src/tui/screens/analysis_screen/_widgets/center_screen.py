from textual.app import ComposeResult
from textual.widgets import Static


class CenterWidget(Static):
    """Center widget"""

    def __init__(self, child_widget=None):
        super().__init__()
        self.child_widget = child_widget

    def compose(self) -> ComposeResult:
        if self.child_widget:
            yield self.child_widget

    def on_mount(self) -> None:
        # Center horizontally but keep natural vertical stacking so we don't
        # consume the full screen height for each wrapped widget.
        self.styles.align = ("center", "top")
        # Also keep this wrapper to content width / height
        self.styles.width = "auto"
        self.styles.height = "auto"
        if self.child_widget:
            self.child_widget.styles.width = "auto"
