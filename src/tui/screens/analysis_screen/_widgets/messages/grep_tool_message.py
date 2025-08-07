"""Grep tool message widget"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Static

from agent.messaging import ToolExecutionMessage
from tui.utils.args import get_arg

from .common import make_markdown


class GrepToolMessage(Static):
    """Tool call made by the agent to *grep* files / patterns with polished search results"""

    example_matches = [
        ("src/agent/agent.py", 15, "def run_analysis(self):"),
        ("src/agent/agent.py", 28, "    analysis_results = []"),
        (
            "src/tui/services/message_renderer.py",
            45,
            "def render_analysis_message(self):",
        ),
        ("src/tui/services/message_renderer.py", 67, "    self.analysis_count += 1"),
        ("README.md", 12, "## Analysis Features"),
        ("README.md", 34, "Run analysis with: `sniff analyze`"),
        ("pyproject.toml", 8, 'name = "analysis-tool"'),
        ("src/utils/helpers.py", 23, "def analyze_code_quality():"),
    ]

    def __init__(self, tool_message: ToolExecutionMessage, search_results=None):
        super().__init__("", classes="agent-tool-message")
        self.tool_message = tool_message
        if search_results is not None:
            self.search_results = search_results
        elif tool_message.result and tool_message.success:
            # Parse the grep result into the expected format
            self.search_results = self._parse_grep_output(tool_message.result)
        else:
            self.search_results = self.example_matches

    def compose(self) -> ComposeResult:
        pattern = get_arg(
            self.tool_message.arguments, ["pattern", "search_pattern"], ""
        )
        match_count = len(self.search_results)

        files_dict = {}
        for file_path, line_num, content in self.search_results:
            if file_path not in files_dict:
                files_dict[file_path] = []
            files_dict[file_path].append((line_num, content.strip()))

        md_lines = [
            f"\n**{match_count} matches** found across **{len(files_dict)} files**",
            "",
        ]

        for file_path, matches in files_dict.items():
            md_lines.append(f"- **{file_path}**")
            for line_num, content in matches:
                md_lines.append(f"  - Line **{line_num}**: `{content}`")
            md_lines.append("")

        markdown_content = "\n".join(md_lines)

        markdown_widget = make_markdown(markdown_content, classes="search-markdown")
        try:
            markdown_widget.BULLETS = ["🖹 ", "• ", "‣ ", "⭑ ", "⭑ "]
        except Exception:
            pass

        yield Vertical(
            Horizontal(
                Label("⌕ Grep", classes="tool-title"),
                Label(f' "{pattern}"', classes="tool-content"),
                classes="tool-horizontal",
            ),
            markdown_widget,
        )

    def _parse_grep_output(self, grep_output: str) -> list:
        """Parse grep output into (file_path, line_number, content) tuples."""
        results = []
        for line in grep_output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # Try to parse grep output format: filename:line_number:content
            parts = line.split(":", 2)
            if len(parts) >= 3:
                try:
                    file_path = parts[0]
                    line_number = int(parts[1])
                    content = parts[2]
                    results.append((file_path, line_number, content))
                except ValueError:
                    # If line number parsing fails, treat as simple match
                    results.append((line, 0, line))
            else:
                # Fallback for non-standard format
                results.append((line, 0, line))

        return results
