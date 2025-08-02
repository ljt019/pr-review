import os
from dotenv import load_dotenv
from bug_bot.bug_bot import BugBot, ModelOptions
from paths import get_assets_path

# Load environment variables
load_dotenv()
os.environ["BUGBOT_DEBUG"] = "0"

zipped_codebase_path = get_assets_path("toy-webserver.zip")

def main():
    try:
        with BugBot(zipped_codebase_path, ModelOptions.QWEN3_30B_A3B_INSTRUCT) as bot:
            print("[DEBUG] Starting streaming...")
            count = 0
            for message in bot.run_streaming():
                print(f"[DEBUG] Message {count}: {type(message).__name__}")
                if hasattr(message, 'tool_name'):
                    print(f"[DEBUG] Tool: {message.tool_name}, Args: {getattr(message, 'arguments', 'N/A')}")
                count += 1
                if count > 10:  # Limit output
                    break
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()