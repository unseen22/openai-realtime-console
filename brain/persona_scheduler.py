import json
from memory import MemoryType
from groq_tool import GroqTool
from perplexity_tool import PerplexityHandler

class PersonaScheduler:
    def __init__(self):
        self.groq = GroqTool()
        self.perplexity = PerplexityHandler(api_key="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")


    def get_plans(self, persona):
        """Evaluate and prioritize plans for the persona based on their profile.
        
        Args:
            persona: The Brain object containing persona information
            
        Returns:
            dict: Prioritized plans and activities for today
        """
        try:
            plans = persona.plans
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get plans: {str(e)}"
            }

        if not plans:
            return {
                "success": False,
                "error": "No plans found for persona"
            }
        
        # Create prompt to evaluate plans
        plans_prompt = f"""Given this persona's profile:
        {persona.persona_profile}

        And these current plans:
        {plans}

        And these recent history:
        {[memory for memory in persona.memories.values() if memory.memory_type == MemoryType.REFLECTION][-10:]}

        Please evaluate which plans are most important to prioritize today. Consider:
        1. Urgency and time-sensitivity
        2. Alignment with persona's goals and values
        3. Current emotional state and energy level
        4. Recent activities and progress

        Return a JSON object with:
        1. Top 3 prioritized plans for today
        2. Brief explanation for each priority
        """

        try:
            # Get plan priorities from LLM
            response = self.groq.generate_text(plans_prompt, temperature=0.1)
            priorities = json.loads(response)
            
            return {
                "success": True,
                "priorities": priorities
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def create_daily_schedule(self, persona):

        # TODO: Add the plans to the prompt
        get_plans = self.get_plans(persona.plans)
        if not get_plans["success"]:
            get_plans = []
        
        groq_prompt = f"""
        Generate a daily schedule for a persona, take into account the persona's profile and recent history and the plans to do today.
        Persona Profile: {persona.persona_profile}
        Recent History: {[memory for memory in persona.memories.values() if memory.memory_type == MemoryType.REFLECTION][-10:]}
        Plans to do: {get_plans}
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

        try:
            response = self.groq.chat_completion(
                messages=[{"role": "user", "content": groq_prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )["choices"][0]["message"]["content"]
            #print(response)
            json_response = json.loads(response)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {str(e)}")
            return {"error": "Invalid JSON response from LLM"}
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return {"error": "Failed to generate schedule"}

        
        return json_response

    def persona_scheduler(self, persona):
        """
        Generate a daily schedule and activities for a persona using LLM.
        
        Args:
            persona: Persona object containing profile information
            
        Returns:
            dict: JSON object containing schedule and daily activities
        """
           





        try:
            # Generate schedule using persona profile
            schedule = self.create_daily_schedule(persona)
            
            # Modernize the activities
            schedule = self.modernize_activities(schedule, persona)
            
            return {
                "success": True,
                "schedule": schedule
            }
            
        except Exception as e:
            print(f"Error generating schedule: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_schedule_times(self, schedule):
        # Check and adjust schedule times and activities
        return schedule

    def modernize_activities(self, schedule, persona):
        # Analyze each activity and find modern alternatives
        if "schedule" in schedule and isinstance(schedule["schedule"], list):
            # Convert schedule to string representation
            schedule_str = "\n".join([f"{task['time']}: {task['activity']}" for task in schedule["schedule"]])
            
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
                modern_suggestions = self.perplexity.generate_completion(
                    messages=[{"role": "user", "content": modern_activity_prompt}],
                    model="llama-3.1-sonar-huge-128k-online",
                    temperature=0.7
                ).split("\n")
                for task, suggestion in zip(schedule["schedule"], modern_suggestions):
                    if suggestion.strip():
                        task["activity"] = suggestion.strip()
            except Exception as e:
                print(f"Error modernizing activities: {str(e)}")
                # Keep original activities if modernization fails
                pass

            print(f"______++++ this is the suggestions: {modern_suggestions} ++++++______")
            # Update schedule with modern suggestions
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
                schedule = self.groq.chat_completion(
                    messages=[{"role": "user", "content": groq_prompt}],
                    model="llama-3.3-70b-versatile", 
                    temperature=0.1,
                    max_tokens=1024,
                    response_format={"type": "json_object"}
                )["choices"][0]["message"]["content"]
                
                # Parse response back to dict
                schedule = json.loads(schedule)
                
            except Exception as e:
                print(f"Error updating schedule with modern activities: {str(e)}")
                # Keep original schedule if update fails
                pass

        print(f"📅 THIS IS THE NEW SCHEDULE: {schedule}")
        return schedule

