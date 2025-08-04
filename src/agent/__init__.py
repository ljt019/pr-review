"""
SniffAgent - Simple, reliable code review agent using qwen models.
"""

import warnings

from .agent import SniffAgent

# Suppress third-party library warnings that we can't control
warnings.filterwarnings(
    "ignore", message="pkg_resources is deprecated", category=UserWarning
)

# Export the main class
__all__ = ["SniffAgent"]
