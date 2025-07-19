import asyncio
import requests
from typing import Dict, List, Optional

class ChatCompletionMessage:
    """Represents a chat completion message"""
    def __init__(self, content: str, role: str = "assistant"):
        self.content = content
        self.role = role

class ChatCompletionChoice:
    """Represents a chat completion choice"""
    def __init__(self, message: ChatCompletionMessage, finish_reason: str = "stop"):
        self.message = message
        self.finish_reason = finish_reason

class ChatCompletionResponse:
    """Represents a chat completion response"""
    def __init__(self, choices: List[ChatCompletionChoice], model: str = "llama"):
        self.choices = choices
        self.model = model

class CompletionMessage:
    """Represents a completion message with text content"""
    def __init__(self, content: str):
        self.content = Content(content)

class Content:
    """Represents text content"""
    def __init__(self, text: str):
        self.text = text

class CompletionResponse:
    """Represents a completion response"""
    def __init__(self, content: str, model: str = "llama"):
        self.completion_message = CompletionMessage(content)
        self.model = model

class AsyncLlamaAPIClient:
    """Async client for Llama API"""

    def __init__(self, api_key: str, base_url: str = "https://api.llama.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self._chat = None

    async def chat_completions_create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 200,
        temperature: float = 0.7,
        max_completion_tokens: Optional[int] = None,
        **kwargs
    ) -> CompletionResponse:
        """Create chat completion"""

        # Use max_completion_tokens if provided, otherwise use max_tokens
        token_limit = max_completion_tokens or max_tokens

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": token_limit,
            "temperature": temperature,
            **kwargs
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        try:
            def make_request():
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                return response

            response = await loop.run_in_executor(None, make_request)

            if response.status_code == 200:
                data = response.json()

                # Extract content from response
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                else:
                    content = "No response generated"

                return CompletionResponse(
                    content=content,
                    model=data.get("model", model)
                )
            else:
                # Handle error response
                error_text = response.text
                raise LlamaAPIError(f"API Error {response.status_code}: {error_text}")

        except requests.exceptions.Timeout:
            raise LlamaAPIError("Request timeout")
        except requests.exceptions.RequestException as e:
            raise LlamaAPIError(f"API request failed: {str(e)}") from e

    class Chat:
        """Chat namespace for completions"""
        def __init__(self, client):
            self.client = client
            self.completions = self.Completions(client)

        class Completions:
            """Completions namespace"""
            def __init__(self, client):
                self.client = client

            async def create(self, **kwargs):
                """Create chat completion"""
                return await self.client.chat_completions_create(**kwargs)

    @property
    def chat(self):
        """Get chat namespace"""
        if self._chat is None:
            self._chat = self.Chat(self)
        return self._chat

class LlamaAPIError(Exception):
    """Custom exception for Llama API errors"""
    pass
