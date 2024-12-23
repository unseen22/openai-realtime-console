from typing import Dict, Any, Optional, List, Tuple
import json
import os
from datetime import datetime

from memory import Memory, MemoryType
from database import Database
from embedder import Embedder
from groq_tool import GroqTool
from pathlib import Path

class Brain:
    def __init__(self, persona_id: str, persona_name: str, persona_profile: str, db_path: str = "memories.db"):
        self.persona_id = persona_id
        self.persona_name = persona_name
        self.persona_profile = persona_profile
        self.db = Database(db_path)
        self.mood: str = 'neutral'
        self.status: str = 'active'
        self.memories: Dict[str, Memory] = {}
        self.embedder = Embedder()
        self._load_memories()
        self.plans = []  # List of strings representing planned actions

    def _load_memories(self):
        """Load memories for the current persona from database"""
        memories = self.db.get_memories(self.persona_id)
        self.memories = {
            memory.timestamp.isoformat(): memory 
            for memory in memories
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
        """Create a new memory with the given content if it doesn't already exist"""
        print(f"\nCreating new memory: {content}...")
        
        # Convert dictionary content to string if necessary
        if isinstance(content, dict):
            content = json.dumps(content)
        
        # Check for duplicate content
        if self.has_duplicate_content(content):
            print("Duplicate content found, skipping")
            return None
        
        # Create embedding for the content
        vector = self.create_embedding(content)
        print(f"Generated embedding vector of length: {len(vector)}")
        
        # Verify vector
        if not vector or len(vector) == 0:
            print("Warning: Generated empty vector")
            return None
            
        # Calculate importance
        importance = self.calculate_importance(content)
        
        # Create memory instance
        memory = Memory(
            content=content,
            vector=vector,
            importance=importance,
            memory_type=memory_type,
            timestamp=datetime.now()
        )
        
        # Store the memory using its timestamp as a key
        memory_key = memory.timestamp.isoformat()
        self.memories[memory_key] = memory
        
        # Store in database
        self.db.store_memory(self.persona_id, memory)
        
        print(f"Successfully created memory with key: {memory_key}")
        return memory

    def search_similar_memories(self, query: str, top_k: int = 3) -> List[Tuple[Memory, float]]:
        """
        Search for memories similar to the query text
        
        Args:
            query: Text to search for
            top_k: Number of results to return
            
        Returns:
            List of tuples containing (Memory, similarity_score)
        """
        print(f"\nSearching for memories similar to: {query}")
        
        # Get query embedding
        query_embedding = self.create_embedding(query)
        
        # Calculate similarity scores for all memories
        memory_scores: List[Tuple[Memory, float]] = []
        
        for memory in self.memories.values():
            if not memory.vector or len(memory.vector) == 0:
                print(f"Warning: Memory has no vector: {memory.content[:100]}...")
                continue
                
            if len(memory.vector) != len(query_embedding):
                print(f"Warning: Memory vector length ({len(memory.vector)}) doesn't match query vector length ({len(query_embedding)})")
                continue
                
            similarity = self.embedder.cosine_similarity(query_embedding, memory.vector)
            memory_scores.append((memory, similarity))
        
        # Sort by similarity score and return top k
        memory_scores.sort(key=lambda x: x[1], reverse=True)
        actual_k = min(top_k, len(memory_scores))
        top_memories = memory_scores[:actual_k]
        
        print(f"\nFound {len(top_memories)} similar memories:")
        for memory, score in top_memories:
            print(f"Memory: {memory.content[:100]}... (similarity: {score:.4f})")
        
        return top_memories

    def clear_memories(self):
        """Clear all memories for this persona"""
        self.memories = {}
        self.db.clear_memories(self.persona_id)

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
            response = groq.generate_text(prompt, temperature=0.7, model="llama-3.1-8b-instant")
            print(f"📝 Groq response: {response}")
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
