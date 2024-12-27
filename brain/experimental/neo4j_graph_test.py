"""
Test file for Neo4j graph functionality.
This file is independent of the main brain package to avoid import conflicts.
"""

import os
import sys
import pathlib
from datetime import datetime
from typing import Dict, List

# Add parent directory to path to allow imports
current_dir = pathlib.Path(__file__).parent
parent_dir = str(current_dir.parent.parent)
sys.path.append(parent_dir)

# Import local modules
from brain.experimental.neo4j_graph import Neo4jGraph
from brain.experimental.memory_parcer import MemoryParser

# Import embedder directly to avoid brain package initialization
embedder_path = current_dir.parent / 'embedder.py'
sys.path.append(str(embedder_path.parent))
from brain.embedder import Embedder

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
    """Test Neo4j Graph functionality"""
    print("\n=== Starting Neo4j Graph Tests ===")
    
    try:
        # Initialize Neo4j graph store, embedder, and memory parser
        print("\nInitializing components...")
        graph = Neo4jGraph()
        print("✓ Neo4j graph initialized")
        
        embedder = Embedder()
        print("✓ Embedder initialized")
        
        parser = MemoryParser(neo4j_graph=graph)
        print("✓ Memory parser initialized")
        
        # Test 1: Create Persona
        print("\n1. Testing Persona Creation...")
        try:
            persona = {
                "id": "turbo_01",
                "name": "TURBO",
                "profile": "A test persona for validating graph store functionality"
            }
            
            persona_id = graph.create_persona_node(
                persona_id=persona["id"],
                persona_name=persona["name"], 
                persona_profile=persona["profile"]
            )
            print(f"✓ Created persona with ID: {persona_id}")
        except Exception as e:
            print(f"Error creating persona: {str(e)}")
            raise
        
        # Test 2: Create Memories with Topic Categorization
        print("\n2. Testing Memory Creation with Topics...")
        try:
            test_memories = [
                {
                    "content": "Just finished a challenging yoga session. My body feels both tired and energized.",
                    "type": MemoryType.OBSERVATION,
                    "importance": 0.7,
                    "emotional_value": 0.6
                },
                {
                    "content": "Contemplating my career path and where I want to be in 5 years. Need to set clearer goals.",
                    "type": MemoryType.REFLECTION,
                    "importance": 0.9,
                    "emotional_value": 0.4
                },
                {
                    "content": "Had an amazing sushi dinner with friends. The conversations and laughter made it special.",
                    "type": MemoryType.OBSERVATION,
                    "importance": 0.6,
                    "emotional_value": 0.8
                },
                {
                    "content": "Started reading 'Atomic Habits'. The concepts about building better habits are eye-opening.",
                    "type": MemoryType.OBSERVATION,
                    "importance": 0.8,
                    "emotional_value": 0.5
                },
                {
                    "content": "Explored a new hiking trail today. The view from the summit was breathtaking.",
                    "type": MemoryType.OBSERVATION,
                    "importance": 0.7,
                    "emotional_value": 0.7
                },
                {
                    "content": "Thinking about how much I've grown this past year. Proud of my personal development.",
                    "type": MemoryType.REFLECTION,
                    "importance": 0.8,
                    "emotional_value": 0.6
                },
                {
                    "content": "Attended a virtual photography workshop. Learning about composition and lighting techniques.",
                    "type": MemoryType.OBSERVATION,
                    "importance": 0.6,
                    "emotional_value": 0.5
                },
                {
                    "content": "Feeling overwhelmed with work lately. Need to find better ways to manage stress.",
                    "type": MemoryType.REFLECTION,
                    "importance": 0.8,
                    "emotional_value": -0.3
                },
                {
                    "content": "Volunteered at the local food bank today. Helping others brings such fulfillment.",
                    "type": MemoryType.OBSERVATION,
                    "importance": 0.7,
                    "emotional_value": 0.9
                },
                {
                    "content": "Realizing how important it is to maintain boundaries in relationships. Growth isn't always easy.",
                    "type": MemoryType.REFLECTION,
                    "importance": 0.9,
                    "emotional_value": 0.4
                }
            ]
            
            # Create embeddings and categorize memories
            print("\nGenerating embeddings and categorizing memories...")
            memory_contents = [memory["content"] for memory in test_memories]
            memory_vectors = embedder.get_embeddings(memory_contents)
            
            memory_ids = []
            for i, (memory, vector) in enumerate(zip(test_memories, memory_vectors)):
                try:
                    # Create memory node
                    memory_id = graph.create_memory_node(
                        persona_id=persona["id"],
                        content=memory["content"],
                        memory_type=memory["type"],
                        importance=memory["importance"],
                        emotional_value=memory["emotional_value"],
                        vector=vector,
                        timestamp=datetime.now()
                    )
                    memory_ids.append(memory_id)
                    print(f"✓ Created memory {i+1}/10 with ID: {memory_id}")
                    
                    # Categorize memory and create topic relationships
                    topic_ids = parser.categorize_memory(memory["content"])
                    if topic_ids:
                        parser.link_memory_to_topics(memory_id, topic_ids)
                        
                        # Print topic categorization
                        print(f"  Topics for memory {i+1}:")
                        for topic_id in topic_ids:
                            topic_path = parser.get_topic_path(topic_id)
                            print(f"    - {' -> '.join(topic_path)}")
                    else:
                        print(f"  No topics found for memory {i+1}")
                except Exception as e:
                    print(f"Error processing memory {i+1}: {str(e)}")
                    continue
        
        except Exception as e:
            print(f"Error in memory creation and categorization: {str(e)}")
            raise
        
        # Test 3: Enhanced Memory Search with Topics
        print("\n3. Testing Enhanced Memory Search...")
        query_text = "Exercise and outdoor activities"
        print(f"Searching for memories similar to: '{query_text}'")
        query_vector = embedder.embed_memory(query_text)
        
        similar_memories = parser.enhance_memory_search(
            query=query_text,
            vector=query_vector,
            top_k=3
        )
        
        print(f"\n✓ Found {len(similar_memories)} relevant memories:")
        for i, result in enumerate(similar_memories):
            print(f"\n  {i+1}. Content: {result['memory']['content']}")
            print(f"     Similarity: {result['similarity']:.4f}")
            print(f"     Topic Relevance: {result['topic_relevance']:.4f}")
        
        # Test 4: Topic-Based Memory Retrieval
        print("\n4. Testing Topic-Based Memory Retrieval...")
        # Get memories for physical activities
        physical_topic_id = "sub_physical"  # ID for physical activities subcategory
        physical_memories = parser.get_memories_by_topic(physical_topic_id)
        
        print(f"\n✓ Found {len(physical_memories)} memories related to physical activities:")
        for i, memory in enumerate(physical_memories):
            print(f"  {i+1}. {memory['memory']['content']}")
        
        # Test 5: Related Topics Analysis
        print("\n5. Testing Related Topics Analysis...")
        test_topic_id = "sub_physical"  # Physical activities subcategory
        related_topics = parser.get_related_topics(test_topic_id)
        
        print(f"\n✓ Found {len(related_topics)} related topics for 'Physical Activities':")
        for topic_id, strength in related_topics:
            topic_path = parser.get_topic_path(topic_id)
            print(f"  - {' -> '.join(topic_path)} (strength: {strength:.2f})")
        
        # Test 6: Get All Memories
        print("\n6. Testing Get All Memories...")
        all_memories = graph.get_all_memories(persona_id=persona["id"])
        print(f"✓ Retrieved {len(all_memories)} total memories")
        print("Memory contents:")
        for i, memory in enumerate(all_memories):
            print(f"  {i+1}. {memory['memory']['content']}")
        
        # Test 7: Get Memories by Type
        print("\n7. Testing Get Memories by Type...")
        observation_memories = graph.get_all_memories_by_type(
            persona_id=persona["id"],
            memory_type=MemoryType.OBSERVATION
        )
        print(f"✓ Retrieved {len(observation_memories)} observation memories")
        print("Memory contents:")
        for i, memory in enumerate(observation_memories):
            print(f"  {i+1}. {memory['memory']['content']}")
        
        # Test 8: Search Memories by Content
        print("\n8. Testing Memory Content Search...")
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
        try:
            graph.close()
            print("✓ Neo4j connection closed")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    try:
        test_neo4j_graph()
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        sys.exit(1) 