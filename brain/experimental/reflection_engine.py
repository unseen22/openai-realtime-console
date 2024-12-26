from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .memory_node import MemoryNode, NodeType, RelationType
from .memory_graph import MemoryGraph
from .activity_logger import ActivityLogger

class ReflectionEngine:
    def __init__(self, memory_graph: MemoryGraph, activity_logger: ActivityLogger):
        self.memory_graph = memory_graph
        self.activity_logger = activity_logger
        print("\n🧠 Initializing ReflectionEngine")
        
    def reflect_on_recent_activities(self, hours: int = 24) -> MemoryNode:
        """Analyze recent activities and create a reflection"""
        print(f"\n🔍 Reflecting on activities from past {hours} hours")
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Get recent activities
        activities = self.memory_graph.get_nodes_by_type(NodeType.ACTIVITY)
        recent_activities = [
            activity for activity in activities
            if activity.timestamp >= cutoff_time
        ]
        print(f"  Found {len(recent_activities)} recent activities")
        
        if not recent_activities:
            print("❌ No recent activities found")
            return None
            
        # Group activities by type
        activity_types: Dict[str, List[MemoryNode]] = {}
        for activity in recent_activities:
            # Find activity type through PART_OF relation
            type_nodes = [
                self.memory_graph.get_node(rel.target_node_id)
                for rel in activity.relations.values()
                if rel.relation_type == RelationType.PART_OF
            ]
            
            if type_nodes:
                activity_type = type_nodes[0].content
                if activity_type not in activity_types:
                    activity_types[activity_type] = []
                activity_types[activity_type].append(activity)
                print(f"  Grouped activity under type: {activity_type}")
        
        # Create reflection content
        print("\n📝 Creating reflection content")
        reflection_content = f"Reflection on activities in past {hours} hours:\n"
        for activity_type, activities in activity_types.items():
            reflection_content += f"\n{activity_type}:\n"
            for activity in activities:
                emotions = self.activity_logger.get_emotional_response(activity.node_id)
                emotion_str = ", ".join([
                    f"{emotion.content} (intensity: {emotion.emotional_valence:.1f})"
                    for emotion in emotions
                ]) if emotions else "no recorded emotional response"
                
                reflection_content += f"- {activity.content} ({emotion_str})\n"
                print(f"  Added reflection for: {activity.content[:50]}...")
        
        # Create reflection node
        print("\n💡 Creating reflection node")
        reflection_node = MemoryNode(
            content=reflection_content,
            node_type=NodeType.REFLECTION,
            importance=0.7,
            timestamp=datetime.now()
        )
        
        self.memory_graph.add_node(reflection_node)
        print(f"  Created reflection node: {reflection_node.node_id}")
        
        # Connect reflection to activities
        print("  Connecting reflection to activities")
        for activity in recent_activities:
            self.memory_graph.add_relation(
                reflection_node.node_id,
                activity.node_id,
                RelationType.RELATED_TO,
                strength=0.8
            )
        
        print("✅ Reflection complete")
        return reflection_node
    
    def update_preferences(self) -> List[MemoryNode]:
        """Update preferences based on activities and emotions"""
        print("\n🔄 Updating preferences based on activities and emotions")
        activities = self.memory_graph.get_nodes_by_type(NodeType.ACTIVITY)
        updated_preferences = []
        
        # Group activities by type
        activity_types: Dict[str, List[MemoryNode]] = {}
        for activity in activities:
            type_nodes = [
                self.memory_graph.get_node(rel.target_node_id)
                for rel in activity.relations.values()
                if rel.relation_type == RelationType.PART_OF
            ]
            
            if type_nodes:
                activity_type = type_nodes[0].content
                if activity_type not in activity_types:
                    activity_types[activity_type] = []
                activity_types[activity_type].append(activity)
                print(f"  Grouped activity under type: {activity_type}")
        
        # Analyze each activity type
        for activity_type, type_activities in activity_types.items():
            print(f"\n  Analyzing type: {activity_type}")
            # Calculate average emotional response
            total_valence = 0.0
            emotion_count = 0
            
            for activity in type_activities:
                emotions = self.activity_logger.get_emotional_response(activity.node_id)
                for emotion in emotions:
                    total_valence += emotion.emotional_valence
                    emotion_count += 1
            
            if emotion_count > 0:
                avg_valence = total_valence / emotion_count
                print(f"    Average emotional valence: {avg_valence:.2f}")
                
                # Create or update preference
                existing_preferences = self.activity_logger.get_preferences_by_category(activity_type)
                
                if existing_preferences:
                    print("    Updating existing preference")
                    pref = existing_preferences[0]
                    # Blend old and new valence (70% old, 30% new)
                    new_valence = (pref.emotional_valence * 0.7) + (avg_valence * 0.3)
                    pref.emotional_valence = new_valence
                    pref.access()  # Update access time
                    updated_preferences.append(pref)
                else:
                    print("    Creating new preference")
                    pref = self.activity_logger.log_preference(
                        preference=f"Interest in {activity_type}",
                        strength=avg_valence,
                        category=activity_type
                    )
                    updated_preferences.append(pref)
        
        print(f"✅ Updated {len(updated_preferences)} preferences")
        return updated_preferences
    
    def find_patterns(self) -> List[Dict]:
        """Find patterns in activities and emotions"""
        print("\n🔍 Finding patterns in activities and emotions")
        activities = self.memory_graph.get_nodes_by_type(NodeType.ACTIVITY)
        patterns = []
        
        # Look for time-based patterns
        print("  Analyzing time patterns")
        hour_distribution = {i: 0 for i in range(24)}
        for activity in activities:
            hour = activity.timestamp.hour
            hour_distribution[hour] += 1
        
        # Find peak hours
        avg_activities = sum(hour_distribution.values()) / 24
        peak_hours = [
            hour for hour, count in hour_distribution.items()
            if count > avg_activities * 1.5  # 50% more than average
        ]
        
        if peak_hours:
            print(f"    Found peak hours: {peak_hours}")
            patterns.append({
                "type": "time_pattern",
                "description": f"Peak activity hours: {peak_hours}",
                "confidence": 0.7
            })
        
        # Look for emotional patterns
        print("  Analyzing emotional patterns")
        for activity in activities:
            emotions = self.activity_logger.get_emotional_response(activity.node_id)
            if emotions:
                avg_valence = sum(e.emotional_valence for e in emotions) / len(emotions)
                if abs(avg_valence) > 0.7:  # Strong emotional response
                    print(f"    Found strong emotional pattern for: {activity.content[:50]}...")
                    pattern = {
                        "type": "emotional_pattern",
                        "activity": activity.content,
                        "avg_valence": avg_valence,
                        "confidence": 0.8
                    }
                    patterns.append(pattern)
        
        print(f"✅ Found {len(patterns)} patterns")
        return patterns
    
    def generate_insights(self) -> MemoryNode:
        """Generate insights based on patterns and preferences"""
        print("\n💡 Generating insights")
        patterns = self.find_patterns()
        preferences = self.memory_graph.get_nodes_by_type(NodeType.PREFERENCE)
        
        insights_content = "Current insights:\n\n"
        
        # Add pattern insights
        if patterns:
            print("  Adding pattern insights")
            insights_content += "Activity Patterns:\n"
            for pattern in patterns:
                if pattern["type"] == "time_pattern":
                    insights_content += f"- {pattern['description']}\n"
                elif pattern["type"] == "emotional_pattern":
                    valence_desc = "positive" if pattern["avg_valence"] > 0 else "negative"
                    insights_content += f"- Strong {valence_desc} response to: {pattern['activity']}\n"
        
        # Add preference insights
        if preferences:
            print("  Adding preference insights")
            insights_content += "\nPreferences:\n"
            for pref in preferences:
                strength_desc = "Strong" if abs(pref.emotional_valence) > 0.7 else "Moderate"
                like_desc = "like" if pref.emotional_valence > 0 else "dislike"
                insights_content += f"- {strength_desc} {like_desc} for {pref.content}\n"
        
        # Create insight node
        print("  Creating insight node")
        insight_node = MemoryNode(
            content=insights_content,
            node_type=NodeType.REFLECTION,
            importance=0.9,  # Insights are highly important
            timestamp=datetime.now(),
            tags={"insight", "analysis"}
        )
        
        self.memory_graph.add_node(insight_node)
        print(f"  Created insight node: {insight_node.node_id}")
        
        # Connect insights to related nodes
        print("  Connecting insights to preferences")
        for pref in preferences:
            self.memory_graph.add_relation(
                insight_node.node_id,
                pref.node_id,
                RelationType.RELATED_TO,
                strength=0.8
            )
        
        print("✅ Insights generated")
        return insight_node 