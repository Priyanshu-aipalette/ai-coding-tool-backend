#!/usr/bin/env python3
"""
Test script for MemoryStore functionality
Demonstrates the 5-message limit and memory persistence across calls
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory_store import MemoryStore
from datetime import datetime


def test_memory_store():
    """Test the MemoryStore functionality"""
    print("🧪 Testing MemoryStore functionality...\n")

    # Initialize memory store with 5 message limit
    memory_store = MemoryStore(max_messages_per_session=5)

    # Test 1: Create session and add messages
    print("1. Testing session creation and message addition...")
    session_id = "test-session-123"

    # Add messages beyond the limit to test truncation
    messages = [
        ("user", "Hello, what's 2+2?"),
        ("assistant", "2+2 equals 4."),
        ("user", "What about 3+3?"),
        ("assistant", "3+3 equals 6."),
        ("user", "And 4+4?"),
        ("assistant", "4+4 equals 8."),
        ("user", "Finally, what's 5+5?"),  # This should push out the first message
        ("assistant", "5+5 equals 10."),  # This should push out the second message
    ]

    for role, content in messages:
        success = memory_store.add_message(session_id, role, content)
        print(f"  Added {role} message: '{content}' - Success: {success}")

    print(
        f"\n  Total messages in session: {len(memory_store.get_messages(session_id))}"
    )
    print(
        f"  Expected: 5 (due to limit), Got: {len(memory_store.get_messages(session_id))}"
    )

    # Test 2: Verify message limit enforcement
    print("\n2. Testing 5-message limit enforcement...")
    all_messages = memory_store.get_messages(session_id)

    print("  Current messages in memory:")
    for i, msg in enumerate(all_messages, 1):
        print(f"    {i}. {msg.role.value}: {msg.content}")

    # Verify the first 3 messages were removed
    first_message_content = all_messages[0].content if all_messages else ""
    expected_first = "And 4+4?"  # Should be the 5th message we added

    print(f"\n  First message in memory: '{first_message_content}'")
    print(f"  Expected first message: '{expected_first}'")
    print(
        f"  Oldest messages correctly removed: {first_message_content == expected_first}"
    )

    # Test 3: Get messages for Gemini format
    print("\n3. Testing Gemini format conversion...")
    gemini_messages = memory_store.get_messages_for_gemini(session_id)

    print("  Messages in Gemini format:")
    for i, msg in enumerate(gemini_messages, 1):
        print(f"    {i}. {msg['role']}: {msg['parts'][0]}")

    # Test 4: Session info
    print("\n4. Testing session info...")
    session_info = memory_store.get_session_info(session_id)
    if session_info:
        print(f"  Session ID: {session_info['session_id']}")
        print(f"  Message count: {session_info['message_count']}")
        print(f"  Max messages: {session_info['max_messages']}")
        print(f"  Created at: {session_info['created_at']}")
        print(f"  Updated at: {session_info['updated_at']}")

    # Test 5: Memory persistence simulation
    print("\n5. Testing memory persistence simulation (like /stream calls)...")

    # Simulate multiple /stream calls
    stream_calls = [
        "What's the weather like?",
        "Tell me a joke",
        "Explain quantum physics",
    ]

    for i, prompt in enumerate(stream_calls, 1):
        print(f"\n  Simulating stream call {i}: '{prompt}'")

        # Add user message
        memory_store.add_message(session_id, "user", prompt)

        # Get context for AI (exclude last message which is the current prompt)
        context_messages = memory_store.get_messages(session_id)[:-1]
        print(f"    Context messages count: {len(context_messages)}")

        # Simulate AI response
        ai_response = f"AI response to: {prompt}"
        memory_store.add_message(session_id, "assistant", ai_response)

        # Show current memory state
        current_messages = memory_store.get_messages(session_id)
        print(f"    Total messages in memory: {len(current_messages)}")
        print(f"    Latest messages:")
        for msg in current_messages[-2:]:  # Show last 2 messages
            print(f"      {msg.role.value}: {msg.content}")

    # Test 6: Multiple sessions
    print("\n6. Testing multiple sessions...")
    session2_id = "test-session-456"

    memory_store.add_message(session2_id, "user", "Hello from session 2")
    memory_store.add_message(session2_id, "assistant", "Hello back from session 2")

    print(f"  Session 1 messages: {len(memory_store.get_messages(session_id))}")
    print(f"  Session 2 messages: {len(memory_store.get_messages(session2_id))}")
    print(f"  Total sessions: {memory_store.get_session_count()}")

    # Test 7: Clear session
    print("\n7. Testing session clearing...")
    memory_store.clear_session_messages(session2_id)
    print(
        f"  Session 2 messages after clear: {len(memory_store.get_messages(session2_id))}"
    )

    print("\n✅ All memory store tests completed!")


def simulate_stream_endpoint():
    """Simulate how the /stream endpoint would use the memory store"""
    print("\n🚀 Simulating /stream endpoint usage...\n")

    memory_store = MemoryStore(max_messages_per_session=5)
    session_id = "stream-session-789"

    # Simulate multiple API calls to /stream endpoint
    api_calls = [
        {"messages": [], "prompt": "Hello, who are you?"},  # First call, no history
        {
            "messages": [],  # Subsequent calls rely on memory store
            "prompt": "Can you help me with Python?",
        },
        {"messages": [], "prompt": "Write a function to reverse a string"},
        {"messages": [], "prompt": "Now optimize that function"},
        {"messages": [], "prompt": "What other string methods are useful?"},
        {
            "messages": [],
            "prompt": "Give me examples of each method",  # This should push out early messages
        },
    ]

    for i, call in enumerate(api_calls, 1):
        print(f"API Call {i}: '{call['prompt']}'")

        # Add user message to memory
        memory_store.add_message(session_id, "user", call["prompt"])

        # Get conversation history (exclude current user message for context)
        conversation_history = memory_store.get_messages(session_id)[:-1]

        print(f"  Context messages: {len(conversation_history)}")
        if conversation_history:
            print(
                f"  Last context: {conversation_history[-1].role.value}: {conversation_history[-1].content[:50]}..."
            )

        # Simulate AI response
        ai_response = f"AI response {i}: Responding to '{call['prompt'][:30]}...'"
        memory_store.add_message(session_id, "assistant", ai_response)

        # Show memory state
        total_messages = memory_store.get_messages(session_id)
        print(f"  Total messages in memory: {len(total_messages)}")
        print(f"  Memory limit enforced: {len(total_messages) <= 5}")
        print()

    print("Final memory state:")
    final_messages = memory_store.get_messages(session_id)
    for i, msg in enumerate(final_messages, 1):
        print(f"  {i}. {msg.role.value}: {msg.content}")

    print(f"\n✅ Stream endpoint simulation completed!")
    print(f"   Memory properly maintained with {len(final_messages)} messages (max 5)")


if __name__ == "__main__":
    test_memory_store()
    simulate_stream_endpoint()
