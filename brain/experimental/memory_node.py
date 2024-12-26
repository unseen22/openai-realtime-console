from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import uuid

class NodeType(Enum):
    ACTIVITY = "activity"
    CONVERSATION = "conversation"
    EMOTION = "emotion"
    PREFERENCE = "preference"
    REFLECTION = "reflection"
    CONCEPT = "concept"
    RELATIONSHIP = "relationship"

class RelationType(Enum):
    CAUSED_BY = "caused_by"
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    LEADS_TO = "leads_to"
    SIMILAR_TO = "similar_to"
    OPPOSITE_OF = "opposite_of"

@dataclass
class Relation:
    relation_type: RelationType
    target_node_id: str
    strength: float  # 0.0 to 1.0
    created_at: datetime
    last_accessed: datetime
    context: Optional[str] = None

class MemoryNode:
    def __init__(
        self,
        content: str,
        node_type: NodeType,
        vector: Optional[List[float]] = None,
        node_id: Optional[str] = None,
        importance: float = 0.5,
        emotional_valence: float = 0.0,  # -1.0 to 1.0
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[Set[str]] = None
    ):
        self.node_id = node_id or str(uuid.uuid4())
        self.content = content
        self.node_type = node_type
        self.vector = vector
        self.importance = max(0.0, min(1.0, importance))
        self.emotional_valence = max(-1.0, min(1.0, emotional_valence))
        self.timestamp = timestamp or datetime.now()
        self.last_accessed = self.timestamp
        self.access_count = 0
        self.metadata = metadata or {}
        self.tags = tags or set()
        self.relations: Dict[str, Relation] = {}  # node_id -> Relation
        
    def add_relation(
        self,
        target_node_id: str,
        relation_type: RelationType,
        strength: float = 1.0,
        context: Optional[str] = None
    ) -> None:
        """Add or update a relation to another node"""
        self.relations[target_node_id] = Relation(
            relation_type=relation_type,
            target_node_id=target_node_id,
            strength=max(0.0, min(1.0, strength)),
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            context=context
        )
    
    def get_related_nodes(self, relation_type: Optional[RelationType] = None) -> List[str]:
        """Get IDs of related nodes, optionally filtered by relation type"""
        if relation_type is None:
            return list(self.relations.keys())
        return [
            node_id for node_id, relation in self.relations.items()
            if relation.relation_type == relation_type
        ]
    
    def strengthen_relation(self, target_node_id: str, amount: float = 0.1) -> None:
        """Strengthen a relation with another node"""
        if target_node_id in self.relations:
            relation = self.relations[target_node_id]
            relation.strength = min(1.0, relation.strength + amount)
            relation.last_accessed = datetime.now()
    
    def weaken_relation(self, target_node_id: str, amount: float = 0.1) -> None:
        """Weaken a relation with another node"""
        if target_node_id in self.relations:
            relation = self.relations[target_node_id]
            relation.strength = max(0.0, relation.strength - amount)
            relation.last_accessed = datetime.now()
    
    def access(self) -> None:
        """Record an access to this memory node"""
        self.access_count += 1
        self.last_accessed = datetime.now()
    
    def calculate_activation(self, current_time: datetime) -> float:
        """Calculate current activation level of the node based on importance, recency, and access frequency"""
        time_decay = (current_time - self.last_accessed).total_seconds() / (24 * 60 * 60)  # Decay over days
        recency_factor = 1.0 / (1.0 + time_decay)
        frequency_factor = min(1.0, self.access_count / 10)  # Caps at 10 accesses
        
        return (
            self.importance * 0.4 +
            recency_factor * 0.3 +
            frequency_factor * 0.3
        )
    
    def to_dict(self) -> dict:
        """Convert node to dictionary for storage"""
        return {
            "node_id": self.node_id,
            "content": self.content,
            "node_type": self.node_type.value,
            "vector": self.vector,
            "importance": self.importance,
            "emotional_valence": self.emotional_valence,
            "timestamp": self.timestamp.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "metadata": self.metadata,
            "tags": list(self.tags),
            "relations": {
                node_id: {
                    "relation_type": relation.relation_type.value,
                    "strength": relation.strength,
                    "created_at": relation.created_at.isoformat(),
                    "last_accessed": relation.last_accessed.isoformat(),
                    "context": relation.context
                }
                for node_id, relation in self.relations.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MemoryNode':
        """Create node instance from dictionary"""
        node = cls(
            content=data["content"],
            node_type=NodeType(data["node_type"]),
            vector=data["vector"],
            node_id=data["node_id"],
            importance=data["importance"],
            emotional_valence=data["emotional_valence"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data["metadata"],
            tags=set(data["tags"])
        )
        node.last_accessed = datetime.fromisoformat(data["last_accessed"])
        node.access_count = data["access_count"]
        
        # Restore relations
        for target_id, rel_data in data["relations"].items():
            node.relations[target_id] = Relation(
                relation_type=RelationType(rel_data["relation_type"]),
                target_node_id=target_id,
                strength=rel_data["strength"],
                created_at=datetime.fromisoformat(rel_data["created_at"]),
                last_accessed=datetime.fromisoformat(rel_data["last_accessed"]),
                context=rel_data["context"]
            )
        
        return node 