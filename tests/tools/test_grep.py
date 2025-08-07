from typing import Generator

import pytest

from agent.tools.grep import GrepTool
from tests.tools import toy_webserver_sandbox


@pytest.fixture(scope="module", autouse=True)
def setup_sandbox() -> Generator[None, None, None]:
    """Set up shared container for all tests in this module."""
    with toy_webserver_sandbox():
        yield


def test_grep_no_pattern() -> None:
    grep_tool = GrepTool()
    result = grep_tool.call("{}")

    assert "requirements.txt" in result
    assert "src/tasks/__init__.py" in result


def test_grep_with_simple_pattern() -> None:
    grep_tool = GrepTool()
    result = grep_tool.call('{"pattern": "print"}')

    assert "src/server/middleware.py" in result
    assert "app.py" not in result


def test_grep_with_multiple_patterns() -> None:
    grep_tool = GrepTool()
    result = grep_tool.call('{"pattern": "print|secret|test"}')

    assert "tests/test_placeholder.py" in result
    assert "src/server/middleware.py" in result
    assert "src/server/routes.py" in result
    assert "src/tasks/__init__.py" not in result
