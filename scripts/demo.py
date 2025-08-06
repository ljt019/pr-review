#!/usr/bin/env python3
"""
Demo script for testing all agent tools with realistic examples.
This runs the exact same tool interfaces the agent uses, with proper JSON parameters.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add src to path so we can import agent tools
sys.path.append(str(Path(__file__).parent.parent / "src"))

from agent.tools.bash import BashTool
from agent.tools.cat import CatTool
from agent.tools.grep import GrepTool
from agent.tools.ls import LsTool
from agent.tools.glob import GlobTool
from agent.tools.todowrite import TodoWriteTool
from agent.tools.todoread import TodoReadTool
from agent.sandbox import Sandbox


class ToolDemo:
    def __init__(self):
        self.tools = {
            "Bash": BashTool(),
            "Cat": CatTool(),
            "Grep": GrepTool(),
            "LS": LsTool(),
            "Glob": GlobTool(),
            "TodoWrite": TodoWriteTool(),
            "TodoRead": TodoReadTool(),
        }
        self.sandbox = None
        
    def setup_test_workspace(self):
        """Create a test workspace with sample files"""
        print("Setting up test workspace...")
        temp_dir = tempfile.mkdtemp()
        workspace_dir = Path(temp_dir) / "test_workspace"
        workspace_dir.mkdir()
        
        # Create sample project structure
        (workspace_dir / "README.md").write_text("""# Test Project
This is a sample project for testing agent tools.

## Features
- User authentication
- Database operations
- Email service

## TODO
- Add more tests
- Improve error handling
""")
        
        (workspace_dir / "app.py").write_text("""#!/usr/bin/env python3
import os
from server.auth import authenticate
from services.db import Database

def main():
    # TODO: Add configuration loading
    print("Starting application...")
    db = Database()
    if authenticate("admin", "password"):
        print("Authentication successful")
    else:
        print("Authentication failed")

if __name__ == "__main__":
    main()
""")
        
        # Create server directory
        server_dir = workspace_dir / "server"
        server_dir.mkdir()
        
        (server_dir / "__init__.py").write_text("")
        
        (server_dir / "auth.py").write_text("""def authenticate(username, password):
    # TODO: Implement real authentication
    # FIXME: Security issue - hardcoded credentials
    if username == "admin" and password == "password":
        return True
    return False

def logout():
    # TODO: Implement logout
    pass
""")
        
        (server_dir / "routes.py").write_text("""from flask import Flask, request

app = Flask(__name__)

@app.route('/api/login', methods=['POST'])
def login():
    # TODO: Add input validation
    username = request.json.get('username')
    password = request.json.get('password')
    return {"status": "ok"}

@app.route('/api/data')
def get_data():
    # FIXME: Add authentication check
    return {"data": [1, 2, 3]}
""")
        
        # Create services directory
        services_dir = workspace_dir / "services"
        services_dir.mkdir()
        
        (services_dir / "__init__.py").write_text("")
        
        (services_dir / "db.py").write_text("""class Database:
    def __init__(self):
        # TODO: Add connection pooling
        self.connection = None
    
    def query(self, sql):
        # FIXME: SQL injection vulnerability
        return f"Executing: {sql}"
""")
        
        (services_dir / "emailer.py").write_text("""def send_email(to, subject, body):
    # TODO: Implement email sending
    print(f"Sending email to {to}")
    return True
""")
        
        # Create tests directory
        tests_dir = workspace_dir / "tests"
        tests_dir.mkdir()
        
        (tests_dir / "test_auth.py").write_text("""import unittest
from server.auth import authenticate

class TestAuth(unittest.TestCase):
    def test_valid_login(self):
        self.assertTrue(authenticate("admin", "password"))
    
    def test_invalid_login(self):
        self.assertFalse(authenticate("user", "wrong"))
