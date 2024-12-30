import groq
from brain.memory import MemoryType
from brain.persona_scheduler import PersonaScheduler
import brain.groq_tool as groq_tool
import json
import time
import brain.perplexity_tool as pt
from datetime import datetime
from brain.llm_chooser import LLMChooser
from brain.open_ai_tool import OpenAITool
from brain.story_engine.roller import StoryRoller
from langsmith import traceable
from brain.experimental.neo4j_graph import Neo4jGraph
from brain.experimental.memory_parcer import MemoryParser
from brain.embedder import Embedder
from typing import Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

class PersonaExecuteSchedule:
    def __init__(self, neo4j_graph: Optional[Neo4jGraph] = None):
        print("🔄 Initializing PersonaExecuteSchedule...")
        self.groq = groq_tool.GroqTool()
        self.openai_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.llm_chooser = LLMChooser()
        self.current_task_index = 0  # Track current task
        
        # Use provided Neo4j connection or create new one
        self.graph = neo4j_graph if neo4j_graph else Neo4jGraph(
            uri="neo4j+s://a9277d8e.databases.neo4j.io",
            username="neo4j",
            password="tKSk2m5MwQr9w25IbSnB07KccMmTfjFtjcCsQIraczk"
        )
        self.embedder = Embedder()
        self.parser = MemoryParser(neo4j_graph=self.graph)
        self.persona_scheduler = PersonaScheduler()
        print("✅ PersonaExecuteSchedule initialized successfully")
        
    def __del__(self):
        """Cleanup Neo4j connection when the object is destroyed"""
        try:
            # Only close if we created the connection
            if hasattr(self, 'graph') and not hasattr(self, '_graph_provided'):
                self.graph.close()
                print("✅ Neo4j connection closed")
        except Exception as e:
            print(f"❌ Error closing Neo4j connection: {str(e)}")
        
    @traceable
    async def get_schedule(self, persona):
        """
        Process and execute tasks from the provided schedule.
        
        Args:
            persona (dict): Persona profile and characteristics
            
        Returns:
            tuple: (schedule_results, updated_persona)
        """
        print("\n📅 Starting schedule processing with tracing...")
        try:
            # Get schedule from persona
            print("🎯 Processing schedule...")
            schedule = persona["schedule"]
            
            # Process each task in the schedule
            print("\n⏳ Processing schedule tasks...")
            task_results = {}
            updated_persona = persona
            
            if schedule and len(schedule) > 0:
                # Take items 2-4 from schedule
                schedule_items = schedule
                print(f"✅ Schedule FOUND EXECUTING")                    
                
            else:
                print("⚠️ No schedule found creating a new one from persona")
                schedule_items = await self.persona_scheduler.create_full_schedule_and_save(persona['id'])

            for i, schedule_item in enumerate([schedule_items[0]]):
                    self.current_task_index = i
                    # Parse time and activity from schedule string (format: "time: activity")
                    time_slot, activity = schedule_item.split(": ", 1)
                    print(f"\n🎯 Executing task for {time_slot}: {activity}")
                    #Pass complete task info including time_slot
                    result, updated_persona = await self._execute_task(updated_persona, {
                       "time": time_slot,
                       "activity": activity,
                       "task_number": i,
                       "total_tasks": len(schedule_items)
                    })
                    
                    #Mark task as completed
                    task_results[time_slot] = {
                       "activity": activity,
                       "result": result,
                       "completed": True,
                       "completion_time": datetime.now().isoformat()
                    }

                    print(f"✅ Completed task {i+1}/{len(schedule_items)}: {activity}")
                    await self.persona_scheduler.task_manager(persona, activity)

            
            print("\n✅ Schedule processing completed successfully")
            # TODO: Have you Completed any plans? If yes, delete it from the plans list, or modify it.
            return {
                "success": True,
                "results": task_results,
                "completed_tasks": len(task_results),
                "total_tasks": len(schedule_items)
            }, updated_persona
            
        except Exception as e:
            print(f"❌ Error executing schedule: {str(e)}")
            return {
                "success": False, 
                "error": str(e),
                "completed_tasks": len(task_results) if 'task_results' in locals() else 0
            }, persona

    @traceable
    async def _execute_task(self, persona, task):
        """
        Execute a single task from the schedule.
        
        Args:
            persona: Brain object containing persona information
            task (dict): Task to execute
            
        Returns:
            tuple: (task_result, updated_persona)
        """
        print("\n📋 Executing task with tracing: {task}")
        print("🔍 Analyzing task requirements...")
        task_actions = await self.judge_task(persona, task)
        print(f"📊 Task analysis results:\n{json.dumps(task_actions, indent=2)}")
        
        print("🎮 Choosing action strategy...")
        action_result = await self.choose_action(task_actions, task, persona)

        print("📝 Generating experience diary entry...")
        experience_prompt = f"""
        You are {persona['profile']} and you are going to write a diary entry about completing this task: {task} with the following results: {action_result}.
        Write the diary entry in a way that is consistent with your personality and characteristics, describing what actually happened.
        Return only a JSON object with:
        - diary_entry: A first-person past-tense account of completing the task, including your thoughts, feelings and reactions and details of the action.
        - timestamp: The time the task was completed
        - mood: Your emotional state after completing this task
        - status: Your current status after this experience
        """

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": experience_prompt}],
                temperature=0.5,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            diary_entry_done = response.choices[0].message.content
            if isinstance(diary_entry_done, str):
                diary_entry_done = json.loads(diary_entry_done)
                
            print(f"📔 Generated diary entry:\n{json.dumps(diary_entry_done, indent=2)}")
            
            # Store memory in Neo4j
            diary_entry = diary_entry_done.get("diary_entry", "")
            if diary_entry:
                # Generate embedding for the diary entry
                diary_vector = await self.embedder.embed_memory(diary_entry)
                print(f"🔍 Mood return mood: {diary_entry_done.get("mood")}")
                # Get mood and emotional value from the response
                current_mood = diary_entry_done.get("mood", "neutral")
               
                # Map mood to emotional value more accurately
                emotional_mapping = {
                    "happy": 0.8,
                    "excited": 0.9,
                    "content": 0.6,
                    "neutral": 0.5,
                    "tired": 0.4,
                    "sad": 0.3,
                    "angry": 0.2,
                    "frustrated": 0.3
                }
                emotional_value = emotional_mapping.get(
                    current_mood.lower(),
                    0.5  # Default to neutral if mood not found
                )
                
                # Create memory node in Neo4j
                memory_id = await self.graph.create_memory_node(
                    persona_id=persona['id'],
                    content=diary_entry,
                    memory_type=MemoryType.EXPERIENCE.value,  # Convert enum to string
                    importance=0.7,  # Default importance for experiences
                    emotional_value=emotional_value,
                    vector=diary_vector,
                    timestamp=datetime.now(),
                    mood=current_mood  # Store the exact mood string
                )
                
                # Categorize and link topics
                topic_ids = await self.parser.categorize_memory(diary_entry)


                if topic_ids:
                    await self.parser.link_memory_to_topics(memory_id, topic_ids)
                    print("Memory categorized with topics:")
                    for topic_id in topic_ids:
                        topic_path = await self.parser.get_topic_path(topic_id)
                        print(f"  - {' -> '.join(topic_path)}")
                else:
                    print("No topics found for this memory")
                
                # Update persona state
    
                self.graph.update_persona_state(
                    persona_id=persona['id'], 
                    mood=diary_entry_done.get("mood", "neutral"), 
                    status=diary_entry_done.get("status", "normal"),
                   )
          
            # Return a properly structured result
            task_result = {
                "diary_entry": diary_entry_done.get("diary_entry", ""),
                "timestamp": diary_entry_done.get("timestamp", datetime.now().isoformat()),
                "mood": diary_entry_done.get("mood", "neutral"),
                "status": diary_entry_done.get("status", "normal"),
                "action_details": action_result
            }
            
            return task_result, persona
            
        except Exception as e:
            print(f"❌ Error in _execute_task: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "mood": "neutral",
                "status": "error occurred"
            }, persona

    @traceable
    async def choose_action(self, task_actions, task, persona):
        """
        Analyze each required action and determine if it needs knowledge gathering or simulation.
        
        Args:
            task_actions (dict): Task type and required actions
            task (dict): Task details
            persona: The persona object
            
        Returns:
            dict: Combined results of executing all actions
        """
        print("\n🤔 Analyzing each required action with tracing...")
        all_results = []
        current_mood = persona['mood']
        current_status = persona['status']
        memory = self.graph.get_persona_memories(persona['id'], limit=1)
        print(f"🔍 Memory: {memory}")
        
        try:
            action = task_actions.get("required_actions", [])
            for action in action:
                groq_prompt = f"""
                Analyze this specific action and determine if we need to:
                1. Gather knowledge (for tasks requiring up-to-date information, or tasks that are not concrete, or need realtime knowledge to simulate, need a decision to make, choosing films, music, activities, etc)
                2. Simulate action (for tasks that don't require external knowledge, or tasks that are concrete and don't need realtime knowledge to simulate, take a walk, have a chat, hit the gym.)

                Required action: {action}

                Return only a JSON object with:
                - tool: Either "gather_knowledge" or "simulate_action"
                - reason: Brief explanation of the choice
                """

                try:
                    print(f"🔄 Getting action choice for: {action}")
                    llm_response = await self.llm_chooser.generate_text(
                        provider="openai",
                        messages=[{"role": "user", "content": groq_prompt}],
                        model="gpt-4o",
                        temperature=0.7,
                        max_tokens=1024,
                        response_format={"type": "json_object"}
                    )
                    
                    # Ensure response is a dictionary
                    action_choice = llm_response if isinstance(llm_response, dict) else json.loads(llm_response)
                    print(f"🎯 Chosen strategy for {action}:\n{json.dumps(action_choice, indent=2)}")
                    
                    # Execute the chosen action for this step
                    if action_choice.get("tool") == "gather_knowledge":
                        print(f"🔍 Gathering knowledge for: {action}")
                        result_knowladge = await self._gather_knowledge(action, task)
                        result = await self._simulate_action(action, persona=persona, current_mood=current_mood, current_status=current_status, memory=memory, result_knowladge=result_knowladge)
                    else:
                        print(f"🎮 Simulating action for: {action}")
                        roller = StoryRoller(persona)
                        story_engine_result = await roller.roll_for_outcome(action)
                        print(f"🎲 Roll outcome: {story_engine_result}")
                        if not isinstance(story_engine_result, str):
                            print(f"❌ Invalid roll result type: {type(story_engine_result)}")
                            story_engine_result = "failure"  # Default to failure if invalid result
                        result = await self._simulate_action(action, persona, current_mood, current_status, story_engine_result, memory)
                        current_mood = result.get("mood", current_mood)
                        current_status = result.get("status", current_status)
                    
                    all_results.append({
                        "action": action,
                        "strategy": action_choice.get("tool"),
                        "result": result
                    })
                    
                except Exception as e:
                    print(f"❌ Error processing action '{action}': {str(e)}")
                    all_results.append({
                        "action": action,
                        "error": str(e)
                    })

            # Return properly structured results
            return {
                "success": True,
                "actions_completed": len(all_results),
                "detailed_results": all_results,
                "final_mood": current_mood,
                "final_status": current_status
            }
            
        except Exception as e:
            print(f"❌ Error in choose_action: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "actions_completed": len(all_results) if all_results else 0
            }

    @traceable
    async def _gather_knowledge(self, action, task):
        """
        Gather knowledge for the task.
        
        Args:
            task_analysis (dict): Analysis of task requirements
            task (dict): Task details
            
        Returns:
            str: Retrieved information from Perplexity
        """
        print("\n🔍 Starting knowledge gathering with tracing...")
        groq_prompt = f"""
        Create a search query to gather information needed for completing this actions: {action} to complete this task {task}.
        Find up to date information on the topic, top 10 results and trending topics. 
        Always add todays date in the query which is {datetime.now().strftime("%Y-%m-%d")}
        Return only a JSON object with:
        - query: A focused search query that will return relevant, up-to-date information
        """

        try:
            print("🤖 Generating search query...")
            llm_response = await self.llm_chooser.generate_text(
                provider="openai",
                messages=[{"role": "user", "content": groq_prompt}],
                model="gpt-4o",
                temperature=0.5,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            query_data = json.loads(llm_response)
            print(f"🔎 Generated search query:\n{json.dumps(query_data, indent=2)}")
            
            print("🌐 Fetching information from Perplexity...")
            perplexity_instance = pt.PerplexityHandler("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")
            perplexity_response = await perplexity_instance.generate_completion(
                messages=[{"role": "user", "content": query_data["query"]}],
                model="llama-3.1-sonar-large-128k-online",
                temperature=0.5
            )
            
            # Ensure we have a proper structure for the knowledge
            knowledge_data = {
                "query": query_data["query"],
                "information": perplexity_response
            }
            print(f"📚 Retrieved information:\n{json.dumps(knowledge_data, indent=2)}")

            validation_result = await self.validate_knowledge(task, knowledge_data)
            print(f"📊 Validation result:\n{json.dumps(validation_result, indent=2)}")
            
            if not validation_result["success"]:
                print(f"⚠️ Missing details: {validation_result['missing']}")
                print("🔄 Fetching additional information...")
                additional_response = await perplexity_instance.generate_completion(
                    messages=[{"role": "user", "content": validation_result["missing"]}],
                    model="llama-3.1-sonar-large-128k-online",
                    temperature=0.5
                )
                # Append additional information
                knowledge_data["additional_information"] = additional_response
                print(f"📚 Retrieved additional information:\n{json.dumps(additional_response, indent=2)}")
            
            # Create structured response
            structured_response = {
                "action": action,
                "result": knowledge_data
            }

            return structured_response
            
        except Exception as e:
            print(f"❌ Error gathering knowledge: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @traceable
    async def validate_knowledge(self, task, knowledge):
        """
        Validate the knowledge for the task by checking if there are sufficient concrete details.
        
        Args:
            task: The task to validate knowledge for
            knowledge: The knowledge to validate
            
        Returns:
            dict: Validation result with success status and any missing details
        """
        print("\n🔍 Validating knowledge with tracing...")
        print(f"🔍 Knowledge:\n{json.dumps(knowledge, indent=2)}")
        print(f"🔍 FOR Task:\n{json.dumps(task, indent=2)}")
        
        print("📝 Creating validation prompt...")
        validation_prompt = f"""
        Check if this information contains enough concrete details to complete the task and its simulation (concrete details include things like songs for creating a playlist, movies for creating a watchlist, etc), if not return the query to find more details:
        
        Task: {task}
        Query Used: {knowledge.get('query', 'No query available')}
        Information: {knowledge.get('information', 'No information available')}
        
        Return only a JSON object with:
        - has_details: true/false indicating if there are sufficient concrete details
        - missing: specific query to find more details that are still needed (if any)
        """
        
        try:
            print("🤖 Sending validation request to LLM...")
            validation = await self.llm_chooser.generate_text(
                provider="groq",
                messages=[{"role": "user", "content": validation_prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            print(f"✨ Raw LLM validation response: {validation}")
            
            try:
                print("🔍 Parsing validation result...")
                validation_result = json.loads(validation)
                print(f"✅ Successfully parsed validation: {validation_result}")
                return {
                    "success": validation_result["has_details"],
                    "missing": validation_result.get("missing", "")
                }
            except json.JSONDecodeError as je:
                print(f"❌ Error parsing validation response: {str(je)}")
                print(f"🔴 Raw response: {validation}")
                return {
                    "success": False,
                    "error": "Invalid validation response",
                    "missing": ""
                }
            
        except Exception as e:
            print(f"❌ Error during validation: {str(e)}")
            print("🔴 Validation failed completely")
            return {
                "success": False,
                "error": str(e),
                "missing": ""
            }

    @traceable
    async def _simulate_action(self, 
                         action, 
                         persona, 
                         current_mood, 
                         current_status, 
                         story_engine_result = [],  # Default to empty list if not provided
                         memory = [],
                         result_knowladge = []):
        """
        Simulate the action for the task.
        
        Args:
            task_analysis (dict): Analysis of task requirements
            
        Returns:
            str: Description of simulated action
        """

        print(f"🔍 INSIDE SIMULATE ACTION with tracing")
        # Safely get memory content
        
        
        groq_prompt = f"""
        You are simulating an action for a persona with these characteristics:
        - Profile: {persona['profile']}
        - Current mood: {current_mood} 
        - Current status: {current_status}
        - This is the last thing you were doing: {memory[0]['memory']['content']}
        - This is the extra information you looked up for this action: {result_knowladge}
        
        The action to simulate is: {action} with the result of the action: {story_engine_result}.

        Return only a JSON object with:
        - action: The action that was simulated
        - result: A detailed description of what happened
        - mood: The persona's mood after completing the action
        - status: The persona's status after completing the action
        """

        print(f"🖕 INSIDE SIMULATE ACTION THE PROMPT IS: {groq_prompt[100:]}")

        try:
            print("🤖 Simulating action with LLM...")
            llm_response = await self.llm_chooser.generate_text(
                provider="openai",
                messages=[{"role": "user", "content": groq_prompt}],
                model="gpt-4o",
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            simulation_result = json.loads(llm_response)
            print(f"✅ Successfully simulated action: {json.dumps(simulation_result, indent=2)}")
            return simulation_result
            
        except Exception as e:
            print(f"❌ Error simulating action: {str(e)}")
            return {
                "action": str(action),
                "result": "Failed to simulate action",
                "mood": current_mood,
                "status": current_status
            }
      

    @traceable
    async def judge_task(self, persona, task):
        """
        Judge the task type based on the persona and task and determine execution strategy.
        
        Args:
            persona: Brain object containing persona information
            task (dict): Task details including activity and time
            
        Returns:
            dict: Task execution plan with type and required actions
        """
        print("\n⚖️ Analyzing task requirements with tracing...")
        # Use LLM to analyze and determine task type
        groq_prompt = f"""
        Given this activity and persona, determine the specific steps needed to complete a simulation of the task in the persona's unique style.

        Activity: {task}
        Persona Profile: {persona['profile']}

        Return only a JSON object with:
        - required_actions: Array of specific action steps for how this persona would complete the task, no more than 3 actions

        Example for "Answer Reddit post about Christmas gifts":
        {{
            "required_actions": [
                "find_reddit_post",
                "read_post_content",
                "generate_sarcastic_response"
            ]
        }}
        """
        
        try:
            print("🤖 Getting task analysis from LLM...")
            llm_response = await self.llm_chooser.generate_text(
                provider="openai",
                messages=[{"role": "user", "content": groq_prompt}],
                model="gpt-4o", 
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            task_analysis = json.loads(llm_response)
            print(f"📊 Task analysis results:\n{json.dumps(task_analysis, indent=2)}")
            
            return {
                "required_actions": task_analysis["required_actions"]
            }
    
            
        except Exception as e:
            print(f"❌ Error analyzing task with LLM: {str(e)}")
            return {
                "type": "default",
                "activity": task, 
                "persona": persona['name'],
                "required_actions": ["process_activity"]
            }
