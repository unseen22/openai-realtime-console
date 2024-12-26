from typing import List, Dict, Optional, Any
from datetime import datetime
from ..brain import Brain
from ..memory import MemoryType
from ..persona_scheduler import PersonaScheduler
from .memory_graph import MemoryGraph
from .memory_node import MemoryNode, NodeType, RelationType
from .activity_logger import ActivityLogger
from .reflection_engine import ReflectionEngine

class MemoryIntegration:
    def __init__(self, brain: Brain, scheduler: PersonaScheduler):
        self.brain = brain
        self.scheduler = scheduler
        self.memory_graph = MemoryGraph()
        self.activity_logger = ActivityLogger(self.memory_graph)
        self.reflection_engine = ReflectionEngine(self.memory_graph, self.activity_logger)
        print("\n🔄 Initializing MemoryIntegration")
        
    def process_schedule(self, schedule: Dict[str, Any]) -> None:
        """Process a new schedule and log activities"""
        if "schedule" not in schedule:
            return
            
        for slot in schedule["schedule"]:
            # Log each scheduled activity
            self.activity_logger.log_activity(
                activity=slot["activity"],
                activity_type="scheduled_activity",
                importance=0.6,
                metadata={
                    "time": slot["time"],
                    "scheduled": True
                }
            )
    
    def process_completed_activity(
        self,
        activity: str,
        activity_type: str,
        emotional_response: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Process a completed activity with emotional response"""
        
        # Log the activity
        activity_node = self.activity_logger.log_activity(
            activity=activity,
            activity_type=activity_type,
            importance=0.7,  # Completed activities are more important than scheduled
            metadata=metadata
        )
        
        # Log emotional response if provided
        if emotional_response:
            self.activity_logger.log_emotion(
                emotion=emotional_response["emotion"],
                intensity=emotional_response["intensity"],
                cause=activity,
                metadata=emotional_response.get("metadata")
            )
        
        # Update brain's memory system
        self.brain.create_memory(
            content={
                "activity": activity,
                "type": activity_type,
                "emotional_response": emotional_response,
                "metadata": metadata
            },
            memory_type=MemoryType.EXPERIENCE
        )
    
    def perform_reflection(self) -> Dict[str, Any]:
        """Perform reflection and generate insights"""
        
        # Create reflection on recent activities
        reflection = self.reflection_engine.reflect_on_recent_activities(hours=24)
        
        # Update preferences based on activities and emotions
        updated_preferences = self.reflection_engine.update_preferences()
        
        # Generate insights
        insights = self.reflection_engine.generate_insights()
        
        # Store reflection in brain's memory
        if reflection:
            self.brain.create_memory(
                content=reflection.content,
                memory_type=MemoryType.REFLECTION
            )
        
        if insights:
            self.brain.create_memory(
                content=insights.content,
                memory_type=MemoryType.REFLECTION
            )
        
        return {
            "reflection": reflection.content if reflection else None,
            "insights": insights.content if insights else None,
            "updated_preferences": [
                {
                    "preference": pref.content,
                    "strength": pref.emotional_valence
                }
                for pref in updated_preferences
            ]
        }
    
    def get_activity_history(
        self,
        activity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get history of activities"""
        
        activities = self.memory_graph.get_nodes_by_type(NodeType.ACTIVITY)
        
        if activity_type:
            # Filter by activity type
            filtered_activities = []
            for activity in activities:
                type_nodes = [
                    self.memory_graph.get_node(rel.target_node_id)
                    for rel in activity.relations.values()
                    if rel.relation_type == RelationType.PART_OF
                ]
                if type_nodes and type_nodes[0].content == activity_type:
                    filtered_activities.append(activity)
            activities = filtered_activities
        
        # Sort by timestamp
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        activities = activities[:limit]
        
        return [
            {
                "activity": activity.content,
                "timestamp": activity.timestamp.isoformat(),
                "emotional_responses": [
                    {
                        "emotion": emotion.content,
                        "intensity": emotion.emotional_valence
                    }
                    for emotion in self.activity_logger.get_emotional_response(activity.node_id)
                ],
                "metadata": activity.metadata
            }
            for activity in activities
        ]
    
    def get_preferences(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get current preferences"""
        if category:
            preferences = self.activity_logger.get_preferences_by_category(category)
        else:
            preferences = self.memory_graph.get_nodes_by_type(NodeType.PREFERENCE)
        
        return [
            {
                "preference": pref.content,
                "strength": pref.emotional_valence,
                "category": pref.metadata.get("category", "unknown"),
                "last_updated": pref.last_accessed.isoformat()
            }
            for pref in preferences
        ]
    
    def search_activities(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """Search for activities and related memories"""
        
        # Search in memory graph
        activities = self.memory_graph.get_nodes_by_type(NodeType.ACTIVITY)
        matching_activities = [
            activity for activity in activities
            if query.lower() in activity.content.lower()
        ]
        
        # Search in brain's memories
        brain_memories = self.brain.search_similar_memories(query)
        
        return {
            "activities": [
                {
                    "activity": activity.content,
                    "timestamp": activity.timestamp.isoformat(),
                    "emotional_responses": [
                        {
                            "emotion": emotion.content,
                            "intensity": emotion.emotional_valence
                        }
                        for emotion in self.activity_logger.get_emotional_response(activity.node_id)
                    ]
                }
                for activity in matching_activities
            ],
            "memories": [
                {
                    "content": memory.content,
                    "similarity": score,
                    "timestamp": memory.timestamp.isoformat()
                }
                for memory, score in brain_memories
            ]
        } 