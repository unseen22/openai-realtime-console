from typing import Dict, Any, Optional, List, Tuple
import json
import os
from datetime import datetime
from brain.story_engine.characteristic import Characteristics
from .memory import Memory, MemoryType, RelationType
from .embedder import Embedder
from .groq_tool import GroqTool

from pathlib import Path

class Brain:
    def __init__(self, persona_id: str, persona_name: str, persona_profile: str, 
                 neo4j_uri: str = "bolt://localhost:7687",
                 neo4j_user: str = "neo4j",
                 neo4j_password: str = "password",
                 characteristics: Optional[Characteristics] = None, 
                 goals: Optional[List[str]] = None):
        self.persona_id = persona_id
        self.persona_name = persona_name
        self.persona_profile = persona_profile
        self.mood: str = 'neutral'
        self.status: str = 'active'
        self.memories: Dict[str, Memory] = {}
        self.embedder = Embedder()
        self._load_memories()
        self.plans = []
        self.goals = goals if goals is not None else []
        self.characteristics = characteristics if characteristics is not None else Characteristics(
            mind=0, body=0, heart=0, soul=0, will=0
        )

    def _load_memories(self):
        """Load memories for the current persona from Neo4j"""
        memory_dicts = self.graph_store.get_all_memories(self.persona_id)
        self.memories = {
            memory_dict["timestamp"]: Memory(
                content=memory_dict["content"],
                vector=memory_dict["vector"],
                importance=memory_dict["importance"],
                memory_type=MemoryType(memory_dict["memory_type"]),
                timestamp=datetime.fromisoformat(memory_dict["timestamp"]),
                node_id=memory_dict["node_id"]
            ) 
            for memory_dict in memory_dicts
        }

    def create_embedding(self, text: str) -> List[float]:
        """Create embeddings using BGE model"""
        return self.embedder.embed_memory(text)

    def calculate_importance(self, content: str) -> float:
        """Judge the importance of the content based on the persona's profile using Groq LLM.
        
        Args:
            content: The text content to evaluate importance for
            
        Returns:
            Float between 0-1 indicating importance score
        """
        # Get persona profile from voice_instruct.json
        with open(Path(__file__).parent / "personas" / "voice_instruct.json", 'r') as f:
            personas = json.load(f)
            
        if self.persona_id not in personas:
            print(f"Warning: Persona {self.persona_id} not found in voice_instruct.json")
            return 0.5
            
        profile = personas[self.persona_id]["profile_prompt"]
        
        # Create prompt for importance evaluation
        prompt = f"""Given the following persona profile:
{profile}

Please evaluate how important/relevant this experience is to the persona on a scale of 0.0 to 1.0:
"{content}"

Return only a single float number between 0.0 and 1.0 representing the importance score."""

        # Get importance score from Groq
        groq = GroqTool()
        try:
            response = groq.generate_text(prompt, temperature=0.1)
            print(f"Groq response: {response}")
            score = float(response.strip())
            # Clamp between 0 and 1
            return max(0.0, min(1.0, score))
        except Exception as e:
            print(f"Error getting importance score: {e}")
            return 0.5

    def has_duplicate_content(self, content: str) -> bool:
        """Check if a memory with the same content already exists"""
        for memory in self.memories.values():
            if memory.content == content:
                return True
        return False

    def create_memory(self, content: str | dict, memory_type: MemoryType = MemoryType.CONVERSATION) -> Optional[Memory]:
        """Create a new memory and store it in Neo4j graph"""
        print(f"\nCreating new memory: {content}...")
        
        if isinstance(content, dict):
            content = json.dumps(content)
        
        if self.has_duplicate_content(content):
            print("Duplicate content found, skipping")
            return None
        
        vector = self.create_embedding(content)
        print(f"Generated embedding vector of length: {len(vector)}")
        
        if not vector or len(vector) == 0:
            print("Warning: Generated empty vector")
            return None
            
        importance = self.calculate_importance(content)
        
        memory = Memory(
            content=content,
            vector=vector,
            importance=importance,
            memory_type=memory_type,
            timestamp=datetime.now()
        )
        
        # Store in Neo4j and get node ID
        node_id = self.graph_store.create_memory_node(memory, self.persona_id)
        memory.node_id = node_id
        
        # Store the memory using its timestamp as a key
        memory_key = memory.timestamp.isoformat()
        self.memories[memory_key] = memory
        
        self._create_temporal_relationships(memory)
        self._create_semantic_relationships(memory)
        
        print(f"Successfully created memory with key: {memory_key}")
        return memory

    def _create_temporal_relationships(self, memory: Memory):
        """Create temporal relationships with nearby memories"""
        sorted_memories = sorted(self.memories.values(), key=lambda x: x.timestamp)
        current_index = sorted_memories.index(memory)
        
        # Connect to previous and next memory
        if current_index > 0:
            prev_memory = sorted_memories[current_index - 1]
            self.graph_store.create_relationship(
                memory.node_id,
                prev_memory.node_id,
                RelationType.TEMPORAL.value
            )
            memory.add_relationship(prev_memory.node_id)
            
        if current_index < len(sorted_memories) - 1:
            next_memory = sorted_memories[current_index + 1]
            self.graph_store.create_relationship(
                memory.node_id,
                next_memory.node_id,
                RelationType.TEMPORAL.value
            )
            memory.add_relationship(next_memory.node_id)

    def _create_semantic_relationships(self, memory: Memory, threshold: float = 0.7):
        """Create semantic relationships based on vector similarity"""
        for other_memory in self.memories.values():
            if other_memory.node_id == memory.node_id:
                continue
                
            similarity = self.embedder.cosine_similarity(memory.vector, other_memory.vector)
            if similarity > threshold:
                weight = similarity
                self.graph_store.create_relationship(
                    memory.node_id,
                    other_memory.node_id,
                    RelationType.SEMANTIC.value,
                    weight
                )
                memory.add_relationship(other_memory.node_id, weight)

    def get_related_memories(self, memory: Memory, relationship_type: Optional[RelationType] = None) -> List[Tuple[Memory, float]]:
        """Get memories related to the given memory"""
        related = self.graph_store.get_related_memories(
            memory.node_id,
            relationship_type.value if relationship_type else None
        )
        
        result = []
        for record in related:
            related_memory = Memory.from_dict(record["related"])
            weight = record["weight"]
            result.append((related_memory, weight))
            
        return result

    def search_similar_memories(self, query: str, top_k: int = 3) -> List[Tuple[Memory, float]]:
        """Search for memories similar to the query text using Neo4j vector similarity search"""
        print(f"\nSearching for memories similar to: {query}")
        
        query_embedding = self.create_embedding(query)
        
        # Use Neo4j for vector similarity search
        results = self.graph_store.search_similar_vectors(
            query_vector=query_embedding,
            persona_id=self.persona_id,
            top_k=top_k
        )
        
        memory_scores = []
        for result in results:
            memory_dict = result["memory"]
            memory = Memory(
                content=memory_dict["content"],
                vector=memory_dict["vector"],
                importance=memory_dict["importance"],
                memory_type=MemoryType(memory_dict["memory_type"]),
                timestamp=datetime.fromisoformat(memory_dict["timestamp"]),
                node_id=memory_dict["node_id"]
            )
            similarity = result["similarity"]
            memory_scores.append((memory, similarity))
            print(f"Found memory: {memory.content[:100]}... (similarity: {similarity:.4f})")
        
        return memory_scores

    def clear_memories(self):
        """Clear all memories for this persona from Neo4j"""
        self.graph_store.clear_all_memories(self.persona_id)
        self.memories = {}

    def get_all_memories(self) -> List[Memory]:
        """Get all memories for this persona"""
        return list(self.memories.values())

    def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a function with given arguments"""
        available_functions = {
            "example_function": self.example_function,
        }

        if function_name not in available_functions:
            raise ValueError(f"Function {function_name} not found")

        return available_functions[function_name](**arguments)

    def example_function(self, param1: str, param2: int = 0) -> Dict[str, Any]:
        return {
            "param1": param1,
            "param2": param2,
            "result": "Function executed successfully"
        }
    
    def importance_judge(self, content: str) -> float:
        """Judge the importance of the content based on the persona's profile using Groq LLM.
        
        Args:
            content: The text content to evaluate importance for
            
        Returns:
            Float between 0-1 indicating importance score
        """
        # Get persona profile from voice_instruct.json
        with open(Path(__file__).parent / "personas" / "voice_instruct.json", 'r') as f:
            personas = json.load(f)
            
        if self.persona_id not in personas:
            print(f"Warning: Persona {self.persona_id} not found in voice_instruct.json")
            return 0.5
            
        profile = personas[self.persona_id]["profile_prompt"]
        
        # Create prompt for importance evaluation
        prompt = f"""Given the following persona profile:
{profile}

