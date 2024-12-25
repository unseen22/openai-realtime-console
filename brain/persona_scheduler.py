import json
from memory import MemoryType
from groq_tool import GroqTool
from perplexity_tool import PerplexityHandler
from llm_chooser import LLMChooser
from datetime import datetime

class PersonaScheduler:
    def __init__(self):
        print("🔧 Initializing PersonaScheduler...")
        self.groq = GroqTool()
        self.perplexity = PerplexityHandler(api_key="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")
        self.llm_chooser = LLMChooser()
        print("✅ PersonaScheduler initialized successfully")


    def get_plans(self, persona):
        """Evaluate and prioritize plans for the persona based on their profile.
        
        Args:
            persona: The Brain object containing persona information
            
        Returns:
            dict: Prioritized plans and activities for today
        """
        print("\n🔍 GETTING PLANS FOR PERSONA...")
        try:
            plans = persona.plans
            print(f"📋 Retrieved {len(plans)} plans")
        except Exception as e:
            print(f"❌ Error getting plans: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get plans: {str(e)}"
            }

        if not plans:
            print("⚠️ No plans found for persona")
            return {
                "success": False,
                "error": "No plans found for persona"
            }
        
        print("\n=== PERSONA DETAILS ===")
        print(f"👤 Profile: {persona.persona_profile}")
        print(f"📝 Plans: {json.dumps(plans, indent=2)}")
        print(f"📜 Recent history: {[memory.content for memory in persona.memories.values() if memory.memory_type == MemoryType.REFLECTION][-3:]}")
        
        plans_prompt = f"""Given this persona's profile:
        {persona.persona_profile}
        Take into account the goals of this persona:
        {persona.goals}
        And these current plans:
        {plans}
        This is the current date:
        {datetime.now().strftime("%Y-%m-%d")}
        And these recent history:
        {[{"content": memory.content, "timestamp": memory.timestamp} for memory in persona.memories.values() if memory.memory_type == MemoryType.REFLECTION][-3:]}

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
            response = self.llm_chooser.generate_text(
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

    def create_daily_schedule(self, persona):
        print("\n📅 CREATING DAILY SCHEDULE...")
        plans_result = self.get_plans(persona)
        plans_to_use = plans_result.get("plans", []) if plans_result.get("success", False) else []
        print(f"📋 Using plans: {json.dumps(plans_to_use, indent=2)}")
        
        groq_prompt = f"""
        Generate a daily schedule for a persona, take into account the persona's profile and recent history and the plans to do today.
        Persona Profile: {persona.persona_profile}
        Take into account the goals of this persona: {persona.goals}
        These are the recent exeriences: {[{"content": memory.content, "timestamp": memory.timestamp} for memory in persona.memories.values() if memory.memory_type == MemoryType.REFLECTION][-10:]}

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
            response = self.llm_chooser.generate_text(
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
            return json_response
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {str(e)}")
            return {"error": "Invalid JSON response from LLM"}
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return {"error": "Failed to generate schedule"}

    def persona_scheduler(self, persona):
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
            schedule = self.create_daily_schedule(persona)
            
            print("🔄 Modernizing activities...")
            schedule = self.modernize_activities(schedule, persona)
            
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

    def modernize_activities(self, schedule, persona):
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
            
            try:
                print("🤖 Getting modern suggestions from Perplexity...")
                modern_suggestions = self.perplexity.generate_completion(
                    messages=[{"role": "user", "content": modern_activity_prompt}],
                    model="llama-3.1-sonar-huge-128k-online",
                    temperature=0.7
                ).split("\n")
                print(f"✨ Modern suggestions:\n{json.dumps(modern_suggestions, indent=2)}")
                
                for task, suggestion in zip(schedule["schedule"], modern_suggestions):
                    if suggestion.strip():
                        task["activity"] = suggestion.strip()
                        print(f"📝 Updated activity: {task['time']} -> {suggestion.strip()}")
            except Exception as e:
                print(f"⚠️ Error getting modern suggestions: {str(e)}")
                print("👉 Keeping original activities")
                pass

            print("\n🔄 Finalizing schedule with modern activities...")
            groq_prompt = f"""
            Given this schedule with modernized activities:
            {schedule_str}
            
            And this persona profile:
            {persona.persona_profile}

            Change the shedule according to this feedback:
            {modern_suggestions}
            
            Return only a JSON object with the same schedule structure but with the modernized activities.
            The schedule should have:
            - success: true
            - schedule: array of tasks with time and activity fields
            """
            
            try:
                print("🤖 Getting final schedule from LLM...")
                schedule = self.llm_chooser.generate_text(
                    provider="openai",
                    messages=[{"role": "user", "content": groq_prompt}],
                    model="gpt-4o", 
                    temperature=0.1,
                    max_tokens=1024,
                    response_format={"type": "json_object"}
                )
                
                schedule = json.loads(schedule)
                print("✅ Successfully updated schedule with modern activities")
                
            except Exception as e:
                print(f"❌ Error updating schedule: {str(e)}")
                print("👉 Keeping previous schedule version")
                pass

        print(f"\n📅 FINAL SCHEDULE:\n{json.dumps(schedule, indent=2)}")
        return schedule

