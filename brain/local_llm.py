from openai import OpenAI

class LocalLLM:
    def __init__(self, base_url: str, api_key: str):
        """Initialize OpenAI client with local server settings"""
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def chat(self):
        """Return chat completions interface"""
        return self.client.chat

    def completions(self):
        """Return completions interface"""
        return self.client.completions

