# MemoryStore Usage Guide

## Overview

The `MemoryStore` class provides in-memory conversation persistence for the AI Coding Agent. It automatically maintains the last 5 messages per session, enabling contextual conversations across multiple API calls.

## Key Features

- ✅ **5-Message Limit**: Keeps only the last 5 messages per session
- ✅ **Automatic Memory Management**: Removes oldest messages when limit exceeded
- ✅ **Session Persistence**: Maintains conversation across multiple `/stream` calls
- ✅ **Multi-Session Support**: Handles multiple independent conversation sessions
- ✅ **Gemini Integration**: Provides formatted context for Gemini API calls

## MemoryStore API

### Core Methods

```python
# Add a message to a session
memory_store.add_message(session_id: str, role: str, content: str) -> bool

# Get messages from a session
memory_store.get_messages(session_id: str, limit: Optional[int] = None) -> List[ChatMessage]

# Get messages formatted for Gemini API
memory_store.get_messages_for_gemini(session_id: str) -> List[dict]

# Create a session
session_id = memory_store.create_session() -> str

# Get session information
session_info = memory_store.get_session_info(session_id: str) -> Optional[dict]
```

## Usage with `/stream` Endpoint

### 1. Basic Usage (No Session ID)

```bash
curl -X POST "http://localhost:8000/api/v1/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [],
    "prompt": "Hello, what can you help me with?"
  }'
```

**Response:**
- Creates a new session automatically
- Returns `session_id` for subsequent calls
- No conversation history (first message)

### 2. Persistent Conversation (With Session ID)

```bash
# First call
curl -X POST "http://localhost:8000/api/v1/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [],
    "prompt": "Can you help me write a Python function?",
    "session_id": "user-123-session"
  }'

# Second call (with memory context)
curl -X POST "http://localhost:8000/api/v1/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [],
    "prompt": "Make it handle edge cases",
    "session_id": "user-123-session"
  }'
```

**Benefits:**
- Second call has context from first call
- AI understands "it" refers to the Python function
- Conversation flows naturally

### 3. Frontend Integration

```javascript
// Using the sendPrompt function from frontend
const sendPromptWithMemory = async (prompt, sessionId = null) => {
  const requestBody = {
    messages: [], // Let memory store handle history
    prompt: prompt,
    session_id: sessionId || `user-${Date.now()}`
  };

  const response = await fetch('/api/v1/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody)
  });

  // Handle streaming response...
};
```

## Memory Management Example

```python
from memory_store import MemoryStore

# Initialize with 5-message limit
memory_store = MemoryStore(max_messages_per_session=5)
session_id = "conversation-123"

# Conversation flow
messages = [
    ("user", "What's 2+2?"),
    ("assistant", "2+2 equals 4."),
    ("user", "What about 3+3?"),
    ("assistant", "3+3 equals 6."),
    ("user", "And 4+4?"),
    ("assistant", "4+4 equals 8."),
    ("user", "Finally, 5+5?"),    # Pushes out first message
    ("assistant", "5+5 equals 10.") # Pushes out second message
]

for role, content in messages:
    memory_store.add_message(session_id, role, content)

# Result: Only last 5 messages kept
final_messages = memory_store.get_messages(session_id)
print(f"Messages in memory: {len(final_messages)}")  # Output: 5
```

## Session Management

### Session Information

```python
session_info = memory_store.get_session_info(session_id)
# Returns:
# {
#   "session_id": "conversation-123",
#   "message_count": 5,
#   "created_at": "2025-01-01T10:00:00",
#   "updated_at": "2025-01-01T10:05:00",
#   "max_messages": 5
# }
```

### Clear Session Messages

```python
# Clear all messages but keep session
memory_store.clear_session_messages(session_id)

# Delete entire session
memory_store.delete_session(session_id)
```

## How `/stream` Uses Memory

1. **Add User Message**: Current prompt added to memory
2. **Get Context**: Retrieve conversation history (excluding current prompt)
3. **Send to Gemini**: Use context messages for AI generation
4. **Add AI Response**: Store AI response in memory
5. **Enforce Limit**: Automatically remove oldest messages if > 5

```python
# Simplified /stream endpoint logic
def stream_endpoint(prompt, session_id):
    # Step 1: Add user message
    memory_store.add_message(session_id, "user", prompt)
    
    # Step 2: Get context (exclude current message)
    context = memory_store.get_messages(session_id)[:-1]
    
    # Step 3: Generate AI response with context
    ai_response = gemini_service.generate_response(prompt, context)
    
    # Step 4: Add AI response to memory
    memory_store.add_message(session_id, "assistant", ai_response)
    
    # Memory automatically enforces 5-message limit
```

## Benefits

### For Users
- **Contextual Conversations**: AI remembers recent context
- **Natural Flow**: No need to repeat information
- **Session Persistence**: Conversations persist across page reloads

### For System
- **Memory Efficient**: Only 5 messages per session
- **Fast Access**: In-memory storage for quick retrieval
- **Scalable**: Automatic cleanup of old sessions
- **Simple Integration**: Easy to use with existing endpoints

## Configuration

```python
# Customize memory store settings
memory_store = MemoryStore(
    max_sessions=1000,              # Maximum number of sessions
    session_timeout_hours=24,       # Session expiration time
    max_messages_per_session=5      # Messages per session limit
)
```

## Testing

Run the test script to verify functionality:

```bash
cd backend
python test_memory_store.py
```

This will demonstrate:
- 5-message limit enforcement
- Memory persistence across calls
- Multiple session handling
- Gemini format conversion
- Session management features 