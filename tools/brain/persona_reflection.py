import json
from brain.groq_tool import GroqTool
from brain.llm_chooser import LLMChooser
from langsmith import traceable
from datetime import datetime
from brain.memory import MemoryType
from brain.experimental.neo4j_graph import Neo4jGraph
from brain.embedder import Embedder
from brain.experimental.memory_parcer import MemoryParser


class PersonaReflection:
    def __init__(self, neo4j_graph=None, llm_chooser=None, groq=None, embedder=None, parser=None):
        print("🔄 Initializing PersonaReflection...")
        self.llm_chooser = LLMChooser() if llm_chooser is None else llm_chooser
        self.groq = GroqTool() if groq is None else groq
        self.graph = Neo4jGraph() if neo4j_graph is None else neo4j_graph
        self.embedder = Embedder() if embedder is None else embedder
        self.parser = MemoryParser(neo4j_graph=self.graph) if parser is None else parser
        print("✅ PersonaReflection initialized successfully")
        
    def _get_unreflected_experiences(self, persona_id: str):
        """Get all experience nodes that don't have a reflection connection and belong to the specified persona."""
        if not self.graph:
            return []
            
        # Query to find experiences without reflection connections from the same persona
        query = """
        MATCH (p:Persona {id: $persona_id})-[:HAS_MEMORY]->(e:Memory)
        WHERE e.type = $experience_type
        AND NOT EXISTS((e)-[:BELONGS_TO]->(:Memory {type: $reflection_type}))
        RETURN e, elementId(e) as node_id
        """
        params = {
            "experience_type": "experience",  # Use string directly since it's the type in the database
            "reflection_type": "reflection",
            "persona_id": persona_id
        }
        
        with self.graph.driver.session() as session:
            result = session.run(query, params)
            experiences = [{"content": record["e"]["content"], "node_id": record["node_id"]} for record in result]
            return experiences
        
    async def _connect_reflection_to_experiences(self, reflection_id: str, experience_ids: list, persona_id: str):
        """Create BELONGS_TO relationships between experiences and the reflection for the same persona."""
        if not self.graph:
            return
            
        with self.graph.driver.session() as session:
            for exp_id in experience_ids:
                query = """
                MATCH (p:Persona {id: $persona_id})-[:HAS_MEMORY]->(e:Memory)
                WHERE elementId(e) = $exp_id AND e.type = 'experience'
                MATCH (p)-[:HAS_MEMORY]->(r:Memory)
                WHERE elementId(r) = $ref_id AND r.type = 'reflection'
                CREATE (e)-[:BELONGS_TO]->(r)
                """
                params = {
                    "exp_id": exp_id, 
                    "ref_id": reflection_id,
                    "persona_id": persona_id
                }
                session.run(query, params)
        
    @traceable
    async def reflect_on_day(self, persona: str) -> dict:
        """
        Generate a reflection on the day's activities and experiences with details of the activities.
        
        Args:
            persona_profile: String containing the persona's profile/characteristics
            
        Returns:
            list: Contains only the plans extracted from the reflection
        """
        print("\n🤔 Starting daily reflection process...")
        
        # Get unreflected experiences
        experiences = self._get_unreflected_experiences(persona['id'])
        print(f"🔍 Found {len(experiences)} unreflected experiences")
        experience_contents = [exp["content"] for exp in experiences]
        experience_ids = [exp["node_id"] for exp in experiences]  # Use the node_id from Neo4j
        
        print(f"📊 Activities to reflect on: {json.dumps(experience_contents, indent=2)}")

        if not experience_contents:
            print("No unreflected experiences found to reflect on")
            return []

        reflection_prompt = f"""
        As {persona['profile']}, reflect on your day and experiences:
        
        Today's Activities and Experiences:
        {experience_contents}
        
        Write a thoughtful reflection that includes:
        1. Your overall feelings about the day
        2. What you learned or accomplished
        3. How the activities aligned with your personality and goals
        4. Any insights or plans for tomorrow
        5. Details of the activity, like what movie you watched, what book you read, what artist you listened to, etc.
        
        Return only a JSON object with:
        - summary: A summary of the day with the details of the activities
        - reflection: Your personal reflection on the day
        - mood: Your overall emotional state
        - plans: Things that you plan to do in the future
        - key_insights: List of main takeaways from the day
        """

        print("\n🤖 Generating reflection using LLM...")
        try:
            print("📝 Sending reflection prompt to OpenAI...")
            response = await self.llm_chooser.generate_text(
                provider="openai",
                messages=[{"role": "user", "content": reflection_prompt}],
                model="gpt-4o",
                temperature=0.8,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            print("✨ Successfully received LLM response")
            print("🔄 Parsing reflection data...")
            
            # Parse the JSON string response
            reflection_data = json.loads(response)
            
            # Store reflection in Neo4j if graph components are available
            reflection_content = reflection_data.get("reflection", "")
            if reflection_content:
                # Generate embedding for the reflection
                reflection_vector = await self.embedder.embed_memory(reflection_content)
                
                # Create memory node in Neo4j
                memory = {
                    "content": reflection_content,
                    "type": MemoryType.REFLECTION.value,
                    "importance": 0.8,
                    "emotional_value": 0.5,
                    "vector": reflection_vector,
                    "timestamp": datetime.now().isoformat()
                }
                
                memory_id = await self.graph.create_memory_node(
                    persona_id=persona['id'],
                    content=memory["content"],
                    memory_type=memory["type"],
                    importance=memory["importance"],
                    emotional_value=memory["emotional_value"],
                    vector=memory["vector"],
                    timestamp=datetime.now()
                )
                print(f"🔗 Created memory node with ID: {memory_id}")

                # Connect reflection to experiences from the same persona
                if experience_ids:
                    await self._connect_reflection_to_experiences(memory_id, experience_ids, persona['id'])
                    print(f"Connected reflection to {len(experience_ids)} experiences")
                
                # Categorize and link topics
                topic_ids = await self.parser.categorize_memory(reflection_content)
                if topic_ids:
                    await self.parser.link_memory_to_topics(memory_id, topic_ids)
                    print("Memory categorized with topics:")
                    for topic_id in topic_ids:
                        topic_path = await self.parser.get_topic_path(topic_id)
                        print(f"  - {' -> '.join(topic_path)}")
                else:
                    print("No topics found for this memory")
            
            # Return only the plans
            return reflection_data.get("plans", [])
            
        except Exception as e:
            print(f"❌ Error generating reflection: {str(e)}")
            return []

