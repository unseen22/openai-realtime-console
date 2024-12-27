import json
import os
import sys
import pathlib
from datetime import datetime
from typing import Dict, List
from neo4j import GraphDatabase

# Add parent directory to path to allow absolute imports
current_dir = pathlib.Path(__file__).parent
parent_dir = str(current_dir.parent.parent)
sys.path.append(parent_dir)

from brain.experimental.neo4j_graph import Neo4jGraph

# Define memory types enum-like class for testing
class MemoryType:
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    CONVERSATION = "conversation"

def test_neo4j_graph():
    """Test Neo4jGraph functionality"""
    print("\n=== Starting Neo4j Graph Tests ===")
    
    # Initialize Neo4j graph store with test credentials
    graph = Neo4jGraph()
    
    try:
        # Test 1: Create Persona
        print("\n1. Testing Persona Creation...")
        persona = {
            "id": "test_persona",
            "name": "Test Persona",
            "profile": "A test persona for validating graph store functionality"
        }
        
        persona_id = graph.create_persona_node(
            persona_id=persona["id"],
            persona_name=persona["name"], 
            persona_profile=persona["profile"]
        )
        print(f"Created persona with ID: {persona_id}")
        
        # Test 2: Create Memories
        print("\n2. Testing Memory Creation...")
        test_memories = [
            {
                "content": f"Test memory {i}",
                "type": MemoryType.OBSERVATION,
                "importance": 0.5,
                "vector": [0.1 * i for i in range(10)]  # Simple test vectors
            }
            for i in range(5)
        ]
        
        memory_ids = []
        for memory in test_memories:
            memory_id = graph.create_memory_node(
                persona_id=persona["id"],
                content=memory["content"],
                memory_type=memory["type"],
                importance=memory["importance"],
                vector=memory["vector"],
                timestamp=datetime.now()
            )
            memory_ids.append(memory_id)
            print(f"Created memory with ID: {memory_id}")
        
        # Test 3: Query Similar Memories
        print("\n3. Testing Similar Memory Search...")
        query_vector = [0.1 * i for i in range(10)]
        similar_memories = graph.search_similar_memories(
            persona_id=persona["id"],
            query_vector=query_vector,
            top_k=3
        )
        
        print(f"Found {len(similar_memories)} similar memories:")
        for memory in similar_memories:
            print(f"Memory: {memory['memory']['content']}, Similarity: {memory['similarity']}")
        
        # Test 4: Get All Memories
        print("\n4. Testing Get All Memories...")
        all_memories = graph.get_all_memories(persona_id=persona["id"])
        print(f"Retrieved {len(all_memories)} total memories")
        
        # Test 5: Get Memories by Type
        print("\n5. Testing Get Memories by Type...")
        observation_memories = graph.get_all_memories_by_type(
            persona_id=persona["id"],
            memory_type=MemoryType.OBSERVATION
        )
        print(f"Retrieved {len(observation_memories)} observation memories")
        
        # Test 6: Search Memories by Content
        print("\n6. Testing Memory Content Search...")
        content_search = graph.get_all_memories_by_content(
            persona_id=persona["id"],
            content="Test memory 1"
        )
        print(f"Found {len(content_search)} memories matching content search")
        
        print("\n=== All Tests Completed Successfully ===")
        
    except Exception as e:
        print(f"\nError during testing: {str(e)}")
        raise
    
    finally:
        # Clean up
        print("\nCleaning up...")
        graph.close()

if __name__ == "__main__":
    test_neo4j_graph()
