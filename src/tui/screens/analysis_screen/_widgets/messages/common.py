from textual.widgets import Markdown


def make_markdown(content: str, classes: str = "search-markdown") -> Markdown:
    md = Markdown(content, classes=classes)
    try:
        md.code_dark_theme = "catppuccin-mocha"
    except Exception:
        pass
    return md
