import json
import os
import sys
import pathlib
from datetime import datetime
from typing import Dict, List
from neo4j import GraphDatabase
from dotenv import load_dotenv
import asyncio
load_dotenv()

# Add parent directory to path to allow absolute imports
current_dir = pathlib.Path(__file__).parent
parent_dir = str(current_dir.parent.parent)
sys.path.append(parent_dir)

from brain.experimental.neo4j_graph import Neo4jGraph
from brain.embedder import Embedder
from brain.experimental.memory_parcer import MemoryParser

# Define memory types enum-like class for testing
class MemoryType:
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    CONVERSATION = "conversation"
    EXPERIENCE = "experience"


graph = Neo4jGraph(
        username=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"), 
        uri=os.getenv("NEO4J_URI")
    )
embedder = Embedder()
memory_parser = MemoryParser(graph)

async def search_memories_by_topic(topic: str, persona_id: str = "hanna"):
    """Search for topic-related memories for a persona"""
    print(f"\n=== Searching {topic} Memories for {persona_id} ===")
    
    # Initialize Neo4j graph store and embedder
    
    
    try:
        # Use enhanced search with topic awareness
        print(f"\nSearching for {topic}-related memories...")
        
        memories = await memory_parser.enhance_memory_search(
            query=topic,
            persona_id=persona_id,
            top_k=3
        )
        
        print(f"\nFound {len(memories)} memories:")
        for memory in memories:
            print(f"\nMemory Content: {memory['memory']['content'][:100]}...")
            print(f"Memory Type: {memory['memory'].get('type', 'unknown')}")
            print(f"Timestamp: {memory['memory']['timestamp']}")
            print(f"Similarity Score: {memory['similarity']:.4f}")
            print(f"Topic Relevance: {memory['topic_relevance']:.4f}")
            print(f"Keyword Relevance: {memory['keyword_relevance']:.4f}")
            print("-" * 50)
        
        print("\n=== Search Complete ===")
    except Exception as e:
        print(f"\nError during search: {str(e)}")
        raise
    
    finally:
        graph.close()

if __name__ == "__main__":
    # Example search queries
    search_topics = [
        "What did you watch?",
        "Life is so hard.",
        "I just lost all my crypto."
    ]
    
    async def main():
        for topic in search_topics:
            await search_memories_by_topic(topic)
            print("\n" + "="*70 + "\n")  # Separator between searches

        # Create memory with vector embedding and topic categorization
        memory_content = "I just lost all my Bitcoin. And invested a bunch of money in a new AI company and lost it all. And now Im borke and just hava a few etherium left."
        memory_vector = await embedder.embed_memory(memory_content)
        memory_id = await graph.create_memory_node(
            content=memory_content,
            memory_type=MemoryType.EXPERIENCE,  # OBSERVATION is defined in test file
            vector=memory_vector,
            importance=0.8,
            emotional_value=-0.7,
            persona_id="hanna"
        )
        
        # Categorize and link to topics
        topic_ids = await memory_parser.categorize_memory(memory_content)
        memory_parser.link_memory_to_topics(memory_id, topic_ids)

    # Run the async main function
    asyncio.run(main())
