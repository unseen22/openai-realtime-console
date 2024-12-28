from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime
import json
from enum import Enum
from dataclasses import dataclass
import pathlib
import sys
import asyncio
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
    def link_memory_to_topics(self, memory_id: str, topic_ids: List[str]):
        """Create relationships between a memory and its topics in Neo4j"""
        if not self.graph:
            return

        with self.graph.driver.session() as session:
            for topic_id in topic_ids:
                session.execute_write(
                    self._create_memory_topic_relationship_tx,
                    memory_id,
                    topic_id
                )

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
        
        Args:
            query: The search query text
            vector: The query embedding vector
            persona_id: Optional persona ID to filter memories
            top_k: Maximum number of results to return
            
        Returns:
            List of dicts containing memory data with similarity and topic relevance scores
        """
        if not self.graph:
            return []

        # Run topic categorization and keyword extraction concurrently
        query_vector_future = asyncio.create_task(self.embedder.embed_memory(query))
        topic_ids_future = asyncio.create_task(self.categorize_memory(query))
        query_keywords_future = asyncio.create_task(self.generate_keywords(query))
        
        # Wait for all tasks to complete
        query_vector = await query_vector_future
        topic_ids = await topic_ids_future
        query_keywords = await query_keywords_future
        
        with self.graph.driver.session() as session:
            return session.execute_read(
                self._enhanced_memory_search_tx,
                query_vector=query_vector,
                topic_ids=topic_ids,
                query_keywords=query_keywords,
                persona_id=persona_id,
                top_k=top_k
            )

    @staticmethod
    def _enhanced_memory_search_tx(tx, query_vector: List[float], topic_ids: List[str], query_keywords: List[str], persona_id: Optional[str], top_k: int) -> List[Dict]:
        """
        Transaction function for enhanced memory search
        Combines vector similarity with topic relevance and keyword matching
        """
        # Build base query with proper persona matching if needed
        base_match = "MATCH (m:Memory)"
        if persona_id:
            base_match = "MATCH (p:Persona {id: $persona_id})-[:HAS_MEMORY]->(m:Memory)"

        # Build topic filter condition if topics are provided
        topic_filter = ""
        if topic_ids:
            topic_filter = "AND EXISTS ((m)-[:BELONGS_TO]->(:Topic)) "
            topic_filter += "AND ANY(topic IN [(m)-[:BELONGS_TO]->(t:Topic) | t.id] WHERE topic IN $topic_ids) "

        # Manual cosine similarity calculation with zero-division protection
        query = (
            f"{base_match} "
            f"WHERE m.vector IS NOT NULL {topic_filter}"
            "WITH m, "
            "REDUCE(dot = 0.0, i IN RANGE(0, size(m.vector)-1) | dot + m.vector[i] * $query_vector[i]) as dot_product, "
            "SQRT(REDUCE(l2 = 0.0, i IN RANGE(0, size(m.vector)-1) | l2 + m.vector[i] * m.vector[i])) as mag1, "
            "SQRT(REDUCE(l2 = 0.0, i IN RANGE(0, size($query_vector)-1) | l2 + $query_vector[i] * $query_vector[i])) as mag2 "
            "WITH m, "
            "CASE "
            "  WHEN mag1 * mag2 = 0 THEN 0 "  # Handle zero magnitude
            "  ELSE dot_product / (mag1 * mag2) "
            "END as similarity "
            "WITH m, similarity, "
            "CASE "
            "  WHEN $topic_ids = [] THEN 0 "  # Handle empty topic list
            "  ELSE SIZE([(m)-[:BELONGS_TO]->(t:Topic) WHERE t.id IN $topic_ids | t]) "
            "END as topic_matches "
            "WITH m, similarity, topic_matches, "
            "CASE "
            "  WHEN $topic_ids = [] THEN 0 "  # Handle empty topic list for relevance calculation
            "  ELSE toFloat(topic_matches) / size($topic_ids) "
            "END as topic_relevance "
            "WITH m, similarity, topic_matches, topic_relevance, "
            "CASE "
            "  WHEN $query_keywords = [] THEN 0 "  # Handle empty keywords list
            "  ELSE SIZE([k IN $query_keywords WHERE k IN m.keywords | k]) / toFloat(SIZE($query_keywords)) "
            "END as keyword_relevance "
            "RETURN m, similarity, topic_matches, topic_relevance, keyword_relevance "
            "ORDER BY (similarity * 0.5 + topic_relevance * 0.25 + keyword_relevance * 0.25) DESC "  # Adjusted weights
            "LIMIT $top_k"
        )
        
        result = tx.run(
            query,
            query_vector=query_vector,
            topic_ids=topic_ids or [],  # Ensure topic_ids is never None
            query_keywords=query_keywords or [],  # Ensure query_keywords is never None
            persona_id=persona_id,
            top_k=top_k
        )
        
        return [
            {
                "memory": dict(record["m"]),
                "similarity": record["similarity"],
                "topic_relevance": record["topic_relevance"],
                "keyword_relevance": record["keyword_relevance"]
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

    def get_topic_path(self, topic_id: str) -> List[str]:
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

    async def generate_keywords(self, content: str) -> List[str]:
        """Generate keywords for a memory.
        
        Args:
            content: The text content to generate keywords from
            
        Returns:
            List of keyword strings
        """
        return await self.keyword_extractor.extract_keywords(content)
