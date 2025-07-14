from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Single chat message"""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None


class ChatSession(BaseModel):
    """Chat session containing multiple messages"""

    session_id: str
    messages: List[ChatMessage] = []
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    """Request to send a chat message"""

    message: str
    session_id: Optional[str] = None
    stream: bool = True


class ChatResponse(BaseModel):
    """Response from chat endpoint"""

    message: str
    session_id: str
    role: MessageRole = MessageRole.ASSISTANT
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionCreateResponse(BaseModel):
    """Response when creating a new session"""

    session_id: str
    created_at: datetime


class SessionInfo(BaseModel):
    """Information about a chat session"""

    session_id: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    active_sessions: int = 0


class StreamRequest(BaseModel):
    """Request format for /stream endpoint"""

    messages: List[dict] = Field(
        description="List of messages with role ('user' or 'assistant') and content"
    )
    prompt: str = Field(description="The user's prompt/message")
    session_id: Optional[str] = Field(
        default=None, description="Optional session ID for memory persistence"
    )
