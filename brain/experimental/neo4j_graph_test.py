"""
Test file for Neo4j graph functionality.
This file is independent of the main brain package to avoid import conflicts.
"""

import os
import sys
import pathlib
from datetime import datetime
from typing import Dict, List
from neo4j import GraphDatabase
from neo4j_graph import Neo4jGraph

# Add parent directory to path to allow imports
current_dir = pathlib.Path(__file__).parent
parent_dir = str(current_dir.parent.parent)
sys.path.append(parent_dir)

# Import embedder directly to avoid brain package initialization
embedder_path = current_dir.parent / 'embedder.py'
sys.path.append(str(embedder_path.parent))
from embedder import Embedder

# Define memory types enum-like class for testing
class MemoryType:
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    CONVERSATION = "conversation"

def cleanup_database(graph: Neo4jGraph):
    """Clean up any existing test data"""
    try:
        with graph.driver.session() as session:
            # Delete all nodes and relationships
            print("Deleting existing nodes and relationships...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # Drop existing indexes
            print("Dropping existing indexes...")
            session.run("DROP INDEX memory_vector_idx IF EXISTS")
            session.run("DROP INDEX memory_type_idx IF EXISTS")
            session.run("DROP INDEX memory_content_idx IF EXISTS")
    except Exception as e:
        print(f"Warning during cleanup: {str(e)}")

def test_neo4j_graph():
    """Test Neo4jGraph functionality"""
    print("\n=== Starting Neo4j Graph Tests ===")
    
    # Initialize Neo4j graph store and embedder
    graph = Neo4jGraph()
    embedder = Embedder()
    
    try:
        # Clean up any existing data
        cleanup_database(graph)
        
        # Test 1: Create Persona
        print("\n1. Testing Persona Creation...")
        persona = {
            "id": "hanna_01",
            "name": "Hanna",
            "profile": "A test persona for validating graph store functionality"
        }
        
        persona_id = graph.create_persona_node(
            persona_id=persona["id"],
            persona_name=persona["name"], 
            persona_profile=persona["profile"]
        )
        print(f"✓ Created persona with ID: {persona_id}")
        
        # Test 2: Create Memories
        print("\n2. Testing Memory Creation...")
        test_memories = [
            {
                "content": "Went for a morning jog in the park today. The fresh air and exercise made me feel energized.",
                "type": MemoryType.OBSERVATION,
                "importance": 0.7
            },
            {
                "content": "Feeling anxious about the upcoming presentation at work. Need to practice more.",
                "type": MemoryType.REFLECTION,
                "importance": 0.8
            },
            {
                "content": "Watched 'The Shawshank Redemption' last night. The story of hope and friendship really moved me.",
                "type": MemoryType.OBSERVATION,
                "importance": 0.6
            },
            {
                "content": "Tried a new recipe for pasta carbonara. It turned out delicious!",
                "type": MemoryType.OBSERVATION,
                "importance": 0.5
            },
            {
                "content": "Spent the afternoon painting watercolors. It's so relaxing and helps clear my mind.",
                "type": MemoryType.OBSERVATION,
                "importance": 0.6
            },
            {
                "content": "Had a deep conversation with my friend about life goals. Feel inspired to make some changes.",
                "type": MemoryType.REFLECTION,
                "importance": 0.9
            },
            {
                "content": "Started learning to play the guitar. My fingers hurt but I'm excited about this new hobby.",
                "type": MemoryType.OBSERVATION,
                "importance": 0.7
            },
            {
                "content": "Feeling grateful for the small things today - good coffee, sunshine, and a quiet moment to read.",
                "type": MemoryType.REFLECTION,
                "importance": 0.6
            },
            {
                "content": "Attended a local pottery workshop. Created my first bowl, though it's a bit wonky!",
                "type": MemoryType.OBSERVATION,
                "importance": 0.5
            },
            {
                "content": "Missing home today. Called family and felt better after catching up with everyone.",
                "type": MemoryType.REFLECTION,
                "importance": 0.8
            }
        ]
        
        # Create embeddings for all memories
        print("\nGenerating embeddings for memories...")
        memory_contents = [memory["content"] for memory in test_memories]
        memory_vectors = embedder.get_embeddings(memory_contents)
        
        memory_ids = []
        for i, (memory, vector) in enumerate(zip(test_memories, memory_vectors)):
            memory_id = graph.create_memory_node(
                persona_id=persona["id"],
                content=memory["content"],
                memory_type=memory["type"],
                importance=memory["importance"],
                vector=vector,
                timestamp=datetime.now()
            )
            memory_ids.append(memory_id)
            print(f"✓ Created memory {i+1}/10 with ID: {memory_id}")
        
        # Test 3: Query Similar Memories
        print("\n3. Testing Similar Memory Search...")
        # Use the first memory's content as query
        query_text = "Exercise and outdoor activities"
        print(f"Searching for memories similar to: '{query_text}'")
        query_vector = embedder.embed_memory(query_text)
        
        similar_memories = graph.search_similar_memories(
            persona_id=persona["id"],
            query_vector=query_vector,
            top_k=3
        )
        
        print(f"\n✓ Found {len(similar_memories)} similar memories:")
        for i, memory in enumerate(similar_memories):
            print(f"\n  {i+1}. Content: {memory['memory']['content']}")
            print(f"     Similarity: {memory['similarity']:.4f}")
        
        # Test 4: Get All Memories
        print("\n4. Testing Get All Memories...")
        all_memories = graph.get_all_memories(persona_id=persona["id"])
        print(f"✓ Retrieved {len(all_memories)} total memories")
        print("Memory contents:")
        for i, memory in enumerate(all_memories):
            print(f"  {i+1}. {memory['memory']['content']}")
        
        # Test 5: Get Memories by Type
        print("\n5. Testing Get Memories by Type...")
        observation_memories = graph.get_all_memories_by_type(
            persona_id=persona["id"],
            memory_type=MemoryType.OBSERVATION
        )
        print(f"✓ Retrieved {len(observation_memories)} observation memories")
        print("Memory contents:")
        for i, memory in enumerate(observation_memories):
            print(f"  {i+1}. {memory['memory']['content']}")
        
        # Test 6: Search Memories by Content
        print("\n6. Testing Memory Content Search...")
        search_content = "feeling"
        content_search = graph.get_all_memories_by_content(
            persona_id=persona["id"],
            content=search_content
        )
        print(f"✓ Found {len(content_search)} memories matching content: '{search_content}'")
        for i, memory in enumerate(content_search):
            print(f"  {i+1}. {memory['memory']['content']}")
        
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