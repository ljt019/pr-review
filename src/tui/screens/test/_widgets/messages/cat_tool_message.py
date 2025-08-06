"""Cat tool message widget"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Markdown, Static


class CatToolMessage(Static):
    """Tool call made by the agent to *cat* files using Markdown code fencing"""

    file_content: str = """import os
import shutil
import time

def cleanup_tmp():
    # Bug: Deletes entire /tmp subdirs without filtering (security/resource_management)
    base = "/tmp"
    for name in os.listdir(base):
        path = os.path.join(base, name)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except Exception:
            # Bug: Swallowing exceptions hides failures (error_handling)
            pass

def rotate_logs():
    # Bug: Inefficient rotation copies entire file repeatedly (performance)
    log = "/tmp/app.log"
    if not os.path.exists(log):
        return
    ts = int(time.time())
    shutil.copy(log, f"/tmp/app.{ts}.log")"""

    def __init__(self, tool_args: dict):
        super().__init__("", classes="agent-tool-message")
        self.tool_args = tool_args

    def compose(self) -> ComposeResult:
        file_path = self.tool_args.get("file", "")
        file_ext = file_path.split(".")[-1] if "." in file_path else "text"

        lines = self.file_content.split("\n")
        line_count = len(lines)
        line_num_width = len(str(line_count))
        max_line_width = 80

        numbered_lines = []
        for i, line in enumerate(lines, 1):
            line_num = str(i).rjust(line_num_width)

            available_width = max_line_width - line_num_width - 3
            if len(line) > available_width and available_width > 0:
                truncated_line = line[: available_width - 3] + "..."
            else:
                truncated_line = line

            numbered_lines.append(f"{line_num}  {truncated_line}")

        numbered_content = "\n".join(numbered_lines)

        markdown_content = f"```{file_ext}\n{numbered_content}\n```"

        markdown_widget = Markdown(markdown_content, classes="code-markdown")
        markdown_widget.code_dark_theme = "catppuccin-mocha"

        yield Vertical(
            Horizontal(
                Label("⚯ Cat", classes="tool-title"),
                Label(
                    f" {self.tool_args.get('file', 'unknown')}", classes="tool-content"
                ),
                classes="tool-horizontal",
            ),
            markdown_widget,
        )