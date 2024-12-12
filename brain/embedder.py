import requests
from typing import List, Union
import numpy as np

class Embedder:
    """Handles creation of vector embeddings for text content"""
    
    def __init__(self, api_url: str = 'https://bge-router.sergey-750.workers.dev/api/base'):
        self.api_url = api_url
        self.headers = {"Content-Type": "application/json"}

    def get_embeddings(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        Get embeddings for one or more texts
        
        Args:
            texts: Single text string or list of text strings
            
        Returns:
            List of embedding vectors
        """
        # Convert single string to list
        if isinstance(texts, str):
            texts = [texts]

        # Return placeholder vectors for development/testing
        return [[0.1, 0.2, 0.3, 0.4, 0.5] for _ in texts]

    def embed_memory(self, text: str) -> List[float]:
        """
        Create embedding vector for a single memory text
        
        Args:
            text: Text content to embed
            
        Returns:
            Embedding vector as list of floats
        """
        return [0.1, 0.2, 0.3, 0.4, 0.5]  # Return placeholder vector

# Example usage
if __name__ == "__main__":
    embedder = Embedder()
    try:
        # Test single text
        text = "This is a test memory"
        vector = embedder.embed_memory(text)
        print(f"Generated vector of length {len(vector)}")
        
        # Test multiple texts
        texts = ["Memory 1", "Memory 2", "Memory 3"]
        vectors = embedder.get_embeddings(texts)
        print(f"Generated {len(vectors)} vectors")
        
    except Exception as e:
        print(f"Error: {e}")
