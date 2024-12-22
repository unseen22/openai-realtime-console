import json
from groq_tool import GroqTool
from perplexity_tool import PerplexityHandler

class PersonaScheduler:
    def __init__(self):
        self.groq = GroqTool()
        self.perplexity = PerplexityHandler(api_key="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")

    def create_daily_schedule(self, persona_profile, recent_history):
        groq_prompt = f"""
        Generate a daily schedule for a persona, take into account the persona's profile and recent history.
        Persona Profile: {persona_profile}
        Recent History: {recent_history}


        Return only the JSON object with the schedule.
        Example:
        {{
            "schedule": [
                {{"time": "06:00", "activity": "Wake up and meditate"}},
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
                model="llama-3.3-70b-specdec",
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
        self.persona = persona
        





        try:
            # Generate schedule using persona profile
            schedule_raw = self.create_daily_schedule(
                persona_profile=persona,
                recent_history={}
            )
            
            # Check and adjust schedule times and activities
            #schedule = self.validate_schedule_times(schedule_raw)
            schedule = self.modernize_activities(schedule_raw)
            
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

    def modernize_activities(self, schedule):
        # Analyze each activity and find modern alternatives
        if "schedule" in schedule and isinstance(schedule["schedule"], list):
            # Convert schedule to string representation
            schedule_str = "\n".join([f"{task['time']}: {task['activity']}" for task in schedule["schedule"]])
            
            modern_activity_prompt = f"""
            Given this full schedule:
            {schedule_str}
            
            And this persons profile: {self.persona['profile_prompt']}
            
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
            {self.persona['profile_prompt']}

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
                    model="llama-3.3-70b-specdec", 
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

