from typing import Optional
from groq_tool import GroqTool
from local_llm import LocalLLM
from open_ai_tool import OpenAITool
class LLMChooser:
    def __init__(self):
        """Initialize LLM chooser with available models"""
        self.groq = GroqTool()
        self.local_llm = LocalLLM(base_url="http://localhost:1234/v1", api_key="lm-studio")
        self.openai = OpenAITool()
    def get_llm(self, provider: str = "groq", **kwargs) -> any:
        """
        Get the specified LLM client
        
        Args:
            provider: LLM provider to use ('groq', 'local', or 'openai')
            **kwargs: Additional arguments to pass to the LLM client
            
        Returns:
            LLM client instance
        """
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
            
    def generate_text(self, prompt: str = None, provider: str = "groq", messages: list = None, **kwargs) -> str:
        """
        Generate text using the specified LLM
        
        Args:
            prompt: Text prompt (optional)
            provider: LLM provider to use
            messages: List of message dictionaries (optional)
            **kwargs: Additional arguments passed to the LLM
            
        Returns:
            Generated text response
        """
        llm = self.get_llm(provider)
        
        if provider.lower() == "groq":
            # Use GroqTool's generate_text which handles both prompt and messages
            return llm.generate_text(prompt=prompt, messages=messages, **kwargs)
        elif provider.lower() == "openai":
            # Use OpenAITool's generate_text method
            return llm.generate_text(prompt=prompt, messages=messages, **kwargs)
        else:
            # For local LLM, use the chat interface
            if messages is None and prompt is not None:
                messages = [{"role": "user", "content": prompt}]
            elif messages is None and prompt is None:
                raise ValueError("Either prompt or messages must be provided")
                
            completion = llm.chat().completions.create(
                model=kwargs.get("model", "redponike/phi-4-GGUF"),
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 1024)
            )
            return completion.choices[0].message.content
