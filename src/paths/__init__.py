"""
This module defines all project paths relative to the project root directory.
"""

from pathlib import Path

_CURRENT_FILE = Path(__file__).resolve()
_BUG_BOT_DIR = _CURRENT_FILE.parent  # src/bug_bot/
_SRC_DIR = _BUG_BOT_DIR.parent       # src/
PROJECT_ROOT = _SRC_DIR.parent       # project root

# Main Project Non-Code Directories 
EVALS_DIR = PROJECT_ROOT / "evals"

# Source Code Directories
SRC_DIR = PROJECT_ROOT / "src"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# bug_bot
BUG_BOT_DIR = SRC_DIR / "bug_bot"
TOOLS_DIR = BUG_BOT_DIR / "tools"
DOCKER_DIR = BUG_BOT_DIR / "docker" # Source code for bot containers, not Docker config

# evaluation
EVALUATION_DIR = SRC_DIR / "evaluation"

# paths
PATHS_DIR = SRC_DIR / "paths"

# server
SERVER_DIR = SRC_DIR / "server"
ROUTERS_DIR = SERVER_DIR / "routers"


## UTILITY FUNCTIONS ## 

def get_src_path(*parts: str) -> Path:
    """Get full path to a file in the src directory."""
    return SRC_DIR.joinpath(*parts)

def get_script_path(filename: str) -> Path:
    """Get full path to a script file."""
    return SCRIPTS_DIR / filename

def get_tool_path(filename: str) -> Path:
    """Get full path to a tool file."""
    return TOOLS_DIR / filename

def get_docker_path(filename: str) -> Path:
    """Get full path to a docker (bot container) source file."""
    return DOCKER_DIR / filename

def get_eval_path(filename: str) -> Path:
    """Get full path to an evaluation file."""
    return EVALS_DIR / filename