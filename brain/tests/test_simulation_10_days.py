import json
import os
import logging
from datetime import datetime, timedelta
from brain import Brain
from memory import MemoryType
from persona_scheduler import PersonaScheduler
from persona_execute_schedule import PersonaExecuteSchedule
from persona_reflection import PersonaReflection
import time
import re
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simulation.log'),
        logging.StreamHandler()
    ]
)

# API Key Management
class GroqAPIKeyManager:
    def __init__(self):
        self.api_keys = [
            "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",
            "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",
            "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"
        ]
        self.current_key_index = 0
        logging.info(f"Initialized with {len(self.api_keys)} Groq API keys")
        # Set initial API key
        os.environ['GROQ_API_KEY'] = self.get_current_key()

    def get_current_key(self):
        """Get the current API key"""
        if not self.api_keys:
            raise ValueError("No API keys available")
        return self.api_keys[self.current_key_index]

    def switch_to_next_key(self):
        """Switch to the next available API key"""
        if not self.api_keys:
            raise ValueError("No API keys available")
        
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        os.environ['GROQ_API_KEY'] = self.get_current_key()
        logging.info(f"Switched to API key {self.current_key_index + 1}")
        return self.get_current_key()

    def has_more_keys(self):
        """Check if there are more unused API keys available"""
        return len(self.api_keys) > 1

# Initialize API key manager
api_key_manager = GroqAPIKeyManager()
Brain.api_key = api_key_manager.get_current_key()  # Set initial API key in Brain class

def extract_wait_time(error_message, retry_count=0):
    """Extract wait time from Groq rate limit error message with exponential backoff"""
    base_wait_time = 300  # 5 minutes default
    try:
        match = re.search(r'try again in (\d+)m(\d+\.\d+)s', error_message)
        if match:
            minutes, seconds = match.groups()
            wait_time = int(minutes) * 60 + float(seconds)
        else:
            wait_time = base_wait_time
        
        # Apply exponential backoff
        if retry_count > 0:
            wait_time = wait_time * (2 ** retry_count)
            logging.info(f"Applied exponential backoff for retry {retry_count}, new wait time: {wait_time:.2f} seconds")
        
        return min(wait_time, 3600)  # Cap at 1 hour
    except Exception as e:
        logging.error(f"Error parsing wait time: {str(e)}")
        return base_wait_time * (2 ** retry_count)

def handle_api_error(error_msg, day_retries, day, current_activity="unknown", max_retries=3):
    """Handle API errors including rate limits and service unavailable"""
    retry_count = day_retries.get(day, 0)
    
    # Check if this is a rate limit error
    if "rate limit" in error_msg.lower():
        # Try switching to next API key first
        if api_key_manager.has_more_keys():
            try:
                new_key = api_key_manager.switch_to_next_key()
                logging.info(f"Switched to API key {api_key_manager.current_key_index + 1} after rate limit during {current_activity}")
                # Update the API key in the environment
                os.environ['GROQ_API_KEY'] = new_key
                # Update API key in Brain class
                Brain.api_key = new_key
                return False  # Continue with new key immediately
            except Exception as e:
                logging.error(f"Error switching API key: {str(e)}")
    
    # Check if this is a service unavailable error
    elif "503" in error_msg or "service unavailable" in error_msg.lower():
        wait_time = 5 * (2 ** retry_count)  # Start with 5 seconds, double each retry
        logging.warning(f"""
Service Unavailable:
- Activity: {current_activity}
- Retry count: {retry_count + 1}/{max_retries}
- Wait time: {wait_time:.2f} seconds
- Current API key: {api_key_manager.current_key_index + 1}
- Error: {error_msg}
""")
        try:
            time.sleep(wait_time)
            return False  # Try again after waiting
        except KeyboardInterrupt:
            logging.info("\nUser interrupted wait time. Saving partial results...")
            return True
    
    # If we've hit max retries
    if retry_count >= max_retries:
        logging.warning(f"Maximum retries ({max_retries}) reached for day {day + 1} during {current_activity}")
        return True
    
    # For other errors or if we need to wait
    wait_time = extract_wait_time(error_msg, retry_count)
    
    logging.warning(f"""
API Error:
- Activity: {current_activity}
- Retry count: {retry_count + 1}/{max_retries}
- Wait time: {wait_time:.2f} seconds
- Current API key: {api_key_manager.current_key_index + 1}
- Error: {error_msg}
""")
    
    try:
        time.sleep(wait_time)
    except KeyboardInterrupt:
        logging.info("\nUser interrupted wait time. Saving partial results...")
        return True
    
    day_retries[day] = retry_count + 1
    return False

