from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import os
from pathlib import Path
from datetime import datetime

from brain.brain import Brain
from brain.memory import Memory, MemoryType
from brain.fake_memories import create_fake_memories_for_persona, init_all_persona_memories
from brain.init_personas import init_persona_brains

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize brains for all personas
init_persona_brains()

# After app initialization, add brain registry
brain_registry: Dict[str, Brain] = {}

# Add this near the top of your file, after creating the FastAPI app
app.mount("/static", StaticFiles(directory="public"), name="static")
app.mount("/static/personas", StaticFiles(directory="brain/personas"), name="personas")

class MemoryItem(BaseModel):
    key: str
    value: str

class FunctionCall(BaseModel):
    function_name: str
    arguments: Dict[str, Any]

class ConversationItem(BaseModel):
    speaker: str
    content: str
    timestamp: Optional[str] = None

class MemoryCreate(BaseModel):
    content: str
    memory_type: str = "CONVERSATION"
    importance: float = 0.5

class MemoryResponse(BaseModel):
    content: str
    timestamp: datetime
    importance: float
    similarity: Optional[float] = None

class SearchResponse(BaseModel):
    memories: List[MemoryResponse]

@app.get("/")
async def read_root():
    return {"status": "alive"}

@app.get("/memories")
async def get_memories(persona_id: str = Query("default")):
    """Get all stored memories for a specific persona"""
    try:
        if persona_id not in brain_registry:
            brain_registry[persona_id] = Brain(persona_id=persona_id)
        return brain_registry[persona_id].get_all_memories()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/{key}")
async def get_memory(key: str):
    """Get a specific memory by key"""
    try:
        memory = brain.get_memory(key)
        if memory is None:
            raise HTTPException(status_code=404, detail="Memory not found")
        return memory
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory")
async def set_memory(memory_item: MemoryItem):
    """Store a new memory"""
    try:
        brain.set_memory(memory_item.key, memory_item.value)
        return {"status": "success", "message": f"Memory stored for key: {memory_item.key}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/function")
