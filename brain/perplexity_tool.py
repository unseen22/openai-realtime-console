import requests
from typing import Optional

class PerplexityHandler:
    def __init__(self, api_key: str):
        self.api_key = "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"
        self.base_url = "https://api.perplexity.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.system_prompt = "You are a helpful assistant."  # Default prompt

    def generate_completion(self, messages: list, model: str, temperature: float) -> str:
        """Generate chat completion using Perplexity API"""
        try:
            # Format messages to ensure alternating user/assistant with system at start
            formatted_messages = []
            system_messages = []
            conversation_messages = []
            
            # Separate system and conversation messages
            for msg in messages:
                if msg["role"] == "system":
                    system_messages.append(msg)
                else:
                    conversation_messages.append(msg)
            
            # Add system messages first
            formatted_messages.extend(system_messages)
            
            # Add conversation messages ensuring alternation
            for i, msg in enumerate(conversation_messages):
                if i > 0 and msg["role"] == conversation_messages[i-1]["role"]:
                    continue  # Skip consecutive messages with same role
                formatted_messages.append(msg)
            
            payload = {
                "model": model,
                "messages": formatted_messages,
                "temperature": temperature,
                "max_tokens": 4000,
                "top_p": 0.9,
                "stream": False,
                "presence_penalty": 0,
                "frequency_penalty": 1,
                "return_images": False,
                "return_related_questions": False
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                st.error(f"Perplexity API error: {response.text}")
                return None
                
        except Exception as e:
            st.error(f"Error generating completion with Perplexity: {str(e)}")
            return None

    @property
    def available_models(self):
        """Available Perplexity models with their specifications"""
        return {
            # Sonar Online Models (with search capability)
            "Sonar Small Online": "llama-3.1-sonar-small-128k-online",
            "Sonar Large Online": "llama-3.1-sonar-large-128k-online",
            "Sonar Huge Online": "llama-3.1-sonar-huge-128k-online",
            
            # Sonar Chat Models
            "Sonar Small Chat": "llama-3.1-sonar-small-128k-chat",
            "Sonar Large Chat": "llama-3.1-sonar-large-128k-chat",
            
            # Open Source Models
            "LLaMA 3.1 8B": "llama-3.1-8b-instruct",
            "LLaMA 3.1 70B": "llama-3.1-70b-instruct"
        }

    @property
    def model_context_lengths(self):
        """Context length limits for each model"""
        return {
            "llama-3.1-sonar-small-128k-online": 127072,
            "llama-3.1-sonar-large-128k-online": 127072,
            "llama-3.1-sonar-huge-128k-online": 127072,
            "llama-3.1-sonar-small-128k-chat": 127072,
            "llama-3.1-sonar-large-128k-chat": 127072,
            "llama-3.1-8b-instruct": 131072,
            "llama-3.1-70b-instruct": 131072
        }

    def get_model_info(self, model_name: str) -> dict:
        """Get detailed information about a specific model"""
        model_info = {
            "llama-3.1-sonar-small-128k-online": {
                "parameters": "8B",
                "context_length": 127072,
                "type": "Chat Completion with Search",
                "features": ["Online Search", "Real-time Information"]
            },
            "llama-3.1-sonar-large-128k-online": {
                "parameters": "70B",
                "context_length": 127072,
                "type": "Chat Completion with Search",
                "features": ["Online Search", "Real-time Information"]
            },
            "llama-3.1-sonar-huge-128k-online": {
                "parameters": "405B",
                "context_length": 127072,
                "type": "Chat Completion with Search",
                "features": ["Online Search", "Real-time Information"]
            },
            # Add other models...
        }
        return model_info.get(model_name, {})