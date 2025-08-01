import json5
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv
from bug_bot.tools import load_prompt, run_in_container
from bug_bot.metadata import enhance_bug_report
from bug_bot.response_saver import save_response_with_summary
from paths import PROJECT_ROOT

from bug_bot.docker.bot_container import BotContainer

# MUST modify settings BEFORE importing Assistant to avoid import-time binding
from qwen_agent import settings
settings.MAX_LLM_CALL_PER_RUN = 500

from qwen_agent.agents import Assistant

# Import tools to register them
from bug_bot.tools import ls, cat, grep, glob, todo 

load_dotenv()

class ModelOptions(Enum):
    QWEN3_480B_A35B_CODER = "qwen/qwen3-coder"
    QWEN3_235B_A22B_INSTRUCT = "qwen/qwen3-235b-a22b-2507"
    QWEN3_30B_A3B_INSTRUCT = "qwen/qwen3-30b-a3b-instruct-2507"

class BugBot:
    def __init__(self, zipped_codebase: str, model_option: ModelOptions = ModelOptions.QWEN3_30B_A3B_INSTRUCT):
        
        import os
        
        llm_cfg = {
            'model': model_option.value,
            'model_server': 'https://openrouter.ai/api/v1',
            'api_key': os.getenv("OPEN_ROUTER_API_KEY"),
            'generate_cfg': {
                'max_input_tokens': 100000,
            }
        }

        system_instruction = load_prompt("system_prompt")
        tools = ['ls', 'cat', 'grep', 'glob', 'todo_write', 'todo_read']

        self.agent = Assistant(
            llm=llm_cfg,
            system_message=system_instruction,
            function_list=tools,
        )

        self.messages = []
        self.container = BotContainer(zipped_codebase)

        # Start container; if it fails, raise so the caller knows the environment is broken
        self.container.start()

        # Wait until some files are present in /workspace to avoid race conditions
        self._wait_for_workspace_ready()

    def __del__(self):
        self.container.stop()

    def run(self, save_response=False):
        self.messages.append({'role': 'user', 'content': load_prompt("starting_query")})
        
        final_response = ""
        for response in self.agent.run(messages=self.messages):
            if response and len(response) > 0:
                last_message = response[-1]
                if last_message.get('role') == 'assistant' and 'content' in last_message:
                    final_response = last_message['content']
        
        # Process the response and add metadata
        if final_response:
            enhanced_response = self._process_response(final_response)
            if save_response:
                saved_paths = save_response_with_summary(enhanced_response, PROJECT_ROOT)
                if saved_paths:
                    print(f"Response saved to: {saved_paths['response']}")
                    if 'summary' in saved_paths:
                        print(f"Summary saved to: {saved_paths['summary']}")
            return enhanced_response
        
        return final_response
    
    def _cleanup(self):
        """Clean up resources, specifically the container"""
        if hasattr(self, 'container'):
            self.container.stop()
    
    def _process_response(self, response_content):
        """Process LLM response and add metadata automatically"""
        try:
            # Clean the response content - extract JSON from between {} if needed
            response_content = response_content.strip()
            
            # Find the JSON part if it's embedded in other text
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_content = response_content[json_start:json_end]
            else:
                json_content = response_content
            
            # Try to parse the LLM response as JSON
            llm_output = json5.loads(json_content)
            
            # Extract core components from LLM output
            summary = llm_output.get('summary', '')
            bugs = llm_output.get('bugs', [])
            nitpicks = llm_output.get('nitpicks', [])
            
            # Get list of files that were analyzed (from container context)
            files_analyzed = self._get_analyzed_files()
            
            # Use metadata generator to enhance the response
            enhanced_response = enhance_bug_report(
                summary=summary,
                bugs=bugs, 
                nitpicks=nitpicks,
                files_analyzed=files_analyzed
            )
            
            return enhanced_response
            
        except Exception as e:
            # If LLM didn't return valid JSON, wrap it with minimal metadata
            print(f"JSON parsing error: {e}")
            print(f"Response content preview: {response_content[:500]}...")
            return {
                "summary": "Failed to parse LLM response",
                "bugs": [],
                "nitpicks": [],
                "raw_response": response_content,
                "metadata": {
                    "parse_error": True,
                    "timestamp": datetime.now().isoformat() + 'Z'
                }
            }
    
    def _wait_for_workspace_ready(self, timeout: int = 15):
        """Block until the /workspace directory inside the container has at least one file.
        Helps avoid a race where the container is started but the initial copy/unzip is still running.
        """
        from time import sleep, time as now
        start = now()
        while True:
            count_cmd = 'find /workspace -maxdepth 2 -type f | head -1'
            result = run_in_container(count_cmd)
            if result and not result.startswith('Error:'):
                # At least one file found
                return
            if now() - start > timeout:
                print("Warning: workspace still empty after wait; continuing anyway")
                return
            sleep(0.5)

    def _get_analyzed_files(self):
        """Get list of files that were analyzed during the scan"""
        # For now, return empty list. Could be enhanced to track actual files accessed
        return []