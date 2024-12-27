from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
from .embedder import Embedder

class MemoryType(Enum):
    CONVERSATION = "conversation"
    EXPERIENCE = "experience"
    PROFILE = "profile"
    SYSTEM = "system"
    REFLECTION = "reflection"
    OBSERVATION = "observation"  # For direct observations of the environment

class RelationType(Enum):
    TEMPORAL = "TEMPORAL"  # Time-based relationship
    SEMANTIC = "SEMANTIC"  # Meaning-based relationship
    CAUSAL = "CAUSAL"     # Cause-effect relationship
    EMOTIONAL = "EMOTIONAL"  # Emotional connection
    REFERENCE = "REFERENCE"  # Direct reference/mention

class Memory:
    _embedder = Embedder()
    
    def __init__(
        self,
        content: str,
        vector: List[float],
        importance: float = 0.0,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        timestamp: Optional[datetime] = None,
        node_id: Optional[str] = None,
        relationships: Optional[Dict[str, float]] = None
    ):
        self.content: str = content
        self.vector: List[float] = vector
        self.importance: float = max(0.0, min(1.0, importance))  # Clamp between 0 and 1
        self.memory_type: MemoryType = memory_type
        self.timestamp: datetime = timestamp or datetime.now()
        self.node_id: Optional[str] = node_id  # Neo4j node ID
        self.relationships: Dict[str, float] = relationships or {}  # node_id -> weight mapping

    def to_dict(self) -> dict:
        """Convert memory to dictionary for storage"""
        return {
            "content": self.content,
            "vector": self.vector,
            "importance": self.importance,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp.isoformat(),
            "node_id": self.node_id,
            "relationships": self.relationships
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Memory':
        """Create memory instance from dictionary"""
        return cls(
            content=data["content"],
            vector=data["vector"],
            importance=data["importance"],
            memory_type=MemoryType(data["memory_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            node_id=data.get("node_id"),
            relationships=data.get("relationships", {})
        )

    def add_relationship(self, target_node_id: str, weight: float = 1.0):
        """Add or update a relationship to another memory node"""
        self.relationships[target_node_id] = weight

    def remove_relationship(self, target_node_id: str):
        """Remove a relationship to another memory node"""
        self.relationships.pop(target_node_id, None)

    def get_relationships(self) -> Dict[str, float]:
        """Get all relationships for this memory"""
        return self.relationships.copy()

    def __str__(self) -> str:
        """String representation of the memory"""
        return f"Memory({self.memory_type.value}: {self.content[:50]}... | Importance: {self.importance:.2f})"

    @classmethod
    def create(cls, content: str, importance: float = 0.0, 
               memory_type: MemoryType = MemoryType.CONVERSATION,
               timestamp: Optional[datetime] = None) -> 'Memory':
        """
        Create a new memory with automatically generated embedding vector
        """
        vector = cls._embedder.embed_memory(content)
        return cls(
            content=content,
            vector=vector,
            importance=importance,
            memory_type=memory_type,
            timestamp=timestamp
        )
