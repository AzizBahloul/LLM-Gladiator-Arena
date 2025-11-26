# core/messaging.py
"""Real-time messaging system for LLM agents to discuss and negotiate."""
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import queue
import time


class MessageType(Enum):
    """Types of messages in the arena."""
    PUBLIC = "public"           # Visible to all agents
    PRIVATE = "private"         # Only between specific agents
    ALLIANCE = "alliance"       # Alliance channel
    BROADCAST = "broadcast"     # System announcements
    TAUNT = "taunt"            # Trash talk / provocations
    STRATEGY = "strategy"       # Strategic discussions
    WHISPER = "whisper"        # Secret messages


@dataclass
class Message:
    """A single message in the arena."""
    sender: str
    content: str
    msg_type: MessageType
    timestamp: datetime = field(default_factory=datetime.now)
    recipients: List[str] = field(default_factory=list)  # Empty = all
    reply_to: Optional[str] = None  # Message ID being replied to
    id: str = field(default_factory=lambda: f"msg_{datetime.now().timestamp()}")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'sender': self.sender,
            'content': self.content,
            'type': self.msg_type.value,
            'timestamp': self.timestamp.isoformat(),
            'recipients': self.recipients,
            'reply_to': self.reply_to
        }
    
    def format_display(self) -> str:
        """Format message for display."""
        time_str = self.timestamp.strftime("%H:%M:%S")
        type_emoji = {
            MessageType.PUBLIC: "💬",
            MessageType.PRIVATE: "🔒",
            MessageType.ALLIANCE: "🤝",
            MessageType.BROADCAST: "📢",
            MessageType.TAUNT: "🔥",
            MessageType.STRATEGY: "🎯",
            MessageType.WHISPER: "👂"
        }
        emoji = type_emoji.get(self.msg_type, "💬")
        
        if self.msg_type == MessageType.PRIVATE and self.recipients:
            target = f" → {', '.join(self.recipients)}"
        else:
            target = ""
        
        return f"[{time_str}] {emoji} {self.sender}{target}: {self.content}"


class DiscussionTopic:
    """A topic for structured multi-agent discussion."""
    
    def __init__(self, topic: str, initiator: str, participants: List[str]):
        self.topic = topic
        self.initiator = initiator
        self.participants = participants
        self.messages: List[Message] = []
        self.started_at = datetime.now()
        self.concluded = False
        self.outcome: Optional[str] = None
    
    def add_message(self, msg: Message):
        self.messages.append(msg)
    
    def get_context(self, for_agent: str) -> str:
        """Get discussion context for an agent to respond."""
        context_lines = [f"Topic: {self.topic}"]
        context_lines.append(f"Participants: {', '.join(self.participants)}")
        context_lines.append("\nDiscussion so far:")
        
        for msg in self.messages[-10:]:  # Last 10 messages for context
            context_lines.append(f"  {msg.sender}: {msg.content}")
        
        return "\n".join(context_lines)


