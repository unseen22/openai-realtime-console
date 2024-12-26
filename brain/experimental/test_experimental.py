import sys
import pathlib
import json
from datetime import datetime
from pprint import pprint

# Add parent directory to path to allow imports
current_dir = pathlib.Path(__file__).parent
parent_dir = str(current_dir.parent.parent)
sys.path.append(parent_dir)

from brain.brain import Brain
from brain.memory import MemoryType
from brain.persona_scheduler import PersonaScheduler
from brain.story_engine.characteristic import Characteristics
from .memory_integration import MemoryIntegration
from .memory_graph import MemoryGraph
from .memory_node import NodeType

def print_separator(title: str):
    print("\n" + "="*50)
    print(f" {title} ")
    print("="*50 + "\n")

def print_node(node, indent=""):
    """Pretty print a memory node"""
    print(f"{indent}Node ID: {node.node_id}")
    print(f"{indent}Type: {node.node_type.value}")
    print(f"{indent}Content: {node.content[:100]}...")
    print(f"{indent}Importance: {node.importance:.2f}")
    print(f"{indent}Emotional Valence: {node.emotional_valence:.2f}")
    print(f"{indent}Access Count: {node.access_count}")
    print(f"{indent}Tags: {node.tags}")
    if node.relations:
        print(f"{indent}Relations:")
        for target_id, relation in node.relations.items():
            print(f"{indent}  → {relation.relation_type.value} to {target_id} (strength: {relation.strength:.2f})")
    print()

def visualize_memory_graph(memory_graph):
    """Visualize the entire memory graph structure"""
    print_separator("MEMORY GRAPH VISUALIZATION")
    
    for node_type in NodeType:
        nodes = memory_graph.get_nodes_by_type(node_type)
        if nodes:
            print(f"\n[{node_type.value.upper()} NODES]")
            for node in nodes:
                print_node(node, indent="  ")

def run_test():
    print_separator("INITIALIZING TEST")
    
    # Initialize brain with test persona
    brain = Brain(
        persona_id="test_persona",
        persona_name="Test Persona",
        persona_profile="A test persona for debugging memory systems",
        db_path="test_memories.db",
        characteristics=Characteristics(
            mind=2, body=2, heart=2, soul=2, will=2
        )
    )
    
    scheduler = PersonaScheduler()
    memory_integration = MemoryIntegration(brain, scheduler)
    
    print_separator("TESTING SCHEDULE PROCESSING")
    
    # Test schedule
    test_schedule = {
        "schedule": [
            {"time": "08:00", "activity": "Morning workout"},
            {"time": "10:00", "activity": "Read a book about AI"},
            {"time": "14:00", "activity": "Listen to techno music"},
            {"time": "16:00", "activity": "Practice coding"}
        ]
    }
    
    print("Processing test schedule:")
    pprint(test_schedule)
    memory_integration.process_schedule(test_schedule)
    
    print_separator("TESTING ACTIVITY COMPLETION")
    
    # Test completing activities with emotions
    test_activities = [
        {
            "activity": "Morning workout",
            "type": "exercise",
            "emotion": {"emotion": "energized", "intensity": 0.8}
        },
        {
            "activity": "Read a book about AI",
            "type": "learning",
            "emotion": {"emotion": "fascinated", "intensity": 0.9}
        },
        {
            "activity": "Listen to techno music",
            "type": "entertainment",
            "emotion": {"emotion": "joy", "intensity": 0.7}
        }
    ]
    
    print("Processing completed activities:")
    for activity_data in test_activities:
        print(f"\nCompleting activity: {activity_data['activity']}")
        memory_integration.process_completed_activity(
            activity=activity_data["activity"],
            activity_type=activity_data["type"],
            emotional_response=activity_data["emotion"]
        )
    
    print_separator("TESTING REFLECTION")
    
    # Test reflection
    reflection_result = memory_integration.perform_reflection()
    print("\nReflection Result:")
    pprint(reflection_result)
    
    print_separator("TESTING ACTIVITY HISTORY")
    
    # Test activity history
    history = memory_integration.get_activity_history()
    print("\nActivity History:")
    pprint(history)
    
    print_separator("TESTING PREFERENCES")
    
    # Test preferences
    preferences = memory_integration.get_preferences()
    print("\nCurrent Preferences:")
    pprint(preferences)
    
    print_separator("MEMORY GRAPH VISUALIZATION")
    
    # Visualize final memory graph
    visualize_memory_graph(memory_integration.memory_graph)
    
    print_separator("TEST COMPLETE")

if __name__ == "__main__":
    run_test()
