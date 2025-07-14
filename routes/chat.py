from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional
import json
from datetime import datetime

from models.chat_models import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    MessageRole,
    SessionCreateResponse,
    SessionInfo,
    StreamRequest,
)
from services.gemini_service import GeminiService

chat_router = APIRouter()
gemini_service = GeminiService()


@chat_router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(request: Request):
    """Create a new chat session"""
    memory_store = request.app.state.memory_store
    session_id = memory_store.create_session()

    return SessionCreateResponse(session_id=session_id, created_at=datetime.utcnow())


@chat_router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str, request: Request):
    """Get information about a specific session"""
    memory_store = request.app.state.memory_store
    session = memory_store.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionInfo(
        session_id=session.session_id,
        message_count=len(session.messages),
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@chat_router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, request: Request, limit: Optional[int] = None):
    """Get messages from a session"""
    memory_store = request.app.state.memory_store
    messages = memory_store.get_messages(session_id, limit)

    if not messages and not memory_store.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    return {"messages": messages}


@chat_router.post("/chat")
async def chat(chat_request: ChatRequest, request: Request):
    """Send a chat message (non-streaming)"""
    memory_store = request.app.state.memory_store

    # Create session if not provided
    if not chat_request.session_id:
        session_id = memory_store.create_session()
    else:
        session_id = chat_request.session_id
        if not memory_store.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")

    # Add user message to session
    user_message = ChatMessage(role=MessageRole.USER, content=chat_request.message)
    memory_store.add_message_object(session_id, user_message)

    try:
        # Get conversation history
        conversation_history = memory_store.get_messages(session_id, limit=20)

        # Generate response
        response_text = await gemini_service.generate_response(
            chat_request.message,
            conversation_history[:-1],  # Exclude the just-added user message
        )

        # Add assistant response to session
        assistant_message = ChatMessage(
            role=MessageRole.ASSISTANT, content=response_text
        )
        memory_store.add_message_object(session_id, assistant_message)

        return ChatResponse(
            message=response_text, session_id=session_id, role=MessageRole.ASSISTANT
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating response: {str(e)}"
        )


@chat_router.post("/chat/stream")
async def chat_stream(chat_request: ChatRequest, request: Request):
    """Send a chat message with streaming response"""
    memory_store = request.app.state.memory_store

    # Create session if not provided
    if not chat_request.session_id:
        session_id = memory_store.create_session()
    else:
        session_id = chat_request.session_id
        if not memory_store.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")

    # Add user message to session
    user_message = ChatMessage(role=MessageRole.USER, content=chat_request.message)
    memory_store.add_message_object(session_id, user_message)

    async def generate_stream():
        try:
            # Get conversation history
            conversation_history = memory_store.get_messages(session_id, limit=20)

            # Generate streaming response
            full_response = ""
            async for chunk in gemini_service.generate_streaming_response(
                chat_request.message,
                conversation_history[:-1],  # Exclude the just-added user message
            ):
                full_response += chunk
                # Send chunk as Server-Sent Event
                yield f"data: {json.dumps({'chunk': chunk, 'session_id': session_id})}\n\n"

            # Add complete response to session
            assistant_message = ChatMessage(
                role=MessageRole.ASSISTANT, content=full_response
            )
            memory_store.add_message_object(session_id, assistant_message)

            # Send completion event
            yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'session_id': session_id})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@chat_router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request):
    """Delete a chat session"""
    memory_store = request.app.state.memory_store

    if not memory_store.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Session deleted successfully"}


@chat_router.post("/stream")
async def stream_chat(stream_request: StreamRequest, request: Request):
    """
    Stream chat endpoint with memory persistence:
    Accepts: { "messages": [{role: "user"|"assistant", content: string}], "prompt": string, "session_id": string? }
    Returns: Streaming response token by token using Server-Sent Events
    Uses memory store to maintain conversation context (last 5 messages)
    """
    memory_store = request.app.state.memory_store

    # Use provided session_id or create a new one
    if stream_request.session_id:
        session_id = stream_request.session_id
        # Check if session exists, if not it will be auto-created when adding messages
    else:
        session_id = memory_store.create_session()

    # Add the current user prompt to memory store
    memory_store.add_message(session_id, "user", stream_request.prompt)

    async def generate_stream():
        try:
            # Get conversation history from memory store (last 5 messages)
            conversation_history = memory_store.get_messages(session_id)

            # If this is a new session and we have initial messages, populate them first
            # (but exclude the user message we just added to avoid duplication)
            if len(conversation_history) == 1 and stream_request.messages:
                # Only add initial messages if this appears to be a new session
                for msg in stream_request.messages:
                    role = msg.get("role", "user").lower()
                    content = msg.get("content", "")
                    if (
                        content and content != stream_request.prompt
                    ):  # Avoid duplicating the current prompt
                        memory_store.add_message(session_id, role, content)

                # Refresh conversation history after adding initial messages
                conversation_history = memory_store.get_messages(session_id)

            # Get messages formatted for Gemini API (excluding the current user message for context)
            # We want to use all stored messages except the last one (current prompt) as context
            context_messages = (
                conversation_history[:-1] if len(conversation_history) > 1 else []
            )

            # Generate streaming response using Gemini with memory context
            full_response = ""
            async for chunk in gemini_service.generate_streaming_response(
                stream_request.prompt,
                context_messages,
            ):
                full_response += chunk
                # Send chunk as Server-Sent Event
                yield f"data: {json.dumps({'chunk': chunk, 'session_id': session_id})}\n\n"

            # Add AI response to memory store
            memory_store.add_message(session_id, "assistant", full_response)

            # Send completion event with session info
            yield f"data: {json.dumps({
                'done': True, 
                'session_id': session_id, 
                'full_response': full_response,
                'message_count': len(memory_store.get_messages(session_id))
            })}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'session_id': session_id})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
