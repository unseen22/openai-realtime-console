from typing import Dict, List
import json
from pathlib import Path

from brain.brain import Brain
from brain.memory import MemoryType

def create_fake_memories_for_persona(persona_id: str, brain: Brain):
    """Create some fake memories for a specific persona"""
    # Check if brain already has memories
    existing_memories = brain.get_all_memories()
    if existing_memories:
        print(f"Brain for {persona_id} already has {len(existing_memories)} memories, skipping initialization")
        return

    # Example memories based on persona type
    with open(Path(__file__).parent / "personas" / "voice_instruct.json", 'r') as f:
        personas = json.load(f)
    
    if persona_id not in personas:
        return
    
    persona = personas[persona_id]
    
    # Create some basic memories
    memories = [
        persona['profile_prompt'],
        persona['opener_prompt']
    ]
    
    # Add some interaction memories
    if "lofi_girl" in persona_id:
        memories.extend([
            "I just finished an amazing track practice!",
            "Found this awesome new lofi playlist today",
            "Sang karaoke with friends last night - did my favorite anime songs!"
        ])

    # Add some interaction memories
    if "pink_man" in persona_id:
        memories.extend([
            "I met Michael Jordan last week",
            "I rode to Miami for the biggest crypto rave ever of 2024",
            "Talked to Elon Musk about AI and moon landing conspiracy theories"
        ])
    # Add more persona-specific memories as needed
    
    print(f"Initializing {len(memories)} memories for new brain: {persona_id}")
    # Store all memories
    for memory in memories:
        brain.create_memory(content=memory, memory_type=MemoryType.EXPERIENCE)

def init_all_persona_memories():
    """Initialize fake memories for all personas"""
    try:
        print("Starting init_all_persona_memories...")
        
        # Load personas file
        personas_path = Path(__file__).parent / "personas" / "voice_instruct.json"
        print(f"Looking for personas file at: {personas_path}")
        
        if not personas_path.exists():
            raise FileNotFoundError(f"Personas file not found at {personas_path}")
            
        with open(personas_path, 'r') as f:
            personas = json.load(f)
        print(f"Loaded {len(personas)} personas from file")
        
        for persona_id in personas:
            try:
                print(f"Initializing brain for persona: {persona_id}")
                brain = Brain(persona_id=persona_id)
                create_fake_memories_for_persona(persona_id, brain)
                print(f"Successfully created memories for {persona_id}")
            except Exception as e:
                print(f"Error creating memories for persona {persona_id}: {str(e)}")
                raise
                
        print("Successfully completed init_all_persona_memories")
        
    except Exception as e:
        print(f"Error in init_all_persona_memories:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        raise

if __name__ == "__main__":
    init_all_persona_memories()