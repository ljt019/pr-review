import os
from dotenv import load_dotenv
from bug_bot.bug_bot import BugBot
from bug_bot.bug_bot import ModelOptions

# Load environment variables from .env file
load_dotenv()

# Enable verbose container debug logs for every run
os.environ["BUGBOT_DEBUG"] = "0"

zipped_codebase_path = "C:\\Users\\lucie\\Desktop\\toy-webserver.zip"

def main():
    try:
        bot = BugBot(zipped_codebase_path, ModelOptions.QWEN3_30B_A3B_INSTRUCT)
        result = bot.run()
        print(result)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'bot' in locals():
            bot._cleanup()

if __name__ == "__main__":
    main()