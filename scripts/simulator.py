#!/usr/bin/env python3
"""
Interactive Tool Simulator

A debugging interface that lets you execute the agent's tools interactively
by selecting them with number keys and providing parameters through guided prompts.
"""

import os
import sys
import json
import json5
import inspect
import tempfile
import shutil
from typing import Dict, Any, List, Optional
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

class ToolSimulator:
    def __init__(self, workspace_path: Optional[str] = None):
        self.tools = {
            1: ("Bash", BashTool(), "Execute bash commands in container"),
            2: ("Cat", CatTool(), "Read file contents with line numbers"),
            3: ("Grep", GrepTool(), "Search for patterns in files"),
            4: ("LS", LsTool(), "List directory contents in tree structure"),
            5: ("Glob", GlobTool(), "Find files matching glob patterns"),
            6: ("TodoWrite", TodoWriteTool(), "Update/manage todo list"),
            7: ("TodoRead", TodoReadTool(), "Read current todo list"),
        }
        
        self.sandbox = None
        self.workspace_path = workspace_path
        self.last_ls_output = None  # Store last ls output for reference
        self.recent_files = []  # Store recently seen files
        
        # Check if container is already available
        self.container_id = os.environ.get("SNIFF_CONTAINER_ID")
        if not self.container_id:
            print("No existing container found. Will create one when needed.")
        else:
            print(f"Connected to existing container: {self.container_id[:12]}...")

    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_menu(self):
        """Display the main tool selection menu"""
        self.clear_screen()
        print("="*60)
        print("AGENT TOOL SIMULATOR")
        print("="*60)
        print("Select a tool to execute:")
        print()
        
        for num, (name, tool, description) in self.tools.items():
            print(f"  {num}. {name:8} - {description}")
        
        print(f"\n  0. Exit")
        print("="*60)

    def get_tool_parameters(self, tool) -> str:
        """Interactively collect parameters for a tool and return as JSON5 string"""
        tool_name = tool.__class__.__name__
        
        # Show simplified header
        print(f"\n[{tool_name}]")
        
        # Show context hints for file-related tools
        if tool_name in ["CatTool", "GrepTool"] and self.recent_files:
            print("\nRecent files from last ls/glob:")
            # Show up to 10 recent files
            for i, file in enumerate(self.recent_files[:10], 1):
                print(f"  {file}")
            if len(self.recent_files) > 10:
                print(f"  ... and {len(self.recent_files) - 10} more")
            print()
        
        params = {}
        
        for param in tool.parameters:
            param_name = param["name"]
            param_type = param["type"]
            param_desc = param["description"]
            is_required = param["required"]
            
            # Get user input with streamlined prompts
            value = self._prompt_for_parameter(param_name, param_type, is_required, tool_name)
            
            if value is not None:
                params[param_name] = value
        
        # Convert to JSON5 format that ParameterParser expects
        if not params:
            return "{}"
        
        return json.dumps(params)

    def _prompt_for_parameter(self, name: str, param_type: str, required: bool, tool_name: str):
        """Prompt user for a specific parameter with improved UX"""
        
        # Build prompt with better defaults and examples
        if tool_name == "LsTool" and name == "path":
            prompt = f"{name} [default: current dir, or enter path like 'server']: "
            default_value = "."
        elif tool_name == "CatTool" and name == "filePath":
            prompt = f"file path (e.g., 'server/auth.py', 'app.py'): "
            default_value = None
        elif name == "command":
            prompt = "command: "
            default_value = None
        elif name == "pattern":
            if tool_name == "GrepTool":
                prompt = "search pattern: "
            else:
                prompt = "file pattern: "
            default_value = None
        elif name == "directory":
            prompt = f"{name} [default: current dir]: "
            default_value = "."
        elif name == "path" and param_type == "string":
            prompt = f"{name} [default: current dir]: "
            default_value = "."
        elif name == "todos":
            print("Enter todos (JSON array format):")
            print('  New list: ["task 1", "task 2"]')
            print('  Updates: [{"content": "task 1", "status": "complete"}]')
            prompt = "todos: "
            default_value = None
        elif name == "offset":
            prompt = f"{name} [default: 0]: "
            default_value = 0
        elif name == "limit":
            prompt = f"{name} [default: 2000]: "
            default_value = 2000
        elif name == "include":
            prompt = f"{name} (e.g., *.py): "
            default_value = None
        elif name == "ignore":
            prompt = f"{name} (comma-separated): "
            default_value = None
        else:
            prompt = f"{name}: "
            default_value = None
        
        # Add required indicator
        if required and default_value is None:
            prompt = "* " + prompt
        elif not required:
            prompt = "  " + prompt
        
        while True:
            try:
                user_input = input(prompt).strip()
                
                # Handle empty input
                if not user_input:
                    if required and default_value is None:
                        print("    ^ Required field")
                        continue
                    elif default_value is not None:
                        return default_value
                    else:
                        return None
                
                # Type conversion
                if param_type == "integer":
                    return int(user_input)
                elif param_type == "array":
                    # Handle comma-separated input for ignore patterns
                    if name == "ignore":
                        return [item.strip() for item in user_input.split(",")]
                    else:
                        # Try to parse as JSON array first
                        try:
                            parsed = json5.loads(user_input)
                            if isinstance(parsed, list):
                                return parsed
                        except:
                            pass
                        # Fall back to comma-separated
                        return [item.strip() for item in user_input.split(",")]
                else:  # string
                    # For todos parameter, validate JSON format
                    if name == "todos":
                        try:
                            parsed = json5.loads(user_input)
                            return json.dumps(parsed)  # Return as JSON string
                        except Exception as e:
                            print(f"    Invalid JSON: {e}")
                            continue
                    
                    # Normalize paths for file/directory parameters
                    if name in ["filePath", "path", "directory"]:
                        # Convert relative paths to absolute container paths
                        if user_input and not user_input.startswith('/'):
                            # Special case: "." should map to /workspace
                            if user_input == ".":
                                return "/workspace"
                            # Otherwise prepend /workspace/
                            return f"/workspace/{user_input}"
                    
                    return user_input
                    
            except ValueError as e:
                print(f"    Invalid {param_type}: {e}")
            except KeyboardInterrupt:
                print("\n    Cancelled.")
                return None

    def _format_params(self, params: Dict[str, Any]) -> str:
        """Format parameters as JSON5 string expected by tools"""
        if not params:
            return "{}"
        return json.dumps(params)
    
    def _extract_files_from_output(self, output: str):
        """Extract file paths from ls or glob output"""
        self.recent_files = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            # Skip empty lines, directories (ending with /), and info messages
            if not line or line.endswith('/') or line.startswith('(') or line.startswith('.'):
                continue
            
            # For ls output, extract file names with proper indentation handling
            if '  ' in line:
                # This is likely from ls with indentation
                file_part = line.lstrip()
                if not file_part.endswith('/') and file_part not in ['', '.']:
                    # Try to reconstruct the path from indentation
                    self.recent_files.append(file_part)
            else:
                # This is likely from glob - full paths
                if '.' in line and not line.startswith('('):
                    self.recent_files.append(line)
        
        # Also extract files from tree structure if present
        current_dir = ""
        for line in lines:
            # Check if this is a directory line in tree output
            if line and not line.startswith(' ') and not line.startswith('('):
                current_dir = line.strip()
                if current_dir.endswith('/'):
                    current_dir = current_dir[:-1]
            elif '  ' in line and not line.strip().endswith('/'):
                # This is a file under a directory
                file_name = line.strip()
                if current_dir and current_dir != '.':
                    full_path = f"{current_dir}/{file_name}"
                else:
                    full_path = file_name
                
                if full_path not in self.recent_files and '.' in full_path:
                    self.recent_files.append(full_path)

    def execute_tool(self, tool_num: int):
        """Execute the selected tool"""
        if tool_num not in self.tools:
            print("ERROR: Invalid tool selection.")
            input("\nPress Enter to continue...")
            return
        
        tool_name, tool_instance, _ = self.tools[tool_num]
        
        try:
            # Clear screen for tool execution
            self.clear_screen()
            print("="*60)
            print(f"EXECUTING: {tool_name}")
            print("="*60)
            
            # Get parameters interactively
            params = self.get_tool_parameters(tool_instance)
            
            # Clear screen again before showing results
            self.clear_screen()
            print("="*60)
            print(f"TOOL OUTPUT: {tool_name}")
            print("="*60)
            
            if params and params != "{}":
                print(f"Parameters: {params}")
                print("-" * 60)
            
            print("Executing...\n")
            
            # Execute the tool
            result = tool_instance.call(params)
            
            # Store file list if this was an ls or glob command
            if tool_name in ["LS", "Glob"]:
                self._extract_files_from_output(result)
            
            # Display result with better formatting
            print(result)
            print("\n" + "="*60)
            input("\nPress Enter to return to menu...")
            
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            input("\nPress Enter to return to menu...")
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
            input("\nPress Enter to return to menu...")

    def setup_container(self):
        """Set up a Docker container for testing"""
        if os.environ.get("SNIFF_CONTAINER_ID"):
            print("Container already available.")
            return True
            
        try:
            self.clear_screen()
            print("="*60)
            print("DOCKER CONTAINER SETUP")
            print("="*60)
            print("\nNo container found. Please provide a workspace to test with:")
            print("\n  1. Use a sample workspace")
            print("  2. Provide a zip file path")
            print("  3. Provide a directory path to zip")
            
            choice = input("\nSelect option (1-3): ").strip()
            
            if choice == "1":
                # Create a minimal sample workspace
                temp_dir = tempfile.mkdtemp()
                sample_dir = Path(temp_dir) / "sample_workspace"
                sample_dir.mkdir()
                
                # Create some sample files
                (sample_dir / "README.md").write_text("# Sample Project\nThis is a test workspace.")
                (sample_dir / "main.py").write_text("def main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()")
                src_dir = sample_dir / "src"
                src_dir.mkdir()
                (src_dir / "utils.py").write_text("def helper():\n    return 42")
                
                # Zip it
                zip_path = Path(temp_dir) / "workspace.zip"
                shutil.make_archive(str(zip_path.with_suffix("")), 'zip', str(sample_dir))
                workspace_path = str(zip_path)
                
            elif choice == "2":
                workspace_path = input("Enter zip file path: ").strip()
                if not Path(workspace_path).exists():
                    print(f"ERROR: File not found: {workspace_path}")
                    return False
                    
            elif choice == "3":
                dir_path = input("Enter directory path: ").strip()
                if not Path(dir_path).is_dir():
                    print(f"ERROR: Directory not found: {dir_path}")
                    return False
                
                # Create a zip file
                temp_dir = tempfile.mkdtemp()
                zip_path = Path(temp_dir) / "workspace.zip"
                shutil.make_archive(str(zip_path.with_suffix("")), 'zip', dir_path)
                workspace_path = str(zip_path)
            else:
                print("Invalid choice.")
                return False
            
            # Start the sandbox
            print(f"\nStarting container with workspace: {workspace_path}")
            self.sandbox = Sandbox(workspace_path)
            container_id = self.sandbox.start()
            print(f"\nContainer started successfully: {container_id}")
            input("\nPress Enter to continue...")
            return True
            
        except Exception as e:
            print(f"\nERROR: Failed to set up container: {e}")
            input("\nPress Enter to continue...")
            return False

    def cleanup(self):
        """Clean up the sandbox if we created one"""
        if self.sandbox:
            print("\nCleaning up container...")
            self.sandbox.stop()
            self.sandbox = None

    def run(self):
        """Main interactive loop"""
        self.clear_screen()
        print("="*60)
        print("INTERACTIVE AGENT TOOL SIMULATOR")
        print("="*60)
        print("\nThis tool lets you test agent tools in the container environment.")
        input("\nPress Enter to start...")
        
        # Ensure container is available
        if not os.environ.get("SNIFF_CONTAINER_ID"):
            if not self.setup_container():
                print("\nCannot continue without container. Exiting.")
                return
        
        try:
            while True:
                try:
                    self.display_menu()
                    
                    # Get user selection
                    try:
                        choice = input("\nSelect tool (0-7): ").strip()
                        if not choice:
                            continue
                        
                        choice = int(choice)
                        
                        if choice == 0:
                            print("\nGoodbye!")
                            break
                        elif choice in self.tools:
                            self.execute_tool(choice)
                        else:
                            print(f"ERROR: Invalid choice: {choice}")
                            
                    except ValueError:
                        print("ERROR: Please enter a valid number.")
                        
                except KeyboardInterrupt:
                    print("\n\nGoodbye!")
                    break
                except EOFError:
                    print("\n\nGoodbye!")
                    break
        finally:
            self.cleanup()

def main():
    """Entry point"""
    simulator = ToolSimulator()
    simulator.run()

if __name__ == "__main__":
    main()