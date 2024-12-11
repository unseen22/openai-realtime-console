from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
from brain.brain import Brain
from brain.fake_memories import get_fake_memories

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Brain
brain = Brain(persona_id="default")

class MemoryItem(BaseModel):
    key: str
    value: str

class FunctionCall(BaseModel):
    function_name: str
    arguments: Dict[str, Any]

@app.get("/")
async def read_root():
    return {"status": "alive"}

@app.get("/memories")
async def get_memories():
    """Get all stored memories"""
    try:
        return brain.get_all_memories()
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
async def get_memories_endpoint():
    """Get fake memories"""
    memories = get_fake_memories()
    return {"memories": memories}
