import json
from datetime import datetime, timedelta
from brain.groq_tool import GroqTool
from brain.perplexity_tool import PerplexityHandler
import random

class DailyScheduler:
    def __init__(self):
        self.schedule = {}
        self.start_time = 6  # 6 AM
        self.end_time = 24   # 12 PM (midnight)
        self.groq = GroqTool()
        self.perplexity = PerplexityHandler(api_key="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")
        self.BROWSING_KEYWORDS = [
            "watch", "read", "browse", "research", "study", "learn",
            "look up", "search", "explore", "check", "review"
        ]

    def generate_time_slots(self):
        """Generate available time slots for the day"""
        time_slots = []
        current_time = datetime.now().replace(hour=self.start_time, minute=0, second=0, microsecond=0)
        end_time = current_time.replace(hour=self.end_time)

        while current_time < end_time:
            time_slots.append(current_time)
            current_time += timedelta(hours=1)
        
        return time_slots

    def create_daily_schedule(self, persona_profile, recent_history):
        """
        Create a daily schedule based on persona profile and recent history using LLM
        Args:
            persona_profile (dict): Profile information of the AI persona
            recent_history (dict): Recent activities and preferences
        Returns:
            dict: Daily schedule in JSON format
        """
        time_slots = self.generate_time_slots()
        
        # Create prompt for the LLM
        prompt = f"""
        Given this persona profile:
        {json.dumps(persona_profile, indent=2)}
        
        And their recent activity history:
        {json.dumps(recent_history, indent=2)}
        
        Please create a detailed daily schedule from {self.start_time}:00 to {self.end_time}:00.
        The schedule should take into account the persona's preferences, habits, and recent activities.
        Return the schedule as a JSON object where each hour is a key (in HH:MM format) with an object containing:
        - activity: detailed description of the activity
        - duration: duration in hours
        - priority: low/normal/high
        
        Format the response as valid JSON only.
        """

        # Get schedule from LLM
        try:
            response = self.groq.generate_text(
                prompt,
                model="llama-3.1-70b-versatile",
                temperature=0.7,
                max_tokens=2048
            )
            schedule = json.loads(response)
            
            if self.validate_schedule(schedule):
                result = json.dumps(schedule, indent=4)
                print(result)
                return result
            else:
                raise ValueError("Generated schedule failed validation")
                
        except Exception as e:
            print(f"Error generating schedule: {str(e)}")
            return self._generate_fallback_schedule(time_slots)

    def _generate_fallback_schedule(self, time_slots):
        """Generate a basic fallback schedule if LLM fails"""
        schedule = {}
        for time_slot in time_slots:
            schedule[time_slot.strftime("%H:%M")] = {
                "activity": "Free time - Schedule generation failed",
                "duration": "1 hour",
                "priority": "normal"
            }
        return json.dumps(schedule, indent=4)


    def execute_current_activity(self, schedule_json, persona_profile, current_time=None):
        """
        Execute the current scheduled activity based on time
        Args:
            schedule_json (str): JSON string containing the schedule
            persona_profile (dict): Profile of the persona
            current_time (datetime): Optional override for current time
        Returns:
            dict: Activity execution results and experience
        """
        try:
            schedule = json.loads(schedule_json)
        except:
            return {"status": "error", "message": "Invalid schedule JSON"}

        if current_time is None:
            current_time = datetime.now()
        current_slot = current_time.strftime("%H:%M")
        
        if current_slot not in schedule:
            return {"status": "error", "message": "No activity scheduled for current time"}
        
        activity = schedule[current_slot]
        
        # Execute activity with appropriate tool
        result = self._execute_with_tools(activity, persona_profile)
            
        # Generate experience based on execution result
        experience = self._generate_experience(activity, result, persona_profile)
        
        return {
            "status": "success",
            "activity": activity,
            "execution_result": result,
            "experience": experience
        }
    def _check_tools_needed(self, activity_description):
        """
        Check if activity requires web browsing or can be handled with simple simulation.
        Uses LLM to determine if the activity involves consuming online content.
        Args:
            activity_description (str): Description of activity
        Returns:
            dict: JSON response with tool type
        """
        prompt = f"""
        Determine if this activity requires accessing online content or information:
        "{activity_description}"
        
        Consider if the activity involves:
        - Reading articles, books, or text content
        - Watching videos, shows, movies
        - Browsing websites or social media
        - Looking up information or learning online
        - Consuming any media or content that would be found on the internet
        
        Return JSON with a single key 'tool_type' and value of either 'web_browsing' or 'simulation'.
        'web_browsing' if the activity involves accessing online content.
        'simulation' if it's a physical or offline activity.
        """
        
        try:
            response = self.groq.generate_text(
                prompt,
                model="llama-3.1-70b-versatile", 
                temperature=0.3,
                max_tokens=50
            )
            result = json.loads(response)
            if result['tool_type'] in ['web_browsing', 'simulation']:
                return result
            return {'tool_type': 'simulation'}  # Default to simulation if invalid
        except:
            return {'tool_type': 'simulation'}  # Default to simulation on error
            
    def _execute_with_tools(self, activity, persona_profile):
        """
        Execute activity using appropriate tools via LLM
        Args:
            activity (dict): Activity details
            persona_profile (dict): Profile of the persona
        Returns:
            dict: Execution results
        """
        tool_type = self._check_tools_needed(activity['activity'])
        
        if tool_type == 'web_browsing':
            return self._execute_web_browsing(activity, persona_profile)
        else:
            return self._execute_simulation(activity, persona_profile)

    def _execute_web_browsing(self, activity, persona_profile):
        """
        Simulate web browsing activity using Perplexity for content retrieval
        Args:
            activity (dict): Activity details
            persona_profile (dict): Profile of the persona
        Returns:
            dict: Execution results
        """
        # First, generate a search query using Groq
        query_prompt = f"""
        Generate a search query to find detailed information about this activity: "{activity['activity']}"

        Create a query that would return:
        1. Basic factual information (e.g. for a movie: runtime, release date, director, main cast)
        2. Plot summary and key moments
        3. Critical reception and ratings
        4. Where to access/watch/read the content
        5. Any additional context needed to simulate the experience

        Return as JSON with:
        - search_query: the optimal search query to find this information
        - required_details: list of specific details needed to simulate this activity
        - experience_type: what kind of content this is (movie/article/video/etc)
        - estimated_duration: how long this activity would take
        Format as valid JSON only.
        """

        try:
            # Get search parameters from Groq
            query_response = self.groq.generate_text(
                query_prompt,
                model="llama-3.1-70b-versatile",
                temperature=0.7,
                max_tokens=1024
            )
            search_params = json.loads(query_response)

            # Use Perplexity to get actual content information
            perplexity_prompt = [
                {"role": "system", "content": "You are a helpful assistant providing detailed information about online content."},
                {"role": "user", "content": f"""
                Search query: {search_params['search_query']}
                Please provide detailed information about this content including:
                1. Basic facts and information
                2. Plot summary or content overview
                3. Critical reception or ratings
                4. Where to access this content
                5. Any notable highlights or key points
                
                Format the response to be informative but concise.
                """}
            ]

            # Get content information from Perplexity
            content_info = self.perplexity.generate_completion(
                messages=perplexity_prompt,
                model="llama-3.1-sonar-large-128k-online",  # Using online model for real-time info
                temperature=0.7
            )

            # Generate experience simulation using the gathered information
            simulation_prompt = f"""
            Given this content information:
            {content_info}
            
            And this persona profile:
            {json.dumps(persona_profile, indent=2)}
            
            Simulate how the persona would experience this content.
            Return as JSON with:
            - success: boolean indicating if they enjoyed/completed the content
            - engagement_level: 1-10 rating of how engaged they were
            - key_reactions: list of their main reactions or thoughts
            - memorable_moments: specific moments that stood out to them
            - learning_outcomes: what they gained from this experience
            Format as valid JSON only.
            """

            simulation_response = self.groq.generate_text(
                simulation_prompt,
                model="llama-3.1-70b-versatile",
                temperature=0.7,
                max_tokens=1024
            )
            
            experience_result = json.loads(simulation_response)
            
            return {
                "success": experience_result["success"],
                "content_info": content_info,
                "experience_details": experience_result,
                "activity_type": search_params["experience_type"],
                "duration": search_params["estimated_duration"]
            }

        except Exception as e:
            print(f"Error in web browsing simulation: {str(e)}")
            return self._execute_with_dice(activity)

    def _execute_simulation(self, activity, persona_profile):
        """
        Simulate regular activity without web browsing
        Args:
            activity (dict): Activity details
            persona_profile (dict): Profile of the persona
        Returns:
            dict: Execution results
        """
        prompt = f"""
        Simulate this activity: "{activity['activity']}"
        For a persona with this profile:
        {json.dumps(persona_profile, indent=2)}

        Return as JSON with:
        - success: boolean indicating if activity was successful
        - details: detailed description of what happened
        - outcomes: any notable results or consequences
        Format as valid JSON only.
        """
        
        try:
            response = self.groq.generate_text(
                prompt,
                model="llama-3.1-70b-versatile",
                temperature=0.7,
                max_tokens=1024
            )
            return json.loads(response)
        except:
            return self._execute_with_dice(activity)

    def _execute_with_dice(self, activity):
        """
        Fallback execution using D20 roll
        Args:
            activity (dict): Activity details
        Returns:
            dict: Execution results
        """
        roll = random.randint(1, 20)
        success = roll >= 10  # 55% success rate
        
        return {
            "success": success,
            "details": f"D20 Roll: {roll} ({'Success' if success else 'Failure'})"
        }
        
    def _generate_experience(self, activity, result, persona_profile):
        """
        Generate experience description based on activity and result
        Args:
            activity (dict): Activity details
            result (dict): Execution results
            persona_profile (dict): Profile of the persona
        Returns:
            str: Experience description
        """
        prompt = f"""
        Given this activity: "{activity['activity']}"
        With this result: {json.dumps(result)}
        For a persona with this profile: {json.dumps(persona_profile, indent=2)}
        
        Generate a detailed description of the persona's experience.
        Focus on:
        1. Their emotional state and reactions
        2. How their personality traits influenced their experience
        3. What they learned or gained from the activity
        4. Any memorable moments or notable outcomes
        Keep response under 200 words.
        """
        
        try:
            experience = self.groq.generate_text(
                prompt,
                model="llama-3.1-70b-versatile",
                temperature=0.7,
                max_tokens=512
            )
            return experience.strip()
        except:
            return "Failed to generate experience description"

    def validate_schedule(self, schedule):
        """
        Validate the generated schedule
        Args:
            schedule (dict): Generated schedule
        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(schedule, dict):
            return False
            
        required_keys = {"activity", "duration", "priority"}
        valid_priorities = {"low", "normal", "high"}
        
        for time_slot, details in schedule.items():
            # Validate time format
            try:
                datetime.strptime(time_slot, "%H:%M")
            except ValueError:
                return False
                
            # Validate activity details
            if not isinstance(details, dict):
                return False
                
            if not all(key in details for key in required_keys):
                return False
                
            if details["priority"] not in valid_priorities:
                return False
                
        return True
