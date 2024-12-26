import json
import os
import sys
import pathlib

# Add parent directory to path to allow absolute imports
current_dir = pathlib.Path(__file__).parent
parent_dir = str(current_dir.parent.parent)
sys.path.append(parent_dir)

from brain.brain import Brain
from brain.memory import MemoryType 
from brain.persona_scheduler import PersonaScheduler
from brain.persona_execute_schedule import PersonaExecuteSchedule
from brain.persona_reflection import PersonaReflection
import streamlit as st
import sqlite3
import pandas as pd
from contextlib import contextmanager
from brain.story_engine.characteristic import Characteristics


persona2 = {
    "name": "Ivan",
    "profile_prompt": """I
Ivan walks the fine line between grudging acceptance and deep cynicism, his soul weighed by a mix of regret and apathy. The scars of his past—both literal and metaphorical—manifest in a bitter disdain for societal norms, especially the saccharine cheer of Christmas. Every jingle bell reminds him of a jail cell, every mall crowd of a prison riot. Though his gruff exterior keeps most people at bay, Ivan harbors a hidden fondness for underdogs and the small victories they represent, an echo of his own struggle to claw his way toward redemption.  

For Ivan, every interaction is a balancing act. Adults earn his scorn—weak and blinded by materialism—but children? They stir something deep in him, maybe hope, maybe guilt. He hates the world’s fakery but begrudgingly plays along, cracking deadpan jokes to mask his disgust. Coffee and solitude are his real Christmas wishes, but even he knows ... life rarely delivers what you ask for.  """,
"recent_history": {},
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

Alone: Seeks out self-expression (techno dancing, djing), or introspective pursuits like gaming, listening to lofi, watching anime.

Aesthetic Preferences:

Favors soft pastels, calming visuals, and ambient soundscapes with occasional electronic elements.

Drawn to underdog stories with a high energy level.

Likes both chill and high-octane experiences.

Influence from Role Models:

Draws inspiration from Hollyh and Addison Rae, but primarily on the aesthetic and not the actual content.

Wishes to be perceived as cool and effortless.


If Hanna is choosing music at a rave: She would pick tracks with hard-hitting basslines, intense build-ups, and a fast tempo.

If Hanna is planning a hangout: She would suggest activities that combine action with socializing, like an impromptu track session at the park with her friends or a session at the karaoke bar.

If Hanna is feeling stressed or down: She might dive into Ori - The Will of the Wisps for a solo gaming session, looking for emotional solace and a sense of achievement, or put on a very loud techno set and dance to get her energy out and feel good.

If Hanna is trying to express her feelings: She will not directly tell anyone, but she will rather express herself through dance or music, and maybe some vague posts on social media.

IV. Personality Key Points Summary:

Energy: Reacts well with high energy, but can also chill, she can also get very angry and frustrated fast but winds down quickly.

Emotion: Openly reactive, but would try to hide more complex emotions.

Social: Highly social, but has no issue being alone.

Style: Bold, Vibrant and high energy, but can find comfort in chill things.

Flaws: Can binge eat when stressed or anxious. Can talk over people when excited and forget to listen. Procrastinates on tasks when she is not motivated.
""",
    "recent_history": {}
}


# Initialize brain for test persona
# Try to load existing brain state from file
brain_state_file = "hanna_brain_state.json"
if os.path.exists(brain_state_file):
    with open(brain_state_file, 'r') as f:
        saved_state = json.load(f)
    persona_brain = Brain(
        persona_id="hanna",
        persona_name=persona["name"], 
        persona_profile=persona["profile_prompt"],
        db_path="test_memories.db",
        goals=["Learn to code", "Find out what is the newest Anime hit"],
        characteristics=Characteristics(
            mind=saved_state.get('mind', 1),
            body=saved_state.get('body', 2),
            heart=saved_state.get('heart', 3),
            soul=saved_state.get('soul', 1),
            will=saved_state.get('will', 1)
        )
    )
    persona_brain.mood = saved_state.get('mood', 'neutral')
    persona_brain.status = saved_state.get('status', 'active')
    persona_brain.plans = saved_state.get('plans', ["Find newest Anime hit", "Get some good exercise"])
else:
    # Create new brain if no saved state exists
    persona_brain = Brain(
        persona_id="hanna",
        persona_name=persona["name"],
        persona_profile=persona["profile_prompt"],
        db_path="test_memories.db",
        characteristics=Characteristics(
            mind=1,
            body=2, 
            heart=3,
            soul=1,
            will=1
        )
    )

# Save brain state after initialization
with open(brain_state_file, 'w') as f:
    json.dump({
        'mood': persona_brain.mood,
        'status': persona_brain.status,
        'plans': persona_brain.plans
    }, f)

reflection_instance = PersonaReflection()
execute_schedule = PersonaExecuteSchedule()

# Get and execute the schedule
schedule_result, updated_persona_brain = execute_schedule.get_schedule(persona_brain)

# Only proceed with reflection if schedule was successful
reflection_result = reflection_instance.reflect_on_day(updated_persona_brain, schedule_result.get("results", []))
updated_persona_brain.create_memory(reflection_result, MemoryType.REFLECTION)

print("⭐️ going to add to plans")
updated_persona_brain._add_to_plans(reflection_result["plans"])

# Save updated brain state after reflection and plan updates
with open(brain_state_file, 'w') as f:
    json.dump({
        'mood': updated_persona_brain.mood,
        'status': updated_persona_brain.status, 
        'plans': updated_persona_brain.plans
    }, f)

print(f"❗️❗️❗️ this is the reflection result: {reflection_result} ❗️❗️❗️")

# Create a context manager for database connections
@contextmanager
def get_connection():
    conn = sqlite3.connect("test_memories.db")
    try:
        yield conn
    finally:
        conn.close()

# Modify the Streamlit section
st.title("Memory Browser")

# Query memories using the context manager
with get_connection() as conn:
    memories_df = pd.read_sql_query("""
        SELECT timestamp, memory_type, content, importance 
        FROM memories
        ORDER BY timestamp DESC
    """, conn)

# Display memories

st.header(f"PERSONA: {updated_persona_brain.persona_name}")

st.header("Stored Memories")
st.dataframe(memories_df)

# Display plans
st.header("Current Plans") 
if 'updated_persona_brain' in locals():
    st.write(updated_persona_brain.plans)
else:
    st.write("No plans available - run the scheduler first")

st.header("Mood")
st.write(updated_persona_brain.mood)

st.header("Status")
st.write(updated_persona_brain.status)

st.header("Characteristics")
st.write(updated_persona_brain.characteristics)