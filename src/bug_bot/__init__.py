"""
BugBot - Simple, reliable code review bot using pydantic-ai.
"""
import warnings

# Suppress third-party library warnings that we can't control
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

from .bug_bot import BugBot

# Main BugBot class is now the clean SimpleBugBot implementation
BugBot = BugBot

# For backward compatibility
__all__ = ["BugBot"]