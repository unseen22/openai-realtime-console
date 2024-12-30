import json
from brain.groq_tool import GroqTool
from brain.perplexity_tool import PerplexityHandler
from brain.llm_chooser import LLMChooser
from datetime import datetime
from langsmith import traceable
from brain.experimental.neo4j_graph import Neo4jGraph
from brain.persona_reflection import PersonaReflection
from brain.experimental.memory_parcer import MemoryParser
from brain.embedder import Embedder

class PersonaScheduler:
    def __init__(self):
        print("🔧 Initializing PersonaScheduler...")
        self.groq = GroqTool()
        self.perplexity = PerplexityHandler(api_key="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")
        self.llm_chooser = LLMChooser()
        self.graph = Neo4jGraph()
        self.embedder = Embedder()
        self.parser = MemoryParser()
        self.reflection = PersonaReflection(neo4j_graph=self.graph, embedder=self.embedder, parser=self.parser)

    @traceable
    async def get_plans(self, persona, memory):
        """Evaluate and prioritize plans for the persona based on their profile.
        
        Args:
            persona: The Brain object containing persona information
            
        Returns:
            dict: Prioritized plans and activities for today
        """
        print("\n🔍 GETTING PLANS FOR PERSONA...")
        try:
            plans = persona['plans']
            if not plans:
                print("⚠️ No plans found for persona")
                return {
                    "success": False,
                    "error": "No plans found for persona"
                }
            print(f"📋 Retrieved {len(plans)} plans")
        except Exception as e:
            print(f"❌ Error getting plans: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get plans: {str(e)}"
            }
        
        print("\n=== PERSONA DETAILS ===")
        print(f"👤 Profile: {persona['profile']}")
        print(f"📝 Plans: {json.dumps(plans, indent=2)}")
        print(f"📜 Recent history: {memory[0]['memory']['content'] + "\n" + memory[1]['memory']['content'] + "\n" + memory[2]['memory']['content']}")
        
        plans_prompt = f"""Given this persona's profile:
        {persona['profile']}
        Take into account the goals of this persona:
        {persona['goals']}
        And these current plans:
        {plans}
        This is the current date:
        {datetime.now().strftime("%Y-%m-%d")}
        And these recent history:
        {memory[0]['memory']['content'] + "\n" + memory[1]['memory']['content'] + "\n" + memory[2]['memory']['content']}

        Please evaluate which plans are most important to prioritize today. Consider:
        1. Urgency and time-sensitivity
        2. Alignment with persona's goals and values
        3. Current emotional state and energy level
        4. Recent activities and progress

        Return a JSON object with:
        1. Top 3 prioritized plans for today
        2. Brief explanation for each priority
        """

        print(f"🤖 Requesting plan priorities from LLM...THIS IS THE PROMPT: {plans_prompt}")
        try:
            response = await self.llm_chooser.generate_text(
                provider="openai",
                prompt=plans_prompt,
                model="gpt-4o",
                temperature=0.1,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            print(f"✨ LLM Response: {json.dumps(response, indent=2)}")
            
            json_response = json.loads(response)
            print("✅ Successfully parsed LLM response")

            return {
                "success": True,
                "plans": json_response
            }
            
        except Exception as e:
            print(f"❌ Error processing LLM response: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get plan priorities: {str(e)}"
            }

    @traceable
    async def create_daily_schedule(self, persona, memories):
        print("\n📅 CREATING DAILY SCHEDULE...")
        plans_result = await self.get_plans(persona, memories)
        plans_to_use = plans_result.get("plans", []) if plans_result.get("success", False) else []
        print(f"📋 Using plans: {json.dumps(plans_to_use, indent=2)}")
        
        groq_prompt = f"""
        Generate a daily schedule for a persona, take into account the persona's profile and recent history and the plans to do today.
        Persona Profile: {persona['profile']}
        Take into account the goals of this persona: {persona['goals']}
        These are the recent exeriences: {memories}

        Plans to do: {plans_to_use}
      
        Today is: {datetime.now().strftime("%Y-%m-%d")}
        Always add to schedule only 1 activity per time slot.

        Return only the JSON object with the schedule.
        Example:
        {{
            "schedule": [
                {{"time": "06:00", "activity": "Wake up"}},
                {{"time": "07:00", "activity": "Exercise"}},
                {{"time": "08:00", "activity": "Breakfast"}},
                {{"time": "09:00", "activity": "Work"}},
                {{"time": "10:00", "activity": "Lunch"}},
                {{"time": "11:00", "activity": "Work"}},
            ]
        }}
        """
        print("\n🤖 Requesting schedule from LLM...")
        try:
            response = await self.llm_chooser.generate_text(
                provider="openai",
                prompt=groq_prompt,
                model="gpt-4o",
                temperature=0.1,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            print(f"✨ LLM Response: {json.dumps(response, indent=2)}")
            
            json_response = json.loads(response)
            print("✅ Successfully parsed schedule")
            return json_response, plans_result
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {str(e)}")
            return {"error": "Invalid JSON response from LLM"}
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return {"error": "Failed to generate schedule"}

    async def persona_scheduler(self, persona, memories):
        """
        Generate a daily schedule and activities for a persona using LLM.
        
        Args:
            persona: Persona object containing profile information
            
        Returns:
            dict: JSON object containing schedule and daily activities
        """
        print("\n🎯 GENERATING PERSONA SCHEDULE...")
        try:
            print("📅 Creating base schedule...")
            schedule, plans_result = await self.create_daily_schedule(persona, memories)
            
            print("🔄 Modernizing activities...")
            schedule = await self.modernize_activities(schedule, persona, plans_result, memories)
            
            print("✅ Schedule generation complete")
            return {
                "success": True,
                "schedule": schedule
            }
            
        except Exception as e:
            print(f"❌ Error in persona_scheduler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_schedule_times(self, schedule):
        print("\n⏰ Validating schedule times...")
        return schedule

    @traceable
    async def modernize_activities(self, schedule, persona, plans_result, memories):
        print("\n🔄 MODERNIZING ACTIVITIES...")
        if isinstance(schedule, dict) and "error" in schedule:
            print("⚠️ Schedule contains error - skipping modernization")
            return schedule
            
        if "schedule" in schedule and isinstance(schedule["schedule"], list):
            schedule_str = "\n".join([f"{task['time']}: {task['activity']}" for task in schedule["schedule"]])
            print(f"📋 Current schedule:\n{schedule_str}")
            
            modern_activity_prompt = f"""
            Given this full schedule:
            {schedule_str}
            
            For each activity, suggest a modern alternative that:
            1. Matches the persona's interests and personality
            2. Is currently popular/trending
            3. Maintains the same general purpose/goal
            4. It must be concrete like suggesting a specific artist or a specific book
            
            Return a list of only the suggested activity names in order, one per line.
            """
            
            modern_suggestions = []
            try:
                print("🤖 Getting modern suggestions from Perplexity...")
                response = self.perplexity.generate_completion(
                    messages=[{"role": "user", "content": modern_activity_prompt}],
                    model="llama-3.1-sonar-huge-128k-online",
                    temperature=0.7
                )
                if isinstance(response, str):
                    modern_suggestions = response.split("\n")
                    print(f"✨ Modern suggestions:\n{json.dumps(modern_suggestions, indent=2)}")
                    
                    for task, suggestion in zip(schedule["schedule"], modern_suggestions):
                        if suggestion.strip():
                            task["activity"] = suggestion.strip()
                            print(f"📝 Updated activity: {task['time']} -> {suggestion.strip()}")

                    print("\n🔄 Finalizing schedule with modern activities...")
                    groq_prompt = f"""
                    Given this schedule with modernized activities:
                    {schedule_str}
                    
                    And this persona profile:
                    {persona['profile']}

                    And this persona earlier activities:
                    {memories}
                    Change the shedule according to this feedback:
                    {modern_suggestions}
                    
                    Also remember the persona's general goals:
                    {persona['goals']}

                    And the plans to do today:
                    {plans_result}


                    Return only a JSON object with the same schedule structure but with the modernized activities.
                    The schedule should have:
                    - success: true
                    - schedule: array of tasks with time and activity fields
                    """
                    
                    try:
                        print("��� Getting final schedule from LLM...")
                        response = await self.llm_chooser.generate_text(
                            provider="openai",
                            messages=[{"role": "user", "content": groq_prompt}],
                            model="gpt-4o", 
                            temperature=0.1,
                            max_tokens=1024,
                            response_format={"type": "json_object"}
                        )
                        
                        schedule = json.loads(response)
                        print("✅ Successfully updated schedule with modern activities")
                        
                    except Exception as e:
                        print(f"❌ Error updating schedule: {str(e)}")
                        print("👉 Keeping previous schedule version")
                else:
                    print("⚠️ Invalid response format from Perplexity")
                    print("👉 Keeping original activities")

            except Exception as e:
                print(f"⚠️ Error getting modern suggestions: {str(e)}")
                print("👉 Keeping original activities")

            print(f"\n📅 FINAL SCHEDULE:\n{json.dumps(schedule, indent=2)}")
            return schedule
        
    async def create_full_schedule_and_save(self, persona_id):
        persona_node = self.graph.get_persona_state(persona_id=persona_id)
        memories = self.graph.get_persona_memories(persona_id=persona_id, limit=3)

        schedule_result = await self.persona_scheduler(persona_node, memories)
            
        # Extract the actual schedule array if successful
        schedule_data = schedule_result.get("schedule", {}).get("schedule", []) if schedule_result.get("success") else []
        
        # Convert schedule items to strings in the format "time: activity"
        formatted_schedule = [f"{item['time']}: {item['activity']}" for item in schedule_data]
        
        self.graph.update_persona_state(persona_id=persona_id, schedule=formatted_schedule)

        return formatted_schedule
    

    async def task_manager(self, persona, task_id):
        # Get current schedule from persona state
        print(f"🔍 Task manager called for persona_id: {persona['id']} and task_id: {task_id}")
        persona_node = self.graph.get_persona_state(persona_id=persona['id'])
        current_schedule = persona_node.get('schedule', [])
        
        # Remove the completed task
        updated_schedule = [
        task for task in current_schedule 
        if not task.split(': ', 1)[1] == task_id
    ]
        
        # Update persona state with new schedule
        self.graph.update_persona_state(persona_id=persona['id'], schedule=updated_schedule)
        

        print(f"🔍 Updated schedule after task completion: {updated_schedule}")
        # If schedule is empty, create new full schedule
        if not updated_schedule:
            await self.reflection.reflect_on_day(persona)
            await self.create_full_schedule_and_save(persona['id'])
            
        return updated_schedule