def save_partial_results(results, current_date, error_info):
    """Save partial results in case of failure"""
    partial_file = f"partial_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        # Convert results to JSON-serializable format
        serializable_results = []
        for day_result in results:
            serializable_day = {
                "date": day_result.get("date"),
                "schedule": day_result.get("schedule"),
                "reflection": day_result.get("reflection"),
                "retries": day_result.get("retries", 0)
            }
            # Remove any non-serializable objects
            if "persona" in serializable_day.get("schedule", {}):
                del serializable_day["schedule"]["persona"]
            serializable_results.append(serializable_day)
            
        with open(partial_file, 'w', encoding='utf-8') as f:
            json.dump({
                "last_date": current_date.strftime("%Y-%m-%d"),
                "error": str(error_info),
                "results": serializable_results
            }, f, indent=2)
        logging.info(f"Saved partial results to {partial_file}")
    except Exception as e:
        logging.error(f"Error saving partial results: {str(e)}")

def run_simulation(start_date, num_days=10, max_retries=3, base_wait_time=300):
    logging.info(f"Starting {num_days}-day Simulation from {start_date}")
    logging.info("=" * 50)

    # Initialize components
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

    # Initialize brain state file path
    brain_state_file = "hanna_brain_state.json"
    simulation_results = []
    current_date = start_date
    day_retries = {}  # Track retries per day
    last_api_call = datetime.now()  # Track time of last API call
    min_api_interval = 5  # Minimum seconds between API calls
    jitter = lambda: random.uniform(0.5, 2.0)  # Random delay multiplier

    try:
        for day in range(num_days):
            if day in day_retries and day_retries[day] >= max_retries:
                logging.warning(f"Maximum retries ({max_retries}) reached for day {day + 1}, skipping to next day")
                current_date += timedelta(days=1)
                continue

            logging.info(f"\nDay {day + 1}: {current_date.strftime('%Y-%m-%d')}")
            logging.info("-" * 30)

            try:
                # Initialize or load brain state
                if os.path.exists(brain_state_file):
                    with open(brain_state_file, 'r') as f:
                        saved_state = json.load(f)
                    persona_brain = Brain(
                        persona_id="hanna",
                        persona_name=persona["name"],
                        persona_profile=persona["profile_prompt"],
                        db_path="test_memories.db"
                    )
                    persona_brain.mood = saved_state.get('mood', 'neutral')
                    persona_brain.status = saved_state.get('status', 'active')
                    persona_brain.plans = saved_state.get('plans', [])
                else:
                    persona_brain = Brain(
                        persona_id="hanna",
                        persona_name=persona["name"],
                        persona_profile=persona["profile_prompt"],
                        db_path="test_memories.db"
                    )

                # Initialize components for the day
                reflection_instance = PersonaReflection()
                execute_schedule = PersonaExecuteSchedule()

                # Add delay if needed between API calls
                time_since_last_call = (datetime.now() - last_api_call).total_seconds()
                if time_since_last_call < min_api_interval:
                    sleep_time = (min_api_interval - time_since_last_call) * jitter()
                    logging.info(f"Waiting {sleep_time:.2f} seconds before next API call")
                    try:
                        time.sleep(sleep_time)
                    except KeyboardInterrupt:
                        logging.info("\nUser interrupted wait time. Saving partial results...")
                        raise

                # Get and execute the schedule
                logging.info("Generating schedule...")
                schedule_result = execute_schedule.get_schedule(persona_brain)
                last_api_call = datetime.now()
                
                if isinstance(schedule_result, dict) and "error" in schedule_result:
                    error_msg = str(schedule_result['error'])
                    logging.error(f"Error in schedule generation: {error_msg}")
                    
                    if handle_api_error(error_msg, day_retries, day, "schedule generation", max_retries):
                        continue
                    # Try again immediately with new key or after waiting
                    schedule_result = execute_schedule.get_schedule(persona_brain)
                    
                persona_brain = schedule_result.get("persona", persona_brain)
                logging.info("Schedule generated successfully")

                # Add delay if needed between API calls
                time_since_last_call = (datetime.now() - last_api_call).total_seconds()
                if time_since_last_call < min_api_interval:
                    sleep_time = (min_api_interval - time_since_last_call) * jitter()
                    logging.info(f"Waiting {sleep_time:.2f} seconds before next API call")
                    try:
                        time.sleep(sleep_time)
                    except KeyboardInterrupt:
                        logging.info("\nUser interrupted wait time. Saving partial results...")
                        raise

                # Perform reflection
                logging.info("Performing daily reflection...")
                reflection_result = reflection_instance.reflect_on_day(persona_brain, schedule_result.get("results", []))
                last_api_call = datetime.now()
                
                if isinstance(reflection_result, dict) and "error" in reflection_result:
                    error_msg = str(reflection_result['error'])
                    logging.error(f"Error in reflection: {error_msg}")
                    
                    if handle_api_error(error_msg, day_retries, day, "reflection", max_retries):
                        continue
                    # Try again immediately with new key or after waiting
                    reflection_result = reflection_instance.reflect_on_day(persona_brain, schedule_result.get("results", []))

                persona_brain.create_memory(reflection_result, MemoryType.REFLECTION)
                persona_brain._add_to_plans(reflection_result["plans"])
                logging.info("Reflection completed successfully")

                # Save brain state
                try:
                    with open(brain_state_file, 'w') as f:
                        json.dump({
                            'mood': persona_brain.mood,
                            'status': persona_brain.status,
                            'plans': persona_brain.plans
                        }, f)
                    logging.info("Brain state saved successfully")
                except Exception as e:
                    logging.error(f"Error saving brain state: {str(e)}")
                    save_partial_results(simulation_results, current_date, e)

                # Store day's results
                day_result = {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "schedule": schedule_result,
                    "reflection": reflection_result,
                    "retries": day_retries.get(day, 0)
                }
                simulation_results.append(day_result)

                # Save day's results to a file (with proper encoding)
                results_file = f"activity_report_{current_date.strftime('%Y%m%d')}.txt"
                try:
                    with open(results_file, 'w', encoding='utf-8') as f:
                        # Header
                        f.write("=" * 80 + "\n")
                        f.write(f"DAILY ACTIVITY REPORT - {current_date.strftime('%Y-%m-%d')}\n")
                        f.write("=" * 80 + "\n\n")
                        
                        # Persona Profile Summary
                        f.write("PERSONA PROFILE SUMMARY:\n")
                        f.write("-" * 20 + "\n")
                        f.write(f"Name: {persona['name']}\n")
                        f.write("Core Traits: High energy, authentic, creative, physically expressive\n")
                        f.write("Current Status: " + persona_brain.status + "\n")
                        f.write("Current Mood: " + persona_brain.mood + "\n\n")
                        
                        # Schedule
                        f.write("TODAY'S SCHEDULE:\n")
                        f.write("-" * 20 + "\n")
                        if isinstance(schedule_result, dict) and "schedule" in schedule_result:
                            for activity in schedule_result["schedule"]:
                                f.write(f"{activity.get('time', 'N/A')}: {activity.get('activity', 'Unknown activity')}\n")
                        f.write("\n")
                        
                        # Reflection
                        f.write("DAY'S REFLECTION:\n")
                        f.write("-" * 20 + "\n")
                        if isinstance(reflection_result, dict):
                            if "diary_entry" in reflection_result:
                                f.write("Diary Entry:\n")
                                f.write(reflection_result["diary_entry"] + "\n\n")
                            if "plans" in reflection_result:
                                f.write("Future Plans:\n")
                                for plan in reflection_result["plans"]:
                                    f.write(f"- {plan}\n")
                        f.write("\n")
                        
                        # Statistics
                        f.write("SIMULATION STATISTICS:\n")
                        f.write("-" * 20 + "\n")
                        f.write(f"API Retries Today: {day_retries.get(day, 0)}\n")
                        f.write(f"Current Memory Count: {len(persona_brain.memories)}\n")
                        f.write(f"Current Plan Count: {len(persona_brain.plans)}\n")
                        f.write(f"Current API Key: {api_key_manager.current_key_index + 1}\n")
                        
                        # Footer
                        f.write("\n" + "=" * 80 + "\n")
                        f.write(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("=" * 80 + "\n")
                    
                    logging.info(f"Activity report saved to {results_file}")
                except Exception as e:
                    logging.error(f"Error saving activity report: {str(e)}")
                    save_partial_results(simulation_results, current_date, e)

                # Reset retry count and move to next day
                day_retries[day] = 0
                current_date += timedelta(days=1)
                logging.info(f"Completed day {day + 1}")

            except KeyboardInterrupt:
                logging.info("\nUser interrupted simulation. Saving partial results...")
                save_partial_results(simulation_results, current_date, "User interrupted simulation")
                raise
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Error during simulation: {error_msg}")
                
                if "rate_limit" in error_msg.lower():
                    if handle_api_error(error_msg, day_retries, day, "unknown activity", max_retries):
                        continue
                else:
                    logging.info("Continuing to next day...")
                    save_partial_results(simulation_results, current_date, e)
                    current_date += timedelta(days=1)

    except KeyboardInterrupt:
        logging.info("\nSimulation interrupted by user")
        return simulation_results
    except Exception as e:
        logging.error(f"Fatal error in simulation: {str(e)}")
        return simulation_results

    return simulation_results

if __name__ == "__main__":
    try:
        # Start simulation from today
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        results = run_simulation(start_date)
        
        if results:
            # Save final results
            final_results_file = f"simulation_results_{start_date.strftime('%Y%m%d')}.json"
            with open(final_results_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": (start_date + timedelta(days=len(results)-1)).strftime("%Y-%m-%d"),
                    "total_days": len(results),
                    "results": results
                }, f, indent=2)
            
            logging.info("\nSimulation Complete!")
            logging.info(f"Generated {len(results)} days of activity reports.")
            logging.info(f"Final results saved to {final_results_file}")
    except KeyboardInterrupt:
        logging.info("\nProgram terminated by user")
    except Exception as e:
        logging.error(f"Fatal error in simulation: {str(e)}")
        if 'results' in locals():
            save_partial_results(results, start_date + timedelta(days=len(results)), e) 