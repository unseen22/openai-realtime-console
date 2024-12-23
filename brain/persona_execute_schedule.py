from memory import MemoryType
from persona_scheduler import PersonaScheduler
import groq_tool
import json
import time
import perplexity_tool as pt
from datetime import datetime
from llm_chooser import LLMChooser



class PersonaExecuteSchedule:
    def __init__(self):
        print("🔄 Initializing PersonaExecuteSchedule...")
        self.groq = groq_tool.GroqTool()
        self.llm_chooser = LLMChooser()
        print("✅ PersonaExecuteSchedule initialized successfully")
        
    def get_schedule(self, persona):
        """
        Process and execute tasks from the provided schedule.
        
        Args:
            persona (dict): Persona profile and characteristics
            
        Returns:
            tuple: (schedule_results, updated_persona)
        """
        print("\n📅 Starting schedule processing...")
        try:
            # Create new schedule using PersonaScheduler
            print("🎯 Creating new schedule...")
            persona_scheduler = PersonaScheduler()
            schedule_result = persona_scheduler.persona_scheduler(persona)
            
            if not schedule_result.get("success"):
                print("❌ Failed to generate schedule")
                raise ValueError("Failed to generate schedule")
                
            schedule_data = schedule_result.get("schedule")
            print(f"📋 Generated schedule data:\n{json.dumps(schedule_data, indent=2)}")

            # Validate schedule format
            if not isinstance(schedule_data, dict):
                print("❌ Invalid schedule format")
                raise ValueError("Schedule must be a dictionary")
                
            # Process each task in the schedule
            print("\n⏳ Processing schedule tasks...")
            task_results = {}
            updated_persona = persona
            # TODO: Need to track which schedule item is currently active
            # TODO: Need to mark tasks as done when completed
            if "schedule" in schedule_data and len(schedule_data["schedule"]) > 0:
                for task in schedule_data["schedule"]:
                    time_slot = task["time"]
                    activity = task["activity"]
                    print(f"\n🎯 Executing task for {time_slot}: {activity}")
                    result, updated_persona = self._execute_task(updated_persona, {"activity": activity})
                    task_results[time_slot] = result
                
            print("\n✅ Schedule processing completed successfully")
            return {
                "success": True,
                "results": task_results
            }, updated_persona
            
        except Exception as e:
            print(f"❌ Error executing schedule: {str(e)}")
            return {
                "success": False, 
                "error": str(e)
            }, persona

    def _execute_task(self, persona, task):
        """
        Execute a single task from the schedule.
        
        Args:
            persona: Brain object containing persona information
            task (dict): Task to execute
            
        Returns:
            tuple: (task_result, updated_persona)
        """
        print(f"\n📋 Executing task: {json.dumps(task, indent=2)}")
        print("🔍 Analyzing task requirements...")
        task_analysis = self.judge_task(persona, task)
        print(f"📊 Task analysis results:\n{json.dumps(task_analysis, indent=2)}")
        
        print("🎮 Choosing action strategy...")
        action_result = self.choose_action(task_analysis, task)
        time.sleep(1)

        print("📝 Generating experience diary entry...")
        experience_prompt = f"""
        You are {persona.persona_profile} and you are going to write a diary entry about completing this task: {task} with the following knowledge: {action_result}.
        Write the diary entry in a way that is consistent with your personality and characteristics, describing what actually happened.
        Return only a JSON object with:
        - diary_entry: A first-person past-tense account of completing the task, including your thoughts, feelings and reactions
        - timestamp: The time the task was completed
        """

        groq_response = self.llm_chooser.generate_text(
            provider="openai",
            messages=[{"role": "user", "content": experience_prompt}],
            model="gpt-4o",
            temperature=0.5,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )
        print(f"📔 Generated diary entry:\n{json.dumps(groq_response, indent=2)}")
        persona.create_memory(groq_response, MemoryType.EXPERIENCE)
        return groq_response, persona

 
    
    def choose_action(self, task_analysis, task):
        """
        Choose between gathering knowledge or simulating action based on task requirements.
        
        Args:
            task_analysis (dict): Task type and required actions
            
        Returns:
            dict: Results of executing the chosen action
        """
        print("\n🤔 Choosing action strategy...")
        groq_prompt = f"""
        Analyze these required actions and determine if we need to:
        1. Gather knowledge (for tasks requiring up-to-date information, or tasks that are not concrete, or need realtime knowladge to simulate, need a decision to make, choosing films, music, activities, etc)
        2. Simulate action (for tasks that don't require external knowledge, or tasks that are concrete and don't need realtime knowledge to simulate, take a walk, have a chat, hit the gym.)

        Required actions: {task_analysis["required_actions"]}

        Return only a JSON object with:
        - tool: Either "gather_knowledge" or "simulate_action"
        - reason: Brief explanation of the choice
        """

        try:
            print("🔄 Getting action choice from LLM...")
            llm_response = self.llm_chooser.generate_text(
                provider="openai",
                messages=[{"role": "user", "content": groq_prompt}],
                model="gpt-4o",
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            action_choice = json.loads(llm_response)
            print(f"🎯 Chosen action strategy:\n{json.dumps(action_choice, indent=2)}")
            
            # Execute the chosen action
            if action_choice["tool"] == "gather_knowledge":
                print(f"🔍 Gathering knowledge for task...")
                return self._gather_knowledge(task_analysis, task)
            else:
                print(f"🎮 Simulating action for task...")
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
        print("\n🔍 Starting knowledge gathering...")
        groq_prompt = f"""
        Create a search query to gather information needed for completing these actions this {task}:
        {task_analysis["required_actions"]}
        Find up to date information on the topic, top 10 results and trending topics. 
        Always add todays date in the query which is {datetime.now().strftime("%Y-%m-%d")}
        Return only a JSON object with:
        - query: A focused search query that will return relevant, up-to-date information
        """

        try:
            print("🤖 Generating search query...")
            llm_response = self.llm_chooser.generate_text(
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
            perplexity_response = perplexity_instance.generate_completion(
                messages=[{"role": "user", "content": query_data["query"]}],
                model="llama-3.1-sonar-large-128k-online",
                temperature=0.5
            )
            print(f"📚 Retrieved information:\n{json.dumps(perplexity_response, indent=2)}")
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
        print("🎮 Simulating action (not implemented)")
        pass

    def judge_task(self, persona, task):
        """
        Judge the task type based on the persona and task and determine execution strategy.
        
        Args:
            persona: Brain object containing persona information
            task (dict): Task details including activity and time
            
        Returns:
            dict: Task execution plan with type and required actions
        """
        print("\n⚖️ Analyzing task requirements...")
        # Use LLM to analyze and determine task type
        groq_prompt = f"""
        Given this activity and persona, determine the specific steps needed to complete the task in the persona's unique style.

        Activity: {task}
        Persona Profile: {persona.persona_profile}

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
            print("🤖 Getting task analysis from LLM...")
            llm_response = self.llm_chooser.generate_text(
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
                "persona": persona.persona_name,
                "required_actions": ["process_activity"]
            }
