from typing import Generator

import pytest

from agent.tools.todoread import TodoReadTool
from agent.tools.todowrite import TodoWriteTool
from tests.tools import toy_webserver_sandbox


@pytest.fixture(scope="module", autouse=True)
def setup_sandbox() -> Generator[None, None, None]:
    """Set up shared container for all tests in this module."""
    with toy_webserver_sandbox():
        yield


def test_todoread_empty_list() -> None:
    todoread_tool = TodoReadTool()
    result = todoread_tool.call('{}')
    
    assert "No todos currently exist" in result


def test_todoread_with_todos() -> None:
    # First create some todos
    todowrite_tool = TodoWriteTool()
    todowrite_tool.call('{"todos": ["Task 1", "Task 2", "Task 3"]}')
    
    # Then read them
    todoread_tool = TodoReadTool()
    result = todoread_tool.call('{}')
    
    assert "Task 1" in result
    assert "Task 2" in result
    assert "Task 3" in result
    # Check for the actual output format (uses [] for pending status)
    assert "[]" in result or "pending" in result


def test_todoread_no_parameters() -> None:
    todoread_tool = TodoReadTool()
    # Should work with completely empty input
    result = todoread_tool.call('')
    
    # Should not error, will show current todos or empty message
    assert "Error" not in result


def test_todoread_rejects_parameters() -> None:
    todoread_tool = TodoReadTool()
    result = todoread_tool.call('{"invalid": "parameter"}')
    
    assert "Error: This tool takes no parameters" in result
