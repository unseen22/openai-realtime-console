from groq_tool import GroqTool
import json

class PersonaReflection:
    def __init__(self):
        self.groq = GroqTool()

    def reflect_on_day(self, persona: str, schedule_results: dict) -> dict:
        """
        Generate a reflection on the day's activities and experiences.
        
        Args:
            persona_profile: String containing the persona's profile/characteristics
            schedule_results: Dictionary containing results of completed schedule activities
            
        Returns:
            dict: Contains the reflection text and any insights
        """
        reflection_prompt = f"""
        As {persona.persona_profile}, reflect on your day and experiences:
        
        Today's Activities:
        {schedule_results}
        
        Write a thoughtful reflection that includes:
        1. Your overall feelings about the day
        2. What you learned or accomplished
        3. How the activities aligned with your personality and goals
        4. Any insights or plans for tomorrow
        5. Details of the activity, like what movie you watched, what book you read, what artist you listened to, etc.
        
        Return only a JSON object with:
        - summary: A short summary of the day with the details of the activities
        - reflection: Your personal reflection on the day
        - mood: Your overall emotional state
        - plans: Things that you plan to do in the future
        - key_insights: List of main takeaways from the day
        """

        try:
            response = self.groq.chat_completion(
                messages=[{"role": "user", "content": reflection_prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.8,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            reflection_data = json.loads(response["choices"][0]["message"]["content"])
            return reflection_data
            
        except Exception as e:
            print(f"Error generating reflection: {str(e)}")
            return {
                "error": "Failed to generate reflection",
                "details": str(e),
                "reflection": "",
                "plans": []
            }

    
