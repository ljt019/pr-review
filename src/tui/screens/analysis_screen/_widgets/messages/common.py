import json
from typing import Any, Dict, Iterable, Optional, Union

from textual.widgets import Markdown


def make_markdown(
    content: str, classes: str = "search-markdown", bullets: list[str] | None = None
) -> Markdown:
    md = Markdown(content, classes=classes)
    try:
        md.code_dark_theme = "catppuccin-mocha"
        # Ensure no code-fence line numbers / gutter are shown by the Markdown widget
        # Different Textual versions expose different flags; guard with try/except
        try:
            md.show_line_numbers = False  # newer API
        except Exception:
            pass
        try:
            md.code_line_numbers = False  # alternative API name
        except Exception:
            pass
        try:
            md.line_numbers = False  # fallback attribute
        except Exception:
            pass
        if bullets:
            try:
                md.BULLETS = bullets
            except Exception:
                pass
    except Exception:
        pass
    return md


def subtitle_from_args(
    arguments: Union[str, Dict[str, Any], None],
    keys: Iterable[str],
    quote: bool = False,
    default: str = "",
) -> str:
    """Extract a subtitle value from arguments by first-present key.

    If quote=True and a value is present, wrap it in double quotes.
    """
    try:
        from tui.utils.args import get_arg
    except Exception:
        return default

    value = get_arg(arguments, keys, default)
    if value is None or value == "":
        return default
    return f' "{value}"' if quote else f" {value}"


def parse_json_block(result: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse an embedded JSON block delimited by <!--JSON-->...<!--/JSON-->."""
    if not result:
        return None
    try:
        start_token = "<!--JSON-->"
        end_token = "<!--/JSON-->"
        start = result.find(start_token)
        end = result.find(end_token)
        if start == -1 or end == -1 or end <= start:
            return None
        json_str = result[start + len(start_token) : end].strip()
        return json.loads(json_str)
    except Exception:
        return None
