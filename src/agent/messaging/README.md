# Messaging Module

Clean, simple messaging system using Python's built-in `queue.Queue`.

## Usage

```python
from messaging import (
    MessageReceiver, MessageType,
    ToolExecutionMessage
)
import time

# Setup
receiver = MessageReceiver()

# Create and send messages
tool_msg = ToolExecutionMessage(
    message_id="msg_1",
    timestamp=time.time(),
    tool_name="cat",
    arguments={"file": "test.py"},
    result="file content",
    success=True
)

receiver.receive_message(tool_msg)

# Receive messages
for message in receiver:
    if message.message_type == MessageType.TOOL_EXECUTION:
        print(f"Tool: {message.tool_name} -> {'success' if message.success else 'failed'}")
```

## Message Types

- `ToolExecutionMessage` - Combined tool call + result
- `StreamStartMessage` - Start of streaming content
- `StreamChunkMessage` - Chunk of streaming content
- `StreamEndMessage` - End of streaming content
- `BugReportMessage` - Bug analysis results

## Architecture

- **MessageReceiver**: Receives messages; call `receiver.receive_message(message)` to enqueue
- **AgentMessage**: Base class for all message types
- Uses Python's built-in `queue.Queue` for reliability and simplicity