from typing import Generator

import pytest

from agent.tools.cat import CatTool
from tests.tools import toy_webserver_sandbox


@pytest.fixture(scope="module", autouse=True)
def setup_sandbox() -> Generator[None, None, None]:
    """Set up shared container for all tests in this module."""
    with toy_webserver_sandbox():
        yield


def test_cat_basic_file() -> None:
    cat_tool = CatTool()
    result = cat_tool.call('{"filePath": "README.md"}')
    
    # Strip line numbers for cleaner assertions
    content = "\n".join(line.split("→", 1)[1] if "→" in line else line for line in result.split("\n"))
    
    assert "# Toy Python Web Server with Planted Bugs" in content
    assert "Endpoints:" in content
    assert "GET /health" in content
    assert "POST /items" in content


def test_cat_python_file() -> None:
    cat_tool = CatTool()
    result = cat_tool.call('{"filePath": "src/app.py"}')
    
    # Strip line numbers for cleaner assertions
    content = "\n".join(line.split("→", 1)[1] if "→" in line else line for line in result.split("\n"))
    
    assert "from server.routes import create_app" in content
    assert "debug=True in production-like code" in content
    assert "app.run(host=" in content


def test_cat_with_offset_limit() -> None:
    cat_tool = CatTool()
    result = cat_tool.call('{"filePath": "src/server/routes.py", "offset": 5, "limit": 10}')
    
    # Strip line numbers for cleaner assertions
    content = "\n".join(line.split("→", 1)[1] if "→" in line else line for line in result.split("\n"))
    
    # Should start from line 6 (offset 5) and show 10 lines
    assert "from utils.validators import is_valid_email" in content
    assert "def create_app():" in content
    assert "app = Flask(__name__)" in content
    # Should show message about file having more lines
    assert "File has" in result and "total lines" in result


def test_cat_nonexistent_file() -> None:
    cat_tool = CatTool()
    result = cat_tool.call('{"filePath": "nonexistent.txt"}')
    
    assert "Error: File not found: nonexistent.txt" in result
