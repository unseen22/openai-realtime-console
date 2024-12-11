import json
from brain.brain import Brain
from brain.database import Database
from brain.memory import MemoryType

def init_voice_personas():
    # Initialize database
    db = Database("voice_memories.db")
    
    # Load voice instruction personas data
    with open("brain/personas/voice_instruct.json", "r") as f:
        personas_data = json.load(f)
    
    personas = {}
    
    # Initialize each persona
    for persona_id, persona_data in personas_data.items():
        # Add persona to database
        db.add_persona(
            persona_id=persona_id,
            name=persona_data.get("name", "Unknown"),
            voice_model=persona_data.get("voice_model", "default")
        )
        
        # Create brain instance for this persona
        brain = Brain(persona_id, "voice_memories.db")
        
        # Add initial memories from the persona data
        # Store profile prompt as a memory
        if "profile_prompt" in persona_data:
            brain.create_memory(
                persona_data["profile_prompt"],
                MemoryType.SUMMARY
            )
        
        # Store opener prompt as a memory
        if "opener_prompt" in persona_data:
            brain.create_memory(
                persona_data["opener_prompt"],
                MemoryType.OPENER
            )
            
        personas[persona_id] = brain
        print(f"Initialized {persona_id} with {len(brain.get_all_memories())} memories")
    
    return personas

if __name__ == "__main__":
    personas = init_voice_personas()
    
    # Test retrieving memories for each persona
    for persona_id, brain in personas.items():
        print(f"\nMemories for {persona_id}:")
        memories = brain.get_all_memories()
        for memory in memories:
            print(f"- [{memory.memory_type.value}] {memory.content[:100]}...") 