import aiohttp
from typing import List, Union
import numpy as np
from numpy.linalg import norm
import json
from openai import AsyncOpenAI
import asyncio
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
import os
from dotenv import load_dotenv

class Embedder2:
    """Handles creation of vector embeddings for text content"""
    
    def __init__(self, api_url: str = 'https://bge-router.sergey-750.workers.dev/api/base'):
        self.api_url = api_url
        self.headers = {"Content-Type": "application/json"}
        self.vector_size = 768  # Updated to match actual API output

    async def get_embeddings(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        Get embeddings for one or more texts using the embedding API
        
        Args:
            texts: Single text string or list of text strings
            
        Returns:
            List of embedding vectors (768 dimensions each)
        """
        if isinstance(texts, str):
            texts = [texts]
        elif isinstance(texts, dict):
            # If input is a dictionary, convert it to a string representation
            texts = [json.dumps(texts)]

        try:
            payload = {
                "batchedInput": texts
            }
            
            print(f"Sending request to {self.api_url}")
            print(f"Payload: {json.dumps(payload)}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                ) as response:
                    print(f"Response status: {response.status}")
                    response.raise_for_status()
                    data = await response.json()
            
            # The API returns embeddings in the 'data' field
            if 'data' not in data:
                raise ValueError(f"No 'data' field in response: {data}")
            
            embeddings = data['data']
            if not isinstance(embeddings, list):
                raise ValueError(f"Expected list of embeddings, got {type(embeddings)}")
            
            # Verify each embedding is a list of floats with correct dimension
            for emb in embeddings:
                if not isinstance(emb, list) or len(emb) != self.vector_size:
                    raise ValueError(f"Invalid embedding format: {len(emb) if isinstance(emb, list) else type(emb)}")
            
            return embeddings

        except Exception as e:
            print(f"Error getting embeddings: {str(e)}")
            print(f"Error type: {type(e)}")
            if isinstance(e, aiohttp.ClientError):
                print(f"Request error details: {str(e)}")
            # Return zero vectors as fallback
            return [[0.0] * self.vector_size for _ in texts]

    async def embed_memory(self, text: str) -> List[float]:
        """
        Create embedding vector for a single memory text
        
        Args:
            text: Text content to embed
            
        Returns:
            Embedding vector as list of floats (768 dimensions)
        """
        vectors = await self.get_embeddings(text)
        return vectors[0]

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            v1, v2: Input vectors
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        v1_array = np.array(v1)
        v2_array = np.array(v2)
        
        dot_product = np.dot(v1_array, v2_array)
        norm_product = norm(v1_array) * norm(v2_array)
        
        if norm_product == 0:
            return 0.0
            
        return float(dot_product / norm_product)
    

class Embedder:
    """Alternative embedder using OpenAI embeddings"""
    
    def __init__(self):
        """Initialize embedder with OpenAI config"""
        load_dotenv()  # Load environment variables
        
        # Get API key from environment
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
            
        self.vector_size = 1536  # OpenAI ada-002 embedding size
        self.model = "text-embedding-ada-002"
        self.batch_size = 100  # OpenAI recommended batch size
        
        # Configure OpenAI client
        self.client = AsyncOpenAI(api_key=self.api_key)
        
    async def get_embeddings(self, *texts: str) -> List[List[float]]:
        """
        Get embeddings for multiple texts using OpenAI API
        
        Args:
            texts: One or more text strings to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
            
        try:
            # Split into batches
            batches = [texts[i:i+self.batch_size] for i in range(0, len(texts), self.batch_size)]
            embeddings = []
            
            for batch in batches:
                response = await self.client.embeddings.create(
                    input=batch,
                    model=self.model
                )
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                
            # Verify embeddings
            for emb in embeddings:
                if not isinstance(emb, list) or len(emb) != self.vector_size:
                    raise ValueError(f"Invalid embedding format: {len(emb) if isinstance(emb, list) else type(emb)}")
                    
            return embeddings
            
        except Exception as e:
            print(f"Error getting OpenAI embeddings: {str(e)}")
            return [[0.0] * self.vector_size for _ in texts]
            
    async def embed_memory(self, text: str) -> List[float]:
        """
        Create embedding vector for a single memory text
        
        Args:
            text: Text content to embed
            
        Returns:
            Embedding vector as list of floats (1536 dimensions)
        """
        vectors = await self.get_embeddings(text)
        return vectors[0]
        
    @staticmethod 
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            v1, v2: Input vectors
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        v1_array = np.array(v1)
        v2_array = np.array(v2)
        
        dot_product = np.dot(v1_array, v2_array)
        norm_product = norm(v1_array) * norm(v2_array)
        
        if norm_product == 0:
            return 0.0
            
        return float(dot_product / norm_product)
