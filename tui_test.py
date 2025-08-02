import os
from dotenv import load_dotenv
from bug_bot.bug_bot import BugBot, ModelOptions
from paths import get_assets_path

# Load environment variables
load_dotenv()
os.environ["BUGBOT_DEBUG"] = "0"

def main():
    try:
        # Import the TUI app
        from src.app import BugBotApp
        
        app = BugBotApp()
        app.selected_model = "Qwen3 30B A3B Instruct"
        
        # Run for a very short time
        print("Starting TUI - check tool indicators...")
        app.run()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()