from datetime import datetime
from typing import Dict, List, Optional
from neo4j import GraphDatabase
from brain.memory import Memory, MemoryType
from .keyword_extractor import KeywordExtractor

class Neo4jGraph:
    def __init__(self, uri: str = "neo4j+s://a9277d8e.databases.neo4j.io", 
                 username: str = "neo4j", 
                 password: str = "tKSk2m5MwQr9w25IbSnB07KccMmTfjFtjcCsQIraczk"):
        """Initialize Neo4j connection with cloud instance parameters"""
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            # Test the connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("✅ Successfully connected to Neo4j database")
            self._setup_indexes()
            # Initialize KeywordExtractor for keyword extraction
            self.keyword_extractor = KeywordExtractor()
        except Exception as e:
            print(f"❌ Failed to connect to Neo4j: {str(e)}")
            raise

    def _setup_indexes(self):
        """Set up required indexes in Neo4j"""
        with self.driver.session() as session:
            # Create basic indexes
            session.execute_write(self._create_basic_indexes)
            # Try to create vector index if available
            try:
                session.execute_write(self._create_vector_index)
            except Exception as e:
                print(f"Note: Vector index not created (optional feature): {str(e)}")

    @staticmethod
    def _create_vector_index(tx):
        """Create vector index for Memory nodes on the vector property"""
        try:
            # Create vector index with proper configuration
            tx.run(
                "CREATE VECTOR INDEX memory_vector_idx IF NOT EXISTS "
                "FOR (m:Memory) "
                "ON m.vector "
                "OPTIONS { indexConfig: { "
                "`vector.dimensions`: 1536, "  # BGE embeddings dimension
                "`vector.similarity_function`: 'cosine', "  # Cosine similarity is generally best for text embeddings
                "`vector.quantization.enabled`: true "  # Enable quantization for better memory usage
                "}} "
            )
            print("✅ Created vector index for Memory nodes")
        except Exception as e:
            print(f"Warning: Vector index not created (optional feature): {str(e)}")
            print("Vector similarity search will fall back to manual calculation")

    @staticmethod
    def _create_basic_indexes(tx):
        """Create basic indexes for Memory nodes"""
        try:
            # Index for memory type
            tx.run(
                "CREATE INDEX memory_type_idx IF NOT EXISTS "
                "FOR (m:Memory) ON (m.type)"
            )
            print("Created memory type index")
            
            # Index for memory content
            tx.run(
                "CREATE INDEX memory_content_idx IF NOT EXISTS "
                "FOR (m:Memory) ON (m.content)"
            )
            print("Created memory content index")
            
            # Index for timestamp
            tx.run(
                "CREATE INDEX memory_timestamp_idx IF NOT EXISTS "
                "FOR (m:Memory) ON (m.timestamp)"
            )
            print("Created memory timestamp index")
        except Exception as e:
            print(f"Warning: Could not create basic indexes: {str(e)}")

    def close(self):
        """Close the Neo4j driver connection"""
        self.driver.close()

    async def create_memory_node(self, persona_id: str, content: str, memory_type: str | MemoryType, importance: float = 0.0,
                           emotional_value: float = 0.0, vector: Optional[List[float]] = None, 
                           timestamp: Optional[datetime] = None, mood: str = "neutral", 
                           keywords: Optional[List[str]] = None) -> str:
        """Create a memory node in Neo4j and connect it to persona
        
        Args:
            persona_id: ID of the persona this memory belongs to
            content: The text content of the memory
            memory_type: The type of memory (e.g. 'observation', 'reflection', etc)
            importance: Importance score of the memory (0.0 to 1.0)
            emotional_value: Emotional impact score (-1.0 to 1.0)
            vector: Optional embedding vector for the memory content
            timestamp: Optional timestamp for when the memory was created
            mood: Current mood when memory was created
            keywords: Optional list of keywords associated with the memory. If not provided,
                     they will be automatically extracted from the content.
            
        Returns:
            str: ID of the created memory node
        """
        # Convert memory_type to string if it's an enum
        if isinstance(memory_type, MemoryType):
            memory_type = memory_type.value

        # Extract keywords if not provided
        if keywords is None:
            try:
                keywords = await self.keyword_extractor.extract_keywords(content)
            except Exception as e:
                print(f"Warning: Failed to extract keywords: {str(e)}")
                keywords = []

        with self.driver.session() as session:
            result = session.execute_write(
                self._create_memory_node_tx,
                persona_id=persona_id,
                content=content,
                memory_type=memory_type,
                importance=importance,
                emotional_value=emotional_value,
                vector=vector,
                timestamp=timestamp or datetime.now(),
                mood=mood,
                keywords=keywords
            )
            return result

    def _create_memory_node_tx(self, tx, persona_id: str, content: str, memory_type: str, importance: float,
                           emotional_value: float, vector: Optional[List[float]], timestamp: datetime,
                           mood: str, keywords: List[str]) -> str:
        """Transaction function to create a memory node and establish relationships"""
        
        
        
        
        
        
        
        # Create memory node
        query = (
            "MATCH (p:Persona {id: $persona_id}) "
            "WITH p LIMIT 1 "  # Ensure single persona match
            "CREATE (m:Memory {"
            "content: $content, "
            "type: $type, "
            "importance: $importance, "
            "emotional_value: $emotional_value, "
            "vector: $vector, "
            "timestamp: $timestamp, "
            "mood: $mood, "
            "keywords: $keywords, "
            "node_type: 'memory'"
            "}) "
            "CREATE (p)-[r:HAS_MEMORY]->(m) "
            "RETURN elementId(m) as node_id"
        )
        
        result = tx.run(
            query,
            persona_id=persona_id,
            content=content,
            type=memory_type,
            importance=importance,
            emotional_value=emotional_value,
            vector=vector,
            timestamp=timestamp.isoformat(),
            mood=mood,
            keywords=keywords
        )
        record = result.single()
        return str(record["node_id"])
    
    async def create_persona_node(self, persona_id: str, persona_name: str, persona_profile: str, 
                         characteristics: Optional[Dict[str, int] | 'Characteristics'] = None, goals: Optional[List[str]] = None, plans: Optional[List[str]] = None, schedule: Optional[List[str]] = None) -> str:
        """Create a persona node in the graph
        
        Args:
            persona_id: ID of the persona
            persona_name: Name of the persona
            persona_profile: Profile description
            characteristics: Either a Characteristics object or a dict with mind, body, heart, soul, will values
        """
        # Convert Characteristics object to dict if needed
        char_dict = {}
        if characteristics is not None:
            if hasattr(characteristics, '__dict__'):
                # It's a Characteristics object
                char_dict = {
                    'mind': getattr(characteristics, 'mind', 0),
                    'body': getattr(characteristics, 'body', 0),
                    'heart': getattr(characteristics, 'heart', 0),
                    'soul': getattr(characteristics, 'soul', 0),
                    'will': getattr(characteristics, 'will', 0)
                }
            else:
                # It's already a dict
                char_dict = characteristics

        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(
                    "CREATE (p:Persona {"
                    "id: $persona_id, "
                    "name: $persona_name, "
                    "profile: $persona_profile, "
                    "node_type: 'persona', "
                    "characteristics: $characteristics, "
                    "mood: $mood, "
                    "status: $status, "
                    "plans: $plans, "
                    "goals: $goals, "
                    "schedule: $schedule"
                    "}) "
                    "RETURN elementId(p) as node_id",
                    persona_id=persona_id,
                    persona_name=persona_name,
                    persona_profile=persona_profile,
                    characteristics=char_dict,
                    mood="neutral",
                    status="active", 
                    plans=plans,
                    goals=goals,
                    schedule=schedule
                ).single()
            )
            return result["node_id"]

    def get_all_memories(self, persona_id: str) -> List[Dict]:
        """Get all memories for a specific persona"""
        with self.driver.session() as session:
            return session.execute_read(self._get_all_memories, persona_id=persona_id)
        
    @staticmethod
    def _get_all_memories(tx, persona_id: str) -> List[Dict]:
        """Transaction function to get all memories for a specific persona"""
        query = (
            "MATCH (p:Persona {id: $persona_id})-[:HAS_MEMORY]->(m:Memory) "
            "RETURN m, elementId(m) as node_id"
        )
        result = tx.run(query, persona_id=persona_id)
        return [{
            "memory": {
                **dict(record["m"]),  # All properties from the memory node
                "node_id": record["node_id"]  # Add the node ID
            }
        } for record in result]
    
    def get_all_personas(self) -> List[Dict]:
        """Get all persona nodes and their IDs from the graph"""
        with self.driver.session() as session:
            return session.execute_read(self._get_all_personas)

    @staticmethod 
    def _get_all_personas(tx) -> List[Dict]:
        query = (
            "MATCH (p:Persona) "
            "RETURN p, elementId(p) as node_id"
        )
        result = tx.run(query)
        return [{
            "persona": {
                **dict(record["p"]),  # All properties from persona node
                "node_id": record["node_id"]  # Add the node ID
            }
        } for record in result]
        
    

    def get_persona_memories(self, persona_id: str, limit: int = 3) -> List[Dict]:
        """Get the last 3 memory nodes attached to this persona"""
        with self.driver.session() as session:
            return session.execute_read(
                self._get_persona_memories,
                persona_id=persona_id,
                limit=limit
            )
        

    @staticmethod
    def _get_persona_memories(tx, persona_id: str, limit: int) -> List[Dict]:
        """Transaction function to get the last 3 memory nodes attached to this persona"""
        query = (
            "MATCH (p:Persona {id: $persona_id})-[:HAS_MEMORY]->(m:Memory) "
            "RETURN m, elementId(m) as node_id "
            "ORDER BY m.timestamp DESC "
            "LIMIT $limit"
        )
        result = tx.run(query, persona_id=persona_id, limit=limit)
        return [{"memory": dict(record["m"]), "node_id": record["node_id"]} for record in result]

    def get_all_memories_by_type(self, persona_id: str, memory_type: str) -> List[Dict]:
        """Get all memories of a specific type for a specific persona"""
        with self.driver.session() as session:
            return session.execute_read(
                self._get_all_memories_by_type,
                persona_id=persona_id,
                memory_type=memory_type
            )
        
    @staticmethod
    def _get_all_memories_by_type(tx, persona_id: str, memory_type: str) -> List[Dict]:
        """Transaction function to get all memories of a specific type for a specific persona"""
        query = (
            "MATCH (p:Persona {id: $persona_id})-[:HAS_MEMORY]->(m:Memory) "
            "WHERE m.type = $memory_type "
            "RETURN m"
        )
        result = tx.run(query, persona_id=persona_id, memory_type=memory_type)
        return [{"memory": dict(record["m"])} for record in result]
    
    def get_all_memories_by_content(self, persona_id: str, content: str) -> List[Dict]:
        """Get all memories containing a specific content for a specific persona"""
        with self.driver.session() as session:
            return session.execute_read(
                self._get_all_memories_by_content,
                persona_id=persona_id,
                content=content
            )
        
    @staticmethod
    def _get_all_memories_by_content(tx, persona_id: str, content: str) -> List[Dict]:
        """Transaction function to get all memories containing a specific content for a specific persona.
        Uses a simple string match since we don't have fulltext search available."""
        query = (
            "MATCH (p:Persona {id: $persona_id})-[:HAS_MEMORY]->(m:Memory) "
            "WHERE toLower(m.content) CONTAINS toLower($content) "  # Case-insensitive contains match
            "RETURN m"
        )
        result = tx.run(query, persona_id=persona_id, content=content)
        return [{"memory": dict(record["m"])} for record in result]
    
    def search_similar_memories(self, persona_id: str, query_vector: List[float], top_k: int = 10) -> List[Dict]:
        """Search for similar memories using vector similarity index"""
        with self.driver.session() as session:
            try:
                # Try using vector index first
                return session.execute_read(
                    self._search_similar_memories_with_index,
                    persona_id=persona_id,
                    query_vector=query_vector,
                    top_k=top_k
                )
            except Exception as e:
                print(f"Warning: Vector index search failed, falling back to manual calculation: {str(e)}")
                return session.execute_read(
                    self._search_similar_memories,
                    persona_id=persona_id,
                    query_vector=query_vector,
                    top_k=top_k
                )
    
    @staticmethod
    def _search_similar_memories_with_index(tx, persona_id: str, query_vector: List[float], top_k: int) -> List[Dict]:
        """Transaction function to search for similar memories using vector index"""
        query = (
            "MATCH (p:Persona {id: $persona_id})-[:HAS_MEMORY]->(m:Memory) "
            "WITH m "
            "CALL db.index.vector.queryNodes('memory_vector_idx', $top_k, $query_vector) "
            "YIELD node AS memory, score "
            "WHERE memory = m "  # Filter to only include memories of this persona
            "RETURN memory AS m, score AS similarity "
            "ORDER BY similarity DESC "
            "LIMIT $top_k"
        )
        result = tx.run(
            query,
            persona_id=persona_id,
            query_vector=query_vector,
            top_k=top_k
        )
        return [{"memory": dict(record["m"]), "similarity": record["similarity"]} for record in result]

    @staticmethod
    def _search_similar_memories(tx, persona_id: str, query_vector: List[float], top_k: int) -> List[Dict]:
        """Transaction function to search for similar memories using manual cosine similarity calculation (fallback)"""
        query = (
            "MATCH (p:Persona {id: $persona_id})-[:HAS_MEMORY]->(m:Memory) "
            "WHERE m.vector IS NOT NULL "
            "WITH m, m.vector as vec1, $query_vector as vec2 "
            "WITH m, "
            "REDUCE(dot = 0.0, i IN RANGE(0, size(vec1)-1) | dot + vec1[i] * vec2[i]) / "
            "(SQRT(REDUCE(l2 = 0.0, i IN RANGE(0, size(vec1)-1) | l2 + vec1[i] * vec1[i])) * "
            "SQRT(REDUCE(l2 = 0.0, i IN RANGE(0, size(vec2)-1) | l2 + vec2[i] * vec2[i]))) "
            "as similarity "
            "WHERE similarity IS NOT NULL "
            "RETURN m, similarity "
            "ORDER BY similarity DESC "
            "LIMIT $top_k"
        )
        result = tx.run(
            query,
            persona_id=persona_id,
            query_vector=query_vector,
            top_k=top_k
        )
        return [{"memory": dict(record["m"]), "similarity": record["similarity"]} for record in result]

    @staticmethod
    def _enhanced_memory_search_tx(tx, query_vector: List[float], topic_ids: List[str], top_k: int) -> List[Dict]:
        """
        Transaction function for enhanced memory search
        Combines vector similarity with topic relevance
        """
        # Build topic filter condition if topics are provided
        topic_filter = ""
        if topic_ids:
            topic_filter = "AND EXISTS ((m)-[:BELONGS_TO]->(:Topic)) "
            topic_filter += "AND ANY(topic IN [(m)-[:BELONGS_TO]->(t:Topic) | t.id] WHERE topic IN $topic_ids) "

        # Manual cosine similarity calculation
        query = (
            "MATCH (m:Memory) "
            f"WHERE m.vector IS NOT NULL {topic_filter}"
            "WITH m, "
            "REDUCE(dot = 0.0, i IN RANGE(0, size(m.vector)-1) | dot + m.vector[i] * $query_vector[i]) / "
            "(SQRT(REDUCE(l2 = 0.0, i IN RANGE(0, size(m.vector)-1) | l2 + m.vector[i] * m.vector[i])) * "
            "SQRT(REDUCE(l2 = 0.0, i IN RANGE(0, size($query_vector)-1) | l2 + $query_vector[i] * $query_vector[i]))) "
            "AS similarity "
            "WITH m, similarity, "
            "SIZE([(m)-[:BELONGS_TO]->(t:Topic) WHERE t.id IN $topic_ids | t]) AS topic_matches "
            "RETURN m, similarity, topic_matches "
            "ORDER BY (similarity * 0.7 + (toFloat(topic_matches) / size($topic_ids) * 0.3)) DESC "
            "LIMIT $top_k"
        )
        
        result = tx.run(
            query,
            query_vector=query_vector,
            topic_ids=topic_ids,
            top_k=top_k
        )
        
        return [
            {
                "memory": dict(record["m"]),
                "similarity": record["similarity"],
                "topic_relevance": record["topic_matches"] / len(topic_ids) if topic_ids else 0
            }
            for record in result
        ]

    def update_persona_state(self, persona_id, characteristics=None, mood=None, status=None, plans=None, goals=None, schedule=None):
        """Update persona state in Neo4j."""
        try:
            # Convert characteristics to primitive types
            if characteristics and isinstance(characteristics, dict):
                characteristics = {k: int(v) if isinstance(v, (int, float)) else v 
                                 for k, v in characteristics.items()}
            
            # Ensure plans, goals, and schedule are lists of strings
            if plans is not None:
                plans = [str(p) for p in plans] if isinstance(plans, list) else []
            if goals is not None:
                goals = [str(g) for g in goals] if isinstance(goals, list) else []
            if schedule is not None:
                schedule = [str(s) for s in schedule] if isinstance(schedule, list) else []
            
            # Build update query dynamically based on provided parameters
            update_parts = []
            params = {"persona_id": persona_id}
            
            if characteristics is not None:
                update_parts.append("p.characteristics = $characteristics")
                params["characteristics"] = characteristics
            if mood is not None:
                update_parts.append("p.mood = $mood")
                params["mood"] = str(mood)
            if status is not None:
                update_parts.append("p.status = $status")
                params["status"] = str(status)
            if plans is not None:
                update_parts.append("p.plans = $plans")
                params["plans"] = plans
            if goals is not None:
                update_parts.append("p.goals = $goals")
                params["goals"] = goals
            if schedule is not None:
                update_parts.append("p.schedule = $schedule")
                params["schedule"] = schedule
                
            if not update_parts:
                return  # Nothing to update
                
            query = f"""
            MATCH (p:Persona {{id: $persona_id}})
            SET {', '.join(update_parts)}
            RETURN p
            """
            
            with self.driver.session() as session:
                result = session.run(query, params)
                return result.single()
                
        except Exception as e:
            print(f"Error updating persona state: {str(e)}")
            raise

    def get_persona_state(self, persona_id: str) -> Dict:
        """Get persona state from Neo4j
        
        Args:
            persona_id: ID of the persona
            
        Returns:
            dict: Persona state including mood, status, plans, goals, and characteristics
        """
        with self.driver.session() as session:
            return session.execute_read(self._get_persona_state_tx, persona_id=persona_id)

    async def check_persona_exists(self, persona_id: str) -> bool:
        """Check if a persona exists in Neo4j
        
        Args:
            persona_id: ID of the persona to check
            
        Returns:
            bool: True if the persona exists, False otherwise
        """
        with self.driver.session() as session:
            result = session.execute_read(self._check_persona_exists_tx, persona_id=persona_id)
            return result

    @staticmethod
    def _check_persona_exists_tx(tx, persona_id: str) -> bool:
        """Transaction function to check if a persona exists"""
        query = (
            "MATCH (p:Persona {id: $persona_id}) "
            "RETURN COUNT(p) > 0 as exists"
        )
        result = tx.run(query, persona_id=persona_id)
        record = result.single()
        return record["exists"]

    @staticmethod
    def _get_persona_state_tx(tx, persona_id: str) -> Dict:
        """Transaction function to get persona state"""
        query = (
            "MATCH (p:Persona {id: $persona_id}) "
            "RETURN p"
        )
        result = tx.run(query, persona_id=persona_id)
        record = result.single()
        if not record:
            raise ValueError(f"Persona with ID {persona_id} not found")
            
        persona = dict(record["p"])
        return {
            "id": persona.get("id"),
            "name": persona.get("name"),
            "profile": persona.get("profile"),
            "mood": persona.get("mood", "neutral"),
            "status": persona.get("status", "active"),
            "plans": persona.get("plans", []),
            "goals": persona.get("goals", []),
            "schedule": persona.get("schedule", []),
            "characteristics": persona.get("characteristics", {
                "mind": 0,
                "body": 0,
                "heart": 0,
                "soul": 0,
                "will": 0
            })
        }
