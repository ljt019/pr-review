"""
BugBot - Simple, reliable code review bot using pydantic-ai.
"""

import warnings

from .bug_bot import BugBot

# Suppress third-party library warnings that we can't control
warnings.filterwarnings(
    "ignore", message="pkg_resources is deprecated", category=UserWarning
)

# Main BugBot class is now the clean SimpleBugBot implementation
BugBot = BugBot

# For backward compatibility
__all__ = ["BugBot"]
