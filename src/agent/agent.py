"""Clean agent implementation using the new messaging system."""

import os
import time
from enum import Enum
from typing import Tuple

from dotenv import load_dotenv

# MUST modify settings BEFORE importing Assistant to avoid import-time binding
from qwen_agent import settings
settings.MAX_LLM_CALL_PER_RUN = 500

from qwen_agent.agents import Assistant

from agent.messaging import (
    MessageReceiver, MessageSender, 
    ToolExecutionMessage,
    StreamStartMessage, StreamChunkMessage, StreamEndMessage,
    BugReportMessage
)
from agent.tools import (
    load_prompt, cat, ls, grep, glob, todoread, todowrite
)
from agent.sandbox import Sandbox

load_dotenv()



class ModelOptions(Enum):
    QWEN3_480B_A35B_CODER = "qwen/qwen3-coder"
    QWEN3_235B_A22B_INSTRUCT = "qwen/qwen3-235b-a22b-2507"
    QWEN3_30B_A3B_INSTRUCT = "qwen/qwen3-30b-a3b-instruct-2507"


def create_agent(
    codebase_path: str,
    model: ModelOptions = ModelOptions.QWEN3_30B_A3B_INSTRUCT
) -> Tuple['SniffAgent', MessageReceiver]:
    """Create an agent and return it along with its message receiver.
    
    Returns:
        Tuple of (agent, receiver) where you can iterate over receiver for messages
    """
    receiver = MessageReceiver()
    agent = SniffAgent(codebase_path, model, receiver)
    return agent, receiver


