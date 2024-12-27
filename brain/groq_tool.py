from typing import Dict, Any, Optional
from groq import Groq
from langsmith import traceable

class GroqTool:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize GroqTool with official Groq client"""
        self.api_key = api_key or self._get_api_key()
        self.client = Groq(api_key=self.api_key)
        self.available_models = {
            "LLaMA3 70B 7.1": "llama-3.1-70b-versatile",
            "LLaMA3 Groq 70B (Tool Use)": "llama3-groq-70b-8192-tool-use-preview",
            "LLaMA 3.2 90B Text": "llama-3.2-90b-text-preview",
            "LLaMA 3.2 90B Vision": "llama-3.2-90b-vision-preview",
            "Gemma 2 9B": "gemma2-9b-it",
            "Gemma 7B": "gemma-7b-it",
            "LLaMA3 Groq 8B (Tool Use)": "llama3-groq-8b-8192-tool-use-preview",
            "LLaMA 3.1 70B Versatile": "llama-3.1-70b-versatile",
            "LLaMA 3.1 8B Instant": "llama-3.3-70b-versatile",
            "LLaMA 3.2 1B": "llama-3.2-1b-preview",
            "LLaMA 3.2 3B": "llama-3.2-3b-preview",
            "LLaMA 3.2 11B Vision": "llama-3.2-11b-vision-preview",
            "LLaMA Guard 3 8B": "llama-guard-3-8b",
            "LLaMA3 8B": "llama3-8b-8192",
            "Mixtral 8x7B": "mixtral-8x7b-32768"
        }

    def _get_api_key(self) -> str:
        """Get API key from environment variable"""
        api_key = "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"#"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"#"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"#"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"#  #"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"
        
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        return api_key

    def chat_completion(
        self,
        messages: list,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.1,
        max_tokens: int = 1024,
        stream: bool = False,
        response_format: dict = None
    ) -> Dict[str, Any]:
        """
        Send a chat completion request using Groq client
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use for completion
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response
            response_format: Optional format specification for the response
            
        Returns:
            API response as dictionary
        """
        try:
            completion_args = {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }
            
            if response_format:
                completion_args["response_format"] = response_format
            
            response = self.client.chat.completions.create(**completion_args)
            
            # Convert the response object to a dictionary format
            return {
                "choices": [{
                    "message": {
                        "content": response.choices[0].message.content,
                        "role": response.choices[0].message.role
                    },
                    "index": 0
                }]
            }
            
        except Exception as e:
            print(f"Error calling Groq API: {str(e)}")
            raise
    @traceable
    def generate_text(self, prompt=None, messages=None, **kwargs) -> str:
        """
        Text generation with either a single prompt or a list of messages
        
        Args:
            prompt: Text prompt (optional)
            messages: List of message dictionaries (optional)
            **kwargs: Additional arguments passed to chat_completion
            
        Returns:
            Generated text response
        """
        if messages is None and prompt is not None:
            messages = [{"role": "user", "content": prompt}]
        elif messages is None and prompt is None:
            raise ValueError("Either prompt or messages must be provided")
            
        response = self.chat_completion(messages, **kwargs)
        
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            print(f"Error parsing response: {str(e)}")
            return ""
