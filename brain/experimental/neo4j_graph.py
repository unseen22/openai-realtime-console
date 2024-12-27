from datetime import datetime
from typing import Dict, List, Optional
from neo4j import GraphDatabase

class Neo4jGraph:
    def __init__(self, uri: str = "neo4j+s://a9277d8e.databases.neo4j.io", 
                 username: str = "neo4j", 
                 password: str = "tKSk2m5MwQr9w25IbSnB07KccMmTfjFtjcCsQIraczk"):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self._setup_indexes()

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
        tx.run(
            "CREATE VECTOR INDEX memory_vector_idx IF NOT EXISTS "
            "FOR (m:Memory) ON (m.vector) "
            "OPTIONS { indexConfig: {"
            "'vector.dimensions': 768, "  # Match embedder's vector size
            "'vector.similarity_function': 'cosine'"
            "}}"
        )

    @staticmethod
    def _create_basic_indexes(tx):
        """Create basic indexes for Memory nodes"""
        try:
            # Index for memory type
            tx.run(
                "CREATE INDEX memory_type_idx IF NOT EXISTS "
                "FOR (m:Memory) ON (m.type)"
            )
            # Index for memory content
            tx.run(
                "CREATE INDEX memory_content_idx IF NOT EXISTS "
                "FOR (m:Memory) ON (m.content)"
            )
        except Exception as e:
            print(f"Warning: Could not create basic indexes: {str(e)}")

    def close(self):
        """Close the Neo4j driver connection"""
        self.driver.close()

    def create_memory_node(self, persona_id: str, content: str, memory_type: str, importance: float = 0.0,
                          vector: Optional[List[float]] = None, timestamp: Optional[datetime] = None) -> str:
        """Create a memory node in Neo4j and connect it to persona
        
        Args:
            persona_id: ID of the persona this memory belongs to
            content: The text content of the memory
            memory_type: The type of memory (e.g. 'observation', 'reflection', etc)
            importance: Importance score of the memory (0.0 to 1.0)
            vector: Optional embedding vector for the memory content
            timestamp: Optional timestamp for when the memory was created
            
        Returns:
            str: ID of the created memory node
        """
        with self.driver.session() as session:
            result = session.execute_write(
                self._create_memory_node_tx,
                persona_id=persona_id,
                content=content,
                memory_type=memory_type,
                importance=importance,
                vector=vector,
                timestamp=timestamp or datetime.now()
            )
            return result

    @staticmethod
    def _create_memory_node_tx(tx, persona_id: str, content: str, memory_type: str, importance: float,
                              vector: Optional[List[float]], timestamp: datetime) -> str:
        """Transaction function to create a memory node and establish relationships"""
        # Create memory node
        query = (
            "MATCH (p:Persona {id: $persona_id}) "
            "WITH p LIMIT 1 "  # Ensure single persona match
            "CREATE (m:Memory {"
            "content: $content, "
            "type: $type, "
            "importance: $importance, "
            "vector: $vector, "
            "timestamp: $timestamp, "
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
            vector=vector,
            timestamp=timestamp.isoformat()
        )
        record = result.single()
        return str(record["node_id"])
    
    def create_persona_node(self, persona_id: str, persona_name: str, persona_profile: str) -> str:
        """Create a persona node in the graph"""
        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(
                    "CREATE (p:Persona {id: $persona_id, name: $persona_name, profile: $persona_profile, "
                    "node_type: 'persona'}) "
                    "RETURN elementId(p) as node_id",
                    persona_id=persona_id,
                    persona_name=persona_name,
                    persona_profile=persona_profile
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
            "RETURN m"
        )
        result = tx.run(query, persona_id=persona_id)
        return [{"memory": dict(record["m"])} for record in result]
    
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
            "WHERE m.vector IS NOT NULL "
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
