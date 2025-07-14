import google.generativeai as genai
from typing import List, AsyncGenerator, Optional
import asyncio
import json
from models.chat_models import ChatMessage, MessageRole


class GeminiService:
    """Service for interacting with Gemini 2.5 API"""

    def __init__(self):
        self.model_name = "gemini-2.0-flash-exp"
        self.system_prompt = """You are a helpful AI coding assistant similar to Claude. You can:
- Help with coding problems and debugging
- Explain code concepts and best practices
- Write code in various programming languages
- Review and improve existing code
- Provide technical guidance and solutions

Be helpful, accurate, and provide clear explanations. When writing code, include comments and explain your reasoning."""

    def _convert_messages_to_gemini_format(
        self, messages: List[ChatMessage]
    ) -> List[dict]:
        """Convert chat messages to Gemini API format"""
        gemini_messages = []

        for msg in messages:
            if msg.role == MessageRole.USER:
                gemini_messages.append({"role": "user", "parts": [msg.content]})
            elif msg.role == MessageRole.ASSISTANT:
                gemini_messages.append({"role": "model", "parts": [msg.content]})

        return gemini_messages

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
        """Generate a streaming response"""
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

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            yield f"Error: {str(e)}"
