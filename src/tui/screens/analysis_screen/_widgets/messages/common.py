from textual.widgets import Markdown


def make_markdown(content: str, classes: str = "search-markdown") -> Markdown:
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
    except Exception:
        pass
    return md
