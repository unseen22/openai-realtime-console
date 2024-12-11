from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime
from brain.memory import Memory, MemoryType
from brain.database import Database

class Brain:
    def __init__(self, persona_id: str, db_path: str = "memories.db"):
        self.persona_id = persona_id
        self.db = Database(db_path)
        self.mood: str = 'neutral'
        self.status: str = 'active'
        self.memories: Dict[str, Memory] = {}
        self._load_memories()

    def _load_memories(self):
        """Load memories for the current persona from database"""
        memories = self.db.get_memories(self.persona_id)
        self.memories = {
            memory.timestamp.strftime('%Y-%m-%d-%H-%M-%S-%f'): memory 
            for memory in memories
        }

    def create_embedding(self, text: str) -> List[float]:
        """
        Placeholder for creating embeddings.
        TODO: Implement actual embedding logic
        """
        # Placeholder: Returns a simple vector of 5 dimensions
        return [0.1, 0.2, 0.3, 0.4, 0.5]

    def calculate_importance(self, text: str) -> float:
        """
        Placeholder for importance calculation.
        TODO: Implement actual importance calculation logic
        """
        return 0.5  # Placeholder fixed value

    def create_memory(self, content: str, memory_type: MemoryType = MemoryType.CONVERSATION) -> Memory:
        """Create a new memory with the given content"""
        # Create embedding for the content
        vector = self.create_embedding(content)
        
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
        memory_key = memory.timestamp.strftime('%Y-%m-%d-%H-%M-%S-%f')
        self.memories[memory_key] = memory
        
        # Store in database
        self.db.store_memory(self.persona_id, memory)
        
        return memory

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
