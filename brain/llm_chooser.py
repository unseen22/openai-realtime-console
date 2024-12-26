from typing import Optional
from .groq_tool import GroqTool
from .local_llm import LocalLLM
from .open_ai_tool import OpenAITool
from brain.perplexity_tool import PerplexityHandler
from langsmith import traceable
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check LangSmith configuration
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "openai-realtime-console")

print(f"\nLangSmith Configuration in LLMChooser:")
print(f"- Tracing Enabled: {LANGCHAIN_TRACING_V2}")
print(f"- Project: {LANGCHAIN_PROJECT}")
print(f"- API Key: {LANGCHAIN_API_KEY[:8]}... (truncated)" if LANGCHAIN_API_KEY else "- API Key: Not Set")

class LLMChooser:
    def __init__(self):
        """Initialize LLM chooser with available models"""
        if not LANGCHAIN_TRACING_V2:
            print("\n⚠️ Warning: LANGCHAIN_TRACING_V2 is not enabled. Set it to 'true' in .env")
        if not LANGCHAIN_API_KEY:
            print("\n⚠️ Warning: LANGCHAIN_API_KEY is not set in .env")
            
        self.groq = GroqTool()
        self.local_llm = LocalLLM(base_url="http://localhost:1234/v1", api_key="lm-studio")
        self.openai = OpenAITool()
        self.perplexity_tool = PerplexityHandler("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")
        self.project_name = LANGCHAIN_PROJECT
        print(f"LLMChooser initialized with project: {self.project_name}")

    def get_llm(self, provider: str = "groq", **kwargs) -> any:
        """Get the specified LLM client"""
        print(f"Getting LLM client for provider: {provider}")
        if provider.lower() == "groq":
            return self.groq
        elif provider.lower() == "local":
            if self.local_llm is None:
                self.local_llm = LocalLLM(
                    base_url="http://localhost:1234/v1",
                    api_key="lm-studio"
                )
            return self.local_llm
        elif provider.lower() == "openai":
            if not hasattr(self, 'openai'):
                self.openai = OpenAITool()
            return self.openai
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
            
    @traceable(project_name=os.getenv("LANGCHAIN_PROJECT", "openai-realtime-console"))
    def generate_text(self, provider="openai", **kwargs):
        """Generate text using the specified provider with tracing enabled."""
        print(f"Generating text with {provider} (traced) in project: {self.project_name}")
        try:
            if provider == "openai":
                print("Using OpenAI with tracing")
                kwargs["langsmith_extra"] = {"project_name": self.project_name}
                return self.openai.generate_text(**kwargs)
            elif provider == "groq":
                print("Using Groq with tracing")
                #kwargs["langsmith_extra"] = {"project_name": self.project_name}
                return self.groq.generate_text(**kwargs)
            elif provider == "perplexity":
                print("Using Perplexity with tracing")
                kwargs["langsmith_extra"] = {"project_name": self.project_name}
                return self.perplexity_tool.generate_text(**kwargs)
            else:
                raise ValueError(f"Unknown provider: {provider}")
        except Exception as e:
            print(f"Error in generate_text with {provider}: {str(e)}")
            raise