Please evaluate how important/relevant this experience is to the persona on a scale of 0.0 to 1.0:
"{content}"

Return only a single float number between 0.0 and 1.0 representing the importance score."""

        # Get importance score from Groq
        groq = GroqTool()
        try:
            response = groq.generate_text(prompt, temperature=0.1)
            print(f"Groq response: {response}")
            score = float(response.strip())
            # Clamp between 0 and 1
            return max(0.0, min(1.0, score))
        except Exception as e:
            print(f"Error getting importance score: {e}")
            return 0.5

    def set_mood(self, mood: str):
        """Set the current mood"""
        self.mood = mood

    def get_mood(self) -> str:
        """Get the current mood"""
        return self.mood

    def set_status(self, status: str):
        """Set the current status"""
        self.status = status

    def get_status(self) -> str:
        """Get the current status"""
        return self.status
    
    def _add_to_plans(self, new_plans: list[str]) -> dict:
        """Add new plans from reflection to existing plans and organize them by time.
        
        Args:
            new_plans: List of new plans to add
            
        Returns:
            dict: Status of the operation with organized plans
        """
        try:
            print("🚀 Starting to add new plans...")
            groq = GroqTool()
            today = datetime.now().strftime("%Y-%m-%d")
            print(f"📅 Today's date: {today}")
            
            # Convert any old format plans (strings) to new format (dicts)
            current_plans = []
            for plan in self.plans:
                if isinstance(plan, str):
                    # Convert old string format to new dict format
                    print(f"🔄 Converting old plan format: {plan}")
                    current_plans.append({
                        "plan": plan,
                        "start_date": today,  # Default to today for old plans
                        "priority": "medium"  # Default priority
                    })
                else:
                    current_plans.append(plan)
            
            print(f"📋 Current plans after conversion: {current_plans}")
            print(f"✨ New plans to organize: {new_plans}")
            
            # Create prompt to organize plans by time through persona's perspective
            prompt = f"""Given this persona's profile:
            {self.persona_profile}
            
            And today's date {today}, organize these new plans by when they should be done, considering the persona's preferences, goals and current plans:

            Current plans: {current_plans}
            New plans to organize: {new_plans}
            
            For each new plan, determine:
            1. When it should start (date in YYYY-MM-DD format) based on the persona's schedule and priorities
            2. Priority level (high/medium/low) based on alignment with persona's goals
            
            Return a JSON array of objects with fields:
            - plan: The plan text
            - start_date: Start date
            - priority: Priority level
            
            Only return the JSON array."""

            print("🤖 Sending prompt to Groq...")
            # Get organized new plans from Groq
            response = groq.generate_text(prompt, temperature=0.7, model="llama-3.3-70b-versatile")
            print(f"���� Groq response: {response}")
            organized_new_plans = json.loads(response)
            print(f"🎯 Organized new plans: {organized_new_plans}")
            
            # Add organized new plans while avoiding duplicates
            for plan_obj in organized_new_plans:
                plan_text = plan_obj["plan"]
                print(f"🔍 Checking for duplicate plan: {plan_text}")
                # Only add if plan text doesn't already exist
                if not any(
                    (isinstance(existing_plan, dict) and existing_plan.get("plan") == plan_text) or
                    (isinstance(existing_plan, str) and existing_plan == plan_text)
                    for existing_plan in current_plans
                ):
                    print(f"➕ Adding new plan: {plan_obj}")
                    current_plans.append(plan_obj)
            
            # Update self.plans with the merged list
            self.plans = current_plans
            print(f"✅ Final plans list: {self.plans}")
            
            return {
                "success": True,
                "message": f"Added and organized {len(new_plans)} new plans",
                "plans": self.plans
            }
            
        except Exception as e:
            print(f"❌ Error occurred: {str(e)}")
            return {
                "success": False, 
                "error": str(e)
            }

    def __del__(self):
        """Cleanup Neo4j connection on deletion"""
        if hasattr(self, 'graph_store'):
            self.graph_store.close()

    def search_memories_by_text(self, query: str, limit: int = 5) -> List[Tuple[Memory, float]]:
        """Search memories using text search
        
        Args:
            query: Text to search for
            limit: Maximum number of results to return
            
        Returns:
            List of tuples containing (Memory, score)
        """
        print(f"\nPerforming text search for: {query}")
        
        results = self.graph_store.search_fulltext(
            query=query,
            persona_id=self.persona_id,
            limit=limit
        )
        
        memory_scores = []
        for result in results:
            memory_dict = result["memory"]
            memory = Memory(
                content=memory_dict["content"],
                vector=memory_dict["vector"],
                importance=memory_dict["importance"],
                memory_type=MemoryType(memory_dict["memory_type"]),
                timestamp=datetime.fromisoformat(memory_dict["timestamp"]),
                node_id=memory_dict["node_id"]
            )
            score = result["score"]
            memory_scores.append((memory, score))
            print(f"Found memory: {memory.content[:100]}... (score: {score:.4f})")
        
        return memory_scores
