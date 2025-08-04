"""
This module defines all project paths relative to the project root directory.
"""

from pathlib import Path

_CURRENT_FILE = Path(__file__).resolve()
_PATHS_DIR = _CURRENT_FILE.parent  # src/paths/
_SRC_DIR = _PATHS_DIR.parent  # src/
PROJECT_ROOT = _SRC_DIR.parent  # project root

# Main Project Non-Code Directories
EVALS_DIR = PROJECT_ROOT / "evals"

# Source Code Directories
SRC_DIR = PROJECT_ROOT / "src"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# agent
AGENT_DIR = SRC_DIR / "agent"
TOOLS_DIR = AGENT_DIR / "tools"
UTILS_DIR = AGENT_DIR / "utils"

# evaluation
EVALUATION_DIR = AGENT_DIR / "evaluation"

# paths
PATHS_DIR = SRC_DIR / "paths"

# tui
TUI_DIR = SRC_DIR / "tui"
WIDGETS_DIR = TUI_DIR / "widgets"
SCREENS_DIR = TUI_DIR / "screens"

# assets
ASSETS_DIR = PROJECT_ROOT / "assets"

## UTILITY FUNCTIONS ##

# Directory mapping for the generic get_path function
_DIRECTORY_MAP = {
    "src": SRC_DIR,
    "scripts": SCRIPTS_DIR,
    "tools": TOOLS_DIR,
    "utils": UTILS_DIR,
    "evals": EVALS_DIR,
    "tui": TUI_DIR,
    "widgets": WIDGETS_DIR,
    "screens": SCREENS_DIR,
    "assets": ASSETS_DIR,
    "agent": AGENT_DIR,
    "evaluation": EVALUATION_DIR,
    "paths": PATHS_DIR,
}


def get_path(directory: str, *parts: str) -> Path:
    """Get full path to a file in a specified project directory.
    
    Args:
        directory: The directory name (e.g., 'tools', 'utils', 'screens')
        *parts: Path parts to join (can be multiple subdirectories and filename)
        
    Returns:
        Path object to the specified file
        
    Raises:
        ValueError: If the directory name is not recognized
    """
    if directory not in _DIRECTORY_MAP:
        raise ValueError(f"Unknown directory: {directory}. Valid options: {list(_DIRECTORY_MAP.keys())}")
    
    return _DIRECTORY_MAP[directory].joinpath(*parts)


# Legacy function wrappers for backwards compatibility
def get_src_path(*parts: str) -> Path:
    """Get full path to a file in the src directory."""
    return SRC_DIR.joinpath(*parts)


def get_script_path(filename: str) -> Path:
    """Get full path to a script file."""
    return get_path("scripts", filename)


def get_tool_path(filename: str) -> Path:
    """Get full path to a tool file."""
    return get_path("tools", filename)


def get_utils_path(filename: str) -> Path:
    """Get full path to a utils file."""
    return get_path("utils", filename)


def get_eval_path(filename: str) -> Path:
    """Get full path to an evaluation file."""
    return get_path("evals", filename)


def get_tui_path(filename: str) -> Path:
    """Get full path to a tui file."""
    return get_path("tui", filename)


def get_widget_path(filename: str) -> Path:
    """Get full path to a widget file."""
    return get_path("widgets", filename)


def get_screen_path(filename: str) -> Path:
    """Get full path to a screen file."""
    return get_path("screens", filename)


def get_assets_path(filename: str) -> Path:
    """Get full path to an asset file."""
    return get_path("assets", filename)
