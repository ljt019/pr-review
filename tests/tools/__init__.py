"""
Utilities for testing agent tools with sandboxed environments.
"""

import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

# Add src to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from agent.sandbox import Sandbox


@contextmanager
def toy_webserver_sandbox():
    """
    Context manager that sets up a sandbox with the toy-webserver.zip mounted.

    Usage:
        with toy_webserver_sandbox() as sandbox:
            # Use tools here
            cat_tool = CatTool()
            result = cat_tool.call('{"filePath": "app.py"}')

    Returns:
        Sandbox: Active sandbox instance with toy-webserver mounted
    """
    toy_webserver_path = PROJECT_ROOT / "assets" / "toy-webserver.zip"

    if not toy_webserver_path.exists():
        raise FileNotFoundError(f"toy-webserver.zip not found at {toy_webserver_path}")

    sandbox = Sandbox(str(toy_webserver_path))

    try:
        _container_id = sandbox.start()
        yield sandbox
    finally:
        sandbox.stop()


@contextmanager
def custom_sandbox(workspace_files: dict):
    """
    Context manager that creates a temporary sandbox with custom files.

    Args:
        workspace_files: Dict mapping file paths to content
                        e.g., {"app.py": "print('hello')", "src/utils.py": "def helper(): pass"}

    Usage:
        with custom_sandbox({"app.py": "print('hello')", "config.json": '{"debug": true}'}) as sandbox:
            # Use tools here
            ls_tool = LsTool()
            result = ls_tool.call('{"path": "."}')
    """
    # Create temporary workspace
    temp_dir = tempfile.mkdtemp()
    workspace_dir = Path(temp_dir) / "workspace"
    workspace_dir.mkdir()

    try:
        # Create all files and directories
        for file_path, content in workspace_files.items():
            full_path = workspace_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        # Create zip file
        zip_path = Path(temp_dir) / "workspace.zip"
        shutil.make_archive(str(zip_path.with_suffix("")), "zip", str(workspace_dir))

        # Start sandbox
        sandbox = Sandbox(str(zip_path))
        container_id = sandbox.start()
        yield sandbox

    finally:
        if "sandbox" in locals():
            sandbox.stop()
        # Cleanup temp files
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass  # Best effort cleanup


def get_toy_webserver_path() -> Path:
    """Get the path to the toy-webserver.zip asset."""
    return PROJECT_ROOT / "assets" / "toy-webserver.zip"


def setup_test_environment():
    """
    Set up the test environment by adding src to Python path.
    Call this at the start of test files if needed.
    """
    if str(PROJECT_ROOT / "src") not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
