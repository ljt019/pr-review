"""Grep tool message widget"""

from textual.widgets import Static

from agent.messaging import ToolExecutionMessage

from .base_tool_message import BaseToolMessage
from .common import make_markdown, parse_json_block, subtitle_from_args


class GrepToolMessage(BaseToolMessage):
    """Tool call made by the agent to grep files / patterns with polished search results"""

    def get_title(self) -> str:
        return "⌕ Grep"

    def get_subtitle(self) -> str:
        return subtitle_from_args(
            self.tool_message.arguments,
            ["pattern", "search_pattern"],
            quote=True,
            default="",
        )

    def create_body(self) -> Static:
        # Prefer structured JSON block if available
        payload = parse_json_block(self.tool_message.result)
        if payload and isinstance(payload, dict) and "matches" in payload:
            # expected: { matches: [ { file, line, content }, ... ] }
            matches = payload.get("matches", [])
            files_dict = {}
            for m in matches:
                fp = m.get("file", "?")
                ln = int(m.get("line", 0) or 0)
                ct = str(m.get("content", "")).strip()
                files_dict.setdefault(fp, []).append((ln, ct))

            md_lines = [
                f"\n**{sum(len(v) for v in files_dict.values())} matches** found across **{len(files_dict)} files**",
                "",
            ]
            for file_path, items in files_dict.items():
                md_lines.append(f"- **{file_path}**")
                for line_num, content in items:
                    md_lines.append(f"  - Line **{line_num}**: `{content}`")
                md_lines.append("")
            markdown_content = "\n".join(md_lines)
            return make_markdown(
                markdown_content,
                classes="search-markdown",
                bullets=["🖹 ", "• ", "‣ ", "⭑ ", "⭑ "],
            )

        return make_markdown("No results.", classes="search-markdown")
