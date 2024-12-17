from typing import Dict, Any, Optional, List, Tuple
import json
import os
from datetime import datetime

from brain.memory import Memory, MemoryType
from brain.database import Database
from brain.embedder import Embedder
from brain.groq_tool import GroqTool
from pathlib import Path

class Brain:
    def __init__(self, persona_id: str, db_path: str = "memories.db"):
        self.persona_id = persona_id
        self.db = Database(db_path)
        self.mood: str = 'neutral'
        self.status: str = 'active'
        self.memories: Dict[str, Memory] = {}
        self.embedder = Embedder()
        self._load_memories()

    def _load_memories(self):
        """Load memories for the current persona from database"""
        memories = self.db.get_memories(self.persona_id)
        self.memories = {
            memory.timestamp.isoformat(): memory 
            for memory in memories
        }

    def create_embedding(self, text: str) -> List[float]:
        """Create embeddings using BGE model"""
        return self.embedder.embed_memory(text)

    def calculate_importance(self, content: str) -> float:
        """Judge the importance of the content based on the persona's profile using Groq LLM.
        
        Args:
            content: The text content to evaluate importance for
            
        Returns:
            Float between 0-1 indicating importance score
        """
        # Get persona profile from voice_instruct.json
        with open(Path(__file__).parent / "personas" / "voice_instruct.json", 'r') as f:
            personas = json.load(f)
            
        if self.persona_id not in personas:
            print(f"Warning: Persona {self.persona_id} not found in voice_instruct.json")
            return 0.5
            
        profile = personas[self.persona_id]["profile_prompt"]
        
        # Create prompt for importance evaluation
        prompt = f"""Given the following persona profile:
{profile}

Please evaluate how important/relevant this experience is to the persona on a scale of 0.0 to 1.0:
"{content}"

Return only a single float number between 0.0 and 1.0 representing the importance score."""

        # Get importance score from Groq
        groq = GroqTool()
        try:
            response = groq.generate_text(prompt, temperature=0.1)
            print(f"Groq response: {response}")
            score = float(response.strip())
            # Clamp between 0 and 1
            return max(0.0, min(1.0, score))
        except Exception as e:
            print(f"Error getting importance score: {e}")
            return 0.5

    def has_duplicate_content(self, content: str) -> bool:
        """Check if a memory with the same content already exists"""
        for memory in self.memories.values():
            if memory.content == content:
                return True
        return False

    def create_memory(self, content: str, memory_type: MemoryType = MemoryType.CONVERSATION) -> Optional[Memory]:
        """Create a new memory with the given content if it doesn't already exist"""
        print(f"\nCreating new memory: {content[:100]}...")
        
        # Check for duplicate content
        if self.has_duplicate_content(content):
            print("Duplicate content found, skipping")
            return None
            
        # Create embedding for the content
        vector = self.create_embedding(content)
        print(f"Generated embedding vector of length: {len(vector)}")
        
        # Verify vector
        if not vector or len(vector) == 0:
            print("Warning: Generated empty vector")
            return None
            
        # Calculate importance
        importance = self.calculate_importance(content)
        
        # Create memory instance
        memory = Memory(
            content=content,
            vector=vector,
            importance=importance,
            memory_type=memory_type,
            timestamp=datetime.now()
        )
        
        # Store the memory using its timestamp as a key
        memory_key = memory.timestamp.isoformat()
        self.memories[memory_key] = memory
        
        # Store in database
        self.db.store_memory(self.persona_id, memory)
        
        print(f"Successfully created memory with key: {memory_key}")
        return memory

    def search_similar_memories(self, query: str, top_k: int = 3) -> List[Tuple[Memory, float]]:
        """
        Search for memories similar to the query text
        
        Args:
            query: Text to search for
            top_k: Number of results to return
            
        Returns:
            List of tuples containing (Memory, similarity_score)
        """
        print(f"\nSearching for memories similar to: {query}")
        
        # Get query embedding
        query_embedding = self.create_embedding(query)
        
        # Calculate similarity scores for all memories
        memory_scores: List[Tuple[Memory, float]] = []
        
        for memory in self.memories.values():
            if not memory.vector or len(memory.vector) == 0:
                print(f"Warning: Memory has no vector: {memory.content[:100]}...")
                continue
                
            if len(memory.vector) != len(query_embedding):
                print(f"Warning: Memory vector length ({len(memory.vector)}) doesn't match query vector length ({len(query_embedding)})")
                continue
                
            similarity = self.embedder.cosine_similarity(query_embedding, memory.vector)
            memory_scores.append((memory, similarity))
        
        # Sort by similarity score and return top k
        memory_scores.sort(key=lambda x: x[1], reverse=True)
        actual_k = min(top_k, len(memory_scores))
        top_memories = memory_scores[:actual_k]
        
        print(f"\nFound {len(top_memories)} similar memories:")
        for memory, score in top_memories:
            print(f"Memory: {memory.content[:100]}... (similarity: {score:.4f})")
        
        return top_memories

    def clear_memories(self):
        """Clear all memories for this persona"""
        self.memories = {}
        self.db.clear_memories(self.persona_id)

    def get_all_memories(self) -> List[Memory]:
        """Get all memories for this persona"""
        return list(self.memories.values())

    def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a function with given arguments"""
        available_functions = {
            "example_function": self.example_function,
        }

        if function_name not in available_functions:
            raise ValueError(f"Function {function_name} not found")

        return available_functions[function_name](**arguments)

    def example_function(self, param1: str, param2: int = 0) -> Dict[str, Any]:
        return {
            "param1": param1,
            "param2": param2,
            "result": "Function executed successfully"
        }
    
    def importance_judge(self, content: str) -> float:
        """Judge the importance of the content based on the persona's profile using Groq LLM.
        
        Args:
            content: The text content to evaluate importance for
            
        Returns:
            Float between 0-1 indicating importance score
        """
        # Get persona profile from voice_instruct.json
        with open(Path(__file__).parent / "personas" / "voice_instruct.json", 'r') as f:
            personas = json.load(f)
            
        if self.persona_id not in personas:
            print(f"Warning: Persona {self.persona_id} not found in voice_instruct.json")
            return 0.5
            
        profile = personas[self.persona_id]["profile_prompt"]
        
        # Create prompt for importance evaluation
        prompt = f"""Given the following persona profile:
{profile}

Please evaluate how important/relevant this experience is to the persona on a scale of 0.0 to 1.0:
"{content}"

Return only a single float number between 0.0 and 1.0 representing the importance score."""

        # Get importance score from Groq
        groq = GroqTool()
        try:
            response = groq.generate_text(prompt, temperature=0.1)
            print(f"Groq response: {response}")
            score = float(response.strip())
            # Clamp between 0 and 1
            return max(0.0, min(1.0, score))
        except Exception as e:
            print(f"Error getting importance score: {e}")
            return 0.5

    def set_mood(self, mood: str):
        """Set the current mood"""
        self.mood = mood

    def get_mood(self) -> str:
        """Get the current mood"""
        return self.mood

    def set_status(self, status: str):
        """Set the current status"""
        self.status = status

    def get_status(self) -> str:
        """Get the current status"""
        return self.status
