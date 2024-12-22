import sqlite3
from typing import List, Dict, Optional
from memory import Memory, MemoryType
import json

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)

    def _create_tables(self):
        self._connect()
        with self.conn:
            # Create personas table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS personas (
                    persona_id TEXT PRIMARY KEY,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create brains table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS brains (
                    brain_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    persona_id TEXT,
                    status TEXT DEFAULT 'active',
                    mood TEXT DEFAULT 'neutral',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (persona_id) REFERENCES personas (persona_id)
                )
            """)

            # Create memories table with reference to brain
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brain_id INTEGER,
                    content TEXT,
                    vector TEXT,
                    importance REAL,
                    memory_type TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (brain_id) REFERENCES brains (brain_id)
                )
            """)

    def create_persona(self, persona_id: str, name: Optional[str] = None):
        self._connect()
        with self.conn:
            self.conn.execute("""
                INSERT OR IGNORE INTO personas (persona_id, name)
                VALUES (?, ?)
            """, (persona_id, name or persona_id))
            
            # Create default brain for persona
            self.conn.execute("""
                INSERT OR IGNORE INTO brains (persona_id)
                VALUES (?)
            """, (persona_id,))

    def get_or_create_brain_id(self, persona_id: str) -> int:
        self._connect()
        with self.conn:
            # Ensure persona exists
            self.create_persona(persona_id)
            
            # Get brain_id
            cursor = self.conn.execute("""
                SELECT brain_id FROM brains
                WHERE persona_id = ?
                LIMIT 1
            """, (persona_id,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # Create new brain if none exists
            cursor = self.conn.execute("""
                INSERT INTO brains (persona_id)
                VALUES (?)
            """, (persona_id,))
            return cursor.lastrowid

    def store_memory(self, persona_id: str, memory: Memory):
        self._connect()
        memory_dict = memory.to_dict()
        brain_id = self.get_or_create_brain_id(persona_id)
        
        with self.conn:
            self.conn.execute("""
                INSERT INTO memories 
                (brain_id, content, vector, importance, memory_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                brain_id,
                memory_dict["content"],
                json.dumps(memory_dict["vector"]),
                memory_dict["importance"],
                memory_dict["memory_type"],
                memory_dict["timestamp"]
            ))

    def get_memories(self, persona_id: str) -> List[Memory]:
        self._connect()
        brain_id = self.get_or_create_brain_id(persona_id)
        
        with self.conn:
            cursor = self.conn.execute("""
                SELECT content, vector, importance, memory_type, timestamp
                FROM memories
                WHERE brain_id = ?
                ORDER BY timestamp DESC
            """, (brain_id,))
            
            memories = []
            for row in cursor:
                memory_dict = {
                    "content": row[0],
                    "vector": json.loads(row[1]),
                    "importance": row[2],
                    "memory_type": row[3],
                    "timestamp": row[4]
                }
                memories.append(Memory.from_dict(memory_dict))
            
            return memories

    def get_brain_status(self, persona_id: str) -> Dict[str, str]:
        self._connect()
        brain_id = self.get_or_create_brain_id(persona_id)
        
        with self.conn:
            cursor = self.conn.execute("""
                SELECT status, mood
                FROM brains
                WHERE brain_id = ?
            """, (brain_id,))
            row = cursor.fetchone()
            return {
                "status": row[0],
                "mood": row[1]
            }

    def update_brain_status(self, persona_id: str, status: Optional[str] = None, mood: Optional[str] = None):
        self._connect()
        brain_id = self.get_or_create_brain_id(persona_id)
        
        updates = []
        params = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if mood is not None:
            updates.append("mood = ?")
            params.append(mood)
            
        if updates:
            with self.conn:
                self.conn.execute(f"""
                    UPDATE brains
                    SET {', '.join(updates)}
                    WHERE brain_id = ?
                """, (*params, brain_id))

    def delete_memory(self, persona_id: str, timestamp: str):
        """Delete a specific memory by its timestamp"""
        self._connect()
        brain_id = self.get_or_create_brain_id(persona_id)
        
        with self.conn:
            self.conn.execute("""
                DELETE FROM memories 
                WHERE brain_id = ? AND timestamp = ?
            """, (brain_id, timestamp))

    def clear_memories(self, persona_id: str):
        """Clear all memories for this persona"""
        self._connect()
        brain_id = self.get_or_create_brain_id(persona_id)
        
        with self.conn:
            self.conn.execute("DELETE FROM memories WHERE brain_id = ?", (brain_id,))

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None 