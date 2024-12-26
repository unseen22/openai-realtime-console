from datetime import datetime
from typing import Optional, Dict, List
from .memory_node import MemoryNode, NodeType, RelationType
from .memory_graph import MemoryGraph

class ActivityLogger:
    def __init__(self, memory_graph: MemoryGraph):
        self.memory_graph = memory_graph
        print("\n🔧 Initializing ActivityLogger")
        
    def log_activity(
        self,
        activity: str,
        activity_type: str,
        importance: float = 0.5,
        emotional_valence: float = 0.0,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> MemoryNode:
        """Log an activity as a memory node"""
        print(f"\n📝 Logging activity: {activity}")
        print(f"  Type: {activity_type}")
        print(f"  Importance: {importance:.2f}")
        print(f"  Emotional Valence: {emotional_valence:.2f}")
        
        # Create activity node
        activity_node = MemoryNode(
            content=activity,
            node_type=NodeType.ACTIVITY,
            importance=importance,
            emotional_valence=emotional_valence,
            metadata=metadata or {},
            tags=set(tags or [])
        )
        print(f"  Created activity node: {activity_node.node_id}")
        
        # Add activity type concept if it doesn't exist
        activity_type_nodes = [
            node for node in self.memory_graph.get_nodes_by_type(NodeType.CONCEPT)
            if node.content == activity_type
        ]
        
        if not activity_type_nodes:
            print(f"  Creating new concept node for type: {activity_type}")
            activity_type_node = MemoryNode(
                content=activity_type,
                node_type=NodeType.CONCEPT,
                importance=0.7,  # Concepts are generally important
                tags={"activity_type"}
            )
            self.memory_graph.add_node(activity_type_node)
        else:
            print(f"  Using existing concept node for type: {activity_type}")
            activity_type_node = activity_type_nodes[0]
            
        # Add activity node to graph
        self.memory_graph.add_node(activity_node)
        
        # Connect activity to its type
        print("  Connecting activity to type concept")
        self.memory_graph.add_relation(
            activity_node.node_id,
            activity_type_node.node_id,
            RelationType.PART_OF,
            strength=1.0
        )
        
        # Find and connect to related activities
        similar_activities = self.memory_graph.get_nodes_by_type(NodeType.ACTIVITY)
        for other_activity in similar_activities:
            if other_activity.node_id != activity_node.node_id:
                # If they share the same activity type
                if any(rel.target_node_id == activity_type_node.node_id 
                      for rel in other_activity.relations.values()):
                    print(f"  Found similar activity: {other_activity.content[:50]}...")
                    self.memory_graph.add_relation(
                        activity_node.node_id,
                        other_activity.node_id,
                        RelationType.SIMILAR_TO,
                        strength=0.7
                    )
        
        print("✅ Activity logged successfully")
        return activity_node
    
    def log_emotion(
        self,
        emotion: str,
        intensity: float,
        cause: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> MemoryNode:
        """Log an emotional response to an activity"""
        print(f"\n💭 Logging emotion: {emotion}")
        print(f"  Intensity: {intensity:.2f}")
        if cause:
            print(f"  Cause: {cause}")
        
        emotion_node = MemoryNode(
            content=emotion,
            node_type=NodeType.EMOTION,
            importance=0.6,
            emotional_valence=intensity,
            metadata=metadata or {}
        )
        
        self.memory_graph.add_node(emotion_node)
        print(f"  Created emotion node: {emotion_node.node_id}")
        
        if cause:
            # Find the most recent activity that matches the cause
            activities = self.memory_graph.get_nodes_by_type(NodeType.ACTIVITY)
            for activity in activities:
                if cause.lower() in activity.content.lower():
                    print(f"  Connecting emotion to activity: {activity.content[:50]}...")
                    self.memory_graph.add_relation(
                        emotion_node.node_id,
                        activity.node_id,
                        RelationType.CAUSED_BY,
                        strength=1.0
                    )
                    break
        
        print("✅ Emotion logged successfully")
        return emotion_node
    
    def log_preference(
        self,
        preference: str,
        strength: float,
        category: str,
        metadata: Optional[Dict] = None
    ) -> MemoryNode:
        """Log a preference (like/dislike)"""
        print(f"\n❤️ Logging preference: {preference}")
        print(f"  Strength: {strength:.2f}")
        print(f"  Category: {category}")
        
        preference_node = MemoryNode(
            content=preference,
            node_type=NodeType.PREFERENCE,
            importance=0.8,  # Preferences are important for personality
            emotional_valence=strength,  # Use strength as valence (-1 for dislike, +1 for like)
            metadata=metadata or {"category": category}
        )
        
        self.memory_graph.add_node(preference_node)
        print(f"  Created preference node: {preference_node.node_id}")
        
        # Create or find category concept
        category_nodes = [
            node for node in self.memory_graph.get_nodes_by_type(NodeType.CONCEPT)
            if node.content == category
        ]
        
        if not category_nodes:
            print(f"  Creating new concept node for category: {category}")
            category_node = MemoryNode(
                content=category,
                node_type=NodeType.CONCEPT,
                importance=0.7,
                tags={"preference_category"}
            )
            self.memory_graph.add_node(category_node)
        else:
            print(f"  Using existing concept node for category: {category}")
            category_node = category_nodes[0]
            
        # Connect preference to category
        print("  Connecting preference to category concept")
        self.memory_graph.add_relation(
            preference_node.node_id,
            category_node.node_id,
            RelationType.PART_OF,
            strength=1.0
        )
        
        print("✅ Preference logged successfully")
        return preference_node
    
    def get_recent_activities(self, limit: int = 5) -> List[MemoryNode]:
        """Get most recent activities"""
        activities = self.memory_graph.get_nodes_by_type(NodeType.ACTIVITY)
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        return activities[:limit]
    
    def get_preferences_by_category(self, category: str) -> List[MemoryNode]:
        """Get all preferences in a category"""
        preferences = []
        category_nodes = [
            node for node in self.memory_graph.get_nodes_by_type(NodeType.CONCEPT)
            if node.content == category
        ]
        
        if category_nodes:
            category_node = category_nodes[0]
            related = self.memory_graph.get_related_nodes(
                category_node.node_id,
                relation_type=RelationType.PART_OF
            )
            preferences = [
                node for node in related
                if node.node_type == NodeType.PREFERENCE
            ]
            
        return preferences
    
    def get_emotional_response(self, activity_id: str) -> List[MemoryNode]:
        """Get emotional responses to an activity"""
        return self.memory_graph.get_related_nodes(
            activity_id,
            relation_type=RelationType.CAUSED_BY
        )
