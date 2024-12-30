import os
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
import openai
from langsmith.wrappers import wrap_openai
from langsmith import traceable
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check if LangSmith tracing is enabled and properly configured
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "openai-realtime-console")

# Print tracing configuration
print(f"\nLangSmith Configuration in OpenAITool:")
print(f"- Tracing Enabled: {LANGCHAIN_TRACING_V2}")
print(f"- Project: {LANGCHAIN_PROJECT}")
print(f"- Endpoint: {LANGCHAIN_ENDPOINT}")
print(f"- API Key: {LANGCHAIN_API_KEY[:8]}... (truncated)" if LANGCHAIN_API_KEY else "- API Key: Not Set")
print(f"- API Key Set: {'Yes' if LANGCHAIN_API_KEY else 'No'}")

if not LANGCHAIN_TRACING_V2:
    print("\n⚠️ Warning: LANGCHAIN_TRACING_V2 is not enabled. Set it to 'true' in .env")
if not LANGCHAIN_API_KEY:
    print("\n⚠️ Warning: LANGCHAIN_API_KEY is not set in .env")

class OpenAITool:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAITool with official OpenAI client"""
        self.api_key = api_key or self._get_api_key()
        self.client = wrap_openai(AsyncOpenAI(api_key=self.api_key))
        self.project_name = LANGCHAIN_PROJECT
        print(f"OpenAITool initialized with project: {self.project_name}")
        
        self.available_models = {
            "GPT-4": "gpt-4",
            "GPT-4 Turbo": "gpt-4-turbo-preview",
            "GPT-3.5 Turbo": "gpt-3.5-turbo",
            "GPT-3.5 Turbo 16K": "gpt-3.5-turbo-16k",
            "GPT-4 Vision": "gpt-4-vision-preview"
        }

    def _get_api_key(self) -> str:
        """Get API key from environment variable"""
        api_key = "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"  # Replace with your OpenAI API key
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        return api_key

    @traceable(project_name=LANGCHAIN_PROJECT)
    async def generate_text(self, prompt=None, messages=None, **kwargs) -> str:
        """Generate text with tracing enabled"""
        print(f"Generating text in project: {self.project_name}")
        try:
            if messages is None and prompt is not None:
                messages = [{"role": "user", "content": prompt}]
            elif messages is None and prompt is None:
                raise ValueError("Either prompt or messages must be provided")

            # Add project name to langsmith_extra if not present
            if "langsmith_extra" not in kwargs:
                kwargs["langsmith_extra"] = {"project_name": self.project_name}
            
            response = await self.chat_completion(messages=messages, **kwargs)
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error in generate_text: {str(e)}")
            raise

    @traceable(project_name=LANGCHAIN_PROJECT)
    async def chat_completion(
        self,
        messages: list,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.1,
        max_tokens: int = 1024,
        stream: bool = False,
        response_format: dict = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat completion request with tracing"""
        try:
            print(f"Starting chat completion with model: {model} in project: {self.project_name}")
            completion_args = {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
                "response_format": response_format,
                **kwargs
            }
            
            response = await self.client.chat.completions.create(**completion_args)
            print("Chat completion successful")
            return response
            
        except Exception as e:
            print(f"Error calling OpenAI API: {str(e)}")
            raise
