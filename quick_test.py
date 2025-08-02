from tui.widgets.tool_indicator import ToolIndicator

# Test the ToolIndicator directly
print("Testing ToolIndicator with ls arguments...")
indicator = ToolIndicator("ls", '{"directory": "."}')
print(f"Display text: '{indicator.display_text}'")

print("\nTesting ToolIndicator with cat arguments...")
indicator2 = ToolIndicator("cat", '{"filePath": "app.py"}')
print(f"Display text: '{indicator2.display_text}'")

print("\nTesting ToolIndicator with empty ls arguments...")
indicator3 = ToolIndicator("ls", '{}')
print(f"Display text: '{indicator3.display_text}'")