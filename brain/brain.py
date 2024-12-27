from typing import Dict, Any, Optional, List, Tuple
import json
import os
from datetime import datetime
from pathlib import Path

from brain.story_engine.characteristic import Characteristics
from brain.experimental.neo4j_graph import Neo4jGraph
from brain.experimental.memory_parcer import MemoryParser
from .memory import Memory, MemoryType, RelationType
from .embedder import Embedder
from .groq_tool import GroqTool

class Brain:
    def __init__(self, persona_id: str, persona_name: str = None, persona_profile: str = None, 
                 neo4j_uri: str = "neo4j+s://a9277d8e.databases.neo4j.io",
                 neo4j_user: str = "neo4j",
                 neo4j_password: str = "tKSk2m5MwQr9w25IbSnB07KccMmTfjFtjcCsQIraczk",
                 characteristics: Optional[Characteristics] = None, 
                 goals: Optional[List[str]] = None,
                 neo4j_graph: Optional[Neo4jGraph] = None):
        """Initialize Brain with Neo4j state management
        
        Args:
            persona_id: Unique identifier for the persona
            persona_name: Name of the persona (only needed for new personas)
            persona_profile: Profile of the persona (only needed for new personas)
            neo4j_uri: URI for Neo4j connection (not used if neo4j_graph is provided)
            neo4j_user: Neo4j username (not used if neo4j_graph is provided)
            neo4j_password: Neo4j password (not used if neo4j_graph is provided)
            characteristics: Optional characteristics
            goals: Optional goals
            neo4j_graph: Optional existing Neo4j connection
        """
        self.persona_id = persona_id
        self.embedder = Embedder()
        self.graph_store = neo4j_graph if neo4j_graph else Neo4jGraph(neo4j_uri, neo4j_user, neo4j_password)
        self.memory_parser = MemoryParser(neo4j_graph=self.graph_store)
        
        try:
            # Try to load existing persona
            state = self.graph_store.get_persona_state(persona_id)
            self.persona_name = state["name"]
            self.persona_profile = state["profile"]
            self.mood = state["mood"]
            self.status = state["status"]
            self.plans = state["plans"]
            self.goals = state["goals"]
            
            # Load characteristics from state
            char_dict = state.get("characteristics", {})
            self.characteristics = Characteristics(
                mind=char_dict.get("mind", 0),
                body=char_dict.get("body", 0),
                heart=char_dict.get("heart", 0),
                soul=char_dict.get("soul", 0),
                will=char_dict.get("will", 0)
            )
            print(f"✅ Loaded existing persona {persona_id}")
        except ValueError:
            # Create new persona if not found
            if not persona_name or not persona_profile:
                raise ValueError("persona_name and persona_profile required for new personas")
            
            self.persona_name = persona_name
            self.persona_profile = persona_profile
            self.mood = "neutral"
            self.status = "active"
            self.plans = []
            self.goals = goals if goals is not None else []
            self.characteristics = characteristics if characteristics is not None else Characteristics(
                mind=0, body=0, heart=0, soul=0, will=0
            )
            
            # Create persona in Neo4j with characteristics
            char_dict = {
                "mind": self.characteristics.mind,
                "body": self.characteristics.body,
                "heart": self.characteristics.heart,
                "soul": self.characteristics.soul,
                "will": self.characteristics.will
            }
            
            self.graph_store.create_persona_node(
                persona_id=persona_id,
                persona_name=persona_name,
                persona_profile=persona_profile,
                characteristics=char_dict
            )
            
            # Initialize state
            self.graph_store.update_persona_state(
                persona_id=persona_id,
                mood=self.mood,
                status=self.status,
                plans=self.plans,
                goals=self.goals,
                characteristics=char_dict
            )
            print(f"✅ Created new persona {persona_id}")
            
        # Load memories
        self.memories = {}
        self._load_memories()

    def _load_memories(self):
        """Load memories for the current persona from Neo4j"""
        memory_dicts = self.graph_store.get_all_memories(self.persona_id)
        self.memories = {}
        
        for memory_data in memory_dicts:
            try:
                # Extract memory data from the nested structure
                memory_dict = memory_data.get("memory", {})
                
                # Create Memory object with proper field mapping
                memory = Memory(
                    content=memory_dict.get("content", ""),
                    vector=memory_dict.get("vector", []),
                    importance=memory_dict.get("importance", 0.0),
                    memory_type=MemoryType(memory_dict.get("type", "conversation")),  # Map 'type' to memory_type
                    timestamp=datetime.fromisoformat(memory_dict.get("timestamp", datetime.now().isoformat())),
                    node_id=memory_dict.get("node_id", None)
                )
                
                # Use timestamp as key
                memory_key = memory.timestamp.isoformat()
                self.memories[memory_key] = memory
                
            except Exception as e:
                print(f"Error loading memory: {str(e)}")
                continue

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
        """Create a new memory and store it in Neo4j graph with topic categorization"""
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
        
        # Categorize memory and create topic relationships
        topic_ids = self.memory_parser.categorize_memory(content)
        self.memory_parser.link_memory_to_topics(node_id, topic_ids)
        
        # Store the memory using its timestamp as a key
        memory_key = memory.timestamp.isoformat()
        self.memories[memory_key] = memory
        
        self._create_temporal_relationships(memory)
        self._create_semantic_relationships(memory)
        
        print(f"Successfully created memory with key: {memory_key}")
        print("Memory categorized with topics:")
        for topic_id in topic_ids:
            topic_path = self.memory_parser.get_topic_path(topic_id)
            print(f"  - {' -> '.join(topic_path)}")
        
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
        """Enhanced memory search combining vector similarity and topic relevance"""
        print(f"\nSearching for memories similar to: {query}")
        
        query_embedding = self.create_embedding(query)
        
        # Use enhanced search with topic awareness
        results = self.memory_parser.enhance_memory_search(
            query=query,
            vector=query_embedding,
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
            topic_relevance = result["topic_relevance"]
            combined_score = similarity * 0.7 + topic_relevance * 0.3
            memory_scores.append((memory, combined_score))
            print(f"Found memory: {memory.content[:100]}... "
                  f"(similarity: {similarity:.4f}, topic relevance: {topic_relevance:.4f})")
        
        return sorted(memory_scores, key=lambda x: x[1], reverse=True)

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
        """Set the current mood and update in Neo4j"""
        self.mood = mood
        self.graph_store.update_persona_state(self.persona_id, mood=mood)

    def get_mood(self) -> str:
        """Get the current mood"""
        return self.mood

    def set_status(self, status: str):
        """Set the current status and update in Neo4j"""
        self.status = status
        self.graph_store.update_persona_state(self.persona_id, status=status)

    def get_status(self) -> str:
        """Get the current status"""
        return self.status
    
    def _add_to_plans(self, new_plans: list[str]) -> dict:
        """Add new plans and update in Neo4j"""
        try:
            print("🚀 Starting to add new plans...")
            current_plans = self.plans.copy() if isinstance(self.plans, list) else []
            
            # Ensure new_plans is a list of strings
            if isinstance(new_plans, str):
                new_plans = [new_plans]
            elif not isinstance(new_plans, list):
                new_plans = list(new_plans)
            
            # Add new plans while avoiding duplicates
            for plan in new_plans:
                if isinstance(plan, str) and plan not in current_plans:
                    current_plans.append(plan)
            
            # Update plans in Neo4j
            print(f"Updating plans: {current_plans}")
            self.update_plans(current_plans)
            
            return {
                "success": True,
                "message": f"Added {len(new_plans)} new plans",
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

    def get_memories_by_topic(self, topic_name: str, limit: int = 10) -> List[Memory]:
        """Get memories associated with a specific topic"""
        # Find topic ID from name
        topic_id = None
        for tid, topic in self.memory_parser.topic_hierarchy.topics.items():
            if topic.name.lower() == topic_name.lower():
                topic_id = tid
                break
        
        if not topic_id:
            print(f"Topic '{topic_name}' not found")
            return []
        
        results = self.memory_parser.get_memories_by_topic(topic_id, limit)
        
        memories = []
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
            memories.append(memory)
        
        return memories

    def get_related_topics(self, topic_name: str, min_strength: float = 0.4) -> List[Tuple[str, float]]:
        """Get topics related to the given topic name"""
        # Find topic ID from name
        topic_id = None
        for tid, topic in self.memory_parser.topic_hierarchy.topics.items():
            if topic.name.lower() == topic_name.lower():
                topic_id = tid
                break
        
        if not topic_id:
            print(f"Topic '{topic_name}' not found")
            return []
        
        related = self.memory_parser.get_related_topics(topic_id, min_strength)
        
        # Convert topic IDs to names
        named_relations = []
        for topic_id, strength in related:
            topic_path = self.memory_parser.get_topic_path(topic_id)
            named_relations.append((" -> ".join(topic_path), strength))
        
        return named_relations

    def update_plans(self, plans: List[str]):
        """Update plans and save to Neo4j"""
        # Ensure plans are complete strings
        self.plans = plans
        self.graph_store.update_persona_state(self.persona_id, plans=plans)

    def update_goals(self, goals: List[str]):
        """Update goals and save to Neo4j"""
        self.goals = goals
        self.graph_store.update_persona_state(self.persona_id, goals=goals)

    def update_characteristics(self, characteristics: Characteristics):
        """Update characteristics and save to Neo4j"""
        self.characteristics = characteristics
        char_dict = {
            "mind": characteristics.mind,
            "body": characteristics.body,
            "heart": characteristics.heart,
            "soul": characteristics.soul,
            "will": characteristics.will
        }
        self.graph_store.update_persona_state(self.persona_id, characteristics=char_dict)