class MessagingSystem:
    """Central messaging hub for real-time agent communication."""
    
    def __init__(self):
        self.messages: List[Message] = []
        self.message_queue = queue.Queue()
        self.active_discussions: List[DiscussionTopic] = []
        self.listeners: List[Callable[[Message], None]] = []
        self._lock = threading.Lock()
        self.message_history: Dict[str, List[Message]] = {}  # Per-agent history
    
    def register_listener(self, callback: Callable[[Message], None]):
        """Register a callback to be notified of new messages."""
        self.listeners.append(callback)
    
    def _notify_listeners(self, message: Message):
        """Notify all registered listeners of a new message."""
        for listener in self.listeners:
            try:
                listener(message)
            except Exception:
                pass
    
    def send_message(self, sender: str, content: str, 
                     msg_type: MessageType = MessageType.PUBLIC,
                     recipients: List[str] = None,
                     reply_to: str = None) -> Message:
        """Send a message in the arena."""
        msg = Message(
            sender=sender,
            content=content,
            msg_type=msg_type,
            recipients=recipients or [],
            reply_to=reply_to
        )
        
        with self._lock:
            self.messages.append(msg)
            self.message_queue.put(msg)
            
            # Track per-agent history
            if sender not in self.message_history:
                self.message_history[sender] = []
            self.message_history[sender].append(msg)
        
        # Notify listeners (for GUI updates)
        self._notify_listeners(msg)
        
        return msg
    
    def broadcast(self, content: str, source: str = "ARENA") -> Message:
        """Send a system broadcast."""
        return self.send_message(
            sender=source,
            content=content,
            msg_type=MessageType.BROADCAST
        )
    
    def get_messages_for_agent(self, agent_name: str, 
                                since: datetime = None,
                                limit: int = 50) -> List[Message]:
        """Get messages visible to a specific agent."""
        visible = []
        
        for msg in reversed(self.messages):
            # Check if message is visible to this agent
            if msg.msg_type in [MessageType.PUBLIC, MessageType.BROADCAST, MessageType.TAUNT]:
                visible.append(msg)
            elif msg.sender == agent_name:
                visible.append(msg)
            elif agent_name in msg.recipients:
                visible.append(msg)
            
            if len(visible) >= limit:
                break
        
        # Filter by time if specified
        if since:
            visible = [m for m in visible if m.timestamp >= since]
        
        return list(reversed(visible))
    
    def get_recent_context(self, limit: int = 20) -> str:
        """Get recent messages as context string."""
        recent = self.messages[-limit:] if len(self.messages) > limit else self.messages
        return "\n".join([msg.format_display() for msg in recent])
    
    def get_chat_history_for_llm(self, agent_name: str, limit: int = 15) -> str:
        """Get formatted chat history that an LLM can understand.
        
        Returns a clean transcript of recent messages so the LLM knows
        what's been said and can respond appropriately.
        """
        visible_messages = self.get_messages_for_agent(agent_name, limit=limit)
        
        if not visible_messages:
            return ""
        
        lines = ["=== RECENT CHAT ==="]
        for msg in visible_messages:
            sender = msg.sender
            content = msg.content
            
            # Mark if it's a system message
            if msg.msg_type == MessageType.BROADCAST:
                lines.append(f"[SYSTEM] {content}")
            elif msg.msg_type == MessageType.TAUNT:
                lines.append(f"{sender} (taunt): {content}")
            elif msg.msg_type == MessageType.ALLIANCE:
                lines.append(f"{sender} (alliance): {content}")
            else:
                lines.append(f"{sender}: {content}")
        
        lines.append("===================")
        return "\n".join(lines)
    
    def start_discussion(self, topic: str, initiator: str, 
                         participants: List[str]) -> DiscussionTopic:
        """Start a new structured discussion."""
        discussion = DiscussionTopic(topic, initiator, participants)
        self.active_discussions.append(discussion)
        
        # Announce the discussion
        self.broadcast(
            f"🗣️ {initiator} initiates discussion: '{topic}' with {', '.join(participants)}"
        )
        
        return discussion
    
    def get_all_messages(self, limit: int = 100) -> List[Message]:
        """Get all messages for display."""
        return self.messages[-limit:] if len(self.messages) > limit else self.messages

    def get_chat_context_for_agent(self, agent_name: str, limit: int = 30) -> str:
        """Get formatted chat context for an agent to understand conversations.
        
        Returns recent messages visible to this agent in a simple format
        that helps the LLM understand what's been said.
        """
        visible_messages = self.get_messages_for_agent(agent_name, limit=limit)
        
        if not visible_messages:
            return ""
        
        lines = ["Recent arena chat:"]
        for msg in visible_messages:
            sender = msg.sender
            content = msg.content
            lines.append(f"[{sender}]: {content}")
        
        return "\n".join(lines)


# Global messaging instance
messaging_system = MessagingSystem()
