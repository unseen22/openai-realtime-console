import json
import os
import sys
import pathlib
from datetime import datetime

# Add parent directory to path to allow absolute imports
current_dir = pathlib.Path(__file__).parent
parent_dir = str(current_dir.parent.parent)
sys.path.append(parent_dir)

from brain.brain import Brain
from brain.memory import MemoryType 
from brain.persona_scheduler import PersonaScheduler
from brain.persona_execute_schedule import PersonaExecuteSchedule
from brain.persona_reflection import PersonaReflection
from brain.experimental.neo4j_graph import Neo4jGraph
from brain.experimental.memory_parcer import MemoryParser
from brain.embedder import Embedder
import streamlit as st
import pandas as pd
from brain.story_engine.characteristic import Characteristics

# Initialize Neo4j components with cloud instance parameters
graph = Neo4jGraph(
    uri="neo4j+s://a9277d8e.databases.neo4j.io",
    username="neo4j",
    password="tKSk2m5MwQr9w25IbSnB07KccMmTfjFtjcCsQIraczk"
)
embedder = Embedder()
parser = MemoryParser(neo4j_graph=graph)

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
try:
    # Try to load existing persona from Neo4j
    persona_brain = Brain(
        persona_id="hanna",
        neo4j_graph=graph
    )
    print("✅ Loaded existing persona from Neo4j")
except ValueError:
    # Create new persona if not found
    print("Creating new persona...")
    persona_brain = Brain(
        persona_id="hanna",
        persona_name=persona["name"],
        persona_profile=persona["profile_prompt"],
        characteristics=Characteristics(
            mind=1,
            body=2,
            heart=3,
            soul=1,
            will=1
        ),
        goals=["Learn to code", "Find out what is the newest Anime hit"],
        neo4j_graph=graph
    )
    print("✅ Created new persona in Neo4j")

# Initialize reflection instance with Neo4j components
reflection_instance = PersonaReflection(
    neo4j_graph=graph,
    embedder=embedder,
    parser=parser
)
execute_schedule = PersonaExecuteSchedule(neo4j_graph=graph)

# Get and execute the schedule
print("🎯 Getting schedule ACTIVATED...")
schedule_result, updated_persona_brain = execute_schedule.get_schedule(persona_brain)

# Generate reflection and get plans
plans = reflection_instance.reflect_on_day(updated_persona_brain)

print("⭐️ going to add to plans")
updated_persona_brain._add_to_plans(plans)

# Modify the Streamlit section
st.title("Memory Browser")

st.header(f"PERSONA: {updated_persona_brain.persona_name}")

# Get memories from Neo4j
try:
    memories = graph.get_all_memories(persona_id="hanna")
    if memories:
        # Convert Neo4j memories to DataFrame
        memories_data = []
        for memory in memories:
            try:
                memory_dict = memory['memory']
                memories_data.append({
                    'timestamp': memory_dict.get('timestamp', ''),
                    'type': memory_dict.get('type', ''),
                    'content': memory_dict.get('content', ''),
                    'importance': memory_dict.get('importance', 0.0),
                    'emotional_value': memory_dict.get('emotional_value', 0.0)
                })
            except Exception as e:
                print(f"Error processing memory: {e}")
                continue
        
        if memories_data:
            memories_df = pd.DataFrame(memories_data)
            # Sort by timestamp if available
            if 'timestamp' in memories_df.columns:
                memories_df = memories_df.sort_values('timestamp', ascending=False)
            
            st.header("Stored Memories")
            st.dataframe(memories_df)
        else:
            st.write("No valid memories found")
    else:
        st.write("No memories found in database")
except Exception as e:
    st.error(f"Error retrieving memories: {str(e)}")
    print(f"Error retrieving memories: {str(e)}")

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

# Cleanup Neo4j connection
graph.close()