class SniffAgent:
    """Clean agent implementation with built-in messaging."""
    
    def __init__(self, codebase_path: str, model: ModelOptions, receiver: MessageReceiver):
        """Initialize agent with messaging system."""
        
        # Setup messaging
        self.receiver = receiver
        self.sender = MessageSender(receiver)
        
        # Setup LLM
        llm_cfg = {
            "model": model.value,
            "model_server": "https://openrouter.ai/api/v1",
            "api_key": os.getenv("OPEN_ROUTER_API_KEY"),
            "generate_cfg": {"max_input_tokens": 100000},
        }
        
        system_instruction = load_prompt("system_prompt")
        tools = ["ls", "cat", "grep", "glob", "todo_write", "todo_read"]
        
        self.llm_agent = Assistant(
            llm=llm_cfg,
            system_message=system_instruction,
            function_list=tools,
        )
        
        # Setup sandbox
        self.sandbox = Sandbox(codebase_path)
        self.messages = []
        
        # Track sent tool executions to avoid duplicates
        self._sent_tool_executions = set()
        
        # Track streaming state
        self._current_stream = None
        self._stream_buffer = ""
        self._chunk_index = 0
        
        # Track JSON detection state
        self._json_buffer = ""
        self._json_depth = 0
        self._in_json_object = False
        
    
    def start(self):
        """Start the agent and its sandbox."""
        self.sandbox.start()
        self._wait_for_workspace_ready()
    
    def _wait_for_workspace_ready(self):
        """Wait for sandbox to be ready."""
        # Simple check - could be enhanced
        import time
        time.sleep(1)
    
    def run_analysis(self):
        """Run the bug analysis. Messages are sent to receiver in real-time."""
        try:
            # Send initial query
            self.messages = [{"role": "user", "content": load_prompt("starting_query")}]
            
            
            # Run LLM and process responses - messages sent in real-time
            llm_responses = self.llm_agent.run(messages=self.messages)
            
            for response_batch in llm_responses:
                self._process_response_batch(response_batch)
            
            # End any active stream
            if self._current_stream:
                self._end_stream()
            
            
        except Exception as e:
            # Just re-raise, let caller handle it
            raise
    
    def _process_response_batch(self, responses):
        """Process a batch of LLM responses and send appropriate messages."""
        if not responses:
            return
        
        # Find all complete tool call + result pairs
        tool_calls_with_results = self._find_complete_tool_executions(responses)
        
        # Send only new complete tool executions
        for tool_call, result in tool_calls_with_results:
            tool_signature = self._get_tool_signature(tool_call, result)
            
            if tool_signature not in self._sent_tool_executions:
                self._send_tool_execution(tool_call, result)
                self._sent_tool_executions.add(tool_signature)
        
        # Handle streaming content properly
        content_chunks = []
        for response in responses:
            if (isinstance(response, dict) and 
                'content' in response and 
                response['content'] and 
                response.get('role') != 'function'):  # Exclude function results
                content_chunks.append(response['content'])
        
        if content_chunks:
            combined = ''.join(content_chunks)
            if combined:
                self._handle_streaming_content(combined)
    
    def _send_batched_content(self, content_chunks):
        """Send batched content as a single message."""
        if not content_chunks:
            return
            
        combined_content = ''.join(content_chunks)
        if combined_content.strip():  # Only send if there's actual content
            self.sender.send(ErrorMessage(
                message_id=self._gen_msg_id(),
                timestamp=time.time(),
                error_type="AgentOutput",
                error_message=combined_content,
                recoverable=True
            ))
    
    def _handle_streaming_content(self, content):
        """Handle streaming content with smart JSON detection."""
        # Check for JSON content first
        if self._detect_and_handle_json(content):
            return  # JSON was handled, don't send as regular stream
        
        # Handle regular streaming content
        if not self._current_stream or not content.startswith(self._stream_buffer):
            # End previous stream if one was active
            if self._current_stream:
                self._end_stream()
            
            # Start new stream
            self._start_stream(content)
        
        # Send new chunk(s)
        new_content = content[len(self._stream_buffer):]
        if new_content:
            self._send_stream_chunk(new_content)
            self._stream_buffer = content
    
    def _detect_and_handle_json(self, content):
        """Detect JSON objects and handle them when complete."""
        # Check if this looks like JSON content
        is_json_like = (
            content.strip().startswith('{') or 
            'summary' in content.lower() or 
            'bugs' in content.lower() or
            self._in_json_object
        )
        
        if is_json_like:
            # We're in a JSON object - start or continue buffering
            if not self._in_json_object:
                # Starting JSON object
                self._in_json_object = True
                self._json_buffer = content
            else:
                # Continue building JSON buffer
                self._json_buffer = content
            
            # Try to parse complete JSON
            complete_json = self._extract_complete_json(self._json_buffer)
            if complete_json:
                self._handle_bug_report_json(complete_json)
                # Reset JSON state
                self._json_buffer = ""
                self._json_depth = 0
                self._in_json_object = False
                return True
            
            # JSON detected but not complete yet - don't stream it
            return True
        
        return False
    
    def _extract_complete_json(self, text):
        """Extract complete JSON object from text using ijson-like approach."""
        import json
        
        # Find potential JSON start
        json_start = -1
        for i, char in enumerate(text):
            if char == '{':
                json_start = i
                break
        
        if json_start == -1:
            return None
        
        # Try to find complete JSON object by tracking braces
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i in range(json_start, len(text)):
            char = text[i]
            
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    
                    # Found complete JSON object
                    if brace_count == 0:
                        json_text = text[json_start:i+1]
                        try:
                            parsed = json.loads(json_text)
                            # Validate it looks like a bug report
                            if isinstance(parsed, dict) and ('summary' in parsed or 'bugs' in parsed):
                                return parsed
                        except json.JSONDecodeError:
                            continue
        
        return None
    
    def _handle_bug_report_json(self, report_data):
        """Handle a complete bug report JSON object."""
        # Count analyzed files (could be enhanced to track this properly)
        files_analyzed = len(set(
            bug.get('file', '') for bug in report_data.get('bugs', [])
            if bug.get('file')
        ))
        
        self.sender.send(BugReportMessage(
            message_id=self._gen_msg_id(),
            timestamp=time.time(),
            report_data=report_data,
            files_analyzed=files_analyzed
        ))
    
    def _start_stream(self, initial_content):
        """Start a new streaming message."""
        self._current_stream = self._gen_msg_id()
        self._stream_buffer = initial_content
        self._chunk_index = 0
        
        self.sender.send(StreamStartMessage(
            message_id=self._gen_msg_id(),
            timestamp=time.time(),
            content_type="analysis"
        ))
        
        # Send the initial content as first chunk
        if initial_content:
            self._send_stream_chunk(initial_content)
    
    def _send_stream_chunk(self, chunk_content):
        """Send a chunk of streaming content."""
        self.sender.send(StreamChunkMessage(
            message_id=self._gen_msg_id(),
            timestamp=time.time(),
            content=chunk_content,
            chunk_index=self._chunk_index
        ))
        self._chunk_index += 1
    
    def _end_stream(self):
        """End the current streaming message."""
        if self._current_stream:
            self.sender.send(StreamEndMessage(
                message_id=self._gen_msg_id(),
                timestamp=time.time(),
                total_chunks=self._chunk_index,
                final_content=self._stream_buffer
            ))
            
            self._current_stream = None
            self._stream_buffer = ""
            self._chunk_index = 0
    
    def _find_complete_tool_executions(self, responses):
        """Find tool calls that have corresponding function results."""
        # Build maps of tool calls and function results
        tool_calls = {}  # tool_name -> latest_tool_call_response
        function_results = {}  # tool_name -> function_result_response
        
        for response in responses:
            if not isinstance(response, dict):
                continue
                
            # Track latest tool call for each tool
            if 'function_call' in response and response['function_call']:
                func_call = response['function_call']
                tool_name = func_call.get('name', '')
                if tool_name:
                    tool_calls[tool_name] = response
            
            # Track function results
            elif response.get('role') == 'function':
                tool_name = response.get('name', '')
                if tool_name:
                    function_results[tool_name] = response
        
        # Return pairs where we have both call and result
        complete_executions = []
        for tool_name, tool_call in tool_calls.items():
            if tool_name in function_results:
                complete_executions.append((tool_call, function_results[tool_name]))
        
        return complete_executions
    
    def _get_tool_signature(self, tool_call, result):
        """Generate unique signature for a tool execution to avoid duplicates."""
        func_call = tool_call['function_call']
        tool_name = func_call.get('name', '')
        arguments = func_call.get('arguments', '')
        result_preview = result['content'][:50] if result and result.get('content') else ''
        
        # For todo tools, only use tool name to avoid multiple indicators
        # since todos are state management tools that get updated via TodoStateMessage
        if tool_name in ['todo_write', 'todo_read']:
            signature_str = f"{tool_name}_latest"
        else:
            # For other tools, use full signature for deduplication
            signature_str = f"{tool_name}|{arguments}|{result_preview}"
            
        import hashlib
        return hashlib.md5(signature_str.encode()).hexdigest()
    
    def _send_tool_execution(self, tool_call, result):
        """Send a single complete tool execution message."""
        func_call = tool_call['function_call']
        tool_name = func_call['name']
        arguments = func_call['arguments']
        
        try:
            import json
            args_dict = json.loads(arguments) if isinstance(arguments, str) else arguments
        except Exception:
            args_dict = {"raw_args": str(arguments)}
        
        # Get result info
        if result:
            result_content = result['content']
            success = not result_content.startswith('Error:')
        else:
            result_content = f"Executed {tool_name}"
            success = True
        
        # Send the complete tool execution message
        self.sender.send(ToolExecutionMessage(
            message_id=self._gen_msg_id(),
            timestamp=time.time(),
            tool_name=tool_name,
            arguments=args_dict,
            result=result_content,
            success=success
        ))
        
        # Todo state is already included in the tool result - no need for separate message
    
    def _handle_complete_tool_call(self, tool_call_response, function_results):
        """Handle a complete tool call with its result."""
        func_call = tool_call_response['function_call']
        tool_name = func_call['name']
        arguments = func_call['arguments']
        
        try:
            # Parse arguments
            import json
            args_dict = json.loads(arguments) if isinstance(arguments, str) else arguments
        except Exception:
            args_dict = {"raw_args": str(arguments)}
        
        # Get the actual function result if available
        function_result = function_results.get(tool_name)
        if function_result:
            result = function_result['content']
            success = not result.startswith('Error:')
        else:
            result = f"Executed {tool_name} with args {args_dict}"
            success = True
        
        # Send single tool execution message with complete info
        self.sender.send(ToolExecutionMessage(
            message_id=self._gen_msg_id(),
            timestamp=time.time(),
            tool_name=tool_name,
            arguments=args_dict,
            result=result,
            success=success
        ))
        
        # Todo state is already included in the tool result - no need for separate message
    
    
    def _gen_msg_id(self) -> str:
        """Generate unique message ID."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def stop(self):
        """Stop the agent and cleanup."""
        if hasattr(self, 'sandbox'):
            self.sandbox.stop()
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()