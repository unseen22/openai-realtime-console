import asyncio
from brain.experimental.memory_parcer import MemoryParser
from brain.experimental.neo4j_graph import Neo4jGraph
from brain.embedder import Embedder

async def test_memory_search():
    # Initialize components
    graph = Neo4jGraph()
    parser = MemoryParser(neo4j_graph=graph)
    embedder = Embedder()
    
    # Test queries with different scenarios
    test_queries = [
        {
            "query": "What did I do yesterday?",
            "persona_id": None,
            "description": "Basic search without persona filter"
        },
        {
            "query": "Tell me about my family",
            "persona_id": "test_persona",
            "description": "Search with persona filter"
        },
        {
            "query": "What are my hobbies?",
            "persona_id": None,
            "description": "Topic-related search (hobbies category)"
        }
    ]
    
    print("\n🔍 Testing Enhanced Memory Search")
    print("=================================")
    
    for test in test_queries:
        print(f"\n📝 Test: {test['description']}")
        print(f"Query: '{test['query']}'")
        
        try:
            # Perform search
            results = await parser.enhance_memory_search(
                query=test['query'],
                persona_id=test['persona_id'],
                top_k=3
            )
            
            # Display results
            print(f"\nFound {len(results)} results:")
            for i, result in enumerate(results, 1):
                memory = result['memory']
                print(f"\n{i}. Memory:")
                print(f"   Content: {memory.get('content', 'N/A')[:100]}...")
                print(f"   Similarity: {result['similarity']:.3f}")
                print(f"   Topic Relevance: {result['topic_relevance']:.3f}")
                print(f"   Keyword Relevance: {result['keyword_relevance']:.3f}")
                print(f"   Final Score: {result['final_score']:.3f}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print(f"Error type: {type(e)}")

async def main():
    try:
        await test_memory_search()
    except Exception as e:
        print(f"❌ Main error: {str(e)}")
    
if __name__ == "__main__":
    asyncio.run(main()) 