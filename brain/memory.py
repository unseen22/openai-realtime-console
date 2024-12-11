from datetime import datetime
from enum import Enum
from typing import List, Optional

class MemoryType(Enum):
    CONVERSATION = "conversation"
    SUMMARY = "summary"
    OPENER = "opener"

class Memory:
    def __init__(
        self,
        content: str,
        vector: List[float],
        importance: float = 0.0,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        timestamp: Optional[datetime] = None
    ):
        self.content: str = content
        self.vector: List[float] = vector
        self.importance: float = max(0.0, min(1.0, importance))  # Clamp between 0 and 1
        self.memory_type: MemoryType = memory_type
        self.timestamp: datetime = timestamp or datetime.now()

    def to_dict(self) -> dict:
        """Convert memory to dictionary for storage"""
        return {
            "content": self.content,
            "vector": self.vector,
            "importance": self.importance,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Memory':
        """Create memory instance from dictionary"""
        return cls(
            content=data["content"],
            vector=data["vector"],
            importance=data["importance"],
            memory_type=MemoryType(data["memory_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )

    def __str__(self) -> str:
        """String representation of the memory"""
        return f"Memory({self.memory_type.value}: {self.content[:50]}... | Importance: {self.importance:.2f})"
