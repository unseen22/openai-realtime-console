import groq
from memory import MemoryType
from persona_scheduler import PersonaScheduler
import groq_tool
import json
import time
import perplexity_tool as pt
from datetime import datetime
from llm_chooser import LLMChooser
from open_ai_tool import OpenAITool




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
                for i, task in enumerate(schedule_data["schedule"]):
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
        Analyze each required action and determine if it needs knowledge gathering or simulation.
        
        Args:
            task_analysis (dict): Task type and required actions
            task (dict): Task details
            
        Returns:
            dict: Combined results of executing all actions
        """
        print("\n🤔 Analyzing each required action...")
        all_results = []
        
        for action in task_analysis["required_actions"]:
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
                llm_response = self.llm_chooser.generate_text(
                    provider="openai",
                    messages=[{"role": "user", "content": groq_prompt}],
                    model="gpt-4o",
                    temperature=0.7,
                    max_tokens=1024,
                    response_format={"type": "json_object"}
                )
                
                action_choice = json.loads(llm_response)
                print(f"🎯 Chosen strategy for {action}:\n{json.dumps(action_choice, indent=2)}")
                
                # Execute the chosen action for this step
                if action_choice["tool"] == "gather_knowledge":
                    print(f"🔍 Gathering knowledge for: {action}")
                    result = self._gather_knowledge({"required_actions": [action]}, task)
                else:
                    print(f"🎮 Simulating action for: {action}")
                    result = self._simulate_action({"required_actions": [action]})
                
                all_results.append({
                    "action": action,
                    "strategy": action_choice["tool"],
                    "result": result
                })
                
            except Exception as e:
                print(f"❌ Error processing action '{action}': {str(e)}")
                all_results.append({
                    "action": action,
                    "error": str(e)
                })

        # Combine all results into a cohesive narrative
        combined_results = {
            "success": True,
            "actions_completed": len(all_results),
            "detailed_results": all_results,
            "summary": "\n".join([
                f"{result['action']}: {result.get('result', result.get('error', 'No result'))}"
                for result in all_results
            ])
        }
        
        return combined_results
        
    def _gather_knowledge(self, task_analysis, task):
        """
        Gather knowledge for the task.
        
        Args:
            task_analysis (dict): Analysis of task requirements
            task (dict): Task details
            
        Returns:
            str: Retrieved information from Perplexity
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
            
            # Ensure we have a proper structure for the knowledge
            knowledge_data = {
                "query": query_data["query"],
                "information": perplexity_response
            }
            print(f"📚 Retrieved information:\n{json.dumps(knowledge_data, indent=2)}")

            validation_result = self.validate_knowledge(task, knowledge_data)
            print(f"📊 Validation result:\n{json.dumps(validation_result, indent=2)}")
            
            if not validation_result["success"]:
                print(f"⚠️ Missing details: {validation_result['missing']}")
                print("🔄 Fetching additional information...")
                additional_response = perplexity_instance.generate_completion(
                    messages=[{"role": "user", "content": validation_result["missing"]}],
                    model="llama-3.1-sonar-large-128k-online",
                    temperature=0.5
                )
                # Append additional information
                knowledge_data["additional_information"] = additional_response
                print(f"📚 Retrieved additional information:\n{json.dumps(additional_response, indent=2)}")
            
            return knowledge_data
            
        except Exception as e:
            print(f"❌ Error gathering knowledge: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def validate_knowledge(self, task, knowledge):
        """
        Validate the knowledge for the task by checking if there are sufficient concrete details.
        
        Args:
            task: The task to validate knowledge for
            knowledge: The knowledge to validate
            
        Returns:
            dict: Validation result with success status and any missing details
        """
        print("\n🔍 Validating knowledge...")
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
            validation = self.llm_chooser.generate_text(
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

    def _simulate_action(self, task_analysis):
        """
        Simulate the action for the task.
        
        Args:
            task_analysis (dict): Analysis of task requirements
            
        Returns:
            str: Description of simulated action
        """
        print("🎮 Simulating action...")
        return "Action simulated successfully"

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
                "find_reddit_post",
                "read_post_content",
                "generate_sarcastic_response",
            
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
