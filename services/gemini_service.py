import google.generativeai as genai
from typing import List, AsyncGenerator, Optional
import asyncio
import json
from models.chat_models import ChatMessage, MessageRole


class GeminiService:
    """Service for interacting with Gemini 2.5 API"""

    def __init__(self):
        self.model_name = "gemini-2.0-flash-exp"
        self.system_prompt = """You are Claude, an AI assistant created by Anthropic. You're a coding expert and helpful assistant.

Key traits:
- Be helpful, harmless, and honest
- Provide clear, accurate information
- When writing code, explain it clearly
- Use proper formatting for code blocks
- Be concise but thorough"""

    def _convert_messages_to_gemini_format(
        self, messages: List[ChatMessage]
    ) -> List[dict]:
        """Convert ChatMessage objects to Gemini API format"""
        gemini_messages = []
        for message in messages:
            role = "user" if message.role == MessageRole.USER else "model"
            gemini_messages.append({"role": role, "parts": [message.content]})
        return gemini_messages

    async def _simulate_smoother_streaming(
        self, text: str
    ) -> AsyncGenerator[str, None]:
        """Break large chunks into smaller pieces for smoother streaming effect"""
        if not text:
            return

        # Even more aggressive: stream word by word or character by character for code
        if "```" in text or "def " in text or "import " in text:
            # For code, be more granular
            words = text.split(" ")
            for word in words:
                if word.strip():  # Skip empty words
                    yield word + " "
                    await asyncio.sleep(0.03)  # 30ms delay for code
        else:
            # For regular text, stream 1-2 words at a time
            words = text.split(" ")
            current_chunk = ""

            for i, word in enumerate(words):
                current_chunk += word

                # Add space except for last word
                if i < len(words) - 1:
                    current_chunk += " "

                # Yield after 1-2 words or at punctuation
                if (
                    len(current_chunk.split()) >= 1
                    or any(
                        char in word for char in [".", "!", "?", "\n", ":", ";", ","]
                    )
                    or i == len(words) - 1
                ):

                    yield current_chunk
                    current_chunk = ""

                    # Small delay for more natural streaming feel
                    await asyncio.sleep(0.08)  # 80ms delay between chunks

    async def generate_response(
        self, user_message: str, conversation_history: List[ChatMessage] = None
    ) -> str:
        """Generate a non-streaming response"""
        try:
            model = genai.GenerativeModel(
                self.model_name, system_instruction=self.system_prompt
            )

            # Prepare conversation history
            messages = conversation_history or []
            messages.append(ChatMessage(role=MessageRole.USER, content=user_message))

            # Convert to Gemini format
            gemini_messages = self._convert_messages_to_gemini_format(messages)

            # Generate response
            response = await asyncio.to_thread(
                model.generate_content,
                gemini_messages,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                ),
            )

            return response.text

        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")

    async def generate_streaming_response(
        self, user_message: str, conversation_history: List[ChatMessage] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response with enhanced smoothness"""
        try:
            model = genai.GenerativeModel(
                self.model_name, system_instruction=self.system_prompt
            )

            # Prepare conversation history
            messages = conversation_history or []
            messages.append(ChatMessage(role=MessageRole.USER, content=user_message))

            # Convert to Gemini format
            gemini_messages = self._convert_messages_to_gemini_format(messages)

            # Generate streaming response
            response = await asyncio.to_thread(
                model.generate_content,
                gemini_messages,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                ),
                stream=True,
            )

            # Process each chunk from Gemini and break it down further
            for chunk in response:
                if chunk.text:
                    # Break the chunk into smaller pieces for smoother streaming
                    async for small_chunk in self._simulate_smoother_streaming(
                        chunk.text
                    ):
                        yield small_chunk

        except Exception as e:
            yield f"Error: {str(e)}"