""")
        
        # Create config file
        (workspace_dir / "config.json").write_text(json.dumps({
            "app_name": "Test Application",
            "version": "1.0.0",
            "debug": True,
            "database": {
                "host": "localhost",
                "port": 5432
            }
        }, indent=2))
        
        # Zip the workspace
        zip_path = Path(temp_dir) / "workspace.zip"
        shutil.make_archive(str(zip_path.with_suffix("")), 'zip', str(workspace_dir))
        
        return str(zip_path)
    
    def setup_container(self):
        """Start the Docker container with test workspace"""
        workspace_path = self.setup_test_workspace()
        print(f"Created test workspace at: {workspace_path}")
        
        print("\nStarting Docker container...")
        self.sandbox = Sandbox(workspace_path)
        container_id = self.sandbox.start()
        print(f"Container started: {container_id}")
        print("="*60)
        return container_id
    
    def run_tool(self, name, params_dict):
        """Run a tool with given parameters and display results"""
        tool = self.tools[name]
        
        # Convert params dict to JSON string as agent would
        params_json = json.dumps(params_dict) if params_dict else "{}"
        
        print(f"\n### Testing {name} Tool ###")
        print(f"Parameters (JSON): {params_json}")
        print("-"*40)
        
        try:
            result = tool.call(params_json)
            print("Output:")
            print(result)
        except Exception as e:
            print(f"ERROR: {e}")
        
        print("="*60)
        return result
    
    def run_demo(self):
        """Run through all tools with example inputs"""
        print("\n" + "="*60)
        print("AGENT TOOLS DEMO - Testing All Tools")
        print("="*60)
        
        # Test 1: LS tool - list workspace
        print("\n[1] LS - List workspace root")
        self.run_tool("LS", {"path": "."})
        
        # Test 2: LS tool - list specific directory
        print("\n[2] LS - List server directory")
        self.run_tool("LS", {"path": "server"})
        
        # Test 3: Cat tool - read a file
        print("\n[3] Cat - Read server/auth.py")
        self.run_tool("Cat", {"filePath": "server/auth.py"})
        
        # Test 4: Cat tool - read with offset and limit
        print("\n[4] Cat - Read app.py with offset")
        self.run_tool("Cat", {"filePath": "app.py", "offset": 5, "limit": 10})
        
        # Test 5: Cat tool - file not found
        print("\n[5] Cat - Try non-existent file")
        self.run_tool("Cat", {"filePath": "server/missing.py"})
        
        # Test 6: Glob tool - find Python files
        print("\n[6] Glob - Find all Python files")
        self.run_tool("Glob", {"pattern": "**/*.py", "path": "."})
        
        # Test 7: Glob tool - find in specific directory
        print("\n[7] Glob - Find files in server directory")
        self.run_tool("Glob", {"pattern": "*.py", "path": "server"})
        
        # Test 8: Grep tool - search for TODO
        print("\n[8] Grep - Search for TODO comments")
        self.run_tool("Grep", {"pattern": "TODO", "directory": "."})
        
        # Test 9: Grep tool - search with file filter
        print("\n[9] Grep - Search for FIXME in Python files")
        self.run_tool("Grep", {"pattern": "FIXME", "directory": ".", "include": "*.py"})
        
        # Test 10: Grep tool - search in specific directory
        print("\n[10] Grep - Search for 'def' in server directory")
        self.run_tool("Grep", {"pattern": "def ", "directory": "server"})
        
        # Test 11: Bash tool - run simple command
        print("\n[11] Bash - List files with ls")
        self.run_tool("Bash", {"command": "ls -la"})
        
        # Test 12: Bash tool - check Python version
        print("\n[12] Bash - Check Python version")
        self.run_tool("Bash", {"command": "python3 --version"})
        
        # Test 13: Bash tool - count lines in files
        print("\n[13] Bash - Count lines in auth.py")
        self.run_tool("Bash", {"command": "wc -l server/auth.py"})
        
        # Test 14: TodoWrite tool - create todo list
        print("\n[14] TodoWrite - Create initial todo list")
        self.run_tool("TodoWrite", {
            "todos": json.dumps([
                "Review authentication code",
                "Fix SQL injection vulnerability",
                "Add input validation"
            ])
        })
        
        # Test 15: TodoRead tool - read todos
        print("\n[15] TodoRead - Read current todos")
        self.run_tool("TodoRead", {})
        
        # Test 16: TodoWrite tool - update todo status
        print("\n[16] TodoWrite - Update todo status")
        self.run_tool("TodoWrite", {
            "todos": json.dumps([
                {"content": "Review authentication code", "status": "complete"},
                {"content": "Fix SQL injection vulnerability", "status": "incomplete"},
                {"content": "Add input validation", "status": "incomplete"}
            ])
        })
        
        # Test 17: Edge cases
        print("\n[17] Edge Cases")
        
        print("\n[17a] LS - Non-existent directory")
        self.run_tool("LS", {"path": "nonexistent"})
        
        print("\n[17b] Glob - No matches")
        self.run_tool("Glob", {"pattern": "*.xyz", "path": "."})
        
        print("\n[17c] Grep - Complex regex pattern (pipe characters)")
        self.run_tool("Grep", {"pattern": "TODO|FIXME", "directory": "."})
        
        print("\n[17d] Grep - Pattern not found")
        self.run_tool("Grep", {"pattern": "NONEXISTENT", "directory": "."})
        
        print("\n[17e] Bash - Command with error")
        self.run_tool("Bash", {"command": "cat /nonexistent/file"})
        
        print("\n" + "="*60)
        print("DEMO COMPLETE")
        print("="*60)
    
    def cleanup(self):
        """Clean up the container"""
        if self.sandbox:
            print("\nCleaning up container...")
            self.sandbox.stop()
            print("Container stopped.")


def main():
    """Run the demo"""
    print("="*60)
    print("AGENT TOOLS DEMO SCRIPT")
    print("="*60)
    print("\nThis script tests all agent tools with the exact interface")
    print("and JSON parameters that the agent would use.")
    print()
    
    demo = ToolDemo()
    
    try:
        # Setup container
        demo.setup_container()
        
        # Run all tool demos
        demo.run_demo()
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always cleanup
        demo.cleanup()
        print("\nDemo finished.")


if __name__ == "__main__":
    main()