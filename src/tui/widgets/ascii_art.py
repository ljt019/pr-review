"""ASCII Art widget for Sniff TUI"""

from textual.widgets import Static
from PIL import Image
import shutil
from paths import PROJECT_ROOT


class ASCIIArt(Static):
    """Widget to display ASCII art"""
    
    def __init__(self, path: str = None):
        super().__init__()
        self.art_text = self.create_banner(path)
    
    def create_banner(self, path: str = None) -> str:
        """Generate ASCII art from image"""
        if path is None:
            path = str(PROJECT_ROOT / "assets" / "sniffer.png")
            
        try:
            from ascii_magic import AsciiArt
            img = Image.open(path)
            img.thumbnail((160, 160), Image.LANCZOS)
            
            term_cols = shutil.get_terminal_size().columns
            cols = max(20, (term_cols - 4) // 3)
            
            art = AsciiArt.from_pillow_image(img)
            return art.to_ascii(columns=cols, monochrome=True)
        except Exception as e:
            try:
                with open(str(PROJECT_ROOT / "assets" / "art.txt"), 'r') as f:
                    return f.read()
            except FileNotFoundError:
                return f"Sniff TUI\n\n[Banner error: {e}]"
    
    def render(self) -> str:
        return self.art_text