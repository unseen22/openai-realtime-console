import persona_scheduler as ps
import groq_tool
import json
import perplexity_tool as pt

class PersonaExecuteSchedule:
    def __init__(self):
        self.groq = groq_tool.GroqTool()
        
    def get_schedule(self, persona):
        """
        Process and execute tasks from the provided schedule.
        
        Args:
            persona (dict): Persona profile and characteristics
            
        Returns:
            dict: Results of schedule execution
        """
        try:
            # Create new schedule using PersonaScheduler
            ps_instance = ps.PersonaScheduler()
            schedule_result = ps_instance.persona_scheduler(persona)
            
            if not schedule_result.get("success"):
                raise ValueError("Failed to generate schedule")
                
            schedule_data = schedule_result.get("schedule")

            # Validate schedule format
            if not isinstance(schedule_data, dict):
                raise ValueError("Schedule must be a dictionary")
                
            # Process each task in the schedule
            task_results = {}
            # TODO: Need to track which schedule item is currently active
            # TODO: Need to mark tasks as done when completed
            if "schedule" in schedule_data and len(schedule_data["schedule"]) > 0:
                for i, task in enumerate(schedule_data["schedule"]):
                    if 1 <= i <= 8:  # Get items between 1 and 8 (0-based indexing)
                        time_slot = task["time"]
                        activity = task["activity"]
                        task_results[time_slot] = self._execute_task(persona, {"activity": activity})
                
            return {
                "success": True,
                "results": task_results
            }
            
        except Exception as e:
            print(f"❌ Error executing schedule: {str(e)}")
            return {
                "success": False, 
                "error": str(e)
            }

    def _execute_task(self, persona, task):
        """
        Execute a single task from the schedule.
        
        Args:
            persona (dict): Persona profile and characteristics
            task (dict): Task to execute
            
        Returns:
            dict: Results of task execution
        """
        print(f"📋 this is the task: {task}")
        task_analysis = self.judge_task(persona, task)
        action_result = self.choose_action(task_analysis, task)

        #print(f"this is the task: {task}")
        #print(f"______++++ {task_analysis} ++++++______")
        #print()
        experience_prompt = f"""
        You are {persona["profile_prompt"]} and you are going to write a diary entry about completing this task: {task} with the following knowledge: {action_result}.
        Write the diary entry in a way that is consistent with your personality and characteristics, describing what actually happened.
        Return only a JSON object with:
        - diary_entry: A first-person past-tense account of completing the task, including your thoughts, feelings and reactions
        - timestamp: The time the task was completed
        """

        groq_response = self.groq.chat_completion(
            messages=[{"role": "user", "content": experience_prompt}],
            model="llama-3.3-70b-specdec",
            temperature=0.5,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )
        print(f"______++++ this is the groq response: {groq_response} ++++++______")
        return groq_response

 
    
    def choose_action(self, task_analysis, task):
        """
        Choose between gathering knowledge or simulating action based on task requirements.
        
        Args:
            task_analysis (dict): Task type and required actions
            
        Returns:
            dict: Results of executing the chosen action
        """
        groq_prompt = f"""
        Analyze these required actions and determine if we need to:
        1. Gather knowledge (for tasks requiring up-to-date information)
        2. Simulate action (for tasks that don't require external knowledge)

        Required actions: {task_analysis["required_actions"]}

        Return only a JSON object with:
        - tool: Either "gather_knowledge" or "simulate_action"
        - reason: Brief explanation of the choice
        """

        try:
            llm_response = self.groq.chat_completion(
                messages=[{"role": "user", "content": groq_prompt}],
                model="llama-3.3-70b-specdec",
                temperature=0.1,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )["choices"][0]["message"]["content"]
            
            action_choice = json.loads(llm_response)
            
            # Execute the chosen action
            if action_choice["tool"] == "gather_knowledge":
                print(f"🔍 Gathering knowledge for task: {task_analysis}")
                return self._gather_knowledge(task_analysis, task)
            else:
                print(f"🎮 Simulating action for task: {task_analysis}")
                return self._simulate_action(task_analysis)
                
        except Exception as e:
            print(f"❌ Error choosing action: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
            
        
    def _gather_knowledge(self, task_analysis, task):
        """
        Gather knowledge for the task.
        """
        groq_prompt = f"""
        Create a search query to gather information needed for completing these actions this {task}:
        {task_analysis["required_actions"]}
        Find up to date information on the topic, top 10 results and trending topics. 
        Return only a JSON object with:
        - query: A focused search query that will return relevant, up-to-date information
        """

        try:
            llm_response = self.groq.chat_completion(
                messages=[{"role": "user", "content": groq_prompt}],
                model="llama-3.3-70b-specdec",
                temperature=0.5,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )["choices"][0]["message"]["content"]
            
            query_data = json.loads(llm_response)
            print(f"______++++ this is the query: {query_data} ++++++______")
            perplexity_instance = pt.PerplexityHandler("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")
            perplexity_response = perplexity_instance.generate_completion(
                messages=[{"role": "user", "content": query_data["query"]}],
                model="llama-3.1-sonar-large-128k-online",
                temperature=0.5
            )
            print(f"______++++ this is the PERPLEXITY response: {perplexity_response} ++++++______")
            return perplexity_response
            
        except Exception as e:
            print(f"❌ Error gathering knowledge: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _simulate_action(self, task_analysis):
        """
        Simulate the action for the task.
        """
       
        pass

    def judge_task(self, persona, task):
        """
        Judge the task type based on the persona and task and determine execution strategy.
        
        Args:
            persona (dict): Persona profile and characteristics
            task (dict): Task details including activity and time
            
        Returns:
            dict: Task execution plan with type and required actions
        """
        # Extract task activity
        
        # Use LLM to analyze and determine task type
        groq_prompt = f"""
        Given this activity and persona, determine the specific steps needed to complete the task in the persona's unique style.

        Activity: {task}
        Persona Profile: {persona["profile_prompt"]}

        Return only a JSON object with:
        - required_actions: Array of specific action steps for how this persona would complete the task

        Example for "Answer Reddit post about Christmas gifts":
        {{
            "required_actions": [
                "read_post_content",
                "analyze_wishlist", 
                "generate_sarcastic_response",
                "add_russian_accent_phrases",
                "post_response"
            ]
        }}
        """
        
        try:
            llm_response = self.groq.chat_completion(
                messages=[{"role": "user", "content": groq_prompt}],
                model="llama-3.3-70b-specdec", 
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )["choices"][0]["message"]["content"]
            
            task_analysis = json.loads(llm_response)
            
            return {
                "required_actions": task_analysis["required_actions"]
            }
    
            
        except Exception as e:
            print(f"❌ Error analyzing task with LLM: {str(e)}")
            return {
                "type": "default",
                "activity": task, 
                "persona": persona["name"],
                "required_actions": ["process_activity"]
            }

persona = {
    "name": "Hanna",
    "profile_prompt": """Hanna's Action-Oriented Personality Profile

I. Core Motivations & Values:

Core Need: To express herself physically and creatively, driven by a desire for excitement and emotional release.

Underlying Desire: To find a sense of belonging and purpose, which she initially found in competitive track and field but now seeks in music and performance.

Core Value: Authenticity, high energy, and finding that high.

Conflict: Between her need for physical expression and her physical limitations due to her ankle injury. Also, a struggle between her hyper-energy and finding calm.

II. Decision-Making Framework (Based on the Profile):

Energy Levels:

High Energy: Favors action-packed, fast-paced content or activities.

Low Energy: Prefers slower, more introspective or creative activities.

Emotional State:

Stressed/Anxious: Seeks high-intensity release (techno, training) or escapism (gaming, vlogging).

Relaxed/Content: Engages in creative pursuits (karaoke, dancing), and social interactions.

Social Context:

With Friends: Highly social, engages in shared activities like karaoke, rave, and training.

Alone: Seeks out self-expression (techno dancing, djing), or introspective pursuits like gaming, listening to lofi.

Aesthetic Preferences:

Favors neon/vibrant, energetic visuals, and electronic soundscapes.

Drawn to underdog stories with a high energy level.

Likes both chill and high-octane experiences.

Influence from Role Models:

Draws inspiration from Hollyh and Addison Rae, but primarily on the aesthetic and not the actual content.

Wishes to be perceived as cool and effortless.

III. Applying the Profile to Different Scenarios:

Let's use your example of "Hanna wants to watch anime." We can now use the profile to determine what anime she would watch.

Scenario: Hanna Wants to Watch Anime

Assess her current state:

Energy Level: Is she feeling energetic or chill? Let's say she's feeling like a solid 7 (somewhat energetic, but not overly so).

Emotional State: Let's assume she's feeling mostly good, hyped from her Demon Slayer binge but looking for a new adventure.

Social Context: Is she alone or with friends? Let's say she's alone today.

Use her preferences:

Based on her likes: She likes Underdog stories with high action, fast paced, and great music.

Aesthetic preferences: She would lean towards anime with vibrant, stylish animation and soundtracks.

Influences: She might look to anime recommended by vloggers she follows or that has a popular following.

Emotional Connection: She would look for a story that resonates with her personal journey (finding a new purpose after loss).

Applying the decision-making process

Not A slice of life or romance anime.

Is More likely to be an action-focused anime with high energy, like:

High Probability: Jujutsu Kaisen, My Hero Academia, Attack on Titan (due to the blend of action, underdog stories, and unique animation) Or she may be diving into the new season of Demon Slayer

Medium Probability: Cyberpunk: Edgerunners (matches her love of vibrant cityscapes and techno vibes)

Expected Reaction

She would probably hum the anime theme songs to herself as she starts the series.

She will most likely dance a little bit at the action sequences.

She would possibly text her friends about the anime.

Examples of How the Profile Drives Other Actions

If Hanna is choosing music at a rave: She would pick tracks with hard-hitting basslines, intense build-ups, and a fast tempo.

If Hanna is planning a hangout: She would suggest activities that combine action with socializing, like an impromptu track session at the park with her friends or a session at the karaoke bar.

If Hanna is feeling stressed or down: She might dive into Ori - The Will of the Wisps for a solo gaming session, looking for emotional solace and a sense of achievement, or put on a very loud techno set and dance to get her energy out and feel good.

If Hanna is trying to express her feelings: She will not directly tell anyone, but she will rather express herself through dance or music, and maybe some vague posts on social media.

IV. Personality Key Points Summary:

Energy: Reacts well with high energy, but can also chill.

Emotion: Openly reactive, but would try to hide more complex emotions.

Social: Highly social, but has no issue being alone.

Style: Bold, Vibrant and high energy, but can find comfort in chill things.""",
    "recent_history": {}
}

execute_schedule = PersonaExecuteSchedule()

# Get and execute the schedule
schedule_result = execute_schedule.get_schedule(persona)

# Print results
if schedule_result["success"]:
    print(f"✅ Schedule executed successfully: {schedule_result['results']}")
else:
    print(f"❌ Failed to execute schedule: {schedule_result.get('error')}")