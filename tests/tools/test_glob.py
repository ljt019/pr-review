from typing import Generator

import pytest

from agent.tools.glob import GlobTool
from tests.tools import toy_webserver_sandbox


@pytest.fixture(scope="module", autouse=True)
def setup_sandbox() -> Generator[None, None, None]:
    """Set up shared container for all tests in this module."""
    with toy_webserver_sandbox():
        yield


def test_glob_python_files() -> None:
    glob_tool = GlobTool()
    result = glob_tool.call('{"pattern": "**/*.py"}')
    
    assert "src/app.py" in result
    assert "src/server/auth.py" in result
    assert "src/server/routes.py" in result


def test_glob_specific_directory() -> None:
    glob_tool = GlobTool()
    result = glob_tool.call('{"pattern": "*.py", "path": "src/server"}')
    
    assert "auth.py" in result
    assert "routes.py" in result
    assert "middleware.py" in result
    # Should not include files from other directories
    assert "src/app.py" not in result


def test_glob_no_matches() -> None:
    glob_tool = GlobTool()
    result = glob_tool.call('{"pattern": "*.nonexistent"}')
    
    assert "No files found matching pattern" in result or result.strip() == ""


def test_glob_all_files() -> None:
    glob_tool = GlobTool()
    result = glob_tool.call('{"pattern": "*"}')
    
    assert "README.md" in result
    assert "requirements.txt" in result


def test_glob_default_path() -> None:
    glob_tool = GlobTool()
    # Test without specifying path (should default to current directory)
    result = glob_tool.call('{"pattern": "*.md"}')
    
    assert "README.md" in result
