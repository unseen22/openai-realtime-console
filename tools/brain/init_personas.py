import json
from pathlib import Path
import numpy as np
from brain.brain import Brain
from brain.memory import Memory, MemoryType
from brain.embedder import Embedder

def verify_vector(vector: list) -> bool:
    """Verify that the vector is not all zeros and has proper values"""
    if not vector:
        return False
    # Convert to numpy array for easier checking
    vec_array = np.array(vector)
    # Check if vector is all zeros or very close to zero
    if np.allclose(vec_array, 0, atol=1e-10):
        return False
    # Check if we have the expected dimension (1024 for BGE-large-en-v1.5)
    if len(vector) != 1024:
        return False
    return True

def init_persona_brains():
    """Initialize brains for all personas in voice_instruct.json"""
    # Initialize embedder
    embedder = Embedder()
    
    # Read persona definitions
    persona_file = Path(__file__).parent / "personas" / "voice_instruct.json"
    with open(persona_file, 'r') as f:
        personas = json.load(f)
    
    print("Starting persona initialization...")
    
    # Initialize brain for each persona
    for persona_id, persona_data in personas.items():
        print(f"\nInitializing persona: {persona_id}")
        brain = Brain(persona_id=persona_id)
        
        # Get the profile prompt
        profile_prompt = persona_data["profile_prompt"]
        print(f"Profile prompt: {profile_prompt[:100]}...")  # Print first 100 chars
        
        # Create embedding directly using embedder
        vector = embedder.embed_memory(profile_prompt)
        
        # Verify vector
        if not verify_vector(vector):
            print(f"WARNING: Invalid vector generated for {persona_id}")
            print(f"Vector stats: length={len(vector)}, sum={sum(vector)}, non_zero={np.count_nonzero(vector)}")
            continue
        
        print(f"Generated valid vector: length={len(vector)}, non_zero_elements={np.count_nonzero(vector)}")
        
        # Create memory with verified vector
        memory = Memory(
            content=profile_prompt,
            vector=vector,
            importance=1.0,  # Profile memories are important
            memory_type=MemoryType.PROFILE,
            timestamp=None  # Let Memory class handle timestamp
        )
        
        # Store memory directly
        brain.memories[memory.timestamp.isoformat()] = memory
        brain.db.store_memory(brain.persona_id, memory)
        
        # Set initial mood and status
        brain.set_mood("neutral")
        brain.set_status("active")
        
        print(f"Successfully initialized brain for persona: {persona_id}")

if __name__ == "__main__":
    init_persona_brains() 