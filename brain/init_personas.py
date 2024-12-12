import json
from pathlib import Path
from brain import Brain
from memory import Memory, MemoryType

def init_persona_brains():
    """Initialize brains for all personas in voice_instruct.json"""
    # Read persona definitions
    persona_file = Path(__file__).parent / "personas" / "voice_instruct.json"
    with open(persona_file, 'r') as f:
        personas = json.load(f)
    
    # Initialize brain for each persona
    for persona_id, persona_data in personas.items():
        brain = Brain(persona_id=persona_id)
        
        # Create initial memory with persona profile
        brain.create_memory(
            content=persona_data["profile_prompt"],
            memory_type=MemoryType.PROFILE
        )
        
        # Set initial mood and status
        brain.set_mood("neutral")
        brain.set_status("active")
        
        print(f"Initialized brain for persona: {persona_id}")

if __name__ == "__main__":
    init_persona_brains() 