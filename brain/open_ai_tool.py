from typing import Dict, Any, Optional
from openai import OpenAI

class OpenAITool:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAITool with official OpenAI client"""
        self.api_key = api_key or self._get_api_key()
        self.client = OpenAI(api_key=self.api_key)
        self.available_models = {
            "GPT-4": "gpt-4",
            "GPT-4 Turbo": "gpt-4-turbo-preview",
            "GPT-3.5 Turbo": "gpt-3.5-turbo",
            "GPT-3.5 Turbo 16K": "gpt-3.5-turbo-16k",
            "GPT-4 Vision": "gpt-4-vision-preview"
        }
        
        # Default JSON schema for structured outputs
        self.default_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "confidence": {"type": "number"},
                                "keywords": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["confidence", "keywords"]
                        }
                    },
                    "required": ["content", "metadata"],
                    "additionalProperties": False
                }
            }
        }

    def _get_api_key(self) -> str:
        """Get API key from environment variable"""
        api_key = ""
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        return api_key

    def chat_completion(
        self,
        messages: list,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.1,
        max_tokens: int = 1024,
        stream: bool = False,
        response_format: dict = None
    ) -> Dict[str, Any]:
        """
        Send a chat completion request using OpenAI client with structured output support
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use for completion
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response
            response_format: Optional custom JSON schema for response format
            
        Returns:
            API response as dictionary with structured output
        """
        try:
            completion_args = {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
                "response_format": response_format or self.default_schema
            }
            
            response = self.client.chat.completions.create(**completion_args)
            return response
            
        except Exception as e:
            print(f"Error calling OpenAI API: {str(e)}")
            raise

    def generate_text(self, prompt=None, messages=None, **kwargs) -> str:
        """
        Text generation with either a single prompt or a list of messages
        
        Args:
            prompt: Text prompt (optional)
            messages: List of message dictionaries (optional)
            **kwargs: Additional arguments passed to chat_completion
            
        Returns:
            Generated text response in structured JSON format
        """
        if messages is None and prompt is not None:
            messages = [{"role": "user", "content": prompt}]
        elif messages is None and prompt is None:
            raise ValueError("Either prompt or messages must be provided")
            
        response = self.chat_completion(messages, **kwargs)
        
        try:
            return response.choices[0].message.content
        except (AttributeError, IndexError) as e:
            print(f"Error parsing response: {str(e)}")
            return ""