async def call_function(function_call: FunctionCall):
    """Execute a brain function"""
    try:
        result = brain.execute_function(
            function_call.function_name, 
            function_call.arguments
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fake-memories")
async def get_memories_endpoint(persona_id: str = Query("default")):
    """Get fake memories for a specific persona"""
    try:
        if persona_id not in brain_registry:
            brain_registry[persona_id] = Brain(persona_id=persona_id)
        
        brain = brain_registry[persona_id]
        
        # Clear existing memories before creating new ones
        brain.clear_memories()
        
        # Create and store fake memories
        create_fake_memories_for_persona(persona_id, brain)
        
        # Get all memories and concatenate their content
        memories = brain.get_all_memories()
        concatenated_memories = "\n".join(memory.content for memory in memories)
        print(f"Initialized memories for persona {persona_id}:", concatenated_memories)
        
        return {
            "status": "success",
            "persona_id": persona_id,
            "memories": concatenated_memories
        }   
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversation")
async def save_conversation(conversation: ConversationItem):
    """Save a conversation transcript as a memory"""
    try:
        # Only save assistant responses as memories
        if conversation.speaker == "assistant":
            memory = Memory.create(
                content=conversation.content,
                memory_type=MemoryType.CONVERSATION
            )
            return {"status": "success", "memory_id": str(memory.timestamp)}
        return {"status": "skipped", "message": "Only assistant messages are saved as memories"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/persona/{persona_id}")
async def get_persona_brain(persona_id: str):
    """Get or create a brain for specific persona"""
    try:
        if persona_id not in brain_registry:
            brain_registry[persona_id] = Brain(persona_id=persona_id)
        
        persona_brain = brain_registry[persona_id]
        
        return {
            "status": "success",
            "persona_id": persona_id,
            "mood": persona_brain.get_mood(),
            "status": persona_brain.get_status(),
            "memory_count": len(persona_brain.get_all_memories()),
            "memories": persona_brain.get_all_memories()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/init-all-personas")
async def init_all_personas():
    """Initialize memories for all personas"""
    try:
        print("Starting persona initialization...")
        
        # Clear existing brains first
        brain_registry.clear()
        print("Cleared brain registry")
        
        # Initialize all personas
        try:
            from brain.fake_memories import init_all_persona_memories
            init_all_persona_memories()
            print("FAKE MEMORIES INITIALIZED")
            
            # Add initialized brains to registry
            personas_path = Path(__file__).parent / "personas" / "voice_instruct.json"
            with open(personas_path, 'r') as f:
                personas = json.load(f)
                print("PERSONAS:", personas)
            
            for persona_id in personas:
                brain_registry[persona_id] = Brain(persona_id=persona_id)
            
            print("Successfully initialized all personas")
            print(f"Brain registry size: {len(brain_registry)}")
            
            # Return more detailed response
            return {
                "status": "success",
                "message": "All persona memories initialized",
                "brain_registry_size": len(brain_registry),
                "initialized_personas": list(brain_registry.keys())
            }
            
        except FileNotFoundError as e:
            print(f"Personas file not found: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Personas file not found: {str(e)}"
            )
        except Exception as init_error:
            print(f"Error during initialization: {str(init_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Initialization error: {str(init_error)}"
            )
            
    except Exception as e:
        print(f"Error in init_all_personas endpoint:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to initialize personas: {str(e)}"
        )

@app.post("/memory/{persona_id}")
async def store_persona_memory(persona_id: str, memory: dict):
    """Store a memory in a specific persona's brain"""
    try:
        if persona_id not in brain_registry:
            raise HTTPException(
                status_code=404,
                detail=f"Persona '{persona_id}' not found in brain registry"
            )

        brain = brain_registry[persona_id]
        content = memory.get("content")
        importance = memory.get("importance", 0.0)
        memory_type_str = memory.get("memory_type", "conversation")

        if not content:
            raise HTTPException(
                status_code=400,
                detail="'content' is required in memory object"
            )

        try:
            memory_type = MemoryType(memory_type_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid memory_type: {memory_type_str}"
            )

        memory_obj = brain.create_memory(
            content=content,
            memory_type=memory_type
        )

        return {
            "status": "success",
            "message": f"Memory stored for persona '{persona_id}'",
            "memory": memory_obj.to_dict()
        }

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        print(f"Error storing memory for persona '{persona_id}':")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store memory: {str(e)}"
        )

@app.delete("/memories/{persona_id}")
async def delete_all_memories(persona_id: str):
    """Delete all memories for a specific persona"""
    try:
        if persona_id not in brain_registry:
            raise HTTPException(
                status_code=404,
                detail=f"Persona '{persona_id}' not found"
            )
        
        brain = brain_registry[persona_id]
        brain.clear_memories()
        
        return {
            "status": "success",
            "message": f"All memories deleted for persona '{persona_id}'"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/memory/{persona_id}/{memory_id}")
async def delete_memory(persona_id: str, memory_id: str):
    """Delete a specific memory from a persona"""
    try:
        if persona_id not in brain_registry:
            raise HTTPException(
                status_code=404,
                detail=f"Persona '{persona_id}' not found"
            )
        
        brain = brain_registry[persona_id]
        if memory_id not in brain.memories:
            raise HTTPException(
                status_code=404,
                detail=f"Memory '{memory_id}' not found"
            )
        
        del brain.memories[memory_id]
        brain.db.delete_memory(persona_id, memory_id)
        
        return {
            "status": "success",
            "message": f"Memory '{memory_id}' deleted from persona '{persona_id}'"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memories/search")
async def search_memories(query: str, persona_id: str = "default", top_k: int = 3) -> SearchResponse:
    """Search for similar memories for a specific persona"""
    try:
        print(f"\nSearching memories for persona '{persona_id}' with query: {query}")
        
        if not persona_id:
            raise HTTPException(status_code=400, detail="persona_id is required")
            
        brain = Brain(persona_id)
        
        # Get all memories first to check if we have any
        all_memories = brain.get_all_memories()
        print(f"Total memories found for persona '{persona_id}': {len(all_memories)}")
        
        if not all_memories:
            print(f"No memories found for persona '{persona_id}'")
            return SearchResponse(memories=[])
        
        # Search for similar memories
        similar_memories = brain.search_similar_memories(query, top_k)
        print(f"Found {len(similar_memories)} similar memories")
        
        # Convert to response format
        memory_responses = []
        for memory, similarity in similar_memories:
            print(f"Memory: {memory.content[:100]}... (similarity: {similarity:.4f})")
            memory_responses.append(
                MemoryResponse(
                    content=memory.content,
                    timestamp=memory.timestamp,
                    importance=memory.importance,
                    similarity=similarity
                )
            )
        
        return SearchResponse(memories=memory_responses)
    except Exception as e:
        print(f"Error in search_memories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
