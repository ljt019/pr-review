"""
Pytest configuration and shared fixtures.
"""
import sys
from pathlib import Path

# Add src to Python path for test imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))