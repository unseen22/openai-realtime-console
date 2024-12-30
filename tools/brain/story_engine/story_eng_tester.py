import sys
import pathlib
import json

# Add the root directory to Python path
root_dir = str(pathlib.Path(__file__).parent.parent.parent)
sys.path.append(root_dir)

from brain.brain import Brain
from brain.story_engine.roller import StoryRoller
from brain.story_engine.characteristic import Characteristics

profile_prompt = """Hanna's Action-Oriented Personality Profile
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

Style: Bold, Vibrant and high energy, but can find comfort in chill things."""

class StoryEngineTester:
    def __init__(self, persona_id: str = "test_persona"):
        """Initialize the story engine tester with a test persona"""
        print("🔧 Initializing StoryEngineTester...")
        self.persona_id = persona_id
        self.persona_name = "Hanna"
        self.persona_profile = profile_prompt
        
        print(f"👤 Creating test persona: {self.persona_name}")
        # Initialize brain with test persona
        self.brain = Brain(
            persona_id=self.persona_id,
            persona_name=self.persona_name,
            persona_profile=self.persona_profile,
            db_path="test_memories.db",
            characteristics=Characteristics(
                mind=1,
                body=2, 
                heart=3,
                soul=4,
                will=5
            )
        )
        print("🧠 Brain initialized with test characteristics")
        
        # Initialize story roller with brain's characteristics
        self.roller = StoryRoller(self.brain)
        print("🎲 Story roller initialized")
        print("✅ StoryEngineTester setup complete")
        
    def test_task(self, task: str) -> dict:
        """Test a specific task and return the outcome with details"""
        print(f"\n🎲 Testing task: {task}")
        
    
        print("🎯 Rolling for outcome...")
        success = self.roller.roll_for_outcome(task)
        print(f"{'✅ Task succeeded!' if success else '❌ Task failed!'}")

        return {
            "task": task,
            "success": success
        }
            

            # Create a memory of the attempt
            
        
    def run_test_suite(self, tasks: list[str]) -> list[dict]:
        """Run a series of tests with different tasks"""
        print("\n🚀 Running test suite...")
        print(f"📋 Total tasks to test: {len(tasks)}")
        results = []
        
        for i, task in enumerate(tasks, 1):
            print(f"\n📌 Testing task {i}/{len(tasks)}")
            result = self.test_task(task)
            results.append(result)
            print(f"✨ Task {i} complete")
            
        print("\n🏁 Test suite completed!")
        return results

if __name__ == "__main__":
    print("\n🔬 Starting StoryEngineTester main execution")
    
    # Create test engine
    print("🛠️ Creating test engine...")
    tester = StoryEngineTester()
    
    # Define test tasks
    print("📝 Defining test tasks...")
    test_tasks = [
        "Research quantum computing basics",
        "Do 50 pushups",
        "Write a poem about AI",
        "Meditate for an hour",
        "Debug a complex code problem",
        "Tie your shoes",
        "Cycle 100km",
        "Get a new girlfriend"
        "Find a new hobby",
        "Hunt a dear",
        "Find a new job",
    ]
    
    # Run tests
    print("🏃 Running tests...")
    results = tester.run_test_suite(test_tasks)
    
    # Print results
    print("\n📊 Test Results:")
    for result in results:
        print(f"\n📎 Task: {result['task']}")
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            outcome_map = {
                "super_success": "✨ Super Success!",
                "success": "✅ Success!",
                "failure": "❌ Failure!",
                "super_failure": "💥 Super Failure!"
            }
            print(f"Outcome: {outcome_map[result['success']]}")