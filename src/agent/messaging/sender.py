"""Simple message sender using queue.Queue internally."""

from .types import AgentMessage


class MessageSender:
    """Sends messages using Python's built-in queue.Queue."""
    
    def __init__(self, receiver=None):
        """Initialize the message sender.
        
        Args:
            receiver: MessageReceiver to send messages to (optional)
        """
        self.receiver = receiver
    
    def send(self, message: AgentMessage) -> None:
        """Send any AgentMessage type."""
        if self.receiver:
            self.receiver.receive_message(message)