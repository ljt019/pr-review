import os
from dotenv import load_dotenv
from agent.agent import SniffAgent
from agent.agent import ModelOptions

from src.paths import get_assets_path

# Load environment variables from .env file
load_dotenv()

# Enable verbose container debug logs for every run
os.environ["SNIFF_DEBUG"] = "0"

zipped_codebase_path = get_assets_path("toy-webserver.zip")

def main():
    try:
        bot = SniffAgent(zipped_codebase_path, ModelOptions.QWEN3_30B_A3B_INSTRUCT)
        print("[DEBUG] Using run_streaming() to debug tool calls...")
        for message in bot.run_streaming():
            print(f"[DEBUG] Got streaming message: {type(message).__name__}")
            if hasattr(message, 'tool_name'):
                print(f"[DEBUG] Tool: {message.tool_name}, Args: {getattr(message, 'arguments', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'bot' in locals():
            bot._cleanup()

if __name__ == "__main__":
    main()