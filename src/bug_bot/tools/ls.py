import json5
import os
from qwen_agent.tools.base import BaseTool, register_tool

from bug_bot.tools import run_in_container, load_tool_description

# Common development directories to ignore for cleaner output
IGNORE_PATTERNS = [
    "node_modules/",
    "__pycache__/",
    ".git/",
    "dist/",
    "build/",
    "target/",
    "vendor/",
    "bin/",
    "obj/",
    ".idea/",
    ".vscode/",
    ".zig-cache/",
    "zig-out",
    ".coverage",
    "coverage/",
    "tmp/",
    "temp/",
    ".cache/",
    "cache/",
    "logs/",
    ".venv/",
    "venv/",
    "env/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".tox/",
    ".DS_Store",
    "Thumbs.db",
]

LIMIT = 100

@register_tool('ls')
class LsTool(BaseTool):
    description = load_tool_description('ls')
    parameters = [{
        'name': 'directory',
        'type': 'string',
        'description': 'Directory path to list (defaults to current directory)',
        'required': False
    }]

    def call(self, params: str, **kwargs) -> str:
        try:
            parsed_params = json5.loads(params)
            directory = parsed_params.get('directory', '.')
            
            self._pretty_print_tool(directory)
            
            # Use find to get all files recursively, excluding ignored patterns
            ignore_conditions = []
            for pattern in IGNORE_PATTERNS:
                if pattern.endswith('/'):
                    # Directory pattern
                    ignore_conditions.append(f'-path "*/{pattern}*" -prune -o')
                else:
                    # File pattern
                    ignore_conditions.append(f'-name "{pattern}" -prune -o')
            
            ignore_clause = ' '.join(ignore_conditions) if ignore_conditions else ''
            find_cmd = f'find "{directory}" {ignore_clause} -type f -print 2>/dev/null | head -{LIMIT}'
            
            result = run_in_container(find_cmd)
            
            if result.startswith("Error:"):
                return result
            
            files = [line.strip() for line in result.split('\n') if line.strip()]
            
            if not files:
                return f"No files found in {directory} (or directory doesn't exist)"
            
            # Build directory tree structure
            tree_structure = self._build_tree_structure(files, directory)
            
            # Check if results were truncated
            if len(files) >= LIMIT:
                tree_structure += f"\n\n(Results limited to {LIMIT} files. Use glob for more specific searches.)"
            
            return tree_structure
            
        except Exception as e:
            return f"Error: {str(e)}"

    def _build_tree_structure(self, files, base_dir):
        """Build a hierarchical tree structure from file paths"""
        # Organize files by directory
        dirs = {}
        
        for file_path in files:
            # Remove base directory prefix for cleaner display
            if file_path.startswith(base_dir + '/'):
                rel_path = file_path[len(base_dir) + 1:]
            elif file_path.startswith('./'):
                rel_path = file_path[2:]
            else:
                rel_path = file_path
            
            if '/' in rel_path:
                dir_part = '/'.join(rel_path.split('/')[:-1])
                file_part = rel_path.split('/')[-1]
            else:
                dir_part = '.'
                file_part = rel_path
            
            if dir_part not in dirs:
                dirs[dir_part] = []
            dirs[dir_part].append(file_part)
        
        # Sort directories and files
        for dir_path in dirs:
            dirs[dir_path].sort()
        
        # Build tree output
        output = []
        
        # Show base directory
        display_base = base_dir if base_dir != '.' else 'current directory'
        output.append(f"{display_base}/")
        
        # Sort directories by depth and name
        sorted_dirs = sorted(dirs.keys(), key=lambda x: (x.count('/'), x))
        
        for dir_path in sorted_dirs:
            if dir_path == '.':
                # Files in root directory
                for file_name in dirs[dir_path]:
                    output.append(f"  {file_name}")
            else:
                # Subdirectory
                depth = dir_path.count('/') + 1
                indent = "  " * depth
                dir_name = dir_path.split('/')[-1]
                output.append(f"{indent}{dir_name}/")
                
                # Files in this directory
                file_indent = "  " * (depth + 1)
                for file_name in dirs[dir_path]:
                    output.append(f"{file_indent}{file_name}")
        
        return '\n'.join(output)

    def _pretty_print_tool(self, directory: str):
        print(f"🛠️ Listing Directory Tree")
        print(f"  - directory: {directory}")
        print()