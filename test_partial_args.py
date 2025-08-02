from tui.widgets.tool_indicator import ToolIndicator

# Test partial arguments that were causing issues
test_cases = [
    ("cat", '{"filePath": "services/email'),  # Incomplete - what was being yielded
    ("cat", '{"filePath": "app.py"}'),        # Complete - what should be yielded
    ("cat", '{"filePath": "server/routes.py"}'),  # Complete
    ("cat", '{"filePath"'),                   # Very incomplete
    ("ls", '{"directory": "."}'),             # Complete
    ("ls", '{}'),                            # Empty but valid
]

print("Testing ToolIndicator with various argument states:")
for tool_name, args in test_cases:
    indicator = ToolIndicator(tool_name, args)
    print(f"{tool_name} + '{args}' -> '{indicator.display_text}'")