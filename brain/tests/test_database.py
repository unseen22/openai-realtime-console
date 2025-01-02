import unittest
import os
import sqlite3
from brain.database import Database
from brain.memory import Memory, MemoryType
from datetime import datetime
import time

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "test_db_init.db"
        # Ensure clean state
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except PermissionError:
                time.sleep(0.1)  # Wait for file handle to be released
                try:
                    os.remove(self.test_db_path)
                except:
                    pass
        self.db = Database(self.test_db_path)

    def tearDown(self):
        if hasattr(self, 'db'):
            self.db.close()
        time.sleep(0.1)  # Wait for file handle to be released
        try:
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
        except:
            pass

    def test_database_structure(self):
        """Test that database has correct tables and schema"""
        # Create a new connection to avoid interfering with self.db
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        try:
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}
            
            # Verify all expected tables exist
            self.assertIn('personas', tables)
            self.assertIn('brains', tables)
            self.assertIn('memories', tables)
            
            # Check personas table structure
            cursor.execute("PRAGMA table_info(personas);")
            columns = {col[1] for col in cursor.fetchall()}
            self.assertIn('persona_id', columns)
            self.assertIn('name', columns)
            self.assertIn('created_at', columns)
            
            # Check brains table structure
            cursor.execute("PRAGMA table_info(brains);")
            columns = {col[1] for col in cursor.fetchall()}
            self.assertIn('brain_id', columns)
            self.assertIn('persona_id', columns)
            self.assertIn('status', columns)
            self.assertIn('mood', columns)
            
            # Check memories table structure
            cursor.execute("PRAGMA table_info(memories);")
            columns = {col[1] for col in cursor.fetchall()}
            self.assertIn('memory_id', columns)
            self.assertIn('brain_id', columns)
            self.assertIn('content', columns)
            self.assertIn('vector', columns)
        finally:
            cursor.close()
            conn.close()

    def test_persona_creation_and_brain_assignment(self):
        """Test creating a persona and its associated brain"""
        persona_id = "test_persona"
        name = "Test Person"
        
        # Create persona
        self.db.create_persona(persona_id, name)
        
        # Verify in database
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        try:
            # Check persona
            cursor.execute("SELECT persona_id, name FROM personas WHERE persona_id = ?", (persona_id,))
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result[0], persona_id)
            self.assertEqual(result[1], name)
            
            # Check brain was created
            cursor.execute("SELECT persona_id FROM brains WHERE persona_id = ?", (persona_id,))
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result[0], persona_id)
        finally:
            cursor.close()
            conn.close()

    def test_memory_storage_and_retrieval(self):
        """Test storing and retrieving memories for a persona"""
        persona_id = "test_persona"
        
        # Create test memory
        test_memory = Memory(
            content="Test content",
            vector=[0.1, 0.2, 0.3],
            importance=0.5,
            memory_type=MemoryType.CONVERSATION,
            timestamp=datetime.now()
        )
        
        # Store memory
        self.db.store_memory(persona_id, test_memory)
        
        # Retrieve memories
        memories = self.db.get_memories(persona_id)
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].content, "Test content")
        self.assertEqual(memories[0].importance, 0.5)

    def test_brain_status_and_mood(self):
        """Test updating and retrieving brain status and mood"""
        persona_id = "test_persona"
        
        # Check default status and mood
        status = self.db.get_brain_status(persona_id)
        self.assertEqual(status["status"], "active")
        self.assertEqual(status["mood"], "neutral")
        
        # Update status and mood
        self.db.update_brain_status(persona_id, status="thinking", mood="happy")
        
        # Verify updates
        status = self.db.get_brain_status(persona_id)
        self.assertEqual(status["status"], "thinking")
        self.assertEqual(status["mood"], "happy")

    def test_clear_memories(self):
        """Test clearing memories for a persona"""
        persona_id = "test_persona"
        
        # Create some test memories
        for i in range(3):
            memory = Memory(
                content=f"Memory {i}",
                vector=[0.1, 0.2, 0.3],
                importance=0.5,
                memory_type=MemoryType.CONVERSATION
            )
            self.db.store_memory(persona_id, memory)
        
        # Verify memories were created
        memories = self.db.get_memories(persona_id)
        self.assertEqual(len(memories), 3)
        
        # Clear memories
        self.db.clear_memories(persona_id)
        
        # Verify memories were cleared
        memories = self.db.get_memories(persona_id)
        self.assertEqual(len(memories), 0)

if __name__ == '__main__':
    unittest.main() 