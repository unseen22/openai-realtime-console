from groq_tool import GroqTool
import json
from llm_chooser import LLMChooser

class PersonaReflection:
    def __init__(self):
        print("🔄 Initializing PersonaReflection...")
        self.llm_chooser = LLMChooser()
        self.groq = GroqTool()
        print("✅ PersonaReflection initialized successfully")
        

    def reflect_on_day(self, persona: str, schedule_results: dict) -> dict:
        """
        Generate a reflection on the day's activities and experiences.
        
        Args:
            persona_profile: String containing the persona's profile/characteristics
            schedule_results: Dictionary containing results of completed schedule activities
            
        Returns:
            dict: Contains the reflection text and any insights
        """
        print("\n🤔 Starting daily reflection process...")
        print(f"📊 Schedule results received: {json.dumps(schedule_results, indent=2)}")

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

        print("\n🤖 Generating reflection using LLM...")
        try:
            print("📝 Sending reflection prompt to OpenAI...")
            response = self.llm_chooser.generate_text(
                provider="openai",
                messages=[{"role": "user", "content": reflection_prompt}],
                model="gpt-4o",
                temperature=0.8,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            print("✨ Successfully received LLM response")
            print("🔄 Parsing reflection data...")
            
            # Parse the JSON string response directly
            reflection_data = json.loads(response)
            print(f"\n📋 Reflection Summary:\n{json.dumps(reflection_data, indent=2)}")
            return reflection_data
            
        except Exception as e:
            print(f"❌ Error generating reflection: {str(e)}")
            error_response = {
                "error": "Failed to generate reflection",
                "details": str(e),
                "reflection": "",
                "plans": []
            }
            print(f"⚠️ Returning error response:\n{json.dumps(error_response, indent=2)}")
            return error_response

