from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid
from models.chat_models import ChatMessage, ChatSession, MessageRole


class MemoryStore:
    """In-memory storage for chat sessions and conversation history"""

    def __init__(
        self,
        max_sessions: int = 1000,
        session_timeout_hours: int = 24,
        max_messages_per_session: int = 5,
    ):
        self.sessions: Dict[str, ChatSession] = {}
        self.max_sessions = max_sessions
        self.session_timeout = timedelta(hours=session_timeout_hours)
        self.max_messages_per_session = (
            max_messages_per_session  # Keep only last 5 messages
        )

    def create_session(self) -> str:
        """Create a new chat session and return its ID"""
        session_id = str(uuid.uuid4())

        # Clean up old sessions if we're at capacity
        if len(self.sessions) >= self.max_sessions:
            self._cleanup_old_sessions()

        self.sessions[session_id] = ChatSession(
            session_id=session_id,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        return session_id

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID"""
        session = self.sessions.get(session_id)
        if session and self._is_session_valid(session):
            return session
        elif session:
            # Remove expired session
            del self.sessions[session_id]
        return None

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """
        Add a message to a session with role and content

        Args:
            session_id (str): The session ID
            role (str): Message role ('user' or 'assistant')
            content (str): Message content

        Returns:
            bool: True if message was added successfully, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            # Auto-create session if it doesn't exist
            self.create_session_with_id(session_id)
            session = self.get_session(session_id)
            if not session:
                return False

        # Create message object
        try:
            message_role = (
                MessageRole.USER if role.lower() == "user" else MessageRole.ASSISTANT
            )
        except:
            message_role = MessageRole.USER  # Default to user if invalid role

        message = ChatMessage(
            role=message_role, content=content, timestamp=datetime.utcnow()
        )

        session.messages.append(message)
        session.updated_at = datetime.utcnow()

        # Keep only last N messages to manage memory (configurable, default 5)
        if len(session.messages) > self.max_messages_per_session:
            session.messages = session.messages[-self.max_messages_per_session :]

        return True

    def add_message_object(self, session_id: str, message: ChatMessage) -> bool:
        """Add a ChatMessage object to a session (for backward compatibility)"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.messages.append(message)
        session.updated_at = datetime.utcnow()

        # Keep only last N messages
        if len(session.messages) > self.max_messages_per_session:
            session.messages = session.messages[-self.max_messages_per_session :]

        return True

    def get_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """
        Get messages from a session

        Args:
            session_id (str): The session ID
            limit (Optional[int]): Maximum number of messages to return

        Returns:
            List[ChatMessage]: List of messages (empty list if session not found)
        """
        session = self.get_session(session_id)
        if not session:
            return []

        messages = session.messages
        if limit and limit > 0:
            messages = messages[-limit:]

        return messages

    def get_messages_for_gemini(self, session_id: str) -> List[dict]:
        """
        Get messages formatted for Gemini API

        Args:
            session_id (str): The session ID

        Returns:
            List[dict]: Messages in Gemini API format
        """
        messages = self.get_messages(session_id)

        gemini_messages = []
        for msg in messages:
            role = "user" if msg.role == MessageRole.USER else "model"
            gemini_messages.append({"role": role, "parts": [msg.content]})

        return gemini_messages

    def create_session_with_id(self, session_id: str) -> str:
        """Create a session with a specific ID (for auto-creation)"""
        if session_id in self.sessions:
            return session_id

        self.sessions[session_id] = ChatSession(
            session_id=session_id,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        return session_id

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_session_count(self) -> int:
        """Get the number of active sessions"""
        return len(self.sessions)

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """Get session information"""
        session = self.get_session(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "message_count": len(session.messages),
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "max_messages": self.max_messages_per_session,
        }

    def clear_session_messages(self, session_id: str) -> bool:
        """Clear all messages from a session but keep the session"""
        session = self.get_session(session_id)
        if not session:
            return False

        session.messages = []
        session.updated_at = datetime.utcnow()
        return True

    def _cleanup_old_sessions(self):
        """Remove expired sessions"""
        current_time = datetime.utcnow()
        expired_sessions = [
            session_id
            for session_id, session in self.sessions.items()
            if current_time - session.updated_at > self.session_timeout
        ]

        for session_id in expired_sessions:
            del self.sessions[session_id]

    def _is_session_valid(self, session: ChatSession) -> bool:
        """Check if a session is still valid (not expired)"""
        return datetime.utcnow() - session.updated_at <= self.session_timeout
