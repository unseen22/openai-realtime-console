import json
from datetime import datetime, timedelta
from groq_tool import GroqTool
from perplexity_tool import PerplexityHandler
import random

class DailyScheduler:
    def __init__(self):
        print("🚀 Initializing DailyScheduler...")
        self.schedule = {}
        self.start_time = 6  # 6 AM
        self.end_time = 23   # 11 PM (changed from 24)
        self.groq = GroqTool()
        self.perplexity = PerplexityHandler(api_key="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")
        self.BROWSING_KEYWORDS = [
            "watch", "read", "browse", "research", "study", "learn",
            "look up", "search", "explore", "check", "review"
        ]
        print("✅ DailyScheduler initialized successfully")

    def generate_time_slots(self):
        """Generate available time slots for the day"""
        print("⏰ Generating time slots...")
        time_slots = []
        current_time = datetime.now().replace(hour=self.start_time, minute=0, second=0, microsecond=0)
        end_time = current_time.replace(hour=self.end_time)

        while current_time < end_time:
            time_slots.append(current_time)
            current_time += timedelta(hours=1)
        
        print(f"✅ Generated {len(time_slots)} time slots")
        return time_slots

    def create_daily_schedule(self, persona_profile, recent_history):
        """
        Create a daily schedule based on persona profile and recent history using LLM
        """
        time_slots = self.generate_time_slots()
        
        # Create system prompt for JSON mode
        system_prompt = """You are a scheduling API that creates daily schedules in JSON format.
        Your responses must be valid JSON objects with the following schema:
        {
            "HH:MM": {
                "activity": "string",
                "duration": "string",
                "priority": "string (low/normal/high)"
            }
        }"""
        
        # Create user prompt
        user_prompt = f"""Given this persona profile:
        {json.dumps(persona_profile, indent=2)}
        
        And their recent activity history:
        {json.dumps(recent_history, indent=2)}
        
        Create a daily schedule from {self.start_time}:00 to {self.end_time}:00.
        The schedule should reflect the persona's preferences and recent activities.
        
        Return a JSON object where each hour is a key in HH:MM format."""

        # Get schedule from LLM
        try:
            print("\nSending prompt to Groq...")
            response = self.groq.generate_text(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama3-groq-70b-8192-tool-use-preview",  # Using Mixtral for better JSON generation
                temperature=0.7,
                max_tokens=2048,
                response_format={"type": "json_object"}  # Enable JSON mode
            )
            
            print("\nGroq response received. Attempting to parse JSON...")
            print(f"Raw response: {response[:200]}...") # Print first 200 chars for debugging
            
            try:
                schedule = json.loads(response)
                if self.validate_schedule(schedule):
                    result = json.dumps(schedule, indent=4)
                    print("\nSchedule generated successfully!")
                    return result
                else:
                    print("\nGenerated schedule failed validation")
                    raise ValueError("Generated schedule failed validation")
                
            except json.JSONDecodeError as je:
                print(f"\nJSON parsing error: {str(je)}")
                print(f"Failed to parse response: {response}")
                raise
                
        except Exception as e:
            print(f"\nError generating schedule: {str(e)}")
            return self._generate_fallback_schedule(time_slots)

    def _generate_fallback_schedule(self, time_slots):
        """Generate a basic fallback schedule if LLM fails"""
        print("\nGenerating fallback schedule...")
        schedule = {}
        activities = [
            "Watch an episode of favorite anime",
            "Read some manga",
            "Work on cosplay",
            "Browse anime recommendations",
            "Free time - Schedule generation failed"
        ]
        
        for time_slot in time_slots:
            schedule[time_slot.strftime("%H:%M")] = {
                "activity": random.choice(activities),
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
        print(f"🔍 Checking tools needed for activity: {activity_description}")
        
        system_prompt = """You are a tool detection API that returns JSON in this format:
        {
            "tool_type": "string (web_browsing/simulation)"
        }"""
        
        user_prompt = f"""Determine if this activity requires accessing online content or information:
        "{activity_description}"
        
        Consider if the activity involves:
        - Reading articles, books, or text content
        - Watching videos, shows, movies
        - Browsing websites or social media
        - Looking up information or learning online
        - Consuming any media or content that would be found on the internet
        
        Return JSON with a single key 'tool_type' and value of either 'web_browsing' or 'simulation'.
        'web_browsing' if the activity involves accessing online content.
        'simulation' if it's a physical or offline activity."""
        
        try:
            response = self.groq.generate_text(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama3-groq-70b-8192-tool-use-preview",
                temperature=0.3,
                max_tokens=50,
                response_format={"type": "json_object"}
            )
            result = json.loads(response)
            if result['tool_type'] in ['web_browsing', 'simulation']:
                return result
            return {'tool_type': 'simulation'}  # Default to simulation if invalid
        except:
            return {'tool_type': 'simulation'}  # Default to simulation on error
            
    def _execute_with_tools(self, activity, persona_profile):
        print(f"🛠️ Executing activity with tools: {activity['activity']}")
        tool_type = self._check_tools_needed(activity['activity'])
        
        # Check if this is a content consumption activity
        content_keywords = [
            'watch', 'read', 'browse', 'stream', 'play', 'listen',
            'tv', 'show', 'movie', 'video', 'book', 'manga', 'anime',
            'game', 'social media', 'phone', 'internet', 'web', 'youtube',
            'series', 'podcast', 'music'
        ]
        
        if any(keyword in activity['activity'].lower() for keyword in content_keywords):
            print("🎬 Detected content consumption activity")
            return self._execute_content_activity(activity, persona_profile)
        elif tool_type == 'web_browsing':
            print("🌐 Using web browsing tools")
            return self._execute_web_browsing(activity, persona_profile)
        else:
            print("🎲 Using simulation tools")
            return self._execute_simulation(activity, persona_profile)

    def _execute_content_activity(self, activity, persona_profile):
        """Handle any type of content consumption with multiple steps"""
        print("🎬 Starting content activity process...")
        
        try:
            # Step 1: Analyze the type of content and current state
            print("🤔 Analyzing content type and state...")
            analysis_prompt = f"""Given this activity: "{activity['activity']}"
            And this persona profile: {json.dumps(persona_profile, indent=2)}
            
            Analyze the content consumption activity.
            Return as JSON:
            {{
                "content_type": "string (tv/movie/book/game/social_media/web/music/podcast/etc)",
                "is_continuing": boolean,
                "current_content": "string, name of current content if continuing, or null",
                "progress_info": "string, progress information if continuing, or null",
                "platform": "string, platform or service used (Netflix/YouTube/Spotify/etc)",
                "duration_estimate": "string, estimated time needed",
                "search_keywords": ["string, relevant search terms for finding new content"]
            }}
            """
            
            analysis_response = self.groq.generate_text(
                messages=[
                    {"role": "system", "content": "You are a content analysis system that helps understand media consumption activities."},
                    {"role": "user", "content": analysis_prompt}
                ],
                model="llama3-groq-70b-8192-tool-use-preview",
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            analysis_result = json.loads(analysis_response)
            print(f"📋 Content analysis: {json.dumps(analysis_result, indent=2)}")
            
            if not analysis_result.get("is_continuing", False):
                # Step 2: Search for modern/top-rated content
                print("🔍 Searching for modern/top-rated content...")
                search_prompt = [
                    {
                        "role": "system",
                        "content": "You are a content discovery specialist focusing on modern and highly-rated content."
                    },
                    {
                        "role": "user",
                        "content": f"""Find the latest and highest-rated {analysis_result['content_type']} content.
                        Consider:
                        - Released in the last 2 years
                        - High ratings and positive reviews
                        - Popular among {analysis_result['content_type']} enthusiasts
                        - Similar to interests in profile: {json.dumps(persona_profile, indent=2)}
                        - Search keywords: {', '.join(analysis_result['search_keywords'])}
                        
                        Return a curated list of 5 recommendations with brief descriptions."""
                    }
                ]
                
                initial_search = self.perplexity.generate_completion(
                    messages=search_prompt,
                    model="llama-3.1-sonar-small-128k-online",
                    temperature=0.7
                )
                
                print("📚 Initial content search results:")
                print(initial_search[:200] + "...")
                
                # Step 3: Select content from search results
                selection_prompt = f"""Based on these search results:
                {initial_search}
                
                And this persona profile:
                {json.dumps(persona_profile, indent=2)}
                
                Select the most suitable content.
                Return as JSON:
                {{
                    "selected_title": "string",
                    "reason": "string explaining why this is the best choice",
                    "expected_appeal": number between 1-10
                }}"""
                
                selection_response = self.groq.generate_text(
                    messages=[
                        {"role": "system", "content": "You are a content recommendation system that makes personalized selections."},
                        {"role": "user", "content": selection_prompt}
                    ],
                    model="llama3-groq-70b-8192-tool-use-preview",
                    temperature=0.7,
                    max_tokens=1024,
                    response_format={"type": "json_object"}
                )
                
                selected_content = json.loads(selection_response)
                print(f"✨ Selected content: {selected_content['selected_title']}")
                
                # Step 4: Detailed research on selected content
                print("🔍 Researching selected content in detail...")
                detail_prompt = [
                    {
                        "role": "system",
                        "content": f"You are a {analysis_result['content_type']} expert providing comprehensive information about content."
                    },
                    {
                        "role": "user",
                        "content": f"""Provide detailed information about '{selected_content['selected_title']}':
                        1. Plot/content summary
                        2. Critical reception and ratings
                        3. Unique selling points
                        4. Target audience and appeal
                        5. Where to watch/access
                        6. Length/duration/episodes
                        7. Creator/studio information
                        8. Similar content recommendations
                        9. Community reception and popularity
                        10. Any content warnings or considerations"""
                    }
                ]
                
                detailed_info = self.perplexity.generate_completion(
                    messages=detail_prompt,
                    model="llama-3.1-sonar-small-128k-online",
                    temperature=0.7
                )
                
                print("📖 Detailed information retrieved")
                print(f"ℹ️ Preview: {detailed_info[:200]}...")
                
                # Step 5: Simulate consumption experience
                print("🎭 Simulating content consumption...")
                experience_prompt = f"""Given this information:
                Content: {selected_content['selected_title']}
                Type: {analysis_result['content_type']}
                Platform: {analysis_result['platform']}
                Details: {detailed_info[:1000]}
                Persona: {json.dumps(persona_profile, indent=2)}
                Expected Appeal: {selected_content['expected_appeal']}
                
                Simulate their content consumption experience.
                Return as JSON:
                {{
                    "success": boolean,
                    "engagement_level": number between 1-10,
                    "time_spent": "string",
                    "emotional_reactions": ["string"],
                    "memorable_moments": ["string"],
                    "thoughts": "string",
                    "will_continue": boolean,
                    "platform_experience": "string",
                    "distractions": ["string"],
                    "satisfaction_level": number between 1-10,
                    "recommendations_for_next_time": ["string"]
                }}"""
                
                experience_response = self.groq.generate_text(
                    messages=[
                        {"role": "system", "content": "You are an experience simulation system that creates detailed content consumption experiences."},
                        {"role": "user", "content": experience_prompt}
                    ],
                    model="llama3-groq-70b-8192-tool-use-preview",
                    temperature=0.7,
                    max_tokens=1024,
                    response_format={"type": "json_object"}
                )
                
                experience_result = json.loads(experience_response)
                print(f"🎬 Experience simulated: {json.dumps(experience_result, indent=2)}")
                
                return {
                    "success": True,
                    "initial_search_results": initial_search,
                    "selected_content": selected_content,
                    "detailed_info": detailed_info,
                    "experience": experience_result,
                    "content_type": analysis_result['content_type'],
                    "platform": analysis_result['platform']
                }
                
            else:
                # Continue with current content
                print(f"📺 Continuing {analysis_result['current_content']}")
                return self._simulate_continued_consumption(
                    analysis_result['current_content'],
                    analysis_result['progress_info'],
                    analysis_result['content_type'],
                    analysis_result['platform'],
                    persona_profile
                )
                
        except Exception as e:
            print(f"❌ Error in content activity: {str(e)}")
            print(f"🔍 Error type: {type(e).__name__}")
            return self._execute_with_dice(activity)

    def _simulate_continued_consumption(self, content_title, progress_info, content_type, platform, persona_profile):
        """Simulate continuing to consume current content"""
        print(f"📺 Simulating continued consumption of {content_title}")
        try:
            experience_prompt = f"""Simulate continuing to consume:
            Content: {content_title}
            Type: {content_type}
            Platform: {platform}
            Progress Info: {progress_info}
            Persona: {json.dumps(persona_profile, indent=2)}
            
            Return as JSON:
            {{
                "success": boolean,
                "engagement_level": number between 1-10,
                "time_spent": "string",
                "progress_made": "string",
                "reactions": ["string"],
                "thoughts": "string",
                "distractions": ["string"],
                "platform_issues": ["string"],
                "satisfaction_level": number between 1-10,
                "will_continue_later": boolean
            }}"""
            
            experience_response = self.groq.generate_text(
                messages=[
                    {"role": "system", "content": "You are an experience simulation system for content consumption."},
                    {"role": "user", "content": experience_prompt}
                ],
                model="llama3-groq-70b-8192-tool-use-preview",
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(experience_response)
            print(f"📝 Consumption experience: {json.dumps(result, indent=2)}")
            
            return {
                "success": True,
                "content_title": content_title,
                "content_type": content_type,
                "platform": platform,
                "progress_info": progress_info,
                "experience": result
            }
            
        except Exception as e:
            print(f"❌ Error in continued consumption: {str(e)}")
            return self._execute_with_dice({"activity": f"Continue {content_title}"})

    def _execute_web_browsing(self, activity, persona_profile):
        print("🌐 Starting web browsing simulation...")
        try:
            print("📝 Generating search query parameters...")
            # Get search parameters from Groq
            query_response = self.groq.generate_text(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama3-groq-70b-8192-tool-use-preview",
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            print("✅ Search query generated successfully")
            print(f"🔍 Raw query response: {query_response[:200]}...")
            
            search_params = json.loads(query_response)
            print(f"🎯 Search parameters: {json.dumps(search_params, indent=2)}")

            try:
                print("🌐 Making Perplexity API call...")
                # Create perplexity prompt
                perplexity_prompt = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that provides detailed information about anime, manga, and Japanese culture."
                    },
                    {
                        "role": "user",
                        "content": f"Search query: {search_params['search_query']}\nRequired details: {', '.join(search_params['required_details'])}"
                    }
                ]
                
                content_info = self.perplexity.generate_completion(
                    messages=perplexity_prompt,
                    model="llama-3.1-sonar-small-128k-online",
                    temperature=0.7
                )
                
                if not content_info:
                    print("⚠️ Warning: Perplexity returned empty response")
                    raise ValueError("Empty response from Perplexity")
                
                print("✅ Perplexity content retrieved successfully")
                print(f"📄 Content preview: {content_info[:200]}...")
                
            except Exception as perplexity_error:
                print(f"❌ Perplexity API error: {str(perplexity_error)}")
                print(f"🔍 Error type: {type(perplexity_error).__name__}")
                raise

            print("💭 Generating experience simulation...")
            simulation_response = self.groq.generate_text(
                messages=[
                    {"role": "system", "content": exp_system_prompt},
                    {"role": "user", "content": exp_user_prompt}
                ],
                model="llama3-groq-70b-8192-tool-use-preview",
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            print("✅ Experience simulation generated")
            print(f"📝 Raw simulation response: {simulation_response[:200]}...")
            
            experience_result = json.loads(simulation_response)
            
            return {
                "success": experience_result["success"],
                "content_info": content_info,
                "experience_details": experience_result,
                "activity_type": search_params["experience_type"],
                "duration": search_params["estimated_duration"]
            }

        except Exception as e:
            print(f"❌ Error in web browsing simulation: {str(e)}")
            print(f"🔍 Error type: {type(e).__name__}")
            print(f"🔬 Error location: {e.__traceback__.tb_frame.f_code.co_name}")
            return self._execute_with_dice(activity)

    def _execute_simulation(self, activity, persona_profile):
        print(f"🎮 Simulating activity: {activity['activity']}")
        try:
            print("📝 Generating simulation prompt...")
            # Define the prompt before using it
            prompt = f"""Simulate this activity: "{activity['activity']}"
            For a persona with this profile:
            {json.dumps(persona_profile, indent=2)}

            Return as JSON with:
            {{
                "success": boolean indicating if activity was successful,
                "details": "detailed description of what happened",
                "outcomes": ["list of notable results or consequences"]
            }}
            Format as valid JSON only."""
            
            print("📄 Using prompt:")
            print(prompt)
            
            response = self.groq.generate_text(
                messages=[
                    {"role": "system", "content": "You are a simulation API that returns JSON results of simulated activities."},
                    {"role": "user", "content": prompt}
                ],
                model="llama3-groq-70b-8192-tool-use-preview",
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            print("✅ Simulation response received")
            print(f"📄 Raw response: {response[:200]}...")
            
            result = json.loads(response)
            print("✅ Successfully parsed simulation result")
            return result
            
        except Exception as e:
            print(f"❌ Error in activity simulation: {str(e)}")
            print(f"🔍 Error type: {type(e).__name__}")
            print(f"🔬 Error location: {e.__traceback__.tb_frame.f_code.co_name}")
            return self._execute_with_dice(activity)

    def _execute_with_dice(self, activity):
        print("🎲 Falling back to dice roll simulation...")
        """
        Fallback execution using D20 roll
        Args:
            activity (dict): Activity details
        Returns:
            dict: Execution results
        """
        roll = random.randint(1, 20)
        success = roll >= 10  # 55% success rate
        
        result = {
            "success": success,
            "details": f"D20 Roll: {roll} ({'Success' if success else 'Failure'})"
        }
        print(f"🎲 Dice roll result: {result['details']}")
        return result
        
    def _generate_experience(self, activity, result, persona_profile):
        print("💭 Generating experience description...")
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
        print("✅ Validating generated schedule...")
        """
        Validate the generated schedule
        Args:
            schedule (dict): Generated schedule
        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(schedule, dict):
            print("❌ Schedule validation failed: Not a dictionary")
            return False
            
        required_keys = {"activity", "duration", "priority"}
        valid_priorities = {"low", "normal", "high"}
        
        for time_slot, details in schedule.items():
            try:
                datetime.strptime(time_slot, "%H:%M")
            except ValueError:
                print(f"❌ Invalid time format for slot: {time_slot}")
                return False
                
            if not isinstance(details, dict):
                print(f"❌ Invalid details format for slot: {time_slot}")
                return False
                
            if not all(key in details for key in required_keys):
                print(f"❌ Missing required keys in slot: {time_slot}")
                return False
                
            if details["priority"] not in valid_priorities:
                print(f"❌ Invalid priority in slot: {time_slot}")
                return False
        
        print("✅ Schedule validation successful")
        return True

    def generate_activity_report(self, schedule_dict, execution_results, persona):
        """Generate a detailed report of the day's activities"""
        print("📝 Generating daily activity report...")
        
        report = f"""
=================================================================
🌟 DAILY ACTIVITY REPORT - {datetime.now().strftime('%Y-%m-%d')} 🌟
=================================================================

👤 PERSONA PROFILE:
{json.dumps(persona, indent=2)}

📅 SCHEDULE OVERVIEW:
"""
        # Add schedule overview
        for time, activity in schedule_dict.items():
            report += f"\n⏰ {time}: {activity['activity']} ({activity['priority']} priority)"
        
        report += "\n\n📊 DETAILED ACTIVITY EXECUTION RESULTS:\n"
        
        # Add detailed results for each activity
        for time_slot, result in execution_results.items():
            report += f"\n{'=' * 50}"
            report += f"\n▶️ Activity at {time_slot}:\n"
            
            if isinstance(result, dict):
                if "status" in result and result["status"] == "success":
                    report += "✅ Execution Status: Successful\n"
                    
                    if "execution_result" in result:
                        execution = result["execution_result"]
                        
                        # Content information if available
                        if "content_info" in execution:
                            report += "\n📚 Content Information:\n"
                            report += f"{execution['content_info'][:500]}...\n"
                        
                        # Experience details if available
                        if "experience_details" in execution:
                            exp = execution["experience_details"]
                            report += "\n💭 Experience Details:\n"
                            
                            if "engagement_level" in exp:
                                report += f"- Engagement Level: {exp['engagement_level']}/10\n"
                            
                            if "emotional_reactions" in exp:
                                report += "- Emotional Reactions:\n"
                                for reaction in exp['emotional_reactions']:
                                    report += f"  • {reaction}\n"
                            
                            if "memorable_moments" in exp:
                                report += "- Memorable Moments:\n"
                                for moment in exp['memorable_moments']:
                                    report += f"  • {moment}\n"
                            
                            if "thoughts" in exp:
                                report += f"- Thoughts: {exp['thoughts']}\n"
                            
                            if "satisfaction_level" in exp:
                                report += f"- Satisfaction: {exp['satisfaction_level']}/10\n"
                            
                            if "platform_experience" in exp:
                                report += f"- Platform Experience: {exp['platform_experience']}\n"
                            
                            if "distractions" in exp:
                                report += "- Distractions:\n"
                                for distraction in exp['distractions']:
                                    report += f"  • {distraction}\n"
                else:
                    report += f"❌ Execution Failed: {result.get('message', 'Unknown error')}\n"
            else:
                report += "❌ Invalid result format\n"
            
            report += "\n"
        
        # Add summary statistics
        successful_activities = sum(1 for r in execution_results.values() if isinstance(r, dict) and r.get("status") == "success")
        total_activities = len(execution_results)
        
        report += f"""
📈 DAILY SUMMARY:
- Total Activities: {total_activities}
- Successful Activities: {successful_activities}
- Success Rate: {(successful_activities/total_activities)*100:.1f}%

Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
=================================================================
"""
        return report


if __name__ == "__main__":
    print("\n🌟 Testing Daily Schedule Generation and Execution 🌟")
    print("=" * 50)

    # Initialize scheduler
    scheduler = DailyScheduler()
    
    # Test persona
    persona = {
        "profile": "Hanna is an anime lover, loves to run and bubble tea. Her friend Leo is a big fan of Cyberpunk they play together."
    }

    try:
        # Generate schedule
        print("\n📋 Generating Daily Schedule...")
        schedule = scheduler.create_daily_schedule(persona, {})
        schedule_dict = json.loads(schedule)
        
        # Display generated schedule
        print("\n📅 Generated Schedule:")
        for time, activity in schedule_dict.items():
            print(f"⏰ {time}: {activity['activity']} ({activity['priority']} priority)")

        # Validate schedule
        if not scheduler.validate_schedule(schedule_dict):
            print("❌ Generated schedule is invalid!")
            exit(1)

        # Store execution results
        execution_results = {}

        # Execute each activity
        print("\n🎬 Executing Activities:")
        for time_slot, activity in schedule_dict.items():
            print(f"\n▶️ Activity at {time_slot}:")
            print(f"   {activity['activity']}")
            
            result = scheduler.execute_current_activity(
                json.dumps({time_slot: activity}),
                persona,
                datetime.strptime(time_slot, "%H:%M")
            )
            
            # Store result
            execution_results[time_slot] = result
            
            # Show execution results
            if result["status"] == "success":
                print("✅ Execution successful")
                if "execution_result" in result:
                    execution = result["execution_result"]
                    if "content_info" in execution:
                        print("\n📚 Content Information:")
                        print(f"   {execution['content_info'][:200]}...")
                    if "experience_details" in execution:
                        exp = execution["experience_details"]
                        print("\n💭 Experience Details:")
                        if "engagement_level" in exp:
                            print(f"   Engagement: {exp['engagement_level']}/10")
                        if "key_reactions" in exp:
                            print("   Key Reactions:")
                            for reaction in exp['key_reactions'][:3]:
                                print(f"   • {reaction}")
            else:
                print(f"❌ Execution failed: {result.get('message', 'Unknown error')}")

            print("-" * 30)

        # Generate and save report
        print("\n📝 Generating activity report...")
        report = scheduler.generate_activity_report(schedule_dict, execution_results, persona)
        
        # Save report to file
        report_filename = f"activity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"✅ Report saved to: {report_filename}")

    except Exception as e:
        print(f"\n⚠️ Test failed: {str(e)}")
        print(f"🔍 Error type: {type(e).__name__}")
