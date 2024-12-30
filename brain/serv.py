from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import os
from pathlib import Path
from datetime import datetime
import tempfile

from brain.experimental.neo4j_graph import Neo4jGraph
from brain.experimental.memory_parcer import MemoryParser
from brain.transcription import TranscriptionHandler

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

print("\n=== Starting FastAPI Server ===")
print("Configuring CORS...")

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("CORS configured")

# Initialize Neo4j connection
print("Initializing Neo4j connection...")
neo4j_graph = Neo4jGraph(
    username=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD"),
    uri=os.getenv("NEO4J_URI")
)
parcer = MemoryParser(neo4j_graph)

print("Neo4j connection initialized")

# Initialize transcription handler
print("Initializing transcription handler...")
transcription_handler = TranscriptionHandler()
print("Transcription handler initialized")

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    print("\nServer startup:")
    
    # Initialize memory parser
    await parcer.initialize()
    print("✓ Memory parser initialized")
    
    # Print available routes
    print("\nAvailable routes:")
    for route in app.routes:
        if hasattr(route, "methods") and route.path != "/openapi.json":
            methods = ", ".join(route.methods)
            print(f"  {methods:<10} {route.path}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("\nServer shutdown:")
    
    # Close Neo4j connection
    if neo4j_graph:
        neo4j_graph.close()
        print("✓ Neo4j connection closed")
    
    # Close any other resources
    if transcription_handler:
        await transcription_handler.close()
        print("✓ Transcription handler closed")

# Add static file serving
app.mount("/static", StaticFiles(directory="public"), name="static")
app.mount("/static/personas", StaticFiles(directory="brain/personas"), name="personas")

class MemoryItem(BaseModel):
    key: str
    value: str

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
    """Get all memories for a specific persona"""
    try:
        memories = neo4j_graph.get_all_memories(persona_id)
        return memories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/{key}")
async def get_memory(key: str):
    """Get a specific memory by key - Placeholder"""
    raise HTTPException(status_code=501, detail="Not implemented")

@app.post("/memory")
async def set_memory(memory_item: MemoryItem):
    """Store a new memory - Placeholder"""
    raise HTTPException(status_code=501, detail="Not implemented")

@app.post("/conversation")
async def save_conversation(conversation: ConversationItem):
    """Save a conversation transcript as a memory - Placeholder"""
    raise HTTPException(status_code=501, detail="Not implemented")

@app.get("/persona/{persona_id}")
async def get_persona_brain(persona_id: str):
    """Get persona details from Neo4j"""
    try:
        state = neo4j_graph.get_persona_state(persona_id)
        return {
            "status": "success",
            "persona_id": persona_id,
            "mood": state.get("mood", "neutral"),
            "status": state.get("status", "active"),
            "characteristics": state.get("characteristics", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/personas")
async def get_all_personas():
    """Get all personas from Neo4j"""
    try:
        print("\n=== Starting get_all_personas endpoint ===")
        print("Calling neo4j_graph.get_all_personas()...")
        
        personas = neo4j_graph.get_all_personas()
        print(f"Raw personas data from Neo4j: {personas}")
        
        # Extract just the persona data and format it for the frontend
        formatted_personas = []
        for p in personas:
            print(f"\nProcessing persona data: {p}")
            persona_data = p["persona"]
            formatted_persona = {
                "id": persona_data.get("id"),
                "name": persona_data.get("name", ""),
                "profile": persona_data.get("profile", ""),
                "node_id": persona_data.get("node_id", "")
            }
            print(f"Formatted persona: {formatted_persona}")
            formatted_personas.append(formatted_persona)
        
        print(f"\nFinal formatted personas list: {formatted_personas}")
        print("=== Finished get_all_personas endpoint ===\n")
        return formatted_personas
        
    except Exception as e:
        print(f"ERROR in get_all_personas: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get personas: {str(e)}"
        )

@app.post("/init-all-personas")
async def init_all_personas():
    """Initialize all personas in Neo4j - Placeholder"""
    try:
        print("Starting persona initialization...")
        # This would be where you initialize personas in Neo4j
        # For now, just return success
        return {
            "status": "success",
            "message": "Personas initialized"
        }
    except Exception as e:
        print(f"Error initializing personas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize personas: {str(e)}"
        )

@app.post("/memory/{persona_id}")
async def store_persona_memory(persona_id: str, memory: MemoryCreate):
    """Store a memory for a specific persona - Placeholder"""
    raise HTTPException(status_code=501, detail="Not implemented")

@app.delete("/memories/{persona_id}")
async def delete_all_memories(persona_id: str):
    """Delete all memories for a specific persona - Placeholder"""
    raise HTTPException(status_code=501, detail="Not implemented")

@app.delete("/memory/{persona_id}/{memory_id}")
async def delete_memory(persona_id: str, memory_id: str):
    """Delete a specific memory from a persona - Placeholder"""
    raise HTTPException(status_code=501, detail="Not implemented")

@app.post("/memories/search")
async def search_memories(query: str, persona_id: str = "default", top_k: int = 3):
    """Search for similar memories using enhanced search"""
    try:
        memories = await parcer.enhance_memory_search(query, persona_id, top_k)
        if not memories:
            return {"memories": [], "status": "success"}
            
        # Format the response
        memory_responses = []
        for memory in memories:
            memory_responses.append({
                "content": memory["memory"]["content"],
                "timestamp": memory["memory"].get("timestamp", datetime.now().isoformat()),
                "importance": memory["memory"].get("importance", 0.5),
                "similarity": memory["similarity"],
                "topic_relevance": memory["topic_relevance"],
                "keyword_relevance": memory["keyword_relevance"],
                "final_score": memory["final_score"]
            })
            
        return {
            "memories": memory_responses,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe/local")
async def transcribe_local(audio_file: UploadFile = File(...), persona_id: str = Query("default")):
    """Transcribe audio and search for relevant memories"""
    try:
        # Read audio file
        audio_data = await audio_file.read()
        
        # Transcribe audio
        transcription = await transcription_handler.transcribe_audio(audio_data)
        
        # Search for relevant memories
        memories = await parcer.enhance_memory_search(
            query=transcription,
            persona_id=persona_id,
            top_k=3
        )
        
        # Format memory results
        search_results = ""
        if memories:
            search_results = "\n".join([
                f"Memory: {mem['memory']['content'][:200]}... "
                f"(Relevance: {mem['final_score']:.2f})"
                for mem in memories
            ])
        
        return {
            "text": transcription,
            "search_results": search_results,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
