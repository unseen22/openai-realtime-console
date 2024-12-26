import sys
import pathlib
import json
from datetime import datetime
from pprint import pprint
import networkx as nx
import matplotlib.pyplot as plt

# Add parent directory to path to allow imports
current_dir = pathlib.Path(__file__).parent
parent_dir = str(current_dir.parent.parent)
sys.path.append(parent_dir)

from brain.brain import Brain
from brain.memory import MemoryType
from brain.persona_scheduler import PersonaScheduler
from brain.story_engine.characteristic import Characteristics
from brain.experimental.memory_integration import MemoryIntegration
from brain.experimental.memory_graph import MemoryGraph
from brain.experimental.memory_node import NodeType, RelationType

def print_separator(title: str):
    print("\n" + "="*80)
    print(f" {title} ".center(80, "="))
    print("="*80 + "\n")

def print_node(node, indent=""):
    """Pretty print a memory node"""
    print(f"{indent}🔹 Node ID: {node.node_id}")
    print(f"{indent}  Type: {node.node_type.value}")
    print(f"{indent}  Content: {node.content[:100]}...")
    print(f"{indent}  Importance: {node.importance:.2f}")
    print(f"{indent}  Emotional Valence: {node.emotional_valence:.2f}")
    print(f"{indent}  Access Count: {node.access_count}")
    print(f"{indent}  Tags: {node.tags}")
    if node.relations:
        print(f"{indent}  Relations:")
        for target_id, relation in node.relations.items():
            print(f"{indent}    → {relation.relation_type.value} to {target_id} (strength: {relation.strength:.2f})")
    print()

def visualize_memory_graph(memory_graph):
    """Visualize the entire memory graph structure"""
    print_separator("MEMORY GRAPH VISUALIZATION")
    
    # Text visualization
    for node_type in NodeType:
        nodes = memory_graph.get_nodes_by_type(node_type)
        if nodes:
            print(f"\n[{node_type.value.upper()} NODES]")
            for node in nodes:
                print_node(node, indent="  ")
    
    # NetworkX visualization
    plt.figure(figsize=(15, 10))
    G = memory_graph.graph
    
    # Create position layout
    pos = nx.spring_layout(G)
    
    # Draw nodes with different colors based on type
    node_colors = []
    node_sizes = []
    labels = {}
    
    for node_id in G.nodes():
        node = memory_graph.get_node(node_id)
        if node:
            # Color based on node type
            color_map = {
                NodeType.ACTIVITY: 'lightblue',
                NodeType.EMOTION: 'lightcoral',
                NodeType.PREFERENCE: 'lightgreen',
                NodeType.CONCEPT: 'yellow',
                NodeType.REFLECTION: 'violet'
            }
            node_colors.append(color_map.get(node.node_type, 'gray'))
            
            # Size based on importance
            node_sizes.append(1000 * node.importance)
            
            # Label with truncated content
            labels[node_id] = f"{node.node_type.value}\n{node.content[:20]}..."
    
    # Draw the graph
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes)
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20)
    nx.draw_networkx_labels(G, pos, labels, font_size=8)
    
    # Add legend
    legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                label=node_type.value,
                                markerfacecolor=color,
                                markersize=10)
                      for node_type, color in color_map.items()]
    plt.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))
    
    plt.title("Memory Graph Visualization")
    plt.axis('off')
    plt.tight_layout()
    plt.savefig('memory_graph.png', bbox_inches='tight')
    plt.close()
    print("\n📊 Graph visualization saved as 'memory_graph.png'")

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
    
    print("📅 Processing test schedule:")
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
    
    print("🎯 Processing completed activities:")
    for activity_data in test_activities:
        print(f"\n▶️ Completing activity: {activity_data['activity']}")
        memory_integration.process_completed_activity(
            activity=activity_data["activity"],
            activity_type=activity_data["type"],
            emotional_response=activity_data["emotion"]
        )
    
    print_separator("TESTING REFLECTION")
    
    # Test reflection
    reflection_result = memory_integration.perform_reflection()
    print("\n🤔 Reflection Result:")
    pprint(reflection_result)
    
    print_separator("TESTING ACTIVITY HISTORY")
    
    # Test activity history
    history = memory_integration.get_activity_history()
    print("\n📚 Activity History:")
    pprint(history)
    
    print_separator("TESTING PREFERENCES")
    
    # Test preferences
    preferences = memory_integration.get_preferences()
    print("\n❤️ Current Preferences:")
    pprint(preferences)
    
    print_separator("MEMORY GRAPH VISUALIZATION")
    
    # Visualize final memory graph
    visualize_memory_graph(memory_integration.memory_graph)
    
    print_separator("TEST COMPLETE")

if __name__ == "__main__":
    run_test()
