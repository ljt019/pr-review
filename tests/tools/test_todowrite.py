from typing import Generator

import pytest

from agent.tools.todowrite import TodoWriteTool
from tests.tools import toy_webserver_sandbox


@pytest.fixture(scope="module", autouse=True)
def setup_sandbox() -> Generator[None, None, None]:
    """Set up shared container for all tests in this module."""
    with toy_webserver_sandbox():
        yield


def test_todowrite_create_initial_list() -> None:
    todowrite_tool = TodoWriteTool()
    result = todowrite_tool.call('{"todos": ["Task 1", "Task 2", "Task 3"]}')
    
    assert "Updated todo list" in result
    assert "3 total" in result


def test_todowrite_update_status() -> None:
    todowrite_tool = TodoWriteTool()
    # First create initial todos
    todowrite_tool.call('{"todos": ["Complete task", "Pending task"]}')
    
    # Then update their status (use correct status values)
    result = todowrite_tool.call('{"todos": [{"content": "Complete task", "status": "complete"}, {"content": "Pending task", "status": "incomplete"}]}')
    
    assert "Updated todo list" in result


def test_todowrite_mixed_formats() -> None:
    todowrite_tool = TodoWriteTool()
    # Test mixing string todos with object todos (use correct status values)
    result = todowrite_tool.call('{"todos": ["New task", {"content": "Existing task", "status": "complete"}]}')
    
    assert "Updated todo list" in result


def test_todowrite_invalid_json() -> None:
    todowrite_tool = TodoWriteTool()
    result = todowrite_tool.call('{"todos": "not an array"}')
    
    # Check for the actual error message
    assert "Error" in result and ("array" in result or "JSON" in result)


def test_todowrite_missing_todos_param() -> None:
    todowrite_tool = TodoWriteTool()
    result = todowrite_tool.call('{}')
    
    assert "Error" in result
