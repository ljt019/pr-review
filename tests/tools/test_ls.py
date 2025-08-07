from typing import Generator
import pytest

from agent.tools.ls import LsTool
from tests.tools import toy_webserver_sandbox


@pytest.fixture(scope="module", autouse=True)
def setup_sandbox() -> Generator[None, None, None]:
    """Set up shared container for all tests in this module."""
    with toy_webserver_sandbox():
        yield


def test_ls_no_path() -> None:
    ls_tool = LsTool()
    result = ls_tool.call('{}')
    assert "src/" in result  # Directory listing shows src/
    assert "README.md" in result  # Root file should be visible


def test_ls_with_path() -> None:
    ls_tool = LsTool()
    result = ls_tool.call('{"path": "src"}')
    assert "app.py" in result  # File in src directory
    assert "legacy/" in result  # Subdirectory in src


def test_ls_with_sub_path() -> None:
    ls_tool = LsTool()
    result = ls_tool.call('{"path": "src/server"}')
    assert "auth.py" in result
    assert "app.py" not in result
