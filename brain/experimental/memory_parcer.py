from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from datetime import datetime
import json
from enum import Enum
from dataclasses import dataclass
import pathlib
import sys
import asyncio
from functools import lru_cache, wraps
from time import time
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import functools
# Add parent directory to path to allow imports
current_dir = pathlib.Path(__file__).parent
parent_dir = str(current_dir.parent.parent)
sys.path.append(parent_dir)

# Import from brain package
from brain.llm_chooser import LLMChooser
from .neo4j_graph import Neo4jGraph  # Changed to relative import
from .keyword_extractor import KeywordExtractor
from brain.embedder import Embedder

class TopicType(Enum):
    CORE = "core"
    CATEGORY = "category"
    SUBCATEGORY = "subcategory"
    CUSTOM = "custom"

class CoreCategory(Enum):
    ENTERTAINMENT = "entertainment"
    HOBBIES = "hobbies"
    SOCIAL = "social"
    DAILY = "daily"

@dataclass
class TopicNode:
    id: str
    name: str
    type: TopicType
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    importance: float = 0.5
    related_topics: List[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.related_topics is None:
            self.related_topics = []

class TopicHierarchy:
    """Manages the topic hierarchy and relationships"""
    
    def __init__(self, graph: Optional[Neo4jGraph] = None):
        self.topics: Dict[str, TopicNode] = {}
        self.graph = graph
        self._initialize_core_topics()
        if self.graph:
            self._sync_topics_to_neo4j()

    def _sync_topics_to_neo4j(self):
        """Synchronize topic hierarchy to Neo4j"""
        try:
            with self.graph.driver.session() as session:
                # Create topic nodes
                for topic in self.topics.values():
                    session.execute_write(self._create_topic_node_tx, topic)
                
                # Create relationships
                for topic in self.topics.values():
                    if topic.parent_id:
                        session.execute_write(
                            self._create_topic_relationship_tx,
                            topic.id,
                            topic.parent_id
                        )
        except Exception as e:
            print(f"Warning during topic sync: {str(e)}")

    @staticmethod
    def _create_topic_node_tx(tx, topic: TopicNode):
        """Create a topic node in Neo4j"""
        # Convert metadata to JSON string to ensure primitive type
        metadata_str = json.dumps(topic.metadata) if topic.metadata else "{}"
        
        query = (
            "MERGE (t:Topic {"
            "id: $id"
            "}) "
            "SET t.name = $name, "
            "t.type = $type, "
            "t.importance = $importance, "
            "t.metadata = $metadata, "
            "t.created_at = datetime()"
        )
        tx.run(
            query,
            id=topic.id,
            name=topic.name,
            type=topic.type.value,
            importance=topic.importance,
            metadata=metadata_str
        )

    @staticmethod
    def _create_topic_relationship_tx(tx, topic_id: str, parent_id: str):
        """Create a topic hierarchy relationship in Neo4j"""
        query = (
            "MATCH (child:Topic {id: $topic_id}), "
            "(parent:Topic {id: $parent_id}) "
            "MERGE (parent)-[:CONTAINS]->(child)"
        )
        tx.run(query, topic_id=topic_id, parent_id=parent_id)

    def _initialize_core_topics(self):
        """Initialize the core topic categories and their subcategories"""
        
        # Entertainment & Media
        entertainment = self._create_category("entertainment", "Entertainment & Media")
        self._create_subcategory("music", "Music", entertainment.id, {
            "topics": ["genres", "artists", "favorite_songs", "listening_history"]
        })
        self._create_subcategory("videos", "Videos", entertainment.id, {
            "topics": ["movies", "tv_shows", "youtube", "creators"]
        })
        self._create_subcategory("games", "Games", entertainment.id, {
            "topics": ["video_games", "board_games", "game_categories"]
        })

        # Hobbies & Activities
        hobbies = self._create_category("hobbies", "Hobbies & Activities")
        self._create_subcategory("creative", "Creative Activities", hobbies.id, {
            "topics": ["writing", "art", "crafts"]
        })
        self._create_subcategory("physical", "Physical Activities", hobbies.id, {
            "topics": ["sports", "exercise", "dance"]
        })
        self._create_subcategory("learning", "Learning", hobbies.id, {
            "topics": ["courses", "books", "skills"]
        })

        # Social & Relationships
        social = self._create_category("social", "Social & Relationships")
        for topic in ["friends", "family", "professional", "communities", "online"]:
            self._create_topic(topic, topic.title(), social.id)

        # Daily Life
        daily = self._create_category("daily", "Daily Life")
        for topic in ["routines", "places", "food", "shopping", "work"]:
            self._create_topic(topic, topic.title(), daily.id)

    def _create_category(self, id_prefix: str, name: str) -> TopicNode:
        """Create a main category topic"""
        topic = TopicNode(
            id=f"cat_{id_prefix}",
            name=name,
            type=TopicType.CATEGORY,
            importance=0.8
        )
        self.topics[topic.id] = topic
        return topic

    def _create_subcategory(self, id_prefix: str, name: str, parent_id: str, 
                           metadata: Optional[Dict] = None) -> TopicNode:
        """Create a subcategory topic"""
        topic = TopicNode(
            id=f"sub_{id_prefix}",
            name=name,
            type=TopicType.SUBCATEGORY,
            parent_id=parent_id,
            metadata=metadata or {},
            importance=0.6
        )
        self.topics[topic.id] = topic
        return topic

    def _create_topic(self, id_prefix: str, name: str, parent_id: str) -> TopicNode:
        """Create a leaf topic"""
        topic = TopicNode(
            id=f"topic_{id_prefix}",
            name=name,
            type=TopicType.CUSTOM,
            parent_id=parent_id,
            importance=0.5
        )
        self.topics[topic.id] = topic
        return topic

def async_cache(ttl_seconds: int = 300):
    """Custom cache decorator for async functions"""
    cache = {}
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = time()
            
            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < ttl_seconds:
                    return result
                del cache[key]
            
            result = await func(*args, **kwargs)
            cache[key] = (result, now)
            return result
        return wrapper
    return decorator

class MemoryParser:
    """Parses and categorizes memories into topics"""
    
    def __init__(self, neo4j_graph=None, llm_tool: Optional[LLMChooser] = None):
        """Initialize MemoryParser
        
        Args:
            neo4j_graph: Optional Neo4j graph instance
            llm_tool: Optional LLM chooser instance
        """
        self.graph = neo4j_graph
        self.topic_hierarchy = TopicHierarchy(graph=neo4j_graph)
        self.llm_tool = llm_tool or LLMChooser()
        self.keyword_extractor = KeywordExtractor(llm_tool=self.llm_tool)
        self.embedder = Embedder()
        
        # Optimize thread pool and connection handling
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._session_pool = []
        self._max_pool_size = 10
        self._warmup_done = False
        
    async def initialize(self):
        """Initialize and warm up the parser components"""
        if self._warmup_done:
            return
            
        # Initialize session pool
        if self.graph:
            for _ in range(min(3, self._max_pool_size)):  # Start with 3 sessions
                self._session_pool.append(self.graph.driver.session())
        
        # Warm up embedder with common queries
        # warmup_texts = [
        #     "What did I do yesterday?",
        #     "Tell me about my day",
        #     "My recent activities"
        # ]
        
        # Run warmup tasks concurrently
        # await asyncio.gather(
        #     *[self.embedder.embed_memory(text) for text in warmup_texts],
        #     *[self.generate_keywords(text) for text in warmup_texts]
        # )
        
        # Warm up Neo4j connection and query plan
        if self.graph:
            with self.graph.driver.session() as session:
                # Warm up index
                session.run(
                    "MATCH (m:Memory) WHERE m.vector IS NOT NULL "
                    "WITH m LIMIT 1 "
                    "RETURN m"
                ).consume()
                
                # Cache topic hierarchy
                self.topic_hierarchy._initialize_core_topics()
        
        self._warmup_done = True
    
    def _get_session(self):
        """Get a session from the pool or create a new one"""
        if not self._session_pool:
            if self.graph and len(self._session_pool) < self._max_pool_size:
                return self.graph.driver.session()
            return None
        return self._session_pool.pop()
    
    def _return_session(self, session):
        """Return a session to the pool"""
        if session and len(self._session_pool) < self._max_pool_size:
            self._session_pool.append(session)
        else:
            session.close()

    @async_cache(ttl_seconds=300)
    async def embed_memory(self, content: str) -> List[float]:
        """Cached wrapper for memory embedding"""
        return await self.embedder.embed_memory(content)

    @async_cache(ttl_seconds=300)
    async def categorize_memory(self, content: str) -> List[str]:
        """
        Analyze memory content and return relevant topic IDs
        Uses LLM to detect topics from content
        """
        # Create hierarchy representation for LLM
        hierarchy_str = self._get_hierarchy_string()
        
        prompt = f"""Given this memory content: "{content}"
        
Identify relevant topics from the following hierarchy:

{hierarchy_str}

Consider:
- Main category (Entertainment, Hobbies, Social, Daily)
- Specific subcategories
- Related topics

Return a JSON array of topic paths, where each path is an array starting from the main category to the specific topic.
Example: [["Entertainment & Media", "Music", "Genres"], ["Social & Relationships", "Friends"]]

Only return the JSON array, no other text."""

        try:
            # Use OpenAI by default with more reliable model
            response = await self.llm_tool.generate_text(
                provider="openai",
                prompt=prompt,
                model="gpt-3.5-turbo",
                temperature=0.3,
                max_tokens=200
            )
            topic_paths = json.loads(response)
            return self._resolve_topic_paths(topic_paths)
        except Exception as e:
            print(f"Error categorizing memory: {e}")
            try:
                # Fallback to simpler categorization if JSON parsing fails
                print("Attempting fallback categorization...")
                lines = response.strip().split('\n')
                paths = []
                for line in lines:
                    if '->' in line:
                        path = [p.strip() for p in line.split('->')]
                        paths.append(path)
                    elif line.strip() and not line.startswith('[') and not line.startswith(']'):
                        paths.append([line.strip()])
                return self._resolve_topic_paths(paths)
            except Exception as e2:
                print(f"Fallback categorization failed: {e2}")
                return []

    @async_cache(ttl_seconds=300)
    async def generate_keywords(self, content: str) -> List[str]:
        """Cached wrapper for keyword generation"""
        return await self.keyword_extractor.extract_keywords(content)

    async def link_memory_to_topics(self, memory_id: str, topic_ids: List[str]):
        """Create relationships between a memory and its topics in Neo4j"""
        if not self.graph:
            print("🔍 No graph found, skipping memory linking in PARCER")
            return

        with self.graph.driver.session() as session:
            print(f"🔍 Linking memory {memory_id} to topics: {topic_ids}")
            for topic_id in topic_ids:
                session.execute_write(
                    self._create_memory_topic_relationship_tx,
                    memory_id,
                    topic_id
                )
            print("🔍 Memory linked to topics successfully")

    @staticmethod
    def _create_memory_topic_relationship_tx(tx, memory_id: str, topic_id: str):
        """Create a relationship between memory and topic in Neo4j"""
        query = (
            "MATCH (m:Memory), (t:Topic) "
            "WHERE elementId(m) = $memory_id AND t.id = $topic_id "
            "MERGE (m)-[:BELONGS_TO]->(t)"
        )
        tx.run(query, memory_id=memory_id, topic_id=topic_id)

    async def enhance_memory_search(self, query: str, persona_id: Optional[str] = None, top_k: int = 3) -> List[Dict]:
        """
        Enhanced memory search combining vector similarity, topic relevance, and keyword matching
        with optimized parallel processing and caching
        
        Args:
            query: The search query text
            persona_id: Optional persona ID to filter memories
            top_k: Maximum number of results to return
            
        Returns:
            List of dicts containing memory data with similarity and topic relevance scores
        """
        if not self.graph:
            return []

        # Ensure initialization is done
        if not self._warmup_done:
            await self.initialize()

        # Run tasks in parallel using asyncio.gather
        query_vector, topic_ids, query_keywords = await asyncio.gather(
            self.embed_memory(query),
            self.categorize_memory(query),
            self.generate_keywords(query)
        )
        # print(f"🔍 Query vector: {query_vector}")
        # print(f"🔍 Topic IDs: {topic_ids}")
        # print(f"🔍 Query keywords: {query_keywords}")
        # Use ThreadPoolExecutor for database operations with connection pooling
        loop = asyncio.get_event_loop()
        session = self._get_session()
        try:
            results = await loop.run_in_executor(
                self._executor,
                lambda: session.execute_read(
                    self._enhanced_memory_search_tx,
                    query_vector=query_vector,
                    topic_ids=topic_ids,
                    query_keywords=query_keywords,
                    persona_id=persona_id,
                    top_k=top_k
                )
            )
            return results
        finally:
            if session:
                self._return_session(session)

    @staticmethod
    def _enhanced_memory_search_tx(tx, query_vector: List[float], topic_ids: List[str], 
                                 query_keywords: List[str], persona_id: Optional[str], top_k: int) -> List[Dict]:
        """Optimized transaction function for enhanced memory search"""
        # Use parameterized query with optimized Neo4j query plan
        query = """
        CALL {
            MATCH (m:Memory)
            WHERE m.vector IS NOT NULL
            WITH m, m.vector AS vec1, $query_vector AS vec2
            WITH m, 
                 reduce(dot = 0.0, i in range(0, size(vec1)-1) | dot + vec1[i] * vec2[i]) as dotProduct,
                 sqrt(reduce(l2 = 0.0, i in range(0, size(vec1)-1) | l2 + vec1[i] * vec1[i])) as norm1,
                 sqrt(reduce(l2 = 0.0, i in range(0, size(vec2)-1) | l2 + vec2[i] * vec2[i])) as norm2
            WITH m, CASE 
                WHEN norm1 * norm2 = 0 THEN 0 
                ELSE abs(dotProduct / (norm1 * norm2))
            END as similarity
            ORDER BY similarity DESC
            LIMIT $top_k * 3
            RETURN m, similarity
        }

        WITH m, similarity
        
        // Optional persona filter
        %s
        
        // Calculate topic relevance efficiently
        WITH m, similarity,
        CASE
            WHEN size($topic_ids) = 0 THEN 0
            ELSE size([(m)-[:BELONGS_TO]->(t:Topic) WHERE t.id IN $topic_ids | t]) / toFloat(size($topic_ids))
        END as topic_relevance,
        
        // Calculate keyword relevance efficiently
        CASE
            WHEN size($query_keywords) = 0 THEN 0
            ELSE size([k IN $query_keywords WHERE k IN m.keywords | k]) / toFloat(size($query_keywords))
        END as keyword_relevance
        
        // Calculate final score and return results
        WITH m, similarity, topic_relevance, keyword_relevance,
        (similarity * 0.5 + topic_relevance * 0.25 + keyword_relevance * 0.25) as final_score
        ORDER BY final_score DESC
        LIMIT $top_k
        RETURN m, similarity, topic_relevance, keyword_relevance, final_score
        """ % ("MATCH (p:Persona {id: $persona_id})-[:HAS_MEMORY]->(m)" if persona_id else "")
        
        result = tx.run(
            query,
            query_vector=query_vector,
            topic_ids=topic_ids or [],
            query_keywords=query_keywords or [],
            persona_id=persona_id,
            top_k=top_k
        )
        
        return [
            {
                "memory": dict(record["m"]),
                "similarity": record["similarity"],
                "topic_relevance": record["topic_relevance"],
                "keyword_relevance": record["keyword_relevance"],
                "final_score": record["final_score"]
            }
            for record in result
        ]

    def get_memories_by_topic(self, topic_id: str, limit: int = 10) -> List[Dict]:
        """Get memories associated with a specific topic"""
        if not self.graph:
            return []

        with self.graph.driver.session() as session:
            return session.execute_read(
                self._get_memories_by_topic_tx,
                topic_id=topic_id,
                limit=limit
            )

    @staticmethod
    def _get_memories_by_topic_tx(tx, topic_id: str, limit: int) -> List[Dict]:
        """Transaction function to get memories by topic"""
        query = (
            "MATCH (t:Topic {id: $topic_id})<-[:BELONGS_TO]-(m:Memory) "
            "WITH m "
            "ORDER BY m.timestamp DESC "
            "LIMIT $limit "
            "RETURN m"
        )
        result = tx.run(query, topic_id=topic_id, limit=limit)
        return [{"memory": dict(record["m"])} for record in result]

    def _get_hierarchy_string(self) -> str:
        """Convert topic hierarchy to string representation for LLM prompt"""
        categories = [topic for topic in self.topic_hierarchy.topics.values() 
                     if topic.type == TopicType.CATEGORY]
        
        hierarchy = []
        for category in categories:
            category_str = [f"{category.name}"]
            subcategories = [topic for topic in self.topic_hierarchy.topics.values()
                           if topic.parent_id == category.id]
            
            for subcategory in subcategories:
                sub_str = f"  - {subcategory.name}"
                topics = [topic for topic in self.topic_hierarchy.topics.values()
                         if topic.parent_id == subcategory.id]
                
                if topics:
                    sub_str += "\n" + "\n".join(f"    - {topic.name}" for topic in topics)
                
                category_str.append(sub_str)
            
            hierarchy.extend(category_str)
        
        return "\n".join(hierarchy)

    def _resolve_topic_paths(self, topic_paths: List[List[str]]) -> List[str]:
        """Convert topic name paths to topic IDs"""
        topic_ids = []
        name_to_id = {topic.name: topic.id for topic in self.topic_hierarchy.topics.values()}
        
        for path in topic_paths:
            for topic_name in path:
                if topic_name in name_to_id:
                    topic_ids.append(name_to_id[topic_name])
        
        return list(set(topic_ids))  # Remove duplicates

    def calculate_topic_relationship(self, topic1_id: str, topic2_id: str) -> float:
        """
        Calculate relationship strength between topics based on:
        - Hierarchical proximity
        - Semantic similarity
        - Shared parent categories
        """
        topic1 = self.topic_hierarchy.topics.get(topic1_id)
        topic2 = self.topic_hierarchy.topics.get(topic2_id)
        
        if not topic1 or not topic2:
            return 0.0
            
        # Base relationship strength
        strength = 0.0
        
        # Same topic
        if topic1_id == topic2_id:
            return 1.0
            
        # Direct parent-child relationship
        if topic1.parent_id == topic2_id or topic2.parent_id == topic1_id:
            return 0.8
            
        # Siblings (same parent)
        if topic1.parent_id and topic1.parent_id == topic2.parent_id:
            return 0.6
            
        # Same category but different branches
        if self._get_root_category(topic1_id) == self._get_root_category(topic2_id):
            return 0.4
            
        return strength

    def _get_root_category(self, topic_id: str) -> Optional[str]:
        """Get the root category ID for a topic"""
        topic = self.topic_hierarchy.topics.get(topic_id)
        if not topic:
            return None
            
        while topic and topic.parent_id:
            topic = self.topic_hierarchy.topics.get(topic.parent_id)
            
        return topic.id if topic else None

    async def get_topic_path(self, topic_id: str) -> List[str]:
        """Get the full path of topic names from root to the given topic"""
        path = []
        topic = self.topic_hierarchy.topics.get(topic_id)
        
        while topic:
            path.append(topic.name)
            topic = self.topic_hierarchy.topics.get(topic.parent_id)
            
        return list(reversed(path))

    def get_related_topics(self, topic_id: str, min_strength: float = 0.4) -> List[Tuple[str, float]]:
        """Get related topics and their relationship strengths"""
        related = []
        topic = self.topic_hierarchy.topics.get(topic_id)
        
        if not topic:
            return []
            
        for other_id in self.topic_hierarchy.topics:
            if other_id != topic_id:
                strength = self.calculate_topic_relationship(topic_id, other_id)
                if strength >= min_strength:
                    related.append((other_id, strength))
                    
        return sorted(related, key=lambda x: x[1], reverse=True)
