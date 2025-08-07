"""
Tests the full agent flow.
Creates a agent, starts the analysis on another thread, and
then prints messages as they are received, on main thread.
"""

import queue
import threading
import sys
from pathlib import Path

from agent.agent import ModelOptions, create_agent
from agent.messaging.types import (
    AgentMessage,
    BugReportMessage,
    StreamChunkMessage,
    StreamEndMessage,
    StreamStartMessage,
    ToolExecutionMessage,
)


def handle_print_message(message: AgentMessage):
    match message:
        case ToolExecutionMessage():
            print("--- TOOL EXECUTION ---")
            print(f"Tool: {message.tool_name}")
            print(f"Arguments: {message.arguments}")
            print(f"Result: {message.result}")
        case StreamStartMessage():
            print("--- STREAM START ---")
            print(f"Content type: {message.content_type}")
        case StreamChunkMessage():
            print("--- STREAM CHUNK ---")
            print(f"Content: {message.content}")
        case StreamEndMessage():
            print("--- STREAM END ---")
            print(f"Total chunks: {message.total_chunks}")
        case BugReportMessage():
            print("--- BUG REPORT ---")
            print(f"Summary: {message.summary}")
            print(f"Bugs: {message.bugs}")
        case _:
            print(f"Unknown message type: {message.message_type}")


def run_agent_analysis(agent, stop_event):
    """Run the agent analysis in a separate thread."""
    try:
        print("Starting agent sandbox...")
        agent.start()  # This starts the sandbox
        print("Starting agent analysis...")
        agent.run_analysis()
        print("Agent analysis completed")
    except Exception as e:
        print(f"Agent analysis failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        try:
            agent.stop()  # Clean up sandbox
        except Exception:
            pass
        stop_event.set()


def main():
    """Main test function."""

    # Get codebase path - use toy webserver zip for testing
    current_dir = Path(__file__).parent.parent
    codebase_path = str(current_dir / "assets" / "toy-webserver.zip")

    print(f"Testing agent with codebase: {codebase_path}")
    print("=" * 50)

    # Create agent and receiver
    agent, receiver = create_agent(
        codebase_path=codebase_path, model=ModelOptions.QWEN3_30B_A3B_INSTRUCT
    )

    # Create stop event for coordination
    stop_event = threading.Event()

    try:
        # Start agent analysis in background thread
        analysis_thread = threading.Thread(
            target=run_agent_analysis, args=(agent, stop_event), daemon=True
        )
        analysis_thread.start()

        # Process messages on main thread
        print("Listening for messages...")
        message_count = 0

        while not stop_event.is_set() or not receiver.empty():
            if not receiver.empty():
                try:
                    message = receiver.get_message_nowait()
                    message_count += 1

                    print(f"\n--- Message {message_count} ---")
                    try:
                        handle_print_message(message)
                    except Exception as print_error:
                        print(f"Error printing message: {print_error}")
                        print(f"Message type: {getattr(message, 'message_type', 'unknown')}")

                except queue.Empty:
                    # Race condition - queue became empty between check and get
                    pass
                except Exception as e:
                    print(f"Unexpected error receiving message: {e}")
            else:
                # No messages available, short sleep to avoid busy waiting
                import time
                time.sleep(0.1)

            # Check if analysis thread is done and no more messages
            if not analysis_thread.is_alive() and receiver.empty():
                break

        # Wait for analysis thread to complete
        analysis_thread.join(timeout=5.0)

        print("\n" + "=" * 50)
        print(f"Test completed! Processed {message_count} messages")

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        stop_event.set()

    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        try:
            agent.stop()
        except Exception as e:
            print(f"Error during cleanup: {e}")


if __name__ == "__main__":
    main()
