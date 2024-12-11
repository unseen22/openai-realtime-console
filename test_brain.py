import unittest
import os
from brain.brain import Brain
from brain.memory import Memory, MemoryType
from brain.database import Database
from datetime import datetime

class TestBrain(unittest.TestCase):
    def setUp(self):
        # Use a test database
        self.test_db_path = "test_memories.db"
        self.db = Database(self.test_db_path)
        
        # Add a test persona
        self.test_persona_id = "test_persona"
        self.db.add_persona(self.test_persona_id, "Test Persona", "test_voice")
        
        # Create brain instance for test persona
        self.brain = Brain(self.test_persona_id, self.test_db_path)

    def tearDown(self):
        # Clean up the test database
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_create_memory(self):
        # Test creating a simple memory
        content = "This is a test memory"
        memory = self.brain.create_memory(content)
        
        # Verify the memory was created correctly
        self.assertEqual(memory.content, content)
        self.assertEqual(memory.memory_type, MemoryType.CONVERSATION)
        self.assertIsInstance(memory.timestamp, datetime)
        self.assertEqual(len(memory.vector), 5)  # Based on the placeholder implementation
        
        # Verify the memory was stored in the brain
        self.assertEqual(len(self.brain.memories), 1)
        
        # Test creating a memory with different type
        summary_content = "This is a summary memory"
        summary_memory = self.brain.create_memory(summary_content, MemoryType.SUMMARY)
        self.assertEqual(summary_memory.memory_type, MemoryType.SUMMARY)
        
        # Verify both memories are stored
        self.assertEqual(len(self.brain.memories), 2)

    def test_memory_persistence(self):
        # Create a memory
        content = "Test persistence"
        self.brain.create_memory(content)
        
        # Create a new brain instance for the same persona
        new_brain = Brain(self.test_persona_id, self.test_db_path)
        
        # Verify the memory was loaded
        self.assertEqual(len(new_brain.memories), 1)
        memory = list(new_brain.memories.values())[0]
        self.assertEqual(memory.content, content)

    def test_clear_memories(self):
        # Create some memories
        self.brain.create_memory("Memory 1")
        self.brain.create_memory("Memory 2")
        self.assertEqual(len(self.brain.memories), 2)
        
        # Clear memories
        self.brain.clear_memories()
        self.assertEqual(len(self.brain.memories), 0)
        
        # Verify memories are cleared in new instance
        new_brain = Brain(self.test_persona_id, self.test_db_path)
        self.assertEqual(len(new_brain.memories), 0)

if __name__ == '__main__':
    unittest.main() 