import os
import sys
import pathlib
import asyncio
import time
from typing import List, Dict
from statistics import mean, stdev
from dotenv import load_dotenv

# Add parent directory to path to allow imports
current_dir = pathlib.Path(__file__).parent
parent_dir = str(current_dir.parent.parent)
sys.path.append(parent_dir)

from brain.experimental.neo4j_graph import Neo4jGraph
from brain.experimental.memory_parcer import MemoryParser
from brain.embedder import Embedder

# Load environment variables
load_dotenv()

class MemorySearchBenchmark:
    def __init__(self):
        # Initialize components
        self.graph = Neo4jGraph(
            username=os.getenv("NEO4J_USER"),
            password=os.getenv("NEO4J_PASSWORD"),
            uri=os.getenv("NEO4J_URI")
        )
        self.parser = MemoryParser(neo4j_graph=self.graph)
        
        # Test queries with different scenarios
        self.test_queries = [
            {
                "query": "Who is Pi didi?",
                "persona_id": None,
                "description": "Basic search for person information"
            },
            {
                "query": "Why are you gay?",
                "persona_id": None,
                "description": "Personal characteristic search"
            },
            {
                "query": "Did you eat a cat today?",
                "persona_id": None,
                "description": "Recent activity search"
            }
        ]

    async def initialize(self):
        """Initialize and warm up the components"""
        print("\n🔧 Initializing Components")
        print("=======================")
        
        # Measure initialization time
        start_time = time.time()
        await self.parser.initialize()
        init_time = time.time() - start_time
        
        print(f"Initialization completed in {init_time:.3f}s")
        return init_time

    async def run_single_query(self, query: str, persona_id: str = None) -> tuple[List[Dict], float]:
        """Run a single search query and measure execution time"""
        start_time = time.time()
        results = await self.parser.enhance_memory_search(
            query=query,
            persona_id=persona_id,
            top_k=3
        )
        execution_time = time.time() - start_time
        print(f"RESULTS: {results}")
        return results, execution_time

    async def run_benchmark(self, iterations: int = 5):
        """Run benchmark tests for memory search"""
        # Initialize first
        init_time = await self.initialize()
        
        print("\n🔍 Memory Search Benchmark")
        print("=======================")
        
        all_times: Dict[str, List[float]] = {}
        first_query_times: Dict[str, float] = {}
        
        for test in self.test_queries:
            print(f"\n📝 Testing: {test['description']}")
            print(f"Query: '{test['query']}'")
            
            # First query (cold start)
            start_time = time.time()
            await self.run_single_query(test['query'], test['persona_id'])
            first_query_time = time.time() - start_time
            first_query_times[test['description']] = first_query_time
            print(f"First query time: {first_query_time:.3f}s")
            
            # Benchmark runs
            times = []
            for i in range(iterations):
                _, execution_time = await self.run_single_query(
                    test['query'], 
                    test['persona_id']
                )
                times.append(execution_time)
                print(f"  Run {i+1}: {execution_time:.3f}s")
            
            # Calculate statistics
            avg_time = mean(times)
            std_dev = stdev(times) if len(times) > 1 else 0
            
            print(f"\nResults:")
            print(f"  Average time: {avg_time:.3f}s")
            print(f"  Std deviation: {std_dev:.3f}s")
            print(f"  Min time: {min(times):.3f}s")
            print(f"  Max time: {max(times):.3f}s")
            
            all_times[test['description']] = times
        
        # Overall statistics
        print("\n📊 Overall Statistics")
        print("===================")
        all_runs = [t for times in all_times.values() for t in times]
        print(f"Initialization time: {init_time:.3f}s")
        print(f"Average first query time: {mean(first_query_times.values()):.3f}s")
        print(f"Total average time: {mean(all_runs):.3f}s")
        print(f"Overall min time: {min(all_runs):.3f}s")
        print(f"Overall max time: {max(all_runs):.3f}s")
        
        # Warmup improvement statistics
        print("\n🚀 Warmup Improvement")
        print("===================")
        for desc, times in all_times.items():
            first_time = first_query_times[desc]
            avg_time = mean(times)
            improvement = ((first_time - avg_time) / first_time) * 100
            print(f"{desc}:")
            print(f"  First query: {first_time:.3f}s")
            print(f"  Average after warmup: {avg_time:.3f}s")
            print(f"  Improvement: {improvement:.1f}%")

async def main():
    benchmark = MemorySearchBenchmark()
    await benchmark.run_benchmark()

if __name__ == "__main__":
    asyncio.run(main()) 