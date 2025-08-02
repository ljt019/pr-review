#!/usr/bin/env python3
"""Test script to demonstrate BugBot streaming functionality."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bug_bot.bug_bot import (
    BugBot,
    BugReportMessage,
    ModelOptions,
    ToolCallMessage,
    ToolResultMessage,
)


def test_streaming(zipped_codebase: str):
    """Test the streaming functionality of BugBot."""
    print("🚀 Starting BugBot streaming test...\n")
    
    with BugBot(
        zipped_codebase=zipped_codebase,
        model_option=ModelOptions.QWEN3_30B_A3B_INSTRUCT
    ) as bot:
        tool_call_count = 0
        bug_report_parts = []
        
        for message in bot.run_streaming():
            match message:
                case ToolCallMessage(tool_name=name, arguments=args, reasoning=reason):
                    tool_call_count += 1
                    print(f"\n🔧 [{tool_call_count}] Calling tool: {name}")
                    if reason:
                        print(f"   💭 Reason: {reason}")
                    # Only show args preview if they're not too long
                    if len(args) < 100:
                        print(f"   📝 Args: {args}")
                    else:
                        print(f"   📝 Args: {args[:100]}... (truncated)")
                    
                case ToolResultMessage(tool_name=name, result=result):
                    # Show a preview of the result
                    result_preview = result.strip()
                    if len(result_preview) > 200:
                        result_preview = result_preview[:200] + "..."
                    print(f"   ✅ Result: {result_preview}\n")
                    
                case BugReportMessage(content=content, is_final=final):
                    if content:  # Only process non-empty content
                        if final:
                            print("\n" + "="*80)
                            print("🐛 FINAL BUG REPORT:")
                            print("="*80)
                            print(content)
                            print("="*80)
                        else:
                            # Accumulate intermediate bug report parts
                            bug_report_parts.append(content)
                            print(f"💭 Analysis update: {content[:100]}..." if len(content) > 100 else f"💭 {content}")
        
        print(f"\n📊 Summary:")
        print(f"   - Total tool calls: {tool_call_count}")
        print(f"   - Intermediate updates: {len(bug_report_parts)}")
        

def main():
    """Main entry point."""
    # Use the same test codebase as other scripts
    from paths import get_assets_path
    
    zipped_codebase_path = get_assets_path("toy-webserver.zip")
    
    if not Path(zipped_codebase_path).exists():
        print(f"❌ Error: Test file '{zipped_codebase_path}' not found")
        sys.exit(1)
    
    print(f"📦 Using test codebase: {zipped_codebase_path}")
    
    # Run the test
    test_streaming(zipped_codebase_path)


if __name__ == "__main__":
    main